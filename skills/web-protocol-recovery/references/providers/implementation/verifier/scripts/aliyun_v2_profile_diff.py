#!/usr/bin/env python3
"""Decode current Aliyun Captcha V2 profile material and compare versions."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl


DEVICE_CONFIG_KEY = "87f879f135f27da7"
DEVICE_UPLOAD_KEY = "a549a55c60a39aa0"
DEVICE_AES_IV = b"0123456789ABCDEF"
DEVICE_TOKEN_SALT = "daye,raolewoba!"

FIELD_ROLES = {
    21: "session field21 binding",
    42: "DeviceConfig IP",
    43: "telemetry timeline",
    52: "version/environment digest",
    72: "device collection start",
    74: "stage timestamp",
    77: "CertifyId",
    87: "DeviceConfig timestamp",
    88: "capability bitmap",
    117: "FeiLin script URL",
    118: "FeiLin resource timing/size",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def body_text(capture: dict[str, Any], name: str) -> str:
    body = capture.get(name)
    if isinstance(body, dict) and isinstance(body.get("text"), str):
        return body["text"]
    if isinstance(body, str):
        return body
    raise ValueError(f"capture has no {name}.text")


def aes_decrypt_base64(ciphertext: str, key: str) -> bytes:
    try:
        from Crypto.Cipher import AES
    except ImportError as exc:
        raise RuntimeError("install pycryptodome to decode Aliyun profiles") from exc
    encrypted = base64.b64decode(ciphertext, validate=True)
    plaintext = AES.new(key.encode("utf-8"), AES.MODE_CBC, DEVICE_AES_IV).decrypt(encrypted)
    padding = plaintext[-1]
    if padding < 1 or padding > 16 or plaintext[-padding:] != bytes([padding]) * padding:
        raise ValueError("invalid AES PKCS7 padding; version key may have changed")
    return plaintext[:-padding]


def decode_config(init_capture: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    response = json.loads(body_text(init_capture, "responseBody"))
    plaintext = aes_decrypt_base64(response["DeviceConfig"], DEVICE_CONFIG_KEY).decode("utf-8")
    fields = plaintext.split("#")

    def decode(index: int) -> str:
        return base64.b64decode(fields[index], validate=True).decode("utf-8") if fields[index] else ""

    config = {
        "encryptionKey": decode(0),
        "switch": int(decode(1)),
        "sessionId": fields[2],
        "version": fields[3],
        "timestamp": int(fields[7]),
        "ip": fields[8],
    }
    return response, config


def decode_log2(log2_capture: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    form = dict(parse_qsl(body_text(log2_capture, "requestBody"), keep_blank_values=True))
    if form.get("Action") != "Log2":
        raise ValueError("capture is not Action=Log2")
    outer = aes_decrypt_base64(form["Data"], DEVICE_UPLOAD_KEY).decode("utf-8").split("#", 6)
    if len(outer) != 7:
        raise ValueError("Log2 outer plaintext must have seven fields")
    event_type, record_b64 = outer[6].split("#", 1)
    if event_type != "501":
        raise ValueError(f"expected Log2 event 501, got {event_type!r}")
    record = base64.b64decode(record_b64, validate=True).decode("utf-8").split("#")
    if len(record) != 6:
        raise ValueError("Log2 record must have six fields")
    fields = aes_decrypt_base64(record[1], config["encryptionKey"]).decode("utf-8").split("#")
    return {
        "gatherCost": int(outer[5]),
        "recordTimestamp": int(aes_decrypt_base64(record[5], config["encryptionKey"])),
        "sessionId": record[0],
        "fields": fields,
    }


def find_token(token_capture: dict[str, Any]) -> str:
    if isinstance(token_capture.get("token"), str):
        return token_capture["token"]
    form = dict(parse_qsl(body_text(token_capture, "requestBody"), keep_blank_values=True))
    verify_param = json.loads(form["CaptchaVerifyParam"])
    return verify_param["deviceToken"]


def decode_token(token: str, config: dict[str, Any]) -> dict[str, Any]:
    outer = base64.b64decode(token, validate=True).decode("utf-8").split("#")
    if len(outer) != 5:
        raise ValueError("deviceToken must have five fields")
    platform, session_id, payload, counter_text, checksum = outer
    counter = int(counter_text)
    expected = hashlib.md5(
        f"{platform}#{session_id}#{payload}#{counter}#{DEVICE_TOKEN_SALT}".encode("utf-8")
    ).hexdigest()
    fields = aes_decrypt_base64(payload, config["encryptionKey"]).decode("utf-8").split("#")
    return {
        "sessionId": session_id,
        "counter": counter,
        "checksumValid": hmac.compare_digest(checksum, expected),
        "fields": fields,
    }


def compare_fields(old: list[str], current: list[str]) -> list[dict[str, Any]]:
    count = max(len(old), len(current))
    return [
        {
            "index": index,
            "role": FIELD_ROLES.get(index, ""),
            "old": old[index] if index < len(old) else None,
            "current": current[index] if index < len(current) else None,
        }
        for index in range(count)
        if (old[index] if index < len(old) else None)
        != (current[index] if index < len(current) else None)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--init", type=Path, required=True, help="js-reverse Init network export")
    parser.add_argument("--log2", type=Path, required=True, help="js-reverse Log2 network export")
    parser.add_argument("--token", type=Path, help="page-eval token JSON or Verify network export")
    parser.add_argument("--old-profile", type=Path, help="existing profile JSON with fullDeviceFields")
    args = parser.parse_args()

    init_response, config = decode_config(load_json(args.init))
    log2 = decode_log2(load_json(args.log2), config)
    if log2["sessionId"] != config["sessionId"]:
        raise ValueError("Init and Log2 use different sessions")

    result: dict[str, Any] = {
        "current": {
            "certifyId": init_response.get("CertifyId"),
            "staticPath": init_response.get("StaticPath"),
            "feilinVersion": config["version"],
            "sessionId": config["sessionId"],
            "ip": config["ip"],
            "gatherCost": log2["gatherCost"],
            "recordTimestamp": log2["recordTimestamp"],
            "fullFieldCount": len(log2["fields"]),
            "fullDeviceFields": log2["fields"],
        }
    }

    if args.token:
        token = decode_token(find_token(load_json(args.token)), config)
        if token["sessionId"] != config["sessionId"]:
            raise ValueError("Init and token use different sessions")
        result["current"].update({
            "tokenCounter": token["counter"],
            "tokenChecksumValid": token["checksumValid"],
            "sparseFieldCount": len(token["fields"]),
            "sparseDeviceFields": token["fields"],
        })

    if args.old_profile:
        old_profile = load_json(args.old_profile)
        old_fields = old_profile.get("fullDeviceFields")
        if not isinstance(old_fields, list):
            raise ValueError("old profile has no fullDeviceFields list")
        result["comparison"] = {
            "oldFeilinVersion": old_profile.get("feilinVersion"),
            "changedFields": compare_fields(old_fields, log2["fields"]),
        }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
