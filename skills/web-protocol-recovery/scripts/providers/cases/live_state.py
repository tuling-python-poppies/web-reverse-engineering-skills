#!/usr/bin/env python3
"""Select case-scoped live cookies and storage values without persisting them."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _read_payload(source: str):
    text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    value = json.loads(text)
    if not isinstance(value, (dict, list)):
        raise ValueError("live state must be a JSON object or cookie list")
    return value


def _cookies_from(value) -> dict[str, str]:
    if isinstance(value, list):
        result = {}
        for item in value:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                raw = item.get("value")
                if isinstance(raw, str):
                    result[item["name"]] = raw
        return result

    raw = value.get("cookies", value)
    if isinstance(raw, list):
        return _cookies_from(raw)
    if not isinstance(raw, dict):
        return {}

    result = {}
    for name, item in raw.items():
        if isinstance(item, str):
            result[str(name)] = item
        elif isinstance(item, dict):
            candidate = item.get("current_value", item.get("value"))
            if isinstance(candidate, str):
                result[str(name)] = candidate
    return result


def _storage_from(value) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result = {}
    for field in ("storage", "localStorage"):
        raw = value.get(field)
        if isinstance(raw, dict):
            result.update({str(k): str(v) for k, v in raw.items()})
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and isinstance(item.get("name"), str):
                    result[item["name"]] = str(item.get("value", ""))
    origins = value.get("origins", [])
    if isinstance(origins, list):
        for origin in origins:
            if isinstance(origin, dict):
                result.update(_storage_from(origin))
    return result


def select_live_state(payload, config: dict) -> dict:
    cookies = _cookies_from(payload)
    storage = _storage_from(payload)
    required = tuple(config.get("requiredCookies", ()))
    optional = tuple(config.get("optionalCookies", ()))
    patterns = tuple(config.get("cookieNamePatterns", ()))
    storage_keys = tuple(config.get("storageKeys", ()))

    missing = [name for name in required if not cookies.get(name)]
    if missing:
        raise ValueError("missing required live cookies: " + ", ".join(missing))

    selected_cookies = {
        name: cookies[name]
        for name in (*required, *optional)
        if isinstance(cookies.get(name), str) and cookies[name]
    }
    for name, value in cookies.items():
        if value and any(re.fullmatch(pattern, name) for pattern in patterns):
            selected_cookies[name] = value

    selected_storage = {
        name: storage[name]
        for name in storage_keys
        if isinstance(storage.get(name), str) and storage[name]
    }
    return {"cookies": selected_cookies, "storage": selected_storage}


def run_case(config: dict) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", default="-", help="JSON path or '-' for stdin")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        selected = select_live_state(_read_payload(args.source), config)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(selected, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", default="-", help="JSON path or '-' for stdin")
    parser.add_argument("--cookie", action="append", default=[])
    parser.add_argument("--optional-cookie", action="append", default=[])
    parser.add_argument("--cookie-pattern", action="append", default=[])
    parser.add_argument("--storage-key", action="append", default=[])
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    config = {
        "requiredCookies": args.cookie,
        "optionalCookies": args.optional_cookie,
        "cookieNamePatterns": args.cookie_pattern,
        "storageKeys": args.storage_key,
    }
    try:
        selected = select_live_state(_read_payload(args.source), config)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(selected, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
