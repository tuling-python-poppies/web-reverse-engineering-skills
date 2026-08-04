#!/usr/bin/env python3
"""Offline Aliyun Captcha V2 FeiLin profile diff helper.

Reads one-round captured artifacts and an optional old profile, decrypts the
FeiLin envelopes offline, and prints a structured diff summary. The script
performs no network traffic and writes no files.

Captured artifact shapes (keep the full request/response bodies):

    init.json:
      {"url": ..., "requestBody": {"text": ...},
       "responseBody": {"text": "<InitCaptchaV2 JSON with DeviceConfig>"}}

    log2.json:
      {"url": ..., "requestBody": {"text": "<form body with Data param>"}}

    token.json:
      {"token": "<deviceToken>", "environment": {...}}

Usage:

    python scripts/aliyun_v2_profile_diff.py \
      --init current_init.json \
      --log2 current_log2.json \
      --token current_token.json \
      --old-profile <projectRoot>/profile.json
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

DEVICE_CONFIG_KEY = "87f879f135f27da7"
DEVICE_UPLOAD_KEY = "a549a55c60a39aa0"
DEVICE_AES_IV = b"0123456789ABCDEF"
DEVICE_TOKEN_SALT = "daye,raolewoba!"
TOKEN_PLATFORM = "WEB"

# Known field roles for the FeiLin full profile / sparse token payload.
FIELD_ROLES: dict[int, str] = {
    0: "device platform marker",
    21: "field21 session-bound value",
    42: "ip",
    43: "cold-start timeline",
    52: "generation-local device digest (feilin123+)",
    72: "device start ms",
    74: "log2 ms",
    86: "generation-local field (feilin123+)",
    87: "DeviceConfig timestamp",
    88: "capability bitmap",
    117: "FeiLin script url / resource timing",
    118: "FeiLin script url / resource timing",
    136: "generation-local field (feilin123+)",
    137: "generation-local field (feilin123+)",
}


def _aes_cbc_decrypt(ciphertext: str, key: str) -> bytes:
    try:
        from Crypto.Cipher import AES
    except ImportError as exc:
        raise RuntimeError("pycryptodome is required for offline decryption") from exc
    key_bytes = key.encode("utf-8")
    if len(key_bytes) != 16:
        raise ValueError("AES key must encode to exactly 16 bytes")
    encrypted = base64.b64decode(ciphertext, validate=True)
    plaintext = AES.new(key_bytes, AES.MODE_CBC, DEVICE_AES_IV).decrypt(encrypted)
    padding = plaintext[-1]
    if padding < 1 or padding > 16 or plaintext[-padding:] != bytes([padding]) * padding:
        raise ValueError("invalid AES PKCS7 padding")
    return plaintext[:-padding]


def parse_device_config(blob: str) -> dict[str, Any]:
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

    return {
        "encryptionKey": decode_field(0),
        "switch": decode_field(1),
        "sessionId": fields[2],
        "version": fields[3],
        "pluginElements": decode_field(4),
        "pluginResource": decode_field(5),
        "globalVariable": decode_field(6),
        "timestamp": fields[7],
        "ip": fields[8],
    }


def _load_capture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _form_data(body_text: str) -> dict[str, str]:
    parsed = urllib.parse.parse_qs(body_text)
    return {key: values[0] for key, values in parsed.items()}


def decode_log2(capture: dict[str, Any], session_key: str) -> dict[str, Any]:
    form = _form_data(_load_capture(capture)["requestBody"]["text"])
    data = form.get("Data")
    if not data:
        raise ValueError("log2 requestBody has no Data param")
    outer = _aes_cbc_decrypt(data, DEVICE_UPLOAD_KEY).decode("utf-8")
    outer_parts = outer.split("#")
    if len(outer_parts) < 7:
        raise ValueError("Log2 outer plaintext has too few fields")
    if outer_parts[6] == "501":
        if len(outer_parts) < 8:
            raise ValueError("Log2 501 event has no record payload")
        record_text = outer_parts[7]
    elif outer_parts[6].startswith("501#"):
        record_text = outer_parts[6].split("#", 1)[1]
    else:
        raise ValueError("Log2 event is not 501")
    record = base64.b64decode(record_text, validate=True).decode("utf-8")
    record_parts = record.split("#")
    if len(record_parts) != 6:
        raise ValueError("Log2 record must contain six fields")
    payload_plaintext = _aes_cbc_decrypt(record_parts[1], session_key).decode("utf-8")
    platform = _aes_cbc_decrypt(record_parts[3], session_key).decode("utf-8")
    timestamp_ms = _aes_cbc_decrypt(record_parts[5], session_key).decode("utf-8")
    full_fields = payload_plaintext.split("#")
    return {
        "gatherCost": outer_parts[5],
        "platform": platform,
        "timestampMs": timestamp_ms,
        "fieldCount": len(full_fields),
        "field21": full_fields[21] if len(full_fields) > 21 else None,
        "fields": full_fields,
    }


def decode_token(capture: dict[str, Any], session_key: str) -> dict[str, Any]:
    token = _load_capture(capture)["token"]
    outer = base64.b64decode(token, validate=True).decode("utf-8")
    outer_parts = outer.split("#")
    if len(outer_parts) != 5:
        raise ValueError("deviceToken must contain five '#' separated fields")
    platform, token_session, payload, counter_text, checksum = outer_parts
    expected = hashlib.md5(
        f"{platform}#{token_session}#{payload}#{counter_text}#{DEVICE_TOKEN_SALT}".encode(
            "utf-8"
        )
    ).hexdigest()
    token_fields = _aes_cbc_decrypt(payload, session_key).decode("utf-8").split("#")
    return {
        "platform": platform,
        "counter": counter_text,
        "checksumOk": expected == checksum,
        "fieldCount": len(token_fields),
        "field21": token_fields[21] if len(token_fields) > 21 else None,
        "fields": token_fields,
    }


def _non_empty_indices(fields: list[str]) -> list[int]:
    return [index for index, value in enumerate(fields) if value]


def diff_profiles(
    log2_fields: list[str],
    token_fields: list[str],
    old_fields: list[str] | None,
) -> dict[str, Any]:
    changed: list[dict[str, Any]] = []
    width = max(len(log2_fields), len(token_fields), len(old_fields or []))
    for index in range(width):
        log2_value = log2_fields[index] if index < len(log2_fields) else ""
        token_value = token_fields[index] if index < len(token_fields) else ""
        old_value = old_fields[index] if old_fields and index < len(old_fields) else ""
        profile_changed = old_fields is not None and log2_value != old_value
        token_diverged = bool(token_value) and token_value != log2_value
        if not profile_changed and not token_diverged:
            continue
        changed.append(
            {
                "index": index,
                "role": FIELD_ROLES.get(index),
                "log2": log2_value[:200],
                "token": token_value[:200],
                "old": old_value[:200] if old_fields is not None else None,
            }
        )
    return {
        "changed": changed,
        "log2NonEmpty": _non_empty_indices(log2_fields),
        "tokenNonEmpty": _non_empty_indices(token_fields),
        "tokenSparseSubsetOfLog2": set(_non_empty_indices(token_fields)).issubset(
            set(_non_empty_indices(log2_fields))
        ),
    }


def _self_test() -> None:
    from Crypto.Cipher import AES  # noqa: F401

    plaintext = b"alpha#beta#gamma"
    iv = DEVICE_AES_IV
    from Crypto.Cipher import AES as AesImpl

    padded = plaintext + bytes([16 - len(plaintext) % 16]) * (16 - len(plaintext) % 16)
    cipher = AesImpl.new(DEVICE_CONFIG_KEY.encode(), AesImpl.MODE_CBC, iv)
    blob = base64.b64encode(cipher.encrypt(padded)).decode()
    decrypted = _aes_cbc_decrypt(blob, DEVICE_CONFIG_KEY)
    assert decrypted == plaintext
    print("self-test PASS")


def build_summary(init: dict[str, Any], log2: dict[str, Any], token: dict[str, Any], diff: dict[str, Any], old_path: str | None) -> dict[str, Any]:
    return {
        "init": {
            "version": init.get("version"),
            "sessionId": init.get("sessionId"),
            "ip": init.get("ip"),
            "timestamp": init.get("timestamp"),
            "encryptionKeyLen": len(init.get("encryptionKey", "")),
        },
        "log2": {
            "gatherCost": log2.get("gatherCost"),
            "platform": log2.get("platform"),
            "timestampMs": log2.get("timestampMs"),
            "fieldCount": log2.get("fieldCount"),
            "field21": log2.get("field21"),
            "nonEmptyCount": len(diff["log2NonEmpty"]),
        },
        "token": {
            "counter": token.get("counter"),
            "checksumOk": token.get("checksumOk"),
            "fieldCount": token.get("fieldCount"),
            "field21": token.get("field21"),
            "nonEmptyCount": len(diff["tokenNonEmpty"]),
        },
        "diff": {
            "oldProfile": old_path,
            "changedCount": len(diff["changed"]),
            "changed": diff["changed"],
            "tokenSparseSubsetOfLog2": diff["tokenSparseSubsetOfLog2"],
            "log2NonEmpty": diff["log2NonEmpty"],
            "tokenNonEmpty": diff["tokenNonEmpty"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--init", type=Path)
    parser.add_argument("--log2", type=Path)
    parser.add_argument("--token", type=Path)
    parser.add_argument("--old-profile", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        _self_test()
        return 0
    if not (args.init and args.log2 and args.token):
        parser.error("--init, --log2 and --token are required unless --self-test is used")

    init_capture = _load_capture(args.init)
    init_response_text = init_capture["responseBody"]["text"]
    init_response = json.loads(init_response_text)
    device_config = parse_device_config(init_response["DeviceConfig"])

    log2 = decode_log2(args.log2, device_config["encryptionKey"])
    token = decode_token(args.token, device_config["encryptionKey"])

    old_fields: list[str] | None = None
    if args.old_profile:
        old = json.loads(args.old_profile.read_text(encoding="utf-8"))
        old_fields = list(old.get("fullDeviceFields") or [])

    diff = diff_profiles(log2["fields"], token["fields"], old_fields)
    init = {**device_config, "staticPath": init_response.get("StaticPath"), "certifyId": init_response.get("CertifyId")}
    summary = build_summary(init, log2, token, diff, str(args.old_profile) if args.old_profile else None)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"profile diff failed: {exc}", file=sys.stderr)
        raise
