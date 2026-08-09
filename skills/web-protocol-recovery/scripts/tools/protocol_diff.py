#!/usr/bin/env python3
"""
Compare two captured protocol samples and surface meaningful deltas.
"""

from __future__ import annotations

import argparse
import difflib
import itertools
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional


SENSITIVE_PATH_PARTS = (
    "authorization",
    "cookie",
    "passwd",
    "password",
    "secret",
    "session",
    "token",
    "api-key",
    "apikey",
    "credential",
    "csrf",
)
MAX_INPUT_BYTES = 5 * 1024 * 1024
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 100_000
MAX_TEXT_LINES = 5_000
SENSITIVE_TEXT_RE = re.compile(
    r"(?i)(authorization|proxy-authorization|cookie|set-cookie|x-api-key|api[_-]?key|token|secret|session(?:id)?)(\s*[:=]\s*)([^\s,;&]+)"
)
SENSITIVE_HEADER_LINE_RE = re.compile(
    r"(?i)^([+\- ]?(?:authorization|proxy-authorization|cookie|set-cookie|x-api-key|api[_-]?key|token|secret|session(?:id)?)\s*:).*$"
)


def load_text(path: Path) -> str:
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError(f"input exceeds {MAX_INPUT_BYTES} bytes: {path}")
    return path.read_text(encoding="utf-8-sig")


def try_load_json(text: str) -> Optional[Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def flatten_json(value: Any, prefix: str = "$", *, depth: int = 0, counter: Optional[list[int]] = None) -> dict[str, str]:
    if depth > MAX_JSON_DEPTH:
        raise ValueError(f"JSON nesting exceeds {MAX_JSON_DEPTH}")
    if counter is None:
        counter = [0]
    counter[0] += 1
    if counter[0] > MAX_JSON_NODES:
        raise ValueError(f"JSON node count exceeds {MAX_JSON_NODES}")
    rows: dict[str, str] = {}
    if isinstance(value, dict):
        label_key = "name" if "name" in value else "key" if "key" in value else None
        sensitive_name = str(value.get(label_key, "")).lower() if label_key else ""
        for key in sorted(value):
            child_key = f"{prefix}.{key}"
            if key == "value" and label_key:
                marker = "sensitive-name-value" if any(part in sensitive_name for part in SENSITIVE_PATH_PARTS) else "named-value"
                child_key += f"<{marker}>"
            rows.update(flatten_json(value[key], child_key, depth=depth + 1, counter=counter))
        return rows
    if isinstance(value, list):
        sensitive_pair = (
            len(value) == 2
            and isinstance(value[0], str)
            and any(part in value[0].lower() for part in SENSITIVE_PATH_PARTS)
        )
        for index, item in enumerate(value):
            child_prefix = f"{prefix}[{index}]"
            if sensitive_pair and index == 1:
                child_prefix += "<sensitive-name-value>"
            rows.update(flatten_json(item, child_prefix, depth=depth + 1, counter=counter))
        return rows
    rows[prefix] = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return rows


def should_ignore(path: str, ignored_paths: list[str]) -> bool:
    return any(path == ignored or path.startswith(f"{ignored}.") or path.startswith(f"{ignored}[") for ignored in ignored_paths)


def is_sensitive_path(path: str) -> bool:
    lowered = path.lower()
    return "<named-value>" in lowered or "<sensitive-name-value>" in lowered or any(part in lowered for part in SENSITIVE_PATH_PARTS)


def format_value(path: str, value: str, *, max_value_len: int, redact: bool) -> str:
    if redact and is_sensitive_path(path):
        return f"<redacted len={len(value)}>"
    if redact and any(part in value.lower() for part in SENSITIVE_PATH_PARTS):
        return f"<redacted embedded-sensitive len={len(value)}>"
    rendered = SENSITIVE_TEXT_RE.sub(r"\1\2<redacted>", value) if redact else value
    if len(rendered) <= max_value_len:
        return rendered
    return f"{rendered[:max_value_len]}... <truncated len={len(rendered)}>"


def redact_text_line(line: str) -> str:
    if SENSITIVE_HEADER_LINE_RE.match(line):
        return SENSITIVE_HEADER_LINE_RE.sub(r"\1 <redacted>", line)
    rendered = SENSITIVE_TEXT_RE.sub(r"\1\2<redacted>", line)
    if any(part in rendered.lower() for part in SENSITIVE_PATH_PARTS):
        prefix = rendered[0] if rendered[:1] in {"+", "-", " "} else ""
        return f"{prefix}<redacted sensitive line len={len(line)}>"
    return rendered


def filter_map(rows: dict[str, str], ignored_paths: list[str]) -> dict[str, str]:
    if not ignored_paths:
        return rows
    return {key: value for key, value in rows.items() if not should_ignore(key, ignored_paths)}


def compare_json(
    left: Any,
    right: Any,
    max_diffs: int,
    *,
    max_value_len: int,
    ignored_paths: list[str],
    redact: bool,
) -> None:
    left_map = flatten_json(left)
    right_map = flatten_json(right)
    left_map = filter_map(left_map, ignored_paths)
    right_map = filter_map(right_map, ignored_paths)
    keys = sorted(set(left_map) | set(right_map))

    only_left = [key for key in keys if key not in right_map]
    only_right = [key for key in keys if key not in left_map]
    changed = [key for key in keys if key in left_map and key in right_map and left_map[key] != right_map[key]]

    print("mode=json")
    print(f"left_only={len(only_left)}")
    print(f"right_only={len(only_right)}")
    print(f"changed={len(changed)}")

    for key in only_left[:max_diffs]:
        print(f"- left_only {key} = {format_value(key, left_map[key], max_value_len=max_value_len, redact=redact)}")
    for key in only_right[:max_diffs]:
        print(f"- right_only {key} = {format_value(key, right_map[key], max_value_len=max_value_len, redact=redact)}")
    for key in changed[:max_diffs]:
        print(f"- changed {key}")
        print(f"  left:  {format_value(key, left_map[key], max_value_len=max_value_len, redact=redact)}")
        print(f"  right: {format_value(key, right_map[key], max_value_len=max_value_len, redact=redact)}")


def compare_text(left_text: str, right_text: str, max_diffs: int, *, redact: bool) -> None:
    print("mode=text")
    if left_text.count("\n") + 1 > MAX_TEXT_LINES or right_text.count("\n") + 1 > MAX_TEXT_LINES:
        raise ValueError(f"text diff input exceeds {MAX_TEXT_LINES} lines")
    diff = difflib.unified_diff(
            left_text.splitlines(),
            right_text.splitlines(),
            fromfile="left",
            tofile="right",
            lineterm="",
        )
    shown = list(itertools.islice(diff, max_diffs))
    print(f"diff_lines_shown={len(shown)}")
    for line in shown:
        if redact:
            line = redact_text_line(line)
        safe = line.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
            sys.stdout.encoding or "utf-8",
            errors="replace",
        )
        print(safe)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two captured protocol samples.")
    parser.add_argument("left", help="Left sample path")
    parser.add_argument("right", help="Right sample path")
    parser.add_argument("--max-diffs", type=int, default=40, help="Maximum diff rows to print")
    parser.add_argument("--max-value-len", type=int, default=240, help="Maximum JSON scalar value length to print")
    parser.add_argument(
        "--ignore-path",
        action="append",
        default=[],
        help="JSON path prefix to ignore, e.g. $.headers.cookie. Repeat as needed.",
    )
    parser.add_argument("--no-redact", action="store_true", help="Print sensitive paths without masking")
    parser.add_argument("--confirm-raw", action="store_true", help="Confirm raw sensitive output when used with --no-redact")
    parser.add_argument("--json-only", action="store_true", help="Fail instead of falling back to text diff when inputs are not JSON")
    parser.add_argument("--text-only", action="store_true", help="Force text diff even when inputs are valid JSON")
    args = parser.parse_args()

    if args.json_only and args.text_only:
        parser.error("--json-only and --text-only cannot be used together")
    if args.no_redact and not args.confirm_raw:
        parser.error("--no-redact requires --confirm-raw")
    if args.max_diffs < 1 or args.max_diffs > 1000:
        parser.error("--max-diffs must be in 1..1000")
    if args.max_value_len < 16 or args.max_value_len > 4096:
        parser.error("--max-value-len must be in 16..4096")

    left_path = Path(args.left)
    right_path = Path(args.right)

    left_text = load_text(left_path)
    right_text = load_text(right_path)
    left_json = None if args.text_only else try_load_json(left_text)
    right_json = None if args.text_only else try_load_json(right_text)

    print(f"left={left_path}")
    print(f"right={right_path}")

    if left_json is not None and right_json is not None:
        compare_json(
            left_json,
            right_json,
            args.max_diffs,
            max_value_len=args.max_value_len,
            ignored_paths=args.ignore_path,
            redact=not args.no_redact,
        )
        return

    if args.json_only:
        raise SystemExit("inputs are not both valid JSON")

    compare_text(left_text, right_text, args.max_diffs, redact=not args.no_redact)


if __name__ == "__main__":
    main()
