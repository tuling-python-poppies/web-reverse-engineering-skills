#!/usr/bin/env python3
"""Validate and compare ordered TLS, HTTP/2, and connection profiles."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence


SCHEMA = "web-protocol-recovery-transport-profile/v1"
MAX_INPUT_BYTES = 5 * 1024 * 1024
HEX_ID = re.compile(r"^0x[0-9a-fA-F]{1,4}$")


class ProfileError(ValueError):
    pass


def protocol_id(value: Any) -> int:
    if isinstance(value, int) and 0 <= value <= 65535:
        return value
    if isinstance(value, str) and HEX_ID.fullmatch(value):
        return int(value, 16)
    raise ProfileError(f"invalid protocol id: {value!r}")


def is_grease(value: int) -> bool:
    return value & 0x0F0F == 0x0A0A and (value >> 8) == (value & 0xFF)


def normalize_id_list(value: Any, label: str, ignore_grease_values: bool) -> List[Any]:
    if not isinstance(value, list):
        raise ProfileError(f"{label} must be an ordered list")
    result: List[Any] = []
    for item in value:
        parsed = protocol_id(item)
        result.append("GREASE" if ignore_grease_values and is_grease(parsed) else parsed)
    return result


def normalize_settings(value: Any, label: str) -> List[Dict[str, int]]:
    if not isinstance(value, list):
        raise ProfileError(f"{label} must be an ordered list")
    result: List[Dict[str, int]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ProfileError(f"{label}[{index}] must be an object")
        setting_id = protocol_id(item.get("id"))
        setting_value = item.get("value")
        if not isinstance(setting_value, int) or setting_value < 0:
            raise ProfileError(f"{label}[{index}].value must be a non-negative integer")
        result.append({"id": setting_id, "value": setting_value})
    return result


def normalize_document(document: Any, ignore_grease_values: bool = False) -> Dict[str, Any]:
    if not isinstance(document, Mapping) or document.get("schemaVersion") != SCHEMA:
        raise ProfileError(f"profile must use schemaVersion={SCHEMA}")
    tls = document.get("tls")
    http2 = document.get("http2", {})
    connection = document.get("connection", {})
    if not isinstance(tls, Mapping) or not isinstance(http2, Mapping) or not isinstance(connection, Mapping):
        raise ProfileError("tls, http2, and connection must be objects")
    normalized: Dict[str, Any] = {
        "schemaVersion": SCHEMA,
        "identity": document.get("identity", {}),
        "tls": dict(tls),
        "http2": dict(http2),
        "connection": dict(connection),
    }
    for field in ("cipherSuites", "extensions", "supportedGroups", "keyShares", "signatureAlgorithms"):
        if field in tls:
            normalized["tls"][field] = normalize_id_list(tls[field], f"tls.{field}", ignore_grease_values)
    if "alpn" in tls:
        if not isinstance(tls["alpn"], list) or not all(isinstance(item, str) for item in tls["alpn"]):
            raise ProfileError("tls.alpn must be an ordered string list")
    if "settings" in http2:
        normalized["http2"]["settings"] = normalize_settings(http2["settings"], "http2.settings")
    if "pseudoHeaderOrder" in http2:
        order = http2["pseudoHeaderOrder"]
        if not isinstance(order, list) or not all(isinstance(item, str) and item.startswith(":") for item in order):
            raise ProfileError("http2.pseudoHeaderOrder must be an ordered pseudo-header list")
    return normalized


def diff_values(left: Any, right: Any, path: str = "$") -> List[Dict[str, Any]]:
    if type(left) is not type(right):
        return [{"path": path, "kind": "type", "left": type(left).__name__, "right": type(right).__name__}]
    if isinstance(left, Mapping):
        findings: List[Dict[str, Any]] = []
        for key in sorted(set(left) | set(right)):
            if key not in left:
                findings.append({"path": f"{path}.{key}", "kind": "right-only"})
            elif key not in right:
                findings.append({"path": f"{path}.{key}", "kind": "left-only"})
            else:
                findings.extend(diff_values(left[key], right[key], f"{path}.{key}"))
        return findings
    if isinstance(left, list):
        findings = []
        if len(left) != len(right):
            findings.append({"path": f"{path}.length", "kind": "length", "left": len(left), "right": len(right)})
        for index, (lvalue, rvalue) in enumerate(zip(left, right)):
            findings.extend(diff_values(lvalue, rvalue, f"{path}[{index}]"))
        return findings
    return [] if left == right else [{"path": path, "kind": "value", "left": left, "right": right}]


def load_profile(path: Path, ignore_grease_values: bool) -> Dict[str, Any]:
    if not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
        raise ProfileError(f"invalid or oversized profile: {path}")
    return normalize_document(json.loads(path.read_text(encoding="utf-8-sig")), ignore_grease_values)


def run_self_test() -> None:
    base = {
        "schemaVersion": SCHEMA,
        "identity": {"browser": "test"},
        "tls": {"cipherSuites": ["0x0a0a", "0x1301"], "extensions": ["0x1a1a", "0x0000"], "alpn": ["h2", "http/1.1"]},
        "http2": {"settings": [{"id": "0x1", "value": 65536}], "pseudoHeaderOrder": [":method", ":authority", ":scheme", ":path"]},
        "connection": {"reuse": True},
    }
    variant = json.loads(json.dumps(base))
    variant["tls"]["cipherSuites"][0] = "0x2a2a"
    assert not diff_values(normalize_document(base, True), normalize_document(variant, True))
    variant["http2"]["pseudoHeaderOrder"][1:3] = reversed(variant["http2"]["pseudoHeaderOrder"][1:3])
    findings = diff_values(normalize_document(base, True), normalize_document(variant, True))
    assert any(item["path"].startswith("$.http2.pseudoHeaderOrder") for item in findings)
    print("transport_profile_diff_self_test=PASS")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", nargs="?")
    parser.add_argument("right", nargs="?")
    parser.add_argument("--ignore-grease-values", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.self_test:
            run_self_test()
            return 0
        if not args.left or not args.right:
            raise ProfileError("left and right profile paths are required")
        findings = diff_values(load_profile(Path(args.left), args.ignore_grease_values), load_profile(Path(args.right), args.ignore_grease_values))
        result = {"equal": not findings, "differences": findings}
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"profiles_equal={str(not findings).lower()} differences={len(findings)}")
            for item in findings[:100]:
                print(json.dumps(item, sort_keys=True))
        return 0 if not findings else 2
    except (ProfileError, OSError, json.JSONDecodeError, AssertionError) as exc:
        print(f"transport_profile_diff=FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
