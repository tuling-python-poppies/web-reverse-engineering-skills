import argparse
import json
import random
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import urljoin

import ddddocr
import requests
from PIL import Image


LOAD_URL = "https://gcaptcha4.geetest.com/load"
VERIFY_URL = "https://gcaptcha4.geetest.com/verify"
STATIC_BASE = "https://static.geetest.com/"


def callback() -> str:
    return f"geetest_{int(time.time() * 1000)}"


def parse_jsonp(text: str) -> dict:
    match = re.fullmatch(r"\s*[^(]+\((.*)\)\s*;?\s*", text, re.S)
    if not match:
        raise ValueError(f"Invalid JSONP: {text[:160]}")
    return json.loads(match.group(1))


def save_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def download_image(session: requests.Session, image_url: str, path: Path) -> bytes:
    response = session.get(urljoin(STATIC_BASE, image_url), timeout=30)
    response.raise_for_status()
    if not response.headers.get("content-type", "").startswith("image/"):
        raise ValueError(f"Expected image, got {response.headers.get('content-type')}")
    path.write_bytes(response.content)
    return response.content


def generate_w(helper: Path, bundle: Path, data: dict, captcha_id: str,
               set_left: int, passtime: int, userresponse: float) -> dict:
    payload = {
        "bundle": str(bundle.resolve()),
        "loadData": data,
        "captchaId": captcha_id,
        "setLeft": set_left,
        "passtime": passtime,
        "userresponse": userresponse,
    }
    result = subprocess.run(
        ["node", str(helper.resolve())],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"Node helper failed:\n{result.stderr}")
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description="Geetest GT4 same-round replay template")
    parser.add_argument("--captcha-id", required=True)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument(
        "--helper",
        type=Path,
        default=Path(__file__).with_name("gt4_bundle_helper.js"),
    )
    parser.add_argument("--cache-root", type=Path, default=Path.cwd() / "js_reverse_cache")
    parser.add_argument("--gap-x", type=int, help="Override OCR source-image gap x")
    parser.add_argument("--use-env-proxy", action="store_true")
    args = parser.parse_args()

    session = requests.Session()
    session.trust_env = args.use_env_proxy
    session.headers.update({
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://gt4.geetest.com/",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
        ),
    })
    load_params = {
        "callback": callback(),
        "captcha_id": args.captcha_id,
        "client_type": "web",
        "risk_type": "slide",
        "pt": "1",
        "lang": "zho",
    }
    load_response = session.get(LOAD_URL, params=load_params, timeout=30)
    load_response.raise_for_status()
    load_json = parse_jsonp(load_response.text)
    if load_json.get("status") != "success":
        raise RuntimeError(f"Load failed: {load_json}")
    data = load_json["data"]

    cache = args.cache_root / data["lot_number"]
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "load.jsonp").write_text(load_response.text, encoding="utf-8")
    save_json(cache / "load.json", load_json)
    save_json(cache / "cookies.json", requests.utils.dict_from_cookiejar(session.cookies))

    slice_bytes = download_image(session, data["slice"], cache / "slice.png")
    bg_bytes = download_image(session, data["bg"], cache / "bg.png")
    detected = ddddocr.DdddOcr(show_ad=False).slide_match(
        slice_bytes, bg_bytes, simple_target=True
    )
    target = detected.get("target")
    detected_x = int(target[0]) if target and int(target[0]) > 0 else int(detected["target_x"])
    gap_x = args.gap_x if args.gap_x is not None else detected_x
    with Image.open(cache / "bg.png") as image:
        bg_width = image.width
    scale = 0.8876 * min(bg_width, 340) / bg_width
    set_left = round((gap_x - 2) * scale)
    userresponse = set_left / scale + 2
    passtime = random.randint(900, 1600)
    save_json(cache / "image_meta.json", {
        "ocr": detected,
        "gap_x": gap_x,
        "bg_width": bg_width,
        "scale": scale,
        "setLeft": set_left,
        "userresponse": userresponse,
        "passtime": passtime,
    })

    helper_output = generate_w(
        args.helper, args.bundle, data, args.captcha_id,
        set_left, passtime, userresponse,
    )
    save_json(cache / "helper_output.json", helper_output)
    time.sleep(passtime / 1000)
    verify_params = {
        "callback": callback(),
        "captcha_id": args.captcha_id,
        "client_type": "web",
        "lot_number": data["lot_number"],
        "risk_type": data["captcha_type"],
        "payload": data["payload"],
        "process_token": data["process_token"],
        "payload_protocol": data["payload_protocol"],
        "pt": data["pt"],
        "w": helper_output["w"],
    }
    verify_response = session.get(VERIFY_URL, params=verify_params, timeout=30)
    verify_response.raise_for_status()
    verify_json = parse_jsonp(verify_response.text)
    (cache / "verify.jsonp").write_text(verify_response.text, encoding="utf-8")
    save_json(cache / "verify.json", verify_json)

    result = verify_json.get("data", {}).get("result")
    print(json.dumps({
        "cache": str(cache.resolve()),
        "lot_number": data["lot_number"],
        "gap_x": gap_x,
        "setLeft": set_left,
        "passtime": passtime,
        "w_length": len(helper_output["w"]),
        "status": verify_json.get("status"),
        "result": result,
        "fail_count": verify_json.get("data", {}).get("fail_count"),
    }, ensure_ascii=False, indent=2))
    return 0 if verify_json.get("status") == "success" and result == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
