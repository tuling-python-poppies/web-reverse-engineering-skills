#!/usr/bin/env python3
"""Deterministic offline protocol controls for recovery implementations."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import zlib
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlencode


@dataclass(frozen=True)
class LabCase:
    case_id: str
    invariant: str
    negative_control: str


CASES = (
    LabCase("exact-wire", "Exact body bytes, duplicate-header order, and field slot matter", "Change serialization, header order, or field slot"),
    LabCase("same-session-bootstrap", "Bootstrap token and session cookie remain on one chain", "Splice a token into a different session"),
    LabCase("response-transform-order", "Prefix removal precedes Base64 and zlib decode", "Change transform order or skip prefix validation"),
    LabCase("pagination-route-pivot", "The returned next route is authoritative", "Guess the next page by URL arithmetic"),
    LabCase("modified-digest", "Custom byte masks and rotate semantics differ from stock digests", "Use stock SHA-256 or drop the mask"),
    LabCase("context-activation", "Account identity and complete business context pass a final reread", "Omit scope type or submit a display label as an ID"),
    LabCase("async-export-isolation", "A new matching task and complete fields are required", "Reuse an existing task or accept fewer columns"),
)


def exact_wire_accepts(body: bytes, headers: Sequence[Tuple[str, str]], slot: str) -> bool:
    expected_body = urlencode([("a", "1"), ("a", "2"), ("empty", "")]).encode("ascii")
    expected_headers = (("x-part", "one"), ("x-part", "two"))
    return body == expected_body and tuple((k.lower(), v) for k, v in headers) == expected_headers and slot == "x-proof"


def session_token(session_id: str) -> str:
    return hashlib.sha256(("bootstrap|" + session_id).encode("utf-8")).hexdigest()[:24]


def same_session_accepts(session_id: str, token: str) -> bool:
    return token == session_token(session_id)


def encode_response(value: Mapping[str, Any]) -> bytes:
    packed = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return b"WPR1." + base64.b64encode(zlib.compress(packed))


def decode_response(payload: bytes) -> Dict[str, Any]:
    if not payload.startswith(b"WPR1."):
        raise ValueError("response prefix mismatch")
    decoded = zlib.decompress(base64.b64decode(payload[5:], validate=True))
    value = json.loads(decoded.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("decoded response must be an object")
    return value


def next_route(page: int) -> str:
    return "/list?page=2" if page == 1 else "/ui/list?cursor=next-3"


def guessed_route(page: int) -> str:
    return f"/list?page={page + 1}"


def rotate_left_32(value: int, amount: int) -> int:
    amount &= 31
    if amount == 0:
        return value & 0xFFFFFFFF
    return ((value << amount) | (value >> (32 - amount))) & 0xFFFFFFFF


def modified_digest(data: bytes, apply_mask: bool = True) -> str:
    words = [0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A]
    for index, byte in enumerate(data):
        if apply_mask:
            byte ^= (0x5A + index * 17) & 0xFF
        slot = index % len(words)
        words[slot] = rotate_left_32(words[slot] ^ byte, index % 32)
        words[slot] = (words[slot] + 0x9E3779B9 + index) & 0xFFFFFFFF
    return "".join(f"{word:08x}" for word in words)


AUTHORIZED_CONTEXTS = (
    {"label": "Alpha Shop", "tenantId": "tenant-a", "scopeType": "shop", "scopeId": "shop-101"},
    {"label": "Alpha Outlet", "tenantId": "tenant-a", "scopeType": "shop", "scopeId": "shop-102"},
)


def resolve_context_id(label: str) -> Mapping[str, str]:
    matches = [row for row in AUTHORIZED_CONTEXTS if row["label"] == label]
    if len(matches) != 1:
        raise ValueError("display label must match exactly one authorized context")
    return matches[0]


def context_accepts(expected: Mapping[str, str], active: Mapping[str, str]) -> bool:
    required = ("tenantId", "scopeType", "scopeId")
    return all(expected.get(field) and expected.get(field) == active.get(field) for field in required)


def select_export_task(before_ids: Sequence[str], after: Sequence[Mapping[str, Any]], condition: Mapping[str, Any]) -> Mapping[str, Any]:
    before = set(before_ids)
    matches = [
        task for task in after
        if task.get("id") not in before
        and task.get("range") == condition.get("range")
        and task.get("fields") == condition.get("fields")
    ]
    if len(matches) != 1:
        raise ValueError("new export task must match exactly once")
    return matches[0]


def require_complete_fields(requested: Sequence[str], downloaded: Sequence[str]) -> None:
    if list(requested) != list(downloaded):
        raise ValueError("downloaded fields do not match the requested ordered field set")


def run_self_test() -> None:
    failures: List[str] = []

    body = b"a=1&a=2&empty="
    headers = (("X-Part", "one"), ("X-Part", "two"))
    if not exact_wire_accepts(body, headers, "x-proof"):
        failures.append("exact-wire positive")
    if exact_wire_accepts(b"a=1&empty=&a=2", headers, "x-proof"):
        failures.append("exact-wire body control")
    if exact_wire_accepts(body, tuple(reversed(headers)), "x-proof"):
        failures.append("exact-wire order control")
    if exact_wire_accepts(body, headers, "etag"):
        failures.append("exact-wire slot control")

    first_token = session_token("session-a")
    if not same_session_accepts("session-a", first_token):
        failures.append("same-session positive")
    if same_session_accepts("session-b", first_token):
        failures.append("same-session splice control")

    encoded = encode_response({"accepted": True, "rows": [1, 2]})
    if decode_response(encoded).get("accepted") is not True:
        failures.append("response-transform positive")
    try:
        decode_response(encoded[5:])
    except ValueError:
        pass
    else:
        failures.append("response-transform prefix control")
    try:
        decode_response(encoded[:-2] + b"**")
    except (ValueError, zlib.error):
        pass
    else:
        failures.append("response-transform encoding control")

    if next_route(1) != guessed_route(1):
        failures.append("pagination first route setup")
    if next_route(2) == guessed_route(2):
        failures.append("pagination pivot control")

    if modified_digest(b"abc") == hashlib.sha256(b"abc").hexdigest():
        failures.append("modified-digest stock control")
    if modified_digest(b"abc") == modified_digest(b"abc", apply_mask=False):
        failures.append("modified-digest mask control")
    if rotate_left_32(0x12345678, 0) != 0x12345678:
        failures.append("modified-digest rotate control")

    context = resolve_context_id("Alpha Shop")
    if not context_accepts(context, context):
        failures.append("context positive")
    incomplete = {"tenantId": "tenant-a", "scopeId": "shop-101"}
    if context_accepts(context, incomplete):
        failures.append("context incomplete control")
    try:
        resolve_context_id("Alpha")
    except ValueError:
        pass
    else:
        failures.append("context label control")

    condition = {"range": "2026-07", "fields": ["id", "amount"]}
    before = ["task-existing"]
    after = [
        {"id": "task-existing", "range": "2026-06", "fields": ["id"]},
        {"id": "task-current", **condition},
    ]
    selected = select_export_task(before, after, condition)
    if selected.get("id") != "task-current":
        failures.append("export positive")
    try:
        select_export_task(before, after[:1], condition)
    except ValueError:
        pass
    else:
        failures.append("export existing-task control")
    try:
        select_export_task(
            before,
            [after[0], {"id": "task-wrong", "range": "2026-06", "fields": ["id", "amount"]}],
            condition,
        )
    except ValueError:
        pass
    else:
        failures.append("export condition control")
    try:
        require_complete_fields(condition["fields"], ["id"])
    except ValueError:
        pass
    else:
        failures.append("export field control")

    if failures:
        raise AssertionError(", ".join(failures))
    print("practice_lab_self_test=PASS cases=7 negative_controls=15")


def describe_cases() -> List[Dict[str, str]]:
    return [
        {"id": case.case_id, "invariant": case.invariant, "negativeControl": case.negative_control}
        for case in CASES
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("command", nargs="?", choices=("describe",))
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.self_test:
            run_self_test()
            return 0
        if args.command == "describe":
            print(json.dumps(describe_cases(), indent=2))
            return 0
        build_parser().print_help(sys.stderr)
        return 2
    except (AssertionError, ValueError, zlib.error) as exc:
        print(f"practice_lab=FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
