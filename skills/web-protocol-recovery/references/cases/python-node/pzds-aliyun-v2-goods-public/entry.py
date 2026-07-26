"""Reusable PZDS Aliyun Captcha V2 primitives.

Importing this module performs no network traffic and writes no files. Live
collectors should combine these helpers with a current project profile selected
through `pull_live_state.py`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qsl, quote


PZDS_ORIGIN = "https://www.pzds.com"
GOODS_PAGE_URL = "https://api.pzds.com/api/web-client/v2/public/goodsPublic/page"
PZDS_VERSION = "26.724.1707"
PZDS_SIGN_VERSION = "v17"
PZDS_CHANNEL_INFO = '{"channelCode":null,"tag":null,"channelType":null,"searchWord":"null","adExtras":"","urlParam":""}'
DEVICE_AES_IV = b"0123456789ABCDEF"
DEVICE_TOKEN_SALT = "daye,raolewoba!"
ASSETS = Path(__file__).resolve().parent / "assets"


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
    return "&".join(f"{percent_encode(key)}={percent_encode(value)}" for key, value in sorted(params.items()) if key != "Signature")


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


def build_field21(local_suffix: str, source_key: str, xor_mask: bytes) -> str:
    if len(local_suffix) != 8 or any(ch not in "0123456789abcdef" for ch in local_suffix):
        raise ValueError("local_suffix must be 8 lowercase hexadecimal chars")
    mixed = bytes(32 + ((ord(source) - 32 + ord(suffix) - 32) % 95) for source, suffix in zip(source_key, local_suffix))
    return base64.b64encode(bytes(value ^ mask for value, mask in zip(mixed, xor_mask))).decode("ascii")


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

    plaintext = AES.new(key.encode("utf-8"), AES.MODE_CBC, DEVICE_AES_IV).decrypt(base64.b64decode(ciphertext, validate=True))
    padding = plaintext[-1]
    if padding < 1 or padding > 16 or plaintext[-padding:] != bytes([padding]) * padding:
        raise ValueError("invalid AES PKCS7 padding")
    return plaintext[:-padding]


def parse_device_token(token: str) -> DeviceToken:
    outer = base64.b64decode(token, validate=True).decode("utf-8")
    platform, session_id, payload, counter_text, checksum = outer.split("#")
    return DeviceToken(platform, session_id, payload, int(counter_text), checksum)


def device_token_checksum(platform: str, session_id: str, payload: str, counter: int) -> str:
    return hashlib.md5(f"{platform}#{session_id}#{payload}#{counter}#{DEVICE_TOKEN_SALT}".encode()).hexdigest()


def build_device_token(session_id: str, payload_plaintext: str, counter: int, encryption_key: str) -> str:
    payload = _aes_cbc_encrypt(payload_plaintext.encode("utf-8"), encryption_key)
    checksum = device_token_checksum("WEB", session_id, payload, counter)
    return base64.b64encode(f"WEB#{session_id}#{payload}#{counter}#{checksum}".encode()).decode()


def decrypt_device_payload(token: str | DeviceToken, encryption_key: str) -> str:
    parsed = parse_device_token(token) if isinstance(token, str) else token
    return _aes_cbc_decrypt(parsed.payload, encryption_key).decode("utf-8")


def pzds_wasm_sign(body: bytes, method: str = "post", timestamp: str | None = None, random_value: str | None = None) -> dict[str, str]:
    request = {"dataJson": body.decode("utf-8"), "method": method.lower()}
    if timestamp is not None:
        request["timestamp"] = str(timestamp)
    if random_value is not None:
        request["random"] = str(random_value)
    process = subprocess.run(
        ["node", str(ASSETS / "pzds_wasm_sign.mjs")],
        input=json.dumps(request, separators=(",", ":")),
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or "pzds_wasm_sign.mjs failed")
    output = json.loads(process.stdout)
    return {"Sign": str(output["sign"]), "PZTimestamp": str(output["timestamp"]), "Random": str(output["random"])}


def pzds_signed_headers(body: bytes, user_agent: str, device_id: str, global_id: str) -> dict[str, str]:
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN",
        "content-type": "application/json",
        "origin": PZDS_ORIGIN,
        "referer": f"{PZDS_ORIGIN}/goodsList/7/6",
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
    headers.update(pzds_wasm_sign(body))
    return headers


def parse_challenge_html(html: str) -> dict[str, Any]:
    marker = "var requestInfo = "
    required = {"sceneId", "traceid", "token", "userId", "userUserId"}
    for start in reversed([idx for idx in range(len(html)) if html.startswith(marker, idx)]):
        payload, _ = json.JSONDecoder().raw_decode(html[start + len(marker):].lstrip())
        if isinstance(payload, dict) and not required.difference(payload):
            return payload
    raise ValueError("challenge HTML has no usable requestInfo JSON")


def build_business_url(target: str, gateway_token: str, certify_id: str, refer: str | None = None) -> str:
    from urllib.parse import quote as urlquote, unquote, urlsplit, urlunsplit

    parts = urlsplit(target)
    remove_keys = {"u_aref", "u_asig", "u_atoken", "decode__1174"}
    query_parts = [item for item in parts.query.split("&") if item and unquote(item.split("=", 1)[0]) not in remove_keys]
    query_parts.extend([f"u_atoken={urlquote(gateway_token, safe='')}", f"u_asig={urlquote(certify_id, safe='')}"])
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
        "recordsCount": len(payload.get("data", {}).get("records", [])) if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else None,
    }


def main() -> int:
    vectors = json.loads((Path(__file__).resolve().parent / "fixtures" / "vectors.json").read_text(encoding="utf-8"))
    body = build_goods_page_body()
    result = {
        "bodySha256": hashlib.sha256(body).hexdigest(),
        "expectedBodySha256": vectors["request"]["bodySha256"],
        "wasmSign": pzds_wasm_sign(body, timestamp=vectors["pzdsWasmSign"]["timestamp"], random_value=vectors["pzdsWasmSign"]["random"]),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["bodySha256"] == result["expectedBodySha256"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
