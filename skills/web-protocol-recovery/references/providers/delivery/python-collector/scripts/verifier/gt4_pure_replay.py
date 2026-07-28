import argparse
import hashlib
import json
import math
import random
import re
import secrets
import time
from pathlib import Path
from urllib.parse import parse_qsl, urljoin, urlparse

import ddddocr
import requests
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad
from PIL import Image


LOAD_URL = "https://gcaptcha4.geetest.com/load"
VERIFY_URL = "https://gcaptcha4.geetest.com/verify"
STATIC_BASE = "https://static.geetest.com/"
LOAD_QUERY_KEYS = {"callback", "captcha_id", "client_type", "risk_type", "lang"}
VERIFY_QUERY_KEYS = {
    "callback", "captcha_id", "client_type", "lot_number", "risk_type",
    "payload", "process_token", "payload_protocol", "pt", "w",
}
RAW_ARTIFACT_FIELDS = {
    "gt4.load.jsonp", "gt4.load.json", "gt4.cookies.json",
    "gt4.slice.png", "gt4.bg.png", "gt4.gct.raw.js", "gt4.trace.json",
    "gt4.image_meta.json", "gt4.pure_output.json", "gt4.verify.jsonp", "gt4.verify.json",
}
LIVE_VERIFY_APPROVED = False
APPROVED_WORK_ORDER_ID = None
APPROVED_SCOPES = []
APPROVED_BUDGET_REMAINING = 0


def approve_live_verify(work_order):
    global LIVE_VERIFY_APPROVED, APPROVED_WORK_ORDER_ID, APPROVED_SCOPES, APPROVED_BUDGET_REMAINING
    authorization = work_order["authorization"]
    LIVE_VERIFY_APPROVED = True
    APPROVED_WORK_ORDER_ID = work_order["workOrderId"]
    APPROVED_SCOPES = authorization["allowedHostsAndRoutes"]
    APPROVED_BUDGET_REMAINING = int(authorization["requestBudget"]["remaining"])


def require_live_verify_approval(target_url):
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


def live_get(session, url, **kwargs):
    target_url = prepared_get_url(url, kwargs.get("params"))
    require_live_verify_approval(target_url)
    kwargs.setdefault("allow_redirects", False)
    response = session.get(url, **kwargs)
    if response.is_redirect:
        location = response.headers.get("location", "")
        raise RuntimeError(f"live verifier redirect denied without explicit work-order hop: {location}")
    return response


RSA_N_HEX = (
    "c1e3934d1614465b33053e7f48ee4ec87b14b95ef88947713d25eecbff7e74c"
    "7977d02dc1d9451f79dd5d1c10c29acb6a9b4d6fb7d0a0279b6719e1772565f"
    "09af627715919221aef91899cae08c0d686d748b20a3603be2318ca6bc2b597"
    "06592a9219d0bf05c9f65023a21d2330807252ae0066d59ceefa5f2748ea80bab81"
)
RSA_E = 65537
GEE_GUARD = {
    "roe": {"aup": "3", "sep": "3", "egp": "3", "auh": "3",
            "rew": "3", "snh": "3", "res": "3", "cdc": "3"},
}
EM = {"ph": 0, "cp": 0, "ek": "11", "wd": 1, "nt": 0, "si": 0, "sc": 0}


def callback():
    return f"geetest_{int(time.time() * 1000)}"


def parse_jsonp(text):
    match = re.fullmatch(r"\s*[^(]+\((.*)\)\s*;?\s*", text, re.S)
    if not match:
        raise ValueError(f"Invalid JSONP: {text[:160]}")
    return json.loads(match.group(1))


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def prepared_get_url(url, params):
    prepared = requests.Request("GET", url, params=params).prepare()
    return prepared.url or url


def query_policy_allows(scope, parsed_query):
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


def scope_matches_route(scope, target_url):
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


def scope_allows(scopes, target_url):
    parsed = urlparse(target_url)
    for scope in scopes:
        if scope_matches_route(scope, target_url) and query_policy_allows(scope, parsed.query):
            return True
    return False


def query_policy_covers(scope, required_keys):
    policy = scope.get("queryPolicy")
    if not isinstance(policy, dict):
        return False
    mode = policy.get("mode")
    if mode == "allow-all":
        return True
    if mode == "deny":
        return not required_keys
    if mode == "allow-listed":
        return set(required_keys) <= set(policy.get("allowedKeys") or [])
    return False


def route_scope_covers(scopes, target_url, required_query_keys):
    return any(
        scope_matches_route(scope, target_url) and query_policy_covers(scope, required_query_keys)
        for scope in scopes
    )


def absolute_under(path, parent):
    try:
        path.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def validate_cache_root(project, cache_root):
    errors = []
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


def safe_lot_cache(cache_root, lot_number):
    lot = str(lot_number or "")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", lot) or lot in {".", ".."}:
        raise ValueError(f"unsafe lot_number for cache path: {lot!r}")
    cache = cache_root / lot
    if not absolute_under(cache, cache_root):
        raise ValueError(f"lot_number escapes cache root: {lot!r}")
    return cache


def validate_work_order(path, cache_root):
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
    if work_order.get("schemaVersion") != "web-protocol-recovery-provider-work-order/v2":
        errors.append("schemaVersion must be web-protocol-recovery-provider-work-order/v2")
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
    if execution_policy.get("targetCodeExecution") != "blocked":
        errors.append("authorization.executionPolicy.targetCodeExecution must be blocked for pure replay")
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


def decode_uri_bytes(value):
    reserved = b";/?:@&=+$,#"
    result = bytearray()
    index = 0
    while index < len(value):
        if value[index] == "%" and index + 2 < len(value):
            decoded = int(value[index + 1:index + 3], 16)
            if decoded in reserved:
                result.extend(value[index:index + 3].encode("ascii"))
            else:
                result.append(decoded)
            index += 3
        else:
            result.extend(value[index].encode("utf-8"))
            index += 1
    return bytes(result)


def decode_string_table(source):
    encoded_match = re.search(r"decodeURI\((['\"])(.*?)\1\)", source)
    if not encoded_match:
        raise ValueError("String table was not found")
    tail = source[encoded_match.end():encoded_match.end() + 3000]
    key_match = re.search(r"\}\((['\"])(.*?)\1\)\s*\n?\s*\}", tail)
    if not key_match:
        raise ValueError("String-table XOR key was not found")
    encoded = decode_uri_bytes(encoded_match.group(2))
    key = key_match.group(2).encode("latin1")
    decoded = bytes(value ^ key[index % len(key)] for index, value in enumerate(encoded))
    return decoded.decode("latin1").split("^")


def extract_bundle_metadata(bundle_path):
    source = bundle_path.read_text(encoding="utf-8")
    strings = decode_string_table(source)
    lot_match = re.search(
        r'["\'](n\[[^"\']+)["\']\s*:\s*[^\n]*?\((\d+)\)', source
    )
    region_start = max(0, lot_match.start() - 3000) if lot_match else 0
    metadata_region = source[region_start:lot_match.end() + 500] if lot_match else ""
    fixed_match = re.search(
        r'\]\s*=\s*\{\s*([A-Za-z_$][A-Za-z0-9_$]*):\s*[^\n]*?\((\d+)\)\s*\}',
        metadata_region,
    )
    if not fixed_match or not lot_match:
        raise ValueError("Current bundle metadata initialization was not recognized")
    return (
        {fixed_match.group(1): strings[int(fixed_match.group(2))]},
        {lot_match.group(1): strings[int(lot_match.group(2))]},
    )


def resolve_lot_expression(expression, lot_number):
    def replace(match):
        start, end = map(int, match.groups())
        return lot_number[start:end + 1]

    return re.sub(r"n\[(\d+):(\d+)\]", replace, expression).replace("+", "")


def resolve_lot_fields(lot_number, rules):
    result = {}
    for key_expression, value_expression in rules.items():
        path = resolve_lot_expression(key_expression, lot_number).split(".")
        value = resolve_lot_expression(value_expression, lot_number)
        target = result
        for key in path[:-1]:
            target = target.setdefault(key, {})
        target[path[-1]] = value
    return result


def extract_function(source, start):
    brace = source.find("{", start)
    if brace < 0:
        raise ValueError("Function opening brace was not found")
    depth = 0
    quote = None
    escaped = False
    for index in range(brace, len(source)):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in "'\"`":
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise ValueError("Function closing brace was not found")


def int32(value):
    value &= 0xFFFFFFFF
    return value if value < 0x80000000 else value - 0x100000000


def js_5381_hash(value):
    state = 5381
    utf16 = value.encode("utf-16-le", "surrogatepass")
    for index in range(0, len(utf16), 2):
        code_unit = int.from_bytes(utf16[index:index + 2], "little")
        state = int32(state) * 33 + code_unit
    return int32(state) & 0x7FFFFFFF


def calculate_biht(gct_source):
    marker = gct_source.find("=5381;")
    if marker < 0:
        raise ValueError("GCT 5381 hash function was not found")
    hash_start = gct_source.rfind("function ", 0, marker)
    if hash_start < 0:
        raise ValueError("GCT hash function start was not found")
    hash_source = extract_function(gct_source, hash_start)
    hash_end = hash_start + len(hash_source)
    guard_match = re.search(r"function\s+\w+\(\w+\)\{", gct_source[hash_end:])
    if not guard_match:
        raise ValueError("GCT guard function was not found")
    guard_source = extract_function(gct_source, hash_end + guard_match.start())
    suffix = decode_string_table(gct_source)[78]
    return str(js_5381_hash(guard_source + str(js_5381_hash(hash_source)))) + suffix


def solve_pow(captcha_id, lot_number, detail):
    hashfunc = detail["hashfunc"].lower()
    if hashfunc != "sha256":
        raise ValueError(f"Unsupported PoW hash: {hashfunc}")
    prefix = "|".join([
        str(detail["version"]), str(detail["bits"]), hashfunc,
        detail["datetime"], captcha_id, lot_number, "",
    ]) + "|"
    target = 1 << (256 - int(detail["bits"]))
    while True:
        message = prefix + secrets.token_hex(8)
        digest = hashlib.sha256(message.encode()).hexdigest()
        if int(digest, 16) < target:
            return {"pow_msg": message, "pow_sign": digest}


def generate_trace(distance, duration_ms):
    count = max(28, min(60, duration_ms // 24))
    points = [[0, 0, 0]]
    last_x = 0
    for index in range(1, count):
        progress = index / (count - 1)
        x = max(last_x, min(distance, round(distance * (1 - (1 - progress) ** 3))))
        y = round(math.sin(progress * math.pi * 2) * 1.4 + random.uniform(-0.7, 0.7))
        if x != last_x or index == count - 1:
            points.append([x, y, round(duration_ms * progress)])
            last_x = x
    points[-1] = [distance, 0, duration_ms]
    return points


def replay_trace_timing(trace):
    started = time.perf_counter()
    for _, _, timestamp in trace[1:]:
        remaining = timestamp / 1000 - (time.perf_counter() - started)
        if remaining > 0:
            time.sleep(remaining)


def encrypt_w(payload, pt):
    compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if str(pt) != "1":
        raise ValueError(f"Pure Python implementation supports pt=1, got {pt}")
    aes_key = secrets.token_hex(8).encode()
    aes_hex = AES.new(aes_key, AES.MODE_CBC, b"0000000000000000").encrypt(
        pad(compact.encode(), AES.block_size)
    ).hex()
    public_key = RSA.construct((int(RSA_N_HEX, 16), RSA_E))
    rsa_hex = PKCS1_v1_5.new(public_key).encrypt(aes_key).hex()
    return aes_hex + rsa_hex, compact


def download(session, url):
    response = live_get(session, urljoin(STATIC_BASE, url), timeout=30)
    response.raise_for_status()
    return response


def main():
    parser = argparse.ArgumentParser(description="Pure Python Geetest GT4 protocol replay")
    parser.add_argument("--captcha-id", required=True)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--cache-root", type=Path, default=Path.cwd() / "js_reverse_cache" / "source" / "geetest_gt4")
    parser.add_argument("--gap-x", type=int)
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
        help="Validated web-protocol-recovery-provider-work-order/v2 JSON.",
    )
    args = parser.parse_args()
    if not args.confirm_live_verify:
        parser.error(
            "--confirm-live-verify is required; copy/adapt this template into an approved "
            "project and record liveReplay/verifier gates before execution"
        )
    try:
        work_order = validate_work_order(args.work_order, args.cache_root)
    except ValueError as error:
        parser.error(str(error))
    approve_live_verify(work_order)

    fixed_fields, lot_rules = extract_bundle_metadata(args.bundle)
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
    load_response = live_get(session, LOAD_URL, params={
        "callback": callback(), "captcha_id": args.captcha_id,
        "client_type": "web", "risk_type": "slide", "lang": "zh",
    }, timeout=30)
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

    slice_response = download(session, data["slice"])
    bg_response = download(session, data["bg"])
    if not slice_response.headers.get("content-type", "").startswith("image/"):
        raise ValueError("Slice response is not an image")
    if not bg_response.headers.get("content-type", "").startswith("image/"):
        raise ValueError("Background response is not an image")
    (cache / "slice.png").write_bytes(slice_response.content)
    (cache / "bg.png").write_bytes(bg_response.content)
    detected = ddddocr.DdddOcr(show_ad=False).slide_match(
        slice_response.content, bg_response.content, simple_target=True
    )
    target = detected.get("target")
    detected_x = int(target[0]) if target and int(target[0]) > 0 else int(detected["target_x"])
    gap_x = args.gap_x if args.gap_x is not None else detected_x
    with Image.open(cache / "bg.png") as image:
        bg_width = image.width
    scale = 0.8876 * min(bg_width, 340) / bg_width
    set_left = round((gap_x - 2) * scale)
    userresponse = set_left / scale + 2
    passtime = random.randint(950, 1650)
    trace = generate_trace(set_left, passtime)

    gct_response = download(session, data["gct_path"])
    gct_source = gct_response.text
    (cache / "gct.raw.js").write_text(gct_source, encoding="utf-8")
    biht = calculate_biht(gct_source)
    pow_data = solve_pow(args.captcha_id, data["lot_number"], data["pow_detail"])
    w_payload = {
        "setLeft": set_left, "passtime": passtime, "userresponse": userresponse,
        "device_id": "", "lot_number": data["lot_number"], **pow_data,
        "geetest": "captcha", "lang": "zh", "ep": "123", "biht": biht,
        "gee_guard": GEE_GUARD, **fixed_fields,
        **resolve_lot_fields(data["lot_number"], lot_rules), "em": EM,
    }
    w, compact = encrypt_w(w_payload, str(data["pt"]))
    save_json(cache / "trace.json", trace)
    save_json(cache / "image_meta.json", {
        "ocr": detected, "gap_x": gap_x, "bg_width": bg_width,
        "scale": scale, "setLeft": set_left, "userresponse": userresponse,
        "passtime": passtime, "trace_points": len(trace),
    })
    save_json(cache / "pure_output.json", {
        "w": w, "wPayload": w_payload, "compact": compact,
        "fixedFields": fixed_fields, "lotRules": lot_rules,
    })
    replay_trace_timing(trace)

    verify_response = live_get(session, VERIFY_URL, params={
        "callback": callback(), "captcha_id": args.captcha_id,
        "client_type": "web", "lot_number": data["lot_number"],
        "risk_type": data["captcha_type"], "payload": data["payload"],
        "process_token": data["process_token"],
        "payload_protocol": data["payload_protocol"], "pt": data["pt"], "w": w,
    }, timeout=30)
    verify_response.raise_for_status()
    verify_json = parse_jsonp(verify_response.text)
    (cache / "verify.jsonp").write_text(verify_response.text, encoding="utf-8")
    save_json(cache / "verify.json", verify_json)
    result = verify_json.get("data", {}).get("result")
    print(json.dumps({
        "runtime": "pure-python", "cache": str(cache.resolve()),
        "workOrderId": APPROVED_WORK_ORDER_ID,
        "budgetRemaining": APPROVED_BUDGET_REMAINING,
        "lot_number": data["lot_number"], "gap_x": gap_x, "setLeft": set_left,
        "passtime": passtime, "trace_points": len(trace), "biht": biht,
        "fixed_fields": fixed_fields, "lot_rules": lot_rules,
        "w_length": len(w), "status": verify_json.get("status"),
        "result": result, "fail_count": verify_json.get("data", {}).get("fail_count"),
    }, ensure_ascii=False, indent=2))
    return 0 if verify_json.get("status") == "success" and result == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
