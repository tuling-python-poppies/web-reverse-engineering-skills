#!/usr/bin/env python3
"""Report the first structural difference between normalized evidence chains."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


SCHEMA = "web-protocol-recovery-evidence/v1"
MAX_INPUT_BYTES = 20 * 1024 * 1024


class TranscriptError(ValueError):
    pass


def fingerprint(value: Any) -> Dict[str, Any]:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"type": type(value).__name__, "length": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def load_document(path: Path) -> Mapping[str, Any]:
    if not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
        raise TranscriptError(f"invalid or oversized input: {path}")
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, Mapping) or value.get("schemaVersion") != SCHEMA:
        raise TranscriptError(f"{path} is not {SCHEMA}")
    return value


def select_chain(document: Mapping[str, Any], chain_id: Optional[str]) -> Mapping[str, Any]:
    chains = document.get("chains")
    if not isinstance(chains, list) or not chains:
        raise TranscriptError("evidence package contains no chains")
    if chain_id is None:
        if len(chains) != 1:
            raise TranscriptError("multiple chains require --chain-id")
        chain = chains[0]
    else:
        matches = [item for item in chains if isinstance(item, Mapping) and item.get("id") == chain_id]
        if len(matches) != 1:
            raise TranscriptError(f"chain id must match exactly once: {chain_id}")
        chain = matches[0]
    if not isinstance(chain, Mapping) or not isinstance(chain.get("steps"), list):
        raise TranscriptError("invalid chain structure")
    return chain


def first_difference(left: Any, right: Any, path: str = "$") -> Optional[Tuple[str, Any, Any, str]]:
    if type(left) is not type(right):
        return path, left, right, "type"
    if isinstance(left, Mapping):
        left_keys = list(left.keys())
        right_keys = list(right.keys())
        if left_keys != right_keys:
            max_len = max(len(left_keys), len(right_keys))
            for index in range(max_len):
                lk = left_keys[index] if index < len(left_keys) else None
                rk = right_keys[index] if index < len(right_keys) else None
                if lk != rk:
                    return f"{path}.<key:{index}>", lk, rk, "mapping-key-order"
        for key in left_keys:
            found = first_difference(left[key], right[key], f"{path}.{key}")
            if found:
                return found
        return None
    if isinstance(left, list):
        if len(left) != len(right):
            return f"{path}.length", len(left), len(right), "list-length"
        for index, (lvalue, rvalue) in enumerate(zip(left, right)):
            found = first_difference(lvalue, rvalue, f"{path}[{index}]")
            if found:
                return found
        return None
    if left != right:
        return path, left, right, "value"
    return None


def compare(left: Mapping[str, Any], right: Mapping[str, Any], chain_id: Optional[str]) -> Dict[str, Any]:
    lchain = select_chain(left, chain_id)
    rchain = select_chain(right, chain_id)
    difference = first_difference(lchain.get("steps"), rchain.get("steps"), "$.steps")
    if difference is None:
        return {"equal": True, "chainId": lchain.get("id"), "firstDifference": None}
    path, lvalue, rvalue, kind = difference
    return {
        "equal": False,
        "chainId": lchain.get("id"),
        "firstDifference": {
            "path": path,
            "kind": kind,
            "left": fingerprint(lvalue),
            "right": fingerprint(rvalue),
        },
    }


def run_self_test() -> None:
    base = {"schemaVersion": SCHEMA, "chains": [{"id": "chain-0", "steps": [{"request": {"headers": [{"name": "x-a"}, {"name": "x-b"}]}, "response": {"status": 200}}]}]}
    changed = json.loads(json.dumps(base))
    changed["chains"][0]["steps"][0]["request"]["headers"][1]["name"] = "x-c"
    result = compare(base, changed, None)
    assert result["firstDifference"]["path"] == "$.steps[0].request.headers[1].name"
    assert compare(base, base, None)["equal"] is True
    print("transcript_diff_self_test=PASS")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", nargs="?")
    parser.add_argument("right", nargs="?")
    parser.add_argument("--chain-id")
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
            raise TranscriptError("left and right paths are required")
        result = compare(load_document(Path(args.left)), load_document(Path(args.right)), args.chain_id)
        if args.json:
            print(json.dumps(result, indent=2))
        elif result["equal"]:
            print("chains_equal=true")
        else:
            diff = result["firstDifference"]
            print("chains_equal=false")
            print(f"first_difference={diff['path']} kind={diff['kind']}")
            print(f"left={diff['left']}")
            print(f"right={diff['right']}")
        return 0 if result["equal"] else 2
    except (TranscriptError, OSError, json.JSONDecodeError, AssertionError) as exc:
        print(f"transcript_diff=FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
