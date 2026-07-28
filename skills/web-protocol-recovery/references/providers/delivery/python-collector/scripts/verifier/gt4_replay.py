import argparse
import hashlib
import json
import random
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import parse_qsl, urljoin, urlparse

import ddddocr
import requests
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent

LOAD_URL = "https://gcaptcha4.geetest.com/load"
VERIFY_URL = "https://gcaptcha4.geetest.com/verify"
STATIC_BASE = "https://static.geetest.com/"
LOAD_QUERY_KEYS = {"callback", "captcha_id", "client_type", "risk_type", "pt", "lang"}
VERIFY_QUERY_KEYS = {
    "callback", "captcha_id", "client_type", "lot_number", "risk_type",
    "payload", "process_token", "payload_protocol", "pt", "w",
}
RAW_ARTIFACT_FIELDS = {
    "gt4.load.jsonp", "gt4.load.json", "gt4.cookies.json",
    "gt4.slice.png", "gt4.bg.png", "gt4.gct.js", "gt4.image_meta.json",
    "gt4.helper_output.json", "gt4.verify.jsonp", "gt4.verify.json",
}
LIVE_VERIFY_APPROVED = False
APPROVED_WORK_ORDER_ID = None
APPROVED_SCOPES: list[dict] = []
APPROVED_BUDGET_REMAINING = 0
APPROVED_CODE_SHA256: set[str] = set()


def approve_live_verify(work_order: dict) -> None:
    global LIVE_VERIFY_APPROVED, APPROVED_WORK_ORDER_ID, APPROVED_SCOPES, APPROVED_BUDGET_REMAINING, APPROVED_CODE_SHA256
    authorization = work_order["authorization"]
    execution_policy = authorization["executionPolicy"]
    LIVE_VERIFY_APPROVED = True
    APPROVED_WORK_ORDER_ID = work_order["workOrderId"]
    APPROVED_SCOPES = authorization["allowedHostsAndRoutes"]
    APPROVED_BUDGET_REMAINING = int(authorization["requestBudget"]["remaining"])
    APPROVED_CODE_SHA256 = set(execution_policy.get("approvedCodeSha256", []))


def require_live_verify_approval(target_url: str) -> None:
    global APPROVED_BUDGET_REMAINING
    if not LIVE_VERIFY_APPROVED:
        raise RuntimeError(
            "live verifier request is not approved; run through main() with "
            "--confirm-live-verify and --work-order after recording liveReplay/verifier gates"
        )
    if not scope_allows(APPROVED_SCOPES, target_url):
        raise RuntimeError(f"live verifier request outside approved scope: {target_url}")
    if APPROVED_BUDGET_REMAINING <= 0:
        raise RuntimeError(f"live verifier request budget exhausted before: {target_url}")
    APPROVED_BUDGET_REMAINING -= 1


def live_get(session: requests.Session, url: str, **kwargs) -> requests.Response:
    target_url = prepared_get_url(url, kwargs.get("params"))
    require_live_verify_approval(target_url)
    # Force-closed: callers cannot re-enable redirects to skip hop-by-hop scope/budget checks.
    kwargs["allow_redirects"] = False
    response = session.get(url, **kwargs)
    if response.is_redirect or 300 <= int(response.status_code) < 400:
        location = response.headers.get("location", "")
        raise RuntimeError(f"live verifier redirect denied without explicit work-order hop: {location}")
    return response


def callback() -> str:
    return f"geetest_{int(time.time() * 1000)}"


def parse_jsonp(text: str) -> dict:
    match = re.fullmatch(r"\s*[^(]+\((.*)\)\s*;?\s*", text, re.S)
    if not match:
        raise ValueError(f"Invalid JSONP: {text[:160]}")
    return json.loads(match.group(1))


def save_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def prepared_get_url(url: str, params: object | None) -> str:
    prepared = requests.Request("GET", url, params=params).prepare()
    return prepared.url or url


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_approved_source(name: str, source: str) -> None:
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if digest not in APPROVED_CODE_SHA256:
        raise RuntimeError(f"{name} sha256 is not approved for target-code execution: {digest}")


def query_policy_allows(scope: dict, parsed_query: str) -> bool:
    policy = scope.get("queryPolicy")
    if not isinstance(policy, dict):
        return False
    pairs = parse_qsl(parsed_query, keep_blank_values=True)
    mode = policy.get("mode")
    if mode == "deny":
        return not pairs
    if mode == "allow-all":
        return True
    if mode != "allow-listed":
        return False
    allowed_keys = set(policy.get("allowedKeys") or [])
    allowed_values = policy.get("allowedValues") or {}
    for key, value in pairs:
        if key not in allowed_keys:
            return False
        if key in allowed_values and value not in set(map(str, allowed_values[key])):
            return False
    return True


def scope_matches_route(scope: dict, target_url: str) -> bool:
    parsed = urlparse(target_url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    prefix = scope.get("routePrefix") or "/"
    if not prefix.startswith("/"):
        return False
    try:
        scope_port = int(scope.get("port", -1))
    except (TypeError, ValueError):
        return False
    return (
        scope.get("scheme") == parsed.scheme
        and str(scope.get("host", "")).lower() == parsed.hostname
        and scope_port == port
        and (path == prefix or path.startswith(prefix.rstrip("/") + "/"))
    )


def scope_allows(scopes: list[dict], target_url: str) -> bool:
    parsed = urlparse(target_url)
    for scope in scopes:
        if scope_matches_route(scope, target_url) and query_policy_allows(scope, parsed.query):
            return True
    return False


def query_policy_covers(scope: dict, required_keys: set[str]) -> bool:
    policy = scope.get("queryPolicy")
    if not isinstance(policy, dict):
        return False
    mode = policy.get("mode")
    if mode == "allow-all":
        return True
    if mode == "deny":
        return not required_keys
    if mode == "allow-listed":
        return required_keys <= set(policy.get("allowedKeys") or [])
    return False


def route_scope_covers(scopes: list[dict], target_url: str, required_query_keys: set[str]) -> bool:
    return any(
        scope_matches_route(scope, target_url) and query_policy_covers(scope, required_query_keys)
        for scope in scopes
    )


def absolute_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def validate_cache_root(project: dict, cache_root: Path) -> list[str]:
    errors: list[str] = []
    project_root = Path(str(project.get("projectRoot") or ""))
    if not project_root.is_absolute():
        return ["project.projectRoot must be absolute"]
    cache_root = cache_root if cache_root.is_absolute() else (Path.cwd() / cache_root)
    allowed_paths = project.get("allowedPaths") or []
    if not absolute_under(cache_root, project_root):
        errors.append("--cache-root must stay under project.projectRoot")
    allowed_roots = []
    for item in allowed_paths:
        candidate = Path(str(item))
        allowed_roots.append(candidate if candidate.is_absolute() else project_root / candidate)
    if not allowed_roots or not any(absolute_under(cache_root, allowed) for allowed in allowed_roots):
        errors.append("--cache-root must stay under one project.allowedPaths entry")
    for ancestor in [cache_root, *cache_root.parents]:
        if not ancestor.exists() or ancestor == ancestor.parent:
            continue
        if ancestor.is_symlink():
            errors.append(f"--cache-root ancestor must not be symlink: {ancestor}")
            break
    return errors


def safe_lot_cache(cache_root: Path, lot_number: object) -> Path:
    lot = str(lot_number or "")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", lot) or lot in {".", ".."}:
        raise ValueError(f"unsafe lot_number for cache path: {lot!r}")
    cache = cache_root / lot
    if not absolute_under(cache, cache_root):
        raise ValueError(f"lot_number escapes cache root: {lot!r}")
    return cache


def validate_work_order(path: Path, cache_root: Path, bundle: Path) -> dict:
    try:
        work_order = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read work order {path}: {error}") from error
    active = work_order.get("activeProvider") or {}
    authorization = work_order.get("authorization") or {}
    budget = authorization.get("requestBudget") or {}
    scopes = authorization.get("allowedHostsAndRoutes") or []
    artifact_policy = authorization.get("artifactPolicy") or {}
    execution_policy = authorization.get("executionPolicy") or {}
    project = work_order.get("project") or {}

    errors = []
    if not work_order.get("workOrderId"):
        errors.append("workOrderId is required")
    if work_order.get("schemaVersion") != "web-protocol-recovery-provider-work-order":
        errors.append("schemaVersion must be web-protocol-recovery-provider-work-order")
    if work_order.get("gateFamily") != "verifier":
        errors.append("gateFamily must be verifier")
    if active.get("id") != "python-collector" or active.get("role") != "delivery":
        errors.append("activeProvider must be python-collector with role=delivery")
    if work_order.get("protocolOwner") != "verifier":
        errors.append("protocolOwner must be verifier")
    if work_order.get("deliveryProvider") != "python-collector":
        errors.append("deliveryProvider must be python-collector")
    if authorization.get("liveReplayAllowed") is not True:
        errors.append("authorization.liveReplayAllowed must be true")
    if authorization.get("actionClass") != "verifier-submit":
        errors.append("authorization.actionClass must be verifier-submit")
    try:
        remaining_budget = int(budget.get("remaining", 0))
    except (TypeError, ValueError):
        remaining_budget = 0
    if remaining_budget < 5:
        errors.append("authorization.requestBudget.remaining must be at least 5")
    try:
        total_budget = int(budget.get("total", budget.get("maxRequests", -1)))
    except (TypeError, ValueError):
        total_budget = -1
    if total_budget < 0:
        errors.append("authorization.requestBudget.total or maxRequests is required")
    elif remaining_budget > total_budget:
        errors.append("authorization.requestBudget.remaining cannot exceed total/maxRequests")
    write_mode = str(project.get("writeMode") or "")
    if write_mode not in {"create-only", "modify-allowlisted"}:
        errors.append("project.writeMode must allow cache writes (create-only or modify-allowlisted)")
    if project.get("projectRoot") in {None, "", "none"}:
        errors.append("project.projectRoot must be an absolute project path for live GT4")
    if artifact_policy.get("repositoryExcluded") is not True:
        errors.append("authorization.artifactPolicy.repositoryExcluded must be true")
    if artifact_policy.get("mode") == "metadata-only":
        errors.append("authorization.artifactPolicy.mode must allow approved raw GT4 artifacts")
    approved_raw = set(map(str, artifact_policy.get("approvedRawFields") or []))
    missing_raw = sorted(RAW_ARTIFACT_FIELDS - approved_raw)
    if missing_raw:
        errors.append("authorization.artifactPolicy.approvedRawFields missing: " + ", ".join(missing_raw))
    if not artifact_policy.get("retentionDeadline") or artifact_policy.get("retentionDeadline") == "none":
        errors.append("authorization.artifactPolicy.retentionDeadline is required for raw GT4 artifacts")
    if execution_policy.get("targetCodeExecution") != "approved-reviewed-hash":
        errors.append("authorization.executionPolicy.targetCodeExecution must be approved-reviewed-hash")
    approved_hashes = set(map(str, execution_policy.get("approvedCodeSha256") or []))
    if not bundle.is_file():
        errors.append(f"--bundle must be a file: {bundle}")
    else:
        bundle_hash = sha256_file(bundle)
        if bundle_hash not in approved_hashes:
            errors.append(f"--bundle sha256 is not approved: {bundle_hash}")
    if not route_scope_covers(scopes, LOAD_URL, LOAD_QUERY_KEYS):
        errors.append(f"allowedHostsAndRoutes missing load scope/query policy for {LOAD_URL}")
    if not route_scope_covers(scopes, VERIFY_URL, VERIFY_QUERY_KEYS):
        errors.append(f"allowedHostsAndRoutes missing verify scope/query policy for {VERIFY_URL}")
    if not route_scope_covers(scopes, STATIC_BASE, set()):
        errors.append(f"allowedHostsAndRoutes missing static scope/query policy for {STATIC_BASE}")
    errors.extend(validate_cache_root(project, cache_root))
    if not work_order.get("acceptanceTest"):
        errors.append("acceptanceTest is required")
    if errors:
        raise ValueError("invalid GT4 work order: " + "; ".join(errors))
    return work_order


def download_text(session: requests.Session, source_url: str, path: Path) -> str:
    response = live_get(session, urljoin(STATIC_BASE, source_url), timeout=30)
    response.raise_for_status()
    path.write_text(response.text, encoding="utf-8")
    return response.text


def download_image(session: requests.Session, image_url: str, path: Path) -> bytes:
    response = live_get(session, urljoin(STATIC_BASE, image_url), timeout=30)
    response.raise_for_status()
    if not response.headers.get("content-type", "").startswith("image/"):
        raise ValueError(f"Expected image, got {response.headers.get('content-type')}")
    path.write_bytes(response.content)
    return response.content


def generate_w(helper: Path, bundle: Path, data: dict, captcha_id: str,
               gct_source: str,
               set_left: int, passtime: int, userresponse: float) -> dict:
    payload = {
        "bundle": str(bundle.resolve()),
        "loadData": data,
        "captchaId": captcha_id,
        "gctSource": gct_source,
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
        default=(SCRIPT_DIR.parents[3]
                 / "implementation" / "python-node" / "scripts" / "gt4_bundle_helper.js"),
    )
    parser.add_argument("--cache-root", type=Path, default=Path.cwd() / "js_reverse_cache" / "source" / "geetest_gt4")
    parser.add_argument("--gap-x", type=int, help="Override OCR source-image gap x")
    parser.add_argument("--use-env-proxy", action="store_true")
    parser.add_argument(
        "--confirm-live-verify",
        action="store_true",
        help="Required because this template calls Geetest /load and /verify.",
    )
    parser.add_argument(
        "--work-order",
        required=True,
        type=Path,
        help="Validated web-protocol-recovery-provider-work-order JSON.",
    )
    args = parser.parse_args()
    if not args.confirm_live_verify:
        parser.error(
            "--confirm-live-verify is required; copy/adapt this template into an approved "
            "project and record liveReplay/verifier gates before execution"
        )
    try:
        work_order = validate_work_order(args.work_order, args.cache_root, args.bundle)
    except ValueError as error:
        parser.error(str(error))
    approve_live_verify(work_order)

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
    load_response = live_get(session, LOAD_URL, params=load_params, timeout=30)
    load_response.raise_for_status()
    load_json = parse_jsonp(load_response.text)
    if load_json.get("status") != "success":
        raise RuntimeError(f"Load failed: {load_json}")
    data = load_json["data"]

    cache = safe_lot_cache(args.cache_root, data["lot_number"])
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "load.jsonp").write_text(load_response.text, encoding="utf-8")
    save_json(cache / "load.json", load_json)
    save_json(cache / "cookies.json", requests.utils.dict_from_cookiejar(session.cookies))

    slice_bytes = download_image(session, data["slice"], cache / "slice.png")
    bg_bytes = download_image(session, data["bg"], cache / "bg.png")
    gct_source = download_text(session, data["gct_path"], cache / "gct.js")
    require_approved_source("gct.js", gct_source)
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
        gct_source,
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
    verify_response = live_get(session, VERIFY_URL, params=verify_params, timeout=30)
    verify_response.raise_for_status()
    verify_json = parse_jsonp(verify_response.text)
    (cache / "verify.jsonp").write_text(verify_response.text, encoding="utf-8")
    save_json(cache / "verify.json", verify_json)

    result = verify_json.get("data", {}).get("result")
    print(json.dumps({
        "cache": str(cache.resolve()),
        "workOrderId": APPROVED_WORK_ORDER_ID,
        "budgetRemaining": APPROVED_BUDGET_REMAINING,
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
