from __future__ import annotations

import base64
import csv
import hashlib
import json
import random
import re
import string
import time
from datetime import datetime
from pathlib import Path
from typing import Any


APP_ID = "2088b"
APPID = "jd-cphdeveloper-m"
FUNCTION_ID = "recommend_like_m"
PAGE_URL = "https://m.jd.com/"
API_URL = "https://api.m.jd.com/api"
REQUEST_ALGO_URL = "https://cactus.jd.com/request_algo?g_ty=ajax"
H5ST_VERSION = "5.3"
FILE_VERSION = "h5_file_v5.3.4"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/150.0.0.0 Safari/537.36"
)

JD_SE_ALPHABET = "nLvT3b-jHrPzX7fD"
JD_B64_ALPHABET = "rqponmlkjihgfedcbaZYXWVUTSRQPONMLKJIHGFEDCBA-_9876543210zyxwvuts"
STD_B64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
APPEND_SALT = "RvI<7|"
ENV_TAIL = "of7rHGHQ8GlOIyVOF6ZNHuFT-bVR7qUT"
RANDOM_CHARS = string.ascii_letters + string.digits + "-_"


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def build_body(*, page: int = 1, page_count: int = 20, start_pos: int | None = None) -> str:
    if page < 1:
        raise ValueError("page must be >= 1")
    if page_count < 1:
        raise ValueError("page_count must be >= 1")
    if start_pos is None:
        start_pos = (page - 1) * page_count
    inner = {
        "pagenum": page,
        "pagecount": page_count,
        "startpos": start_pos,
        "ptag": "",
        "sku": "",
        "cid1": "",
        "cid2": "",
        "cid3": "",
    }
    outer = {
        "func": "item_rec",
        "recpos": 6163,
        "param": compact_json(inner),
        "clientPageId": "",
        "clientVersion": "2.0",
    }
    return compact_json(outer)


def body_sha256(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def now_ms() -> int:
    return int(time.time() * 1000)


def random_text(length: int) -> str:
    return "".join(random.choice(RANDOM_CHARS) for _ in range(length))


def jd_se_data(text: str) -> str:
    bucket_size = len(text) // 6
    suffix = []
    offset = 0
    for index in range(6):
        if index < 5:
            chunk = text[offset : offset + bucket_size]
            offset += bucket_size
        else:
            chunk = text[offset:]
        suffix.append(JD_SE_ALPHABET[sum(ord(char) for char in chunk) & 0xF])
    return text + "".join(suffix)


def jd_hash_bytes(text: str) -> bytes:
    return (jd_se_data(text) + APPEND_SALT).encode("utf-8")


def jd_md5(text: str) -> str:
    return hashlib.md5(jd_hash_bytes(text)).hexdigest()


def jd_sha256(text: str) -> str:
    return hashlib.sha256(jd_hash_bytes(text)).hexdigest()


def jd_base64_encode(text: str) -> str:
    raw = text.encode("utf-8")
    encoded = base64.b64encode(raw).decode("ascii").rstrip("=")
    mapped = "".join(JD_B64_ALPHABET[STD_B64_ALPHABET.index(char)] for char in encoded)
    return {0: "of7r", 1: "pj", 2: "q"}[len(raw) % 3] + mapped[::-1]


def h5st_datetime(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y%m%d%H%M%S") + str(timestamp_ms)[-3:]


def request_algo(*, session: Any | None = None) -> dict[str, Any]:
    from curl_cffi import requests  # type: ignore

    if session is None:
        session = requests.Session(impersonate="chrome")
    fp = random_text(16).lower()
    payload = {
        "version": H5ST_VERSION,
        "fp": fp,
        "appId": APP_ID,
        "timestamp": now_ms(),
        "platform": "web",
        "expandParams": "",
        "fv": FILE_VERSION,
        "localTk": "",
    }
    headers = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Origin": "https://m.jd.com",
        "Referer": PAGE_URL,
    }
    response = session.post(REQUEST_ALGO_URL, json=payload, headers=headers, timeout=30)
    if response.status_code != 200 or not response.content:
        raise RuntimeError(f"request_algo failed status={response.status_code}")
    data = response.json()
    result = ((data.get("data") or {}).get("result") or {}) if isinstance(data, dict) else {}
    algo = str(result.get("algo") or "")
    match = re.search(r"var\s+rd=['\"]([^'\"]+)['\"]", algo)
    if not result.get("tk") or not match:
        raise RuntimeError(f"unexpected request_algo response: {data!r}")
    return {
        "source": "live",
        "tk": str(result["tk"]),
        "fp": str(result.get("fp") or fp),
        "algoTs": str((data.get("data") or {}).get("ts") or payload["timestamp"]),
        "rd": match.group(1),
    }


def build_env_segment(
    fp: str,
    timestamp_ms: int,
    *,
    random_values: tuple[str, str, str] | None = None,
) -> str:
    if random_values is None:
        extend_random, random_value, bu14 = random_text(11), random_text(10), random_text(10)
    else:
        extend_random, random_value, bu14 = random_values
    env = {
        "sua": "Windows NT 10.0; Win64; x64",
        "pp": {},
        "extend": {
            "wd": 0,
            "l": 0,
            "ls": 5,
            "wk": 0,
            "bu1": "0.1.9",
            "bu3": 27,
            "bu4": 0,
            "bu5": 0,
            "bu6": 3,
            "bu7": 0,
            "bu8": 0,
            "random": extend_random,
            "bu12": -8,
            "bu10": 14,
            "bu11": 4,
        },
        "pf": "Win32",
        "random": random_value,
        "v": FILE_VERSION,
        "bu4": "0",
        "canvas": jd_md5(""),
        "webglFp": "",
        "ccn": 8,
        "bu14": bu14,
        "t": timestamp_ms,
        "fp": fp,
    }
    return jd_base64_encode(compact_json(env))


def sign_h5st(
    body: str,
    material: dict[str, Any],
    *,
    timestamp_ms: int | None = None,
    env_timestamp_ms: int | None = None,
    env_random_values: tuple[str, str, str] | None = None,
) -> tuple[str, dict[str, str]]:
    timestamp_ms = now_ms() if timestamp_ms is None else timestamp_ms
    env_timestamp_ms = timestamp_ms - random.randint(1, 9) if env_timestamp_ms is None else env_timestamp_ms
    tk = str(material["tk"])
    fp = str(material["fp"])
    rd = str(material["rd"])
    sign_time = h5st_datetime(timestamp_ms)
    body_hash = body_sha256(body)
    sign_key = jd_sha256(f"{tk}{fp}{sign_time}54{APP_ID}{rd}")
    sign_str = f"appid:{APPID}&body:{body_hash}&functionId:{FUNCTION_ID}"
    signature = jd_sha256(f"{sign_key}{sign_str}{sign_key}")
    env = build_env_segment(fp, env_timestamp_ms, random_values=env_random_values)
    env_digest = jd_sha256(f"{sign_key}appid:appid&functionid:functionId{sign_key}")
    h5st = ";".join(
        [
            sign_time,
            fp,
            APP_ID,
            tk,
            signature,
            H5ST_VERSION,
            str(timestamp_ms),
            env,
            env_digest,
            ENV_TAIL,
        ]
    )
    return h5st, {"bodySha256": body_hash, "signKey": sign_key, "signature": signature}


def fetch_products(body: str, h5st: str, *, session: Any | None = None) -> tuple[dict[str, Any], bytes]:
    from curl_cffi import requests  # type: ignore

    if session is None:
        session = requests.Session(impersonate="chrome")
    headers = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Origin": "https://m.jd.com",
        "Referer": PAGE_URL,
        "x-referer-page": PAGE_URL,
        "x-rp-client": "h5_1.0.0",
    }
    params = {
        "appid": APPID,
        "functionId": FUNCTION_ID,
        "body": body,
        "h5st": h5st,
        "x-api-eid-token": "",
        "loginType": "2",
    }
    response = session.get(API_URL, headers=headers, params=params, timeout=30)
    if response.status_code != 200 or not response.content:
        raise RuntimeError(f"JD API failed status={response.status_code} bytes={len(response.content)}")
    return response.json(), response.content


def parse_products(payload: dict[str, Any]) -> list[dict[str, Any]]:
    content = (((payload.get("data") or {}).get("feeds") or {}).get("content") or [])
    products = []
    for item in content:
        if not isinstance(item, dict):
            continue
        sku = item.get("id")
        name = item.get("name")
        if not sku and not name:
            continue
        ext = item.get("ext") if isinstance(item.get("ext"), dict) else {}
        products.append(
            {
                "sku": str(sku) if sku is not None else "",
                "name": str(name or ""),
                "price": str(item.get("price") or item.get("jdPrice") or item.get("oriprice") or ""),
                "jdPrice": str(item.get("jdPrice") or ""),
                "oriprice": str(item.get("oriprice") or ""),
                "link": str(item.get("link") or ""),
                "img": f"{item.get('imgprefix') or ''}{item.get('imgbase') or ''}",
                "cate1": ext.get("cate1") if ext else None,
                "cate2": ext.get("cate2") if ext else None,
                "cate3": ext.get("cate3") if ext else None,
                "shopId": ext.get("shopId") if ext else None,
                "brandId": ext.get("brandId") if ext else None,
            }
        )
    return products


def write_products_csv(products: list[dict[str, Any]], path: str | Path) -> None:
    with Path(path).open("w", newline="", encoding="utf-8-sig") as handle:
        fieldnames = [
            "sku",
            "name",
            "price",
            "jdPrice",
            "oriprice",
            "link",
            "img",
            "cate1",
            "cate2",
            "cate3",
            "shopId",
            "brandId",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(products)


def run(*, live: bool = False, page: int = 1, page_count: int = 20) -> dict[str, Any]:
    body = build_body(page=page, page_count=page_count)
    if not live:
        return {
            "status": "offline-proof",
            "bodySha256": body_sha256(body),
            "jdSha256Abc": jd_sha256("abc"),
            "jdBase64Abc": jd_base64_encode("abc"),
        }
    from curl_cffi import requests  # type: ignore

    session = requests.Session(impersonate="chrome")
    material = request_algo(session=session)
    h5st, sign_meta = sign_h5st(body, material)
    payload, raw = fetch_products(body, h5st, session=session)
    products = parse_products(payload)
    return {
        "status": "success",
        "runtime": "pure-python",
        "httpStatus": 200,
        "responseBytes": len(raw),
        "productCount": len(products),
        "bodySha256": sign_meta["bodySha256"],
        "h5stLength": len(h5st),
        "h5stPrefix": h5st[:48],
        "products": products,
    }


if __name__ == "__main__":
    print(json.dumps(run(live=False), ensure_ascii=False, indent=2))
