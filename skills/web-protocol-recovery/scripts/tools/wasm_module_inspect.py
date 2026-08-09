#!/usr/bin/env python3
"""Inspect WebAssembly module structure without disassembling function bodies.

This is a bounded, offline, standard-library-only inspector. It parses the
module preamble, section table, import table, export table, and function/
memory/table/global counts. It does NOT decode instructions: the goal is to
locate which export is the signing function and which host capabilities the
module imports, so the caller can execute one export for a narrow artifact.

Deeper disassembly (wat / decompiled C) belongs to external tooling such as
``wasm2wat`` / ``wasm-decompile`` and is only needed when porting the algorithm
to pure Python or when the module cannot be executed locally.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


DEFAULT_MAX_INPUT_BYTES = 64 * 1024 * 1024
DEFAULT_MAX_SECTIONS = 4096
DEFAULT_MAX_VECTOR = 1_000_000

WASM_MAGIC = b"\x00asm"

SECTION_NAMES = {
    0: "custom",
    1: "type",
    2: "import",
    3: "function",
    4: "table",
    5: "memory",
    6: "global",
    7: "export",
    8: "start",
    9: "element",
    10: "code",
    11: "data",
    12: "datacount",
}

IMPORT_KINDS = {0: "func", 1: "table", 2: "memory", 3: "global"}
EXPORT_KINDS = {0: "func", 1: "table", 2: "memory", 3: "global"}


class WasmError(ValueError):
    """Raised when input violates the bounded WebAssembly structure contract."""


def _read_uleb128(data: bytes, offset: int, *, max_bits: int = 32) -> tuple[int, int]:
    result = 0
    shift = 0
    start = offset
    while True:
        if offset >= len(data):
            raise WasmError(f"truncated LEB128 at offset {start}")
        if shift >= max_bits:
            raise WasmError(f"LEB128 exceeds {max_bits} bits at offset {start}")
        byte = data[offset]
        result |= (byte & 0x7F) << shift
        offset += 1
        if not byte & 0x80:
            return result, offset
        shift += 7


def _read_name(data: bytes, offset: int) -> tuple[str, int]:
    length, offset = _read_uleb128(data, offset)
    end = offset + length
    if length < 0 or end > len(data):
        raise WasmError(f"name overruns buffer at offset {offset}")
    try:
        text = data[offset:end].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WasmError(f"invalid UTF-8 name at offset {offset}") from exc
    return text, end


def _skip_limits(data: bytes, offset: int) -> int:
    if offset >= len(data):
        raise WasmError(f"truncated limits at offset {offset}")
    flags = data[offset]
    offset += 1
    _minimum, offset = _read_uleb128(data, offset)
    if flags & 0x01:
        _maximum, offset = _read_uleb128(data, offset)
    return offset


def _skip_global_type(data: bytes, offset: int) -> int:
    if offset + 2 > len(data):
        raise WasmError(f"truncated globaltype at offset {offset}")
    # valtype byte + mutability byte
    return offset + 2


def parse_imports(section: bytes) -> list[dict[str, object]]:
    imports: list[dict[str, object]] = []
    count, offset = _read_uleb128(section, 0)
    if count > DEFAULT_MAX_VECTOR:
        raise WasmError(f"import count exceeds limit {DEFAULT_MAX_VECTOR}")
    for _ in range(count):
        module, offset = _read_name(section, offset)
        name, offset = _read_name(section, offset)
        if offset >= len(section):
            raise WasmError("truncated import descriptor")
        kind = section[offset]
        offset += 1
        entry: dict[str, object] = {
            "module": module,
            "name": name,
            "kind": IMPORT_KINDS.get(kind, f"unknown({kind})"),
        }
        if kind == 0:
            type_index, offset = _read_uleb128(section, offset)
            entry["typeIndex"] = type_index
        elif kind == 1:
            offset += 1  # reftype
            offset = _skip_limits(section, offset)
        elif kind == 2:
            offset = _skip_limits(section, offset)
        elif kind == 3:
            offset = _skip_global_type(section, offset)
        else:
            raise WasmError(f"unknown import kind {kind}")
        imports.append(entry)
    return imports


def parse_exports(section: bytes) -> list[dict[str, object]]:
    exports: list[dict[str, object]] = []
    count, offset = _read_uleb128(section, 0)
    if count > DEFAULT_MAX_VECTOR:
        raise WasmError(f"export count exceeds limit {DEFAULT_MAX_VECTOR}")
    for _ in range(count):
        name, offset = _read_name(section, offset)
        if offset >= len(section):
            raise WasmError("truncated export descriptor")
        kind = section[offset]
        offset += 1
        index, offset = _read_uleb128(section, offset)
        exports.append(
            {
                "name": name,
                "kind": EXPORT_KINDS.get(kind, f"unknown({kind})"),
                "index": index,
            }
        )
    return exports


def _vector_count(section: bytes) -> int:
    count, _ = _read_uleb128(section, 0)
    return count


def inspect_module(
    data: bytes,
    *,
    max_sections: int = DEFAULT_MAX_SECTIONS,
) -> dict[str, object]:
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    if len(data) < 8:
        raise WasmError("input too small to be a WebAssembly module")
    if data[:4] != WASM_MAGIC:
        raise WasmError("bad magic: not a WebAssembly module")
    version = int.from_bytes(data[4:8], "little")

    sections: list[dict[str, object]] = []
    imports: list[dict[str, object]] = []
    exports: list[dict[str, object]] = []
    counts = {"function": 0, "memory": 0, "table": 0, "global": 0}

    offset = 8
    total = len(data)
    while offset < total:
        if len(sections) >= max_sections:
            raise WasmError(f"section count exceeds limit {max_sections}")
        section_id = data[offset]
        offset += 1
        size, offset = _read_uleb128(data, offset)
        end = offset + size
        if size < 0 or end > total:
            raise WasmError(f"section {section_id} overruns buffer at offset {offset}")
        body = data[offset:end]
        name = SECTION_NAMES.get(section_id, f"unknown({section_id})")
        sections.append({"id": section_id, "name": name, "size": size})

        if section_id == 2:
            imports = parse_imports(body)
        elif section_id == 7:
            exports = parse_exports(body)
        elif section_id == 3:
            counts["function"] = _vector_count(body)
        elif section_id == 5:
            counts["memory"] = _vector_count(body)
        elif section_id == 4:
            counts["table"] = _vector_count(body)
        elif section_id == 6:
            counts["global"] = _vector_count(body)

        offset = end

    return {
        "version": version,
        "sectionCount": len(sections),
        "sections": sections,
        "imports": imports,
        "exports": exports,
        "counts": counts,
        "functionExports": [e["name"] for e in exports if e["kind"] == "func"],
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _uleb128(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _name_bytes(text: str) -> bytes:
    raw = text.encode("utf-8")
    return _uleb128(len(raw)) + raw


def _section(section_id: int, body: bytes) -> bytes:
    return bytes([section_id]) + _uleb128(len(body)) + body


def self_test() -> None:
    # Minimal module: one import (env.abort func type 0), one export ("sign" func index 0).
    import_body = _uleb128(1) + _name_bytes("env") + _name_bytes("abort") + b"\x00" + _uleb128(0)
    export_body = _uleb128(1) + _name_bytes("sign") + b"\x00" + _uleb128(0)
    function_body = _uleb128(2)  # declares 2 functions (counts only)
    module = (
        WASM_MAGIC
        + (1).to_bytes(4, "little")
        + _section(2, import_body)
        + _section(3, function_body)
        + _section(7, export_body)
    )
    report = inspect_module(module)
    _require(report["version"] == 1, "version")
    _require(report["functionExports"] == ["sign"], "function export located")
    imports = report["imports"]
    first_import = imports[0] if isinstance(imports, list) else {}
    _require(
        first_import.get("module") == "env" and first_import.get("name") == "abort",
        "import located",
    )
    counts = report["counts"]
    _require(isinstance(counts, dict) and counts.get("function") == 2, "function count")

    invalid_cases = (
        b"not-wasm-",              # bad magic
        WASM_MAGIC + b"\x01\x00",  # truncated version
        WASM_MAGIC + (1).to_bytes(4, "little") + b"\x07\x7f",  # section size overruns
    )
    failures = 0
    for invalid in invalid_cases:
        try:
            inspect_module(invalid)
        except WasmError:
            failures += 1
    _require(failures == len(invalid_cases), "negative controls")
    print("wasm_module_inspect_self_test=PASS exports=1 imports=1 negative_controls=3")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="Path to a .wasm binary")
    parser.add_argument("--max-input-bytes", type=int, default=DEFAULT_MAX_INPUT_BYTES)
    parser.add_argument("--max-sections", type=int, default=DEFAULT_MAX_SECTIONS)
    parser.add_argument(
        "--include-input-sha256",
        action="store_true",
        help="Include the module SHA-256 for task-local correlation",
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
        ("max-sections", args.max_sections),
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

    try:
        report = inspect_module(raw, max_sections=args.max_sections)
    except (WasmError, ValueError, TypeError) as exc:
        return _error(str(exc), input_file=input_path.name)

    report["ok"] = True
    report["inputFile"] = input_path.name
    report["byteLength"] = len(raw)
    if args.include_input_sha256:
        report["inputSha256"] = hashlib.sha256(raw).hexdigest()
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
