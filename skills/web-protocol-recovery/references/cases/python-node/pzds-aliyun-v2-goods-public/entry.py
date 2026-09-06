"""Reusable PZDS Aliyun Captcha V2 primitives.

Importing this module performs no network traffic and writes no files. Live
collectors should combine these helpers with current project login session and
FeiLin profile state selected through `pull_live_state.py`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
import uuid
import zlib
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import quote


PZDS_ORIGIN = "https://www.pzds.com"
GOODS_PAGE_URL = "https://api.pzds.com/api/web-client/v2/public/goodsPublic/page"
PZDS_VERSION = "26.731.2023"
PZDS_SIGN_VERSION = "v18"
PZDS_CHANNEL_INFO = '{"channelCode":null,"tag":null,"channelType":null,"searchWord":"null","adExtras":"","urlParam":""}'
DEVICE_AES_IV = b"0123456789ABCDEF"
DEVICE_TOKEN_SALT = "daye,raolewoba!"
DEVICE_CONFIG_KEY = "87f879f135f27da7"
DEVICE_UPLOAD_KEY = "a549a55c60a39aa0"
DEVICE_APP_NAME = "saf-captcha-waf"
DEVICE_APP_VERSION = "W20220202"
DEVICE_API_VERSION = "2020-10-15"
STREAM_KEY_DEFAULT = "3e627e1b4c63f913"
SUPPORTED_DEVICE_FIELD_COUNTS = frozenset({111, 133, 142})


class TargetCodeExecutionError(RuntimeError):
    """Target JS/WASM needs an explicit controlled python-node runner."""


def _require_target_runner(runner: Any) -> Any:
    if not callable(runner):
        raise TargetCodeExecutionError(
            "target JS/WASM execution is blocked; use an approved python-node provider runner"
        )
    return runner


def approved_target_runner(
    work_order: Mapping[str, Any],
    asset_hashes: Mapping[str, str],
    adapter: Any,
) -> Any:
    """Bind a narrow artifact adapter to a current execution approval.

    The adapter owns the actual capability-denied process. This case helper only
    validates the approval envelope and forwards two named artifact operations.
    """
    authorization = work_order.get("authorization") or {}
    policy = authorization.get("executionPolicy") or {}
    if policy.get("targetCodeExecution") != "approved-reviewed-hash":
        raise TargetCodeExecutionError("target-code execution is not approved")
    deadline = policy.get("approvalDeadline")
    try:
        expires = datetime.fromisoformat(str(deadline).replace("Z", "+00:00"))
    except (TypeError, ValueError) as error:
        raise TargetCodeExecutionError("target-code approval deadline is invalid") from error
    if expires.tzinfo is None or expires <= datetime.now(timezone.utc):
        raise TargetCodeExecutionError("target-code approval deadline is expired")
    approved_hashes = set(map(str, policy.get("approvedCodeSha256") or []))
    if not asset_hashes or not set(asset_hashes.values()) <= approved_hashes:
        raise TargetCodeExecutionError("target-code asset hash is not approved")
    sandbox = policy.get("sandbox") or {}
    required_sandbox = {
        "backend", "adapterId", "adapterSha256", "capabilityEvidence", "timeoutMs", "outputByteCap"
    }
    if not required_sandbox <= set(sandbox) or sandbox.get("backend") != "capability-denied-external":
        raise TargetCodeExecutionError("a reviewed capability-denied sandbox is required")
    if not hasattr(adapter, "execute") or not callable(adapter.execute):
        raise TargetCodeExecutionError("approved target runner adapter is missing execute()")

    def run(operation: str, payload: Mapping[str, Any]) -> Any:
        if operation not in {"data_builder", "pzds_wasm_sign"}:
            raise TargetCodeExecutionError(f"unsupported PZDS target operation: {operation}")
        return adapter.execute(operation, dict(payload), sandbox)

    return run


def build_goods_page_body(page: int = 1, page_size: int = 10) -> bytes:
    payload = {
        "order": "ASC",
        "sort": None,
        "page": page,
        "pageSize": page_size,
        "action": {
            "gameId": "7",
            "merchantMark": None,
            "keywords": [],
            "searchWords": [],
            "searchPropertyIds": [],
            "recommendSearchConfigIds": [],
            "unionGameIds": [],
            "goodsSearchActions": [],
            "metas": {"single1": []},
            "goodsCatalogueId": 6,
            "goodsSubCatalogueIds": [],
            "countFlag": False,
            "conditionSearch": False,
        },
    }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def percent_encode(value: Any) -> str:
    return quote(str(value), safe="-_.~")


def canonical_query(params: Mapping[str, Any]) -> str:
    return "&".join(
        f"{percent_encode(key)}={percent_encode(value)}"
        for key, value in sorted(params.items())
        if key != "Signature"
    )


def sign_rpc(params: Mapping[str, Any], secret: str, method: str = "POST") -> str:
    canonical = canonical_query(params)
    material = f"{method.upper()}&%2F&{percent_encode(canonical)}"
    digest = hmac.new(f"{secret}&".encode(), material.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def rpc_base_params(action: str, access_key_id: str, version: str) -> dict[str, str]:
    return {
        "AccessKeyId": access_key_id,
        "SignatureMethod": "HMAC-SHA1",
        "SignatureVersion": "1.0",
        "Format": "JSON",
        "Version": version,
        "Action": action,
        "SignatureNonce": str(uuid.uuid4()),
    }


def build_field21(
    local_suffix: str,
    source_key: str,
    xor_mask: bytes,
    algorithm: str | None = None,
) -> str:
    if len(local_suffix) != 8 or any(ch not in "0123456789abcdef" for ch in local_suffix):
        raise ValueError("local_suffix must be 8 lowercase hexadecimal chars")
    if algorithm == "feilin142":
        return build_field21_feilin142(local_suffix)
    if algorithm is not None:
        raise ValueError(f"unknown field21 algorithm {algorithm!r}")
    mixed = bytes(
        32 + ((ord(source) - 32 + ord(suffix) - 32) % 95)
        for source, suffix in zip(source_key, local_suffix)
    )
    return base64.b64encode(bytes(value ^ mask for value, mask in zip(mixed, xor_mask))).decode("ascii")


def build_field21_feilin142(local_suffix: str) -> str:
    """FeiLin142 field21: lookup maps for positions 0..3 and digit maps."""
    if len(local_suffix) != 8 or any(ch not in "0123456789abcdef" for ch in local_suffix):
        raise ValueError("local_suffix must be 8 lowercase hexadecimal chars")
    lookup = (
        (5, 4, 7, 6, 1, 0, 3, 2, 13, 12, 101, 104, 103, 98, 97, 100),
        (2, 3, 0, 1, 6, 7, 4, 5, 10, 11, 55, 52, 53, 58, 59, 56),
        (3, 2, 1, 0, 7, 6, 5, 4, 11, 10, 104, 103, 102, 109, 108, 107),
        (99, 100, 97, 98, 103, 104, 101, 102, 107, 108, 3, 0, 1, 6, 7, 4),
    )
    out = bytearray()
    for pos, char in enumerate(local_suffix):
        nibble = int(char, 16)
        if pos < 4:
            out.append(lookup[pos][nibble])
        elif not char.isdigit():
            raise ValueError(f"feilin142 position {pos} currently only supports digits")
        elif pos == 4:
            out.append(nibble ^ 3)
        elif pos == 5:
            out.append(nibble)
        elif pos == 6:
            out.append(55 + (nibble ^ 5))
        elif pos == 7:
            out.append(nibble ^ 6)
        else:
            raise AssertionError("unreachable")
    return base64.b64encode(bytes(out)).decode("ascii")


@dataclass(frozen=True)
class DeviceToken:
    platform: str
    session_id: str
    payload: str
    counter: int
    checksum: str


def _aes_cbc_encrypt(plaintext: bytes, key: str) -> str:
    from Crypto.Cipher import AES

    padding = 16 - len(plaintext) % 16
    padded = plaintext + bytes([padding]) * padding
    encrypted = AES.new(key.encode("utf-8"), AES.MODE_CBC, DEVICE_AES_IV).encrypt(padded)
    return base64.b64encode(encrypted).decode()


def _aes_cbc_decrypt(ciphertext: str, key: str) -> bytes:
    from Crypto.Cipher import AES

    plaintext = AES.new(key.encode("utf-8"), AES.MODE_CBC, DEVICE_AES_IV).decrypt(
        base64.b64decode(ciphertext, validate=True)
    )
    padding = plaintext[-1]
    if padding < 1 or padding > 16 or plaintext[-padding:] != bytes([padding]) * padding:
        raise ValueError("invalid AES PKCS7 padding")
    return plaintext[:-padding]


def parse_device_token(token: str) -> DeviceToken:
    outer = base64.b64decode(token, validate=True).decode("utf-8")
    platform, session_id, payload, counter_text, checksum = outer.split("#")
    return DeviceToken(platform, session_id, payload, int(counter_text), checksum)


def device_token_checksum(platform: str, session_id: str, payload: str, counter: int) -> str:
    return hashlib.md5(
        f"{platform}#{session_id}#{payload}#{counter}#{DEVICE_TOKEN_SALT}".encode()
    ).hexdigest()


def build_device_token(session_id: str, payload_plaintext: str, counter: int, encryption_key: str) -> str:
    payload = _aes_cbc_encrypt(payload_plaintext.encode("utf-8"), encryption_key)
    checksum = device_token_checksum("WEB", session_id, payload, counter)
    return base64.b64encode(f"WEB#{session_id}#{payload}#{counter}#{checksum}".encode()).decode()


def decrypt_device_payload(token: str | DeviceToken, encryption_key: str) -> str:
    parsed = parse_device_token(token) if isinstance(token, str) else token
    return _aes_cbc_decrypt(parsed.payload, encryption_key).decode("utf-8")


def password_md5(password: str) -> str:
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def build_oauth_password_body(username: str, password: str) -> bytes:
    payload = {
        "username": username,
        "password": password_md5(password),
        "scope": "openid",
        "grant_type": "password",
    }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def pzds_wasm_sign(
    body: bytes,
    method: str = "post",
    timestamp: str | None = None,
    random_value: str | None = None,
    runner: Any = None,
) -> dict[str, str]:
    request = {"dataJson": body.decode("utf-8"), "method": method.lower()}
    if timestamp is not None:
        request["timestamp"] = str(timestamp)
    if random_value is not None:
        request["random"] = str(random_value)
    output = _require_target_runner(runner)("pzds_wasm_sign", request)
    if not isinstance(output, dict):
        raise ValueError("approved target runner must return an object")
    return {
        "Sign": str(output["sign"]),
        "PZTimestamp": str(output["timestamp"]),
        "Random": str(output["random"]),
    }


def pzds_signed_headers(
    body: bytes,
    user_agent: str,
    device_id: str,
    global_id: str,
    *,
    token: str | None = None,
    pz_id: str | None = None,
    target_runner: Any = None,
) -> dict[str, str]:
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN",
        "content-type": "application/json",
        "origin": PZDS_ORIGIN,
        "referer": f"{PZDS_ORIGIN}/",
        "user-agent": user_agent,
        "PZOs": "windows",
        "PZPlatform": "pc",
        "PZVersion": PZDS_VERSION,
        "PZVersionCode": "1",
        "Skey": "CLIENT",
        "X-Sign-Version": PZDS_SIGN_VERSION,
        "channelInfo": PZDS_CHANNEL_INFO,
        "deviceId": device_id,
        "globalId": global_id,
    }
    if token:
        headers["token"] = token
    if pz_id:
        headers["PZid"] = str(pz_id)
    headers.update(pzds_wasm_sign(body, runner=target_runner))
    return headers


def parse_challenge_html(html: str) -> dict[str, Any]:
    marker = "var requestInfo = "
    required = {"sceneId", "traceid", "token", "userId", "userUserId"}
    for start in reversed([idx for idx in range(len(html)) if html.startswith(marker, idx)]):
        payload, _ = json.JSONDecoder().raw_decode(html[start + len(marker) :].lstrip())
        if isinstance(payload, dict) and not required.difference(payload):
            return payload
    raise ValueError("challenge HTML has no usable requestInfo JSON")


def build_business_url(target: str, gateway_token: str, certify_id: str, refer: str | None = None) -> str:
    from urllib.parse import quote as urlquote
    from urllib.parse import unquote, urlsplit, urlunsplit

    parts = urlsplit(target)
    remove_keys = {"u_aref", "u_asig", "u_atoken", "decode__1174"}
    query_parts = [
        item
        for item in parts.query.split("&")
        if item and unquote(item.split("=", 1)[0]) not in remove_keys
    ]
    query_parts.extend(
        [
            f"u_atoken={urlquote(gateway_token, safe='')}",
            f"u_asig={urlquote(certify_id, safe='')}",
        ]
    )
    if refer:
        query_parts.append(f"u_aref={urlquote(refer, safe='')}")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "&".join(query_parts), parts.fragment))


def decode_original_body(request_info: Mapping[str, Any], fallback: bytes | None = None) -> bytes:
    encoded = request_info.get("data")
    if not isinstance(encoded, str) or not encoded:
        return fallback if fallback is not None else b"{}"
    return base64.b64decode(encoded, validate=True)


def classify_business_response(status_code: int, content_type: str, body: bytes) -> dict[str, Any]:
    text = body.decode("utf-8", errors="replace")
    is_challenge = "html" in content_type.lower() and "var requestInfo = " in text
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    return {
        "statusCode": status_code,
        "contentType": content_type,
        "isCaptchaChallenge": is_challenge,
        "jsonType": type(payload).__name__ if payload is not None else None,
        "success": payload.get("success") if isinstance(payload, dict) else None,
        "code": payload.get("code") if isinstance(payload, dict) else None,
        "recordsCount": (
            len(payload.get("data", {}).get("records", []))
            if isinstance(payload, dict) and isinstance(payload.get("data"), dict)
            else None
        ),
    }


@dataclass(frozen=True)
class DeviceConfig:
    encryption_key: str
    switch: int
    session_id: str
    version: str
    plugin_elements: str
    plugin_resource: str
    global_variable: str
    timestamp: int
    ip: str


def parse_device_config(blob: str) -> DeviceConfig:
    """Decrypt the server-issued FeiLin DeviceConfig envelope."""
    try:
        plaintext = _aes_cbc_decrypt(blob, DEVICE_CONFIG_KEY).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("DeviceConfig plaintext is not UTF-8") from exc
    fields = plaintext.split("#")
    if len(fields) < 9:
        raise ValueError("DeviceConfig must contain at least nine fields")

    def decode_field(index: int) -> str:
        if not fields[index]:
            return ""
        try:
            return base64.b64decode(fields[index], validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError(f"DeviceConfig field {index} is not UTF-8 Base64") from exc

    key = decode_field(0)
    if len(key.encode("utf-8")) != 16:
        raise ValueError("DeviceConfig encryption key must be 16 bytes")
    try:
        switch = int(decode_field(1))
        timestamp = int(fields[7])
    except ValueError as exc:
        raise ValueError("DeviceConfig switch/timestamp is not decimal") from exc
    return DeviceConfig(
        encryption_key=key,
        switch=switch,
        session_id=fields[2],
        version=fields[3],
        plugin_elements=decode_field(4),
        plugin_resource=decode_field(5),
        global_variable=decode_field(6),
        timestamp=timestamp,
        ip=fields[8],
    )


def build_device_config_blob(config: DeviceConfig) -> str:
    fields = [
        base64.b64encode(config.encryption_key.encode("utf-8")).decode(),
        base64.b64encode(str(config.switch).encode("ascii")).decode(),
        config.session_id,
        config.version,
        base64.b64encode(config.plugin_elements.encode("utf-8")).decode(),
        base64.b64encode(config.plugin_resource.encode("utf-8")).decode(),
        base64.b64encode(config.global_variable.encode("utf-8")).decode(),
        str(config.timestamp),
        config.ip,
    ]
    return _aes_cbc_encrypt("#".join(fields).encode("utf-8"), DEVICE_CONFIG_KEY)


def build_device_log_record(
    config: DeviceConfig,
    payload_plaintext: str,
    *,
    timestamp_ms: int,
    device_platform: str,
) -> str:
    """Build one FeiLin 501/504/511 telemetry record envelope."""
    if timestamp_ms < 0:
        raise ValueError("timestamp_ms must be non-negative")
    fields = [
        config.session_id,
        _aes_cbc_encrypt(payload_plaintext.encode("utf-8"), config.encryption_key),
        _aes_cbc_encrypt(DEVICE_APP_NAME.encode("utf-8"), config.encryption_key),
        _aes_cbc_encrypt(device_platform.encode("utf-8"), config.encryption_key),
        "",
        _aes_cbc_encrypt(str(timestamp_ms).encode("ascii"), config.encryption_key),
    ]
    return base64.b64encode("#".join(fields).encode("utf-8")).decode()


def build_device_log_data(
    config: DeviceConfig,
    scene_id: str,
    event_data: str,
    *,
    gather_cost_ms: int,
    device_platform: str,
) -> str:
    """Wrap telemetry records in the FeiLin Log2/Log3 upload cipher."""
    if not scene_id:
        raise ValueError("scene_id must not be empty")
    if gather_cost_ms < 0:
        raise ValueError("gather_cost_ms must be non-negative")
    session_prefix = config.session_id.split("-", 1)[0]
    if len(session_prefix) != 32:
        raise ValueError("DeviceConfig session prefix must be 32 characters")
    scene_binding = _aes_cbc_encrypt(
        f"{device_platform}#{DEVICE_APP_NAME}#{scene_id}".encode("utf-8"),
        config.encryption_key,
    )
    plaintext = "#".join([
        session_prefix,
        "W",
        scene_binding,
        DEVICE_APP_VERSION,
        "CLOUD",
        str(gather_cost_ms),
        event_data,
    ])
    return _aes_cbc_encrypt(plaintext.encode("utf-8"), DEVICE_UPLOAD_KEY)


def build_log2_data(
    config: DeviceConfig,
    scene_id: str,
    full_device_fields: list[str],
    *,
    gather_cost_ms: int,
    timestamp_ms: int,
    device_platform: str,
) -> str:
    if len(full_device_fields) not in SUPPORTED_DEVICE_FIELD_COUNTS:
        raise ValueError(
            "Log2 device profile must contain one of the supported field counts "
            f"{sorted(SUPPORTED_DEVICE_FIELD_COUNTS)}"
        )
    record = build_device_log_record(
        config,
        "#".join(full_device_fields),
        timestamp_ms=timestamp_ms,
        device_platform=device_platform,
    )
    return build_device_log_data(
        config,
        scene_id,
        f"501#{record}",
        gather_cost_ms=gather_cost_ms,
        device_platform=device_platform,
    )


def build_log3_data(
    config: DeviceConfig,
    scene_id: str,
    combat_511: str,
    combat_504: dict[str, Any],
    *,
    gather_cost_ms: int,
    timestamp_ms: int,
    device_platform: str,
) -> str:
    record_511 = build_device_log_record(
        config,
        combat_511,
        timestamp_ms=timestamp_ms,
        device_platform=device_platform,
    )
    record_504 = build_device_log_record(
        config,
        json.dumps(combat_504, ensure_ascii=False, separators=(",", ":")),
        timestamp_ms=timestamp_ms + 1,
        device_platform=device_platform,
    )
    combat_data = base64.b64encode(
        f"511#{record_511}-504#{record_504}".encode("utf-8")
    ).decode()
    return build_device_log_data(
        config,
        scene_id,
        combat_data,
        gather_cost_ms=gather_cost_ms,
        device_platform=device_platform,
    )


def make_verify_params(
    *,
    scene_id: str,
    certify_id: str,
    device_token: str,
    data: str,
    user_user_id: str,
    access_key_id: str,
    version: str = "2023-03-05",
    signature_nonce: str | None = None,
    secret: str | None = None,
) -> dict[str, str]:
    params = rpc_base_params("VerifyCaptchaV2", access_key_id, version)
    if signature_nonce:
        params["SignatureNonce"] = signature_nonce
    params.update({
        "SceneId": scene_id,
        "CertifyId": certify_id,
        "CaptchaVerifyParam": json.dumps(
            {
                "sceneId": scene_id,
                "certifyId": certify_id,
                "deviceToken": device_token,
                "data": data,
            },
            separators=(",", ":"),
        ),
        "UserUserId": user_user_id,
    })
    if secret:
        params["Signature"] = sign_rpc(params, secret)
    return params


def _run_data_builder(payload: dict[str, str], runner: Any = None) -> str:
    output = _require_target_runner(runner)("data_builder", payload)
    if not isinstance(output, dict) or not isinstance(output.get("output"), str):
        raise ValueError("approved target runner must return an output string")
    return output["output"]


def build_arg(certify_id: str, *, key: str | None = None, runner: Any = None) -> dict[str, str]:
    """Build the dynamic-script ``arg`` with the shared FeiLin stream VM."""
    if not certify_id or any(char not in "0123456789abcdef" for char in certify_id):
        raise ValueError("certify_id must be lowercase hexadecimal")
    key = key or "".join(
        secrets.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(16)
    )
    if len(key) != 16 or any(
        char not in "abcdefghijklmnopqrstuvwxyz0123456789" for char in key
    ):
        raise ValueError("key must be 16 lowercase alphanumeric chars")
    return {"arg": _run_data_builder({"input": certify_id, "key": key}, runner), "key": key}


def build_data(
    track_state: Mapping[str, Any],
    *,
    nonce: str | None = None,
    stream_key: str = STREAM_KEY_DEFAULT,
    runner: Any = None,
) -> dict[str, str]:
    required = {"TrackList", "TrackStartTime", "VerifyTime", "arg"}
    missing = required.difference(track_state)
    if missing:
        raise ValueError(f"track_state is missing: {', '.join(sorted(missing))}")
    nonce = nonce or secrets.token_hex(16)
    if len(nonce) != 32 or any(char not in "0123456789abcdef" for char in nonce):
        raise ValueError("nonce must be 32 lowercase hexadecimal chars")
    track_json = json.dumps(track_state, ensure_ascii=False, separators=(",", ":"))
    compressed = base64.b64encode(
        zlib.compress((nonce + track_json).encode("utf-8"), level=6)
    ).decode()
    return {
        "data": _run_data_builder({"input": compressed, "key": stream_key}, runner),
        "nonce": nonce,
        "streamKey": stream_key,
        "trackJson": track_json,
        "compressed": compressed,
    }


def main() -> int:
    raise TargetCodeExecutionError(
        "case entry does not execute target JS/WASM; use the approved python-node provider runner"
    )


if __name__ == "__main__":
    raise SystemExit(main())
