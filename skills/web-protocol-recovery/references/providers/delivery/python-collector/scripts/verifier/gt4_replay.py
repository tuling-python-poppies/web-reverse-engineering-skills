import argparse
import base64
import binascii
import hashlib
import hmac
import json
import math
import random
import re
import struct
import time
import uuid
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import ddddocr
import requests
from PIL import Image

from gt4_runtime import (
    BudgetLedger,
    SandboxError,
    buffer_response_with_cap,
    create_exclusive_directory,
    ensure_plain_directory,
    read_plain_text,
    require_sandbox_adapter,
    require_unexpired_approval_deadline,
    route_scope_covers,
    safe_lot_cache,
    sha256_file,
    scope_allows,
    validate_cache_root,
    validate_ledger_path,
    write_new_bytes,
    write_new_json,
    write_new_text,
)


SCRIPT_DIR = Path(__file__).resolve().parent
HELPER_PATH = (
    SCRIPT_DIR.parents[3]
    / "implementation"
    / "python-node"
    / "scripts"
    / "gt4_bundle_helper.js"
)

LOAD_URL = "https://gcaptcha4.geetest.com/load"
VERIFY_URL = "https://gcaptcha4.geetest.com/verify"
STATIC_BASE = "https://static.geetest.com/"
LOAD_QUERY_KEYS = {"callback", "captcha_id", "challenge", "client_type", "risk_type", "pt", "lang"}
VERIFY_QUERY_KEYS = {
    "callback", "captcha_id", "client_type", "lot_number", "risk_type",
    "payload", "process_token", "payload_protocol", "pt", "w", "td", "td_sign",
}
RAW_ARTIFACT_FIELDS = {
    "gt4.load.jsonp", "gt4.load.json", "gt4.cookies.json",
    "gt4.slice.png", "gt4.bg.png", "gt4.gct.js", "gt4.image_meta.json",
    "gt4.helper_output.json", "gt4.track.json", "gt4.verify.jsonp", "gt4.verify.json",
}
GT4_EXACT_SCOPES = {
    ("https", "gcaptcha4.geetest.com", 443, "/load"),
    ("https", "gcaptcha4.geetest.com", 443, "/verify"),
    ("https", "static.geetest.com", 443, "/"),
}
GT4_QUERY_KEYS = {
    "/load": LOAD_QUERY_KEYS,
    "/verify": VERIFY_QUERY_KEYS,
}


def _scope_key(scope: Any) -> Optional[tuple[str, str, int, str]]:
    if not isinstance(scope, dict):
        return None
    try:
        return (
            str(scope.get("scheme", "")).lower(),
            str(scope.get("host", "")).lower(),
            int(scope.get("port", -1)),
            str(scope.get("routePrefix", "")),
        )
    except (TypeError, ValueError):
        return None

APPROVED_WORK_ORDER_ID: Optional[str] = None
APPROVED_SCOPES: List[Dict[str, Any]] = []
APPROVED_MIN_DELAY_MS = 0
APPROVED_RESPONSE_BYTE_CAP = 0
BUDGET_LEDGER: Optional[BudgetLedger] = None


def approve_live_verify(work_order: Dict[str, Any]) -> None:
    global APPROVED_WORK_ORDER_ID, APPROVED_SCOPES
    global APPROVED_MIN_DELAY_MS, APPROVED_RESPONSE_BYTE_CAP, BUDGET_LEDGER
    authorization = work_order["authorization"]
    execution_policy = authorization["executionPolicy"]
    APPROVED_WORK_ORDER_ID = work_order["workOrderId"]
    APPROVED_SCOPES = authorization["allowedHostsAndRoutes"]
    APPROVED_MIN_DELAY_MS = int(authorization["requestBudget"]["minDelayMs"])
    APPROVED_RESPONSE_BYTE_CAP = int(authorization["requestBudget"]["responseByteCap"])
    require_unexpired_approval_deadline(execution_policy.get("approvalDeadline"))
    require_sandbox_adapter(execution_policy)
    BUDGET_LEDGER = BudgetLedger.open(work_order)
    if BUDGET_LEDGER.snapshot()["remaining"] < 5:
        close_live_verify()
        raise RuntimeError("reopened GT4 budget ledger has fewer than five requests remaining")


def pack_track(track: Dict[str, Any]) -> str:
    """Pack the current slide adapter track as the documented td sidecar."""
    raw = json.dumps(track, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
    body = compressor.compress(raw) + compressor.flush()
    header = b"\x1f\x8b\x08\x00" + struct.pack("<I", int(time.time())) + b"\x02\x03"
    trailer = struct.pack("<II", binascii.crc32(raw) & 0xffffffff, len(raw) & 0xffffffff)
    return base64.urlsafe_b64encode(header + body + trailer).decode("ascii").rstrip("=")


def credential_handoff(verify_json: Dict[str, Any]) -> Dict[str, Any]:
    seccode = verify_json.get("data", {}).get("seccode")
    fields = ("captcha_output", "pass_token", "gen_time", "captcha_id", "lot_number")
    return {
        "present": isinstance(seccode, dict),
        "fields": [field for field in fields if isinstance(seccode, dict) and field in seccode],
        "values": {
            field: str(seccode[field])
            for field in fields
            if isinstance(seccode, dict) and field in seccode
        },
        "sameRound": True,
        "retention": "memory-only",
    }


def generate_track(distance: int, duration_ms: int, width: int, height: int) -> Dict[str, Any]:
    points = [[0, 0, 0, 0]]
    for index in range(1, 54):
        progress = index / 53
        x = round(distance * (1 - (1 - progress) ** 3))
        y = round(math.sin(progress * math.pi * 2) * 1.4 + random.uniform(-0.7, 0.7))
        event_type = 2 if index == 53 else 1
        points.append([round(duration_ms * progress), max(0, x), y, event_type])
    points[-1] = [duration_ms, distance, 0, 2]
    return {"m": 1, "w": width, "h": height, "s": 0, "e": 0, "p": points}


def close_live_verify() -> None:
    global BUDGET_LEDGER
    if BUDGET_LEDGER is not None:
        BUDGET_LEDGER.close()
        BUDGET_LEDGER = None


def require_live_verify_approval(target_url: str, request_timeout_ms: int) -> int:
    if BUDGET_LEDGER is None:
        raise RuntimeError(
            "live verifier request is not approved; run through main() with "
            "--confirm-live-verify and a validated immutable work order"
        )
    if not scope_allows(APPROVED_SCOPES, target_url):
        raise RuntimeError(f"live verifier request outside approved scope: {target_url}")
    reservation = BUDGET_LEDGER.begin_request(
        "request", target_url, request_timeout_ms
    )
    return int(reservation["reservationId"])


def request_timeout_ms(value: Any) -> int:
    if isinstance(value, (tuple, list)):
        values = [float(item) for item in value if item is not None]
        seconds = max(values) if values else 0
    else:
        seconds = float(value)
    if seconds <= 0:
        raise ValueError("GT4 request timeout must be positive")
    return max(1, round(seconds * 1000))


def live_get(session: requests.Session, url: str, **kwargs: Any) -> requests.Response:
    params = kwargs.pop("params", None)
    timeout = kwargs.pop("timeout", None)
    if kwargs:
        raise ValueError(f"unsupported GT4 live request options: {', '.join(sorted(kwargs))}")
    if timeout is None:
        raise ValueError("GT4 live request timeout is required")
    prepared = session.prepare_request(requests.Request("GET", url, params=params))
    if not prepared.url:
        raise ValueError("GT4 live request has no prepared URL")
    reservation_id = require_live_verify_approval(
        prepared.url, request_timeout_ms(timeout)
    )
    try:
        settings = session.merge_environment_settings(
            prepared.url, {}, stream=None, verify=None, cert=None
        )
        response = session.send(
            prepared, timeout=timeout, allow_redirects=False, **settings
        )
        response = buffer_response_with_cap(response, APPROVED_RESPONSE_BYTE_CAP)
        if response.is_redirect or 300 <= int(response.status_code) < 400:
            location = response.headers.get("location", "")
            raise RuntimeError(f"live verifier redirect denied without explicit work-order hop: {location}")
        return response
    finally:
        if BUDGET_LEDGER is not None:
            BUDGET_LEDGER.finish_request(reservation_id)


def callback() -> str:
    return f"geetest_{int(time.time() * 1000)}"


def parse_jsonp(text: str) -> Dict[str, Any]:
    match = re.fullmatch(r"\s*[^(]+\((.*)\)\s*;?\s*", text, re.S)
    if not match:
        raise ValueError(f"Invalid JSONP: {text[:160]}")
    value = json.loads(match.group(1))
    if not isinstance(value, dict):
        raise ValueError("GT4 JSONP payload must be an object")
    return value


def validate_work_order(path: Path, cache_root: Path, bundle: Path) -> Dict[str, Any]:
    try:
        work_order = json.loads(read_plain_text(path))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"cannot read work order {path}: {error}") from error
    active = work_order.get("activeProvider") or {}
    authorization = work_order.get("authorization") or {}
    budget = authorization.get("requestBudget") or {}
    scopes = authorization.get("allowedHostsAndRoutes") or []
    artifact_policy = authorization.get("artifactPolicy") or {}
    execution_policy = authorization.get("executionPolicy") or {}
    project = work_order.get("project") or {}

    errors: List[str] = []
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
    if authorization.get("actionApproval") not in {
        "standing-verifier-submit",
        "user-confirmed-mutation",
    }:
        errors.append("authorization.actionApproval must authorize verifier-submit")
    try:
        remaining_budget = int(budget.get("remaining", 0))
        total_budget = int(budget.get("total", -1))
    except (TypeError, ValueError):
        remaining_budget = 0
        total_budget = -1
    if remaining_budget < 5:
        errors.append("authorization.requestBudget.remaining must be at least 5")
    if total_budget < remaining_budget:
        errors.append("authorization.requestBudget.total must be at least remaining")
    try:
        response_byte_cap = int(budget.get("responseByteCap", 0))
    except (TypeError, ValueError):
        response_byte_cap = 0
    if response_byte_cap < 1:
        errors.append("authorization.requestBudget.responseByteCap must be positive")
    if project.get("writeMode") != "modify-allowlisted":
        errors.append("GT4 durable budget ledger requires project.writeMode=modify-allowlisted")
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
    if artifact_policy.get("rawSecretHandling") != "confirmed":
        errors.append("authorization.artifactPolicy.rawSecretHandling must be confirmed for GT4 cookies and raw responses")
    if execution_policy.get("targetCodeExecution") != "approved-reviewed-hash":
        errors.append("authorization.executionPolicy.targetCodeExecution must be approved-reviewed-hash")
    if not execution_policy.get("approvalEvidence") or execution_policy.get("approvalEvidence") == "none":
        errors.append("authorization.executionPolicy.approvalEvidence is required")
    if not execution_policy.get("approvalDeadline") or execution_policy.get("approvalDeadline") == "none":
        errors.append("authorization.executionPolicy.approvalDeadline is required")
    approved_hashes = set(map(str, execution_policy.get("approvedCodeSha256") or []))
    try:
        if sha256_file(bundle) not in approved_hashes:
            errors.append("--bundle sha256 is not approved")
        if sha256_file(HELPER_PATH) not in approved_hashes:
            errors.append("GT4 helper sha256 is not approved")
        require_unexpired_approval_deadline(execution_policy.get("approvalDeadline"))
        require_sandbox_adapter(execution_policy)
        validate_cache_root(project, cache_root)
        validate_ledger_path(work_order)
    except (OSError, RuntimeError, SandboxError, ValueError) as error:
        errors.append(str(error))
    scope_keys = {key for scope in scopes if (key := _scope_key(scope)) is not None}
    if scope_keys != GT4_EXACT_SCOPES:
        errors.append("allowedHostsAndRoutes must contain exactly the GT4 /load and /verify scopes")
    for scope in scopes:
        if not isinstance(scope, dict):
            errors.append("allowedHostsAndRoutes entries must be objects")
            continue
        if str(scope.get("host", "")).lower() == "gcaptcha4.geetest.com":
            prefix = scope.get("routePrefix")
            policy = scope.get("queryPolicy") or {}
            if prefix not in GT4_QUERY_KEYS:
                errors.append("gcaptcha4.geetest.com scope must target /load or /verify exactly")
            elif policy.get("mode") != "allow-listed" or set(policy.get("allowedKeys") or []) != GT4_QUERY_KEYS[prefix]:
                errors.append(f"GT4 {prefix} query policy must be the exact allow-listed key set")
    if not route_scope_covers(scopes, LOAD_URL, LOAD_QUERY_KEYS):
        errors.append(f"allowedHostsAndRoutes missing load scope/query policy for {LOAD_URL}")
    if not route_scope_covers(scopes, VERIFY_URL, VERIFY_QUERY_KEYS):
        errors.append(f"allowedHostsAndRoutes missing verify scope/query policy for {VERIFY_URL}")
    if not route_scope_covers(scopes, STATIC_BASE, set()):
        errors.append(f"allowedHostsAndRoutes missing static scope/query policy for {STATIC_BASE}")
    if not work_order.get("acceptanceTest"):
        errors.append("acceptanceTest is required")
    if errors:
        raise ValueError("invalid GT4 work order: " + "; ".join(errors))
    return work_order


def download_text(session: requests.Session, source_url: str, path: Path) -> str:
    response = live_get(session, urljoin(STATIC_BASE, source_url), timeout=30)
    response.raise_for_status()
    write_new_text(path, response.text)
    return response.text


def download_image(session: requests.Session, image_url: str, path: Path) -> bytes:
    response = live_get(session, urljoin(STATIC_BASE, image_url), timeout=30)
    response.raise_for_status()
    if not response.headers.get("content-type", "").startswith("image/"):
        raise ValueError(f"Expected image, got {response.headers.get('content-type')}")
    write_new_bytes(path, response.content)
    return response.content


def generate_w(
    bundle_source: str,
    data: Dict[str, Any],
    captcha_id: str,
    gct_source: str,
    set_left: int,
    passtime: int,
    userresponse: float,
) -> Dict[str, Any]:
    raise SandboxError(
        "GT4 target-JS replay is disabled until a reviewed capability-denied sandbox adapter is bundled"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Geetest GT4 same-round replay template")
    parser.add_argument("--captcha-id", required=True)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=Path.cwd() / "js_reverse_cache" / "source" / "geetest_gt4",
    )
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
        cache_root = validate_cache_root(work_order["project"], args.cache_root)
        bundle_source = read_plain_text(args.bundle)
        approve_live_verify(work_order)
    except (OSError, RuntimeError, SandboxError, ValueError) as error:
        parser.error(str(error))

    try:
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
            "challenge": str(uuid.uuid4()),
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
        if data.get("captcha_type") != "slide" or not data.get("bg") or not data.get("slice"):
            raise RuntimeError("GT4 slider template requires captcha_type=slide with bg and slice")

        ensure_plain_directory(cache_root, create=True)
        cache = create_exclusive_directory(safe_lot_cache(cache_root, data["lot_number"]))
        write_new_text(cache / "load.jsonp", load_response.text)
        write_new_json(cache / "load.json", load_json)
        write_new_json(cache / "cookies.json", requests.utils.dict_from_cookiejar(session.cookies))

        slice_bytes = download_image(session, data["slice"], cache / "slice.png")
        bg_bytes = download_image(session, data["bg"], cache / "bg.png")
        gct_source = download_text(session, data["gct_path"], cache / "gct.js")
        detected = ddddocr.DdddOcr(show_ad=False).slide_match(
            slice_bytes, bg_bytes, simple_target=True
        )
        target = detected.get("target")
        detected_x = int(target[0]) if target and int(target[0]) > 0 else int(detected["target_x"])
        gap_x = args.gap_x if args.gap_x is not None else detected_x
        with Image.open(cache / "bg.png") as image:
            bg_width = image.width
            bg_height = image.height
        set_left = max(0, round(gap_x - 44))
        userresponse = set_left + 1 + random.random()
        passtime = random.randint(900, 1600)
        write_new_json(cache / "image_meta.json", {
            "ocr": detected,
            "gap_x": gap_x,
            "bg_width": bg_width,
            "scale": 1,
            "setLeft": set_left,
            "userresponse": userresponse,
            "passtime": passtime,
        })

        helper_output = generate_w(
            bundle_source,
            data,
            args.captcha_id,
            gct_source,
            set_left,
            passtime,
            userresponse,
        )
        write_new_json(cache / "helper_output.json", helper_output)
        track = generate_track(set_left, passtime, bg_width, bg_height)
        td = pack_track(track)
        td_sign = hmac.new(
            data["lot_number"].encode("utf-8"), td.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        write_new_json(cache / "track.json", {"track": track, "td": td, "td_sign": td_sign})
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
            "td": td,
            "td_sign": td_sign,
        }
        verify_response = live_get(session, VERIFY_URL, params=verify_params, timeout=30)
        verify_response.raise_for_status()
        verify_json = parse_jsonp(verify_response.text)
        write_new_text(cache / "verify.jsonp", verify_response.text)
        write_new_json(cache / "verify.json", verify_json)

        result = verify_json.get("data", {}).get("result")
        budget = BUDGET_LEDGER.snapshot() if BUDGET_LEDGER is not None else {}
        print(json.dumps({
            "cache": str(cache.resolve()),
            "workOrderId": APPROVED_WORK_ORDER_ID,
            "requestBudget": budget,
            "lot_number": data["lot_number"],
            "gap_x": gap_x,
            "setLeft": set_left,
            "passtime": passtime,
            "w_length": len(helper_output["w"]),
            "status": verify_json.get("status"),
            "result": result,
            "fail_count": verify_json.get("data", {}).get("fail_count"),
            "credentialHandoff": credential_handoff(verify_json),
        }, ensure_ascii=False, indent=2))
        return 0 if (
            verify_json.get("status") == "success"
            and result == "success"
            and verify_json.get("data", {}).get("fail_count") == 0
        ) else 1
    finally:
        close_live_verify()


if __name__ == "__main__":
    raise SystemExit(main())
