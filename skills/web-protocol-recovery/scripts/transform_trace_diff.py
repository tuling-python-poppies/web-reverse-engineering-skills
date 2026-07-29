#!/usr/bin/env python3
"""Compare ordered runtime transform traces and report the first divergence."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence


MAX_INPUT_BYTES = 20 * 1024 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class TraceError(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_payload(value: Any, label: str) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TraceError(f"{label} must be an object")
    if "data" in value:
        encoding = value.get("encoding")
        raw = value.get("data")
        if not isinstance(raw, str) or encoding not in {"base64", "hex", "utf8"}:
            raise TraceError(f"{label} raw descriptor needs base64, hex, or utf8 text")
        try:
            if encoding == "base64":
                data = base64.b64decode(raw, validate=True)
            elif encoding == "hex":
                data = bytes.fromhex(raw)
            else:
                data = raw.encode("utf-8")
        except (ValueError, binascii.Error) as exc:
            raise TraceError(f"{label} contains invalid {encoding} data") from exc
        return {"length": len(data), "sha256": sha256_bytes(data), "raw": data}
    length = value.get("length")
    digest = value.get("sha256")
    if not isinstance(length, int) or length < 0:
        raise TraceError(f"{label}.length must be a non-negative integer")
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        raise TraceError(f"{label}.sha256 must be lowercase SHA-256")
    return {"length": length, "sha256": digest, "raw": None}


def parse_trace(document: Any, label: str) -> List[Dict[str, Any]]:
    if not isinstance(document, Mapping) or document.get("traceVersion") != 1:
        raise TraceError(f"{label} must use traceVersion=1")
    stages = document.get("stages")
    if not isinstance(stages, list) or not stages:
        raise TraceError(f"{label}.stages must be a non-empty list")
    parsed: List[Dict[str, Any]] = []
    occurrences: Dict[str, int] = {}
    for index, stage in enumerate(stages):
        if not isinstance(stage, Mapping) or not isinstance(stage.get("name"), str):
            raise TraceError(f"{label}.stages[{index}] needs a name")
        name = stage["name"]
        occurrence = occurrences.get(name, 0)
        occurrences[name] = occurrence + 1
        parsed.append({
            "index": index,
            "name": name,
            "occurrence": occurrence,
            "input": parse_payload(stage.get("input"), f"{label}.stages[{index}].input"),
            "output": parse_payload(stage.get("output"), f"{label}.stages[{index}].output"),
        })
    return parsed


def first_byte_difference(left: Optional[bytes], right: Optional[bytes]) -> Optional[int]:
    if left is None or right is None:
        return None
    for index, (lbyte, rbyte) in enumerate(zip(left, right)):
        if lbyte != rbyte:
            return index
    return min(len(left), len(right)) if len(left) != len(right) else None


def compare(left: List[Dict[str, Any]], right: List[Dict[str, Any]]) -> Dict[str, Any]:
    limit = min(len(left), len(right))
    for index in range(limit):
        lstage, rstage = left[index], right[index]
        if (lstage["name"], lstage["occurrence"]) != (rstage["name"], rstage["occurrence"]):
            return {
                "equal": False,
                "firstDifference": {"stageIndex": index, "part": "stage-order", "left": lstage["name"], "right": rstage["name"]},
            }
        for part in ("input", "output"):
            lp, rp = lstage[part], rstage[part]
            if lp["length"] != rp["length"] or lp["sha256"] != rp["sha256"]:
                return {
                    "equal": False,
                    "firstDifference": {
                        "stageIndex": index,
                        "stageName": lstage["name"],
                        "occurrence": lstage["occurrence"],
                        "part": part,
                        "firstByteOffset": first_byte_difference(lp["raw"], rp["raw"]),
                        "left": {"length": lp["length"], "sha256": lp["sha256"]},
                        "right": {"length": rp["length"], "sha256": rp["sha256"]},
                    },
                }
    if len(left) != len(right):
        return {"equal": False, "firstDifference": {"stageIndex": limit, "part": "stage-count", "left": len(left), "right": len(right)}}
    return {"equal": True, "firstDifference": None}


def load_trace(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
        raise TraceError(f"invalid or oversized trace: {path}")
    return parse_trace(json.loads(path.read_text(encoding="utf-8-sig")), str(path))


def raw_payload(data: bytes) -> Dict[str, str]:
    return {"encoding": "base64", "data": base64.b64encode(data).decode("ascii")}


def run_self_test() -> None:
    left_doc = {"traceVersion": 1, "stages": [{"name": "pack", "input": raw_payload(b"abc"), "output": raw_payload(b"xyz")}]}
    right_doc = {"traceVersion": 1, "stages": [{"name": "pack", "input": raw_payload(b"abc"), "output": raw_payload(b"xYz")}]}
    result = compare(parse_trace(left_doc, "left"), parse_trace(right_doc, "right"))
    assert result["firstDifference"]["firstByteOffset"] == 1
    assert compare(parse_trace(left_doc, "left"), parse_trace(left_doc, "right"))["equal"] is True
    print("transform_trace_diff_self_test=PASS")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", nargs="?")
    parser.add_argument("right", nargs="?")
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
            raise TraceError("left and right trace paths are required")
        result = compare(load_trace(Path(args.left)), load_trace(Path(args.right)))
        if args.json:
            print(json.dumps(result, indent=2))
        elif result["equal"]:
            print("traces_equal=true")
        else:
            print("traces_equal=false")
            print(json.dumps(result["firstDifference"], sort_keys=True))
        return 0 if result["equal"] else 2
    except (TraceError, OSError, json.JSONDecodeError, AssertionError) as exc:
        print(f"transform_trace_diff=FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
