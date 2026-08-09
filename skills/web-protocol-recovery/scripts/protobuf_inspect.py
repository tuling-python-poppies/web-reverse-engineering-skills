#!/usr/bin/env python3
"""Decode protobuf wire-format payloads without a schema (raw field view).

This is a bounded, offline, standard-library-only decoder. It reports the
wire structure of a protobuf message the way ``protoc --decode_raw`` does:
field numbers, wire types, and best-effort value interpretations. Unknown
schema means field names are never invented; length-delimited values that do
not parse as a nested message are kept as raw bytes metadata.

When a ``.proto`` or FileDescriptorSet is available, the richer named decode
belongs to ``protoc --decode`` or the ``protobuf`` Python package. This script
is the portable fallback that always runs offline and gates in preflight.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import sys
from pathlib import Path


DEFAULT_MAX_INPUT_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_DEPTH = 32
DEFAULT_MAX_FIELDS = 20000

WIRE_VARINT = 0
WIRE_I64 = 1
WIRE_LEN = 2
WIRE_SGROUP = 3
WIRE_EGROUP = 4
WIRE_I32 = 5

WIRE_NAMES = {
    WIRE_VARINT: "varint",
    WIRE_I64: "i64",
    WIRE_LEN: "len",
    WIRE_SGROUP: "sgroup",
    WIRE_EGROUP: "egroup",
    WIRE_I32: "i32",
}


class ProtobufError(ValueError):
    """Raised when input violates the bounded protobuf wire contract."""


def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    result = 0
    shift = 0
    start = offset
    while True:
        if offset >= len(data):
            raise ProtobufError(f"truncated varint at offset {start}")
        if shift > 63:
            raise ProtobufError(f"varint exceeds 64 bits at offset {start}")
        byte = data[offset]
        result |= (byte & 0x7F) << shift
        offset += 1
        if not byte & 0x80:
            return result, offset
        shift += 7


def _looks_like_text(raw: bytes) -> bool:
    if not raw:
        return False
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return all(byte >= 0x20 or byte in (0x09, 0x0A, 0x0D) for byte in raw)


class _Counter:
    __slots__ = ("value", "limit")

    def __init__(self, limit: int) -> None:
        self.value = 0
        self.limit = limit

    def bump(self, offset: int) -> None:
        self.value += 1
        if self.value > self.limit:
            raise ProtobufError(f"field count exceeds limit {self.limit} at offset {offset}")


def parse_message(
    data: bytes,
    *,
    depth: int = 0,
    max_depth: int = DEFAULT_MAX_DEPTH,
    counter: _Counter | None = None,
) -> list[dict[str, object]]:
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    if depth > max_depth:
        raise ProtobufError(f"nesting exceeds max depth {max_depth}")
    if counter is None:
        counter = _Counter(DEFAULT_MAX_FIELDS)

    fields: list[dict[str, object]] = []
    offset = 0
    total = len(data)
    while offset < total:
        counter.bump(offset)
        key, offset = _read_varint(data, offset)
        field_number = key >> 3
        wire_type = key & 0x07
        if field_number == 0:
            raise ProtobufError(f"invalid field number 0 at offset {offset}")

        entry: dict[str, object] = {
            "field": field_number,
            "wireType": WIRE_NAMES.get(wire_type, f"unknown({wire_type})"),
        }

        if wire_type == WIRE_VARINT:
            value, offset = _read_varint(data, offset)
            entry["value"] = value
        elif wire_type == WIRE_I64:
            if offset + 8 > total:
                raise ProtobufError(f"truncated i64 at offset {offset}")
            entry["valueHex"] = data[offset : offset + 8].hex()
            offset += 8
        elif wire_type == WIRE_I32:
            if offset + 4 > total:
                raise ProtobufError(f"truncated i32 at offset {offset}")
            entry["valueHex"] = data[offset : offset + 4].hex()
            offset += 4
        elif wire_type == WIRE_LEN:
            length, offset = _read_varint(data, offset)
            end = offset + length
            if length < 0 or end > total:
                raise ProtobufError(f"length-delimited overruns buffer at offset {offset}")
            raw = data[offset:end]
            offset = end
            entry["length"] = length
            nested: list[dict[str, object]] | None = None
            if raw and depth < max_depth:
                try:
                    nested = parse_message(
                        raw,
                        depth=depth + 1,
                        max_depth=max_depth,
                        counter=counter,
                    )
                except ProtobufError:
                    nested = None
            if nested is not None:
                entry["kind"] = "message"
                entry["message"] = nested
            elif _looks_like_text(raw):
                entry["kind"] = "string"
                entry["value"] = raw.decode("utf-8")
            else:
                entry["kind"] = "bytes"
                entry["bytesHex"] = raw.hex()
        elif wire_type in (WIRE_SGROUP, WIRE_EGROUP):
            # Deprecated groups: record the marker and stop descending.
            entry["note"] = "group marker (deprecated wire type)"
        else:
            raise ProtobufError(f"unsupported wire type {wire_type} at offset {offset}")

        fields.append(entry)
    return fields


def decode_raw(
    data: bytes,
    *,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_fields: int = DEFAULT_MAX_FIELDS,
) -> list[dict[str, object]]:
    for name, value in (("max_depth", max_depth), ("max_fields", max_fields)):
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    return parse_message(data, max_depth=max_depth, counter=_Counter(max_fields))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _tag(field_number: int, wire_type: int) -> bytes:
    return _varint((field_number << 3) | wire_type)


def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def self_test() -> None:
    # field 1 varint=150, field 2 string="testing", field 3 nested{field1 varint=1}
    nested = _tag(1, WIRE_VARINT) + _varint(1)
    message = (
        _tag(1, WIRE_VARINT)
        + _varint(150)
        + _tag(2, WIRE_LEN)
        + _varint(len(b"testing"))
        + b"testing"
        + _tag(3, WIRE_LEN)
        + _varint(len(nested))
        + nested
    )
    fields = decode_raw(message)
    _require(fields[0] == {"field": 1, "wireType": "varint", "value": 150}, "varint field")
    _require(
        fields[1]["field"] == 2 and fields[1]["kind"] == "string" and fields[1]["value"] == "testing",
        "string field",
    )
    nested_field = fields[2]
    nested_message = nested_field["message"]
    _require(
        nested_field["field"] == 3
        and nested_field["kind"] == "message"
        and isinstance(nested_message, list)
        and nested_message[0]["value"] == 1,
        "nested message field",
    )

    invalid_cases = (
        b"\x08",              # truncated varint payload
        b"\x08\x80\x80",      # varint never terminates
        b"\x12\x05ab",        # length-delimited overruns buffer
        b"\x00\x01",          # field number 0 is invalid
    )
    failures = 0
    for invalid in invalid_cases:
        try:
            decode_raw(invalid)
        except ProtobufError:
            failures += 1
    _require(failures == len(invalid_cases), "negative controls")
    print("protobuf_inspect_self_test=PASS fields=3 negative_controls=4")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="Captured protobuf body (binary or Base64)")
    parser.add_argument("--base64", action="store_true", help="Decode input as Base64 before parsing")
    parser.add_argument("--max-input-bytes", type=int, default=DEFAULT_MAX_INPUT_BYTES)
    parser.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    parser.add_argument("--max-fields", type=int, default=DEFAULT_MAX_FIELDS)
    parser.add_argument(
        "--include-input-sha256",
        action="store_true",
        help="Include the input SHA-256 for task-local correlation; unsafe for publication",
    )
    parser.add_argument("--self-test", action="store_true")
    return parser


def _error(message: str, *, input_file: str | None = None) -> int:
    payload: dict[str, object] = {"ok": False, "error": message}
    if input_file:
        payload["inputFile"] = input_file
    print(json.dumps(payload, ensure_ascii=True))
    return 2


def main() -> int:
    args = build_parser().parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.input:
        return _error("input is required unless --self-test is used")
    for name, value in (
        ("max-input-bytes", args.max_input_bytes),
        ("max-depth", args.max_depth),
        ("max-fields", args.max_fields),
    ):
        if value <= 0:
            return _error(f"{name} must be positive", input_file=Path(args.input).name)

    input_path = Path(args.input)
    try:
        with input_path.open("rb") as handle:
            raw = handle.read(args.max_input_bytes + 1)
        if len(raw) > args.max_input_bytes:
            return _error(
                f"input length exceeds limit {args.max_input_bytes}",
                input_file=input_path.name,
            )
    except OSError:
        return _error("input read failed", input_file=input_path.name)

    if args.base64:
        try:
            raw = base64.b64decode(bytes(byte for byte in raw if byte not in b" \t\r\n"), validate=True)
        except (binascii.Error, ValueError):
            return _error("invalid Base64 input", input_file=input_path.name)

    try:
        fields = decode_raw(raw, max_depth=args.max_depth, max_fields=args.max_fields)
    except (ProtobufError, ValueError, TypeError) as exc:
        return _error(str(exc), input_file=input_path.name)

    report: dict[str, object] = {
        "ok": True,
        "inputFile": input_path.name,
        "byteLength": len(raw),
        "fieldCount": len(fields),
        "fields": fields,
    }
    if args.include_input_sha256:
        report["inputSha256"] = hashlib.sha256(raw).hexdigest()
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
