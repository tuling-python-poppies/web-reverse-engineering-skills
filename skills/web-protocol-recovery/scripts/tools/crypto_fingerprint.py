#!/usr/bin/env python3
"""
Heuristic fingerprint helper for suspicious crypto or encoding outputs.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import math
import re
import sys
from collections import Counter
from typing import Any, Optional


HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
BASE64_RE = re.compile(r"^[A-Za-z0-9+/=]+$")
URLSAFE_BASE64_RE = re.compile(r"^[A-Za-z0-9_-]+={0,2}$")
MAX_INPUT_BYTES = 1024 * 1024
MAX_DECODED_BYTES = 1024 * 1024


def pad_base64(value: str) -> str:
    return value + "=" * (-len(value) % 4)


def try_standard_base64(value: str) -> Optional[bytes]:
    if not BASE64_RE.fullmatch(value):
        return None
    if len(value) > (MAX_DECODED_BYTES * 4 // 3) + 8:
        return None
    try:
        return base64.b64decode(pad_base64(value), validate=True)
    except (binascii.Error, ValueError):
        return None


def try_urlsafe_base64(value: str) -> Optional[bytes]:
    if not URLSAFE_BASE64_RE.fullmatch(value):
        return None
    if len(value) > (MAX_DECODED_BYTES * 4 // 3) + 8:
        return None
    try:
        return base64.urlsafe_b64decode(pad_base64(value))
    except (binascii.Error, ValueError):
        return None


def decode_json_segment(value: str) -> Optional[Any]:
    decoded = try_urlsafe_base64(value)
    if not decoded:
        return None
    try:
        return json.loads(decoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    total = len(value)
    counts = Counter(value)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def charset_summary(value: str) -> dict[str, int]:
    return {
        "digits": sum(char.isdigit() for char in value),
        "lower": sum(char.islower() for char in value),
        "upper": sum(char.isupper() for char in value),
        "symbols": sum(not char.isalnum() for char in value),
        "unique": len(set(value)),
    }


def guess_kind(value: str) -> list[str]:
    hints: list[str] = []
    length = len(value)
    is_hex = bool(HEX_RE.fullmatch(value))

    if is_hex:
        hints.append("hex")
        if length == 32:
            hints.append("md5-like length")
        elif length == 40:
            hints.append("sha1-like length")
        elif length == 64:
            hints.append("sha256-like length")
        elif length % 2:
            hints.append("odd-length hex, likely not raw bytes encoded as hex")

    if not is_hex and BASE64_RE.fullmatch(value):
        hints.append("base64-like alphabet")
        if try_standard_base64(value) is not None:
            hints.append("valid base64 decode")

    if not is_hex and URLSAFE_BASE64_RE.fullmatch(value):
        hints.append("urlsafe-base64-like alphabet")
        if try_urlsafe_base64(value) is not None:
            hints.append("valid urlsafe-base64 decode")

    parts = value.split(".")
    if len(parts) == 3:
        header = decode_json_segment(parts[0])
        payload = decode_json_segment(parts[1])
        if isinstance(header, dict) and isinstance(payload, dict):
            hints.append("jwt-like three-part token")

    entropy = shannon_entropy(value)
    if entropy >= 4.5:
        hints.append("high-entropy-looking")
    elif entropy <= 2.5 and length >= 12:
        hints.append("low-entropy-looking")

    if not hints:
        hints.append("custom alphabet or mixed encoding")

    return hints


def build_report(value: str) -> dict[str, Any]:
    return {
        "value_length": len(value),
        "entropy_bits_per_char": round(shannon_entropy(value), 3),
        "charset": charset_summary(value),
        "hints": guess_kind(value),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fingerprint suspicious crypto-like strings.")
    parser.add_argument("value", nargs="?", help="Value to inspect. If omitted, reads stdin.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()
    if args.value is not None:
        value = args.value
    else:
        value = sys.stdin.read(MAX_INPUT_BYTES + 1).strip()
    if len(value.encode("utf-8")) > MAX_INPUT_BYTES:
        parser.error(f"input exceeds {MAX_INPUT_BYTES} bytes")
    if not value:
        parser.error("value is required, either as an argument or stdin")

    report = build_report(value)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print(f"value_length={report['value_length']}")
    print(f"entropy_bits_per_char={report['entropy_bits_per_char']}")
    charset = report["charset"]
    print(
        "charset="
        f"digits:{charset['digits']} lower:{charset['lower']} upper:{charset['upper']} "
        f"symbols:{charset['symbols']} unique:{charset['unique']}"
    )
    for hint in report["hints"]:
        print(f"- {hint}")


if __name__ == "__main__":
    main()
