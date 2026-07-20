#!/usr/bin/env python3
"""
Quick environment check for protocol-first reverse work.
"""

from __future__ import annotations

import importlib.util
import argparse
import json
import importlib.metadata
import shutil
import sys
import re


TOOLS = [
    ("python", sys.executable),
    ("node", shutil.which("node")),
    ("npm", shutil.which("npm")),
    ("curl", shutil.which("curl")),
    ("git", shutil.which("git")),
]

PYTHON_MODULES = [
    "iv8",
    "curl_cffi",
]

MIN_PYTHON = (3, 9)
MODULE_NAME_RE = re.compile(r"^[A-Za-z_]\w*$")


def module_status(name: str) -> str:
    return "available" if importlib.util.find_spec(name) else "missing"


def module_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def build_report(required_tools: list[str], required_modules: list[str]) -> dict:
    tool_map = {name: path for name, path in TOOLS}
    module_names = sorted(set(PYTHON_MODULES) | set(required_modules))
    tools = {
        name: {
            "path": path,
            "available": bool(path),
            "required": name in required_tools,
        }
        for name, path in tool_map.items()
    }
    modules = {
        name: {
            "status": module_status(name),
            "version": module_version(name) if module_status(name) == "available" else "missing",
            "required": name in required_modules,
        }
        for name in module_names
    }
    python_ok = sys.version_info >= MIN_PYTHON
    missing_required_tools = [name for name in required_tools if not tool_map.get(name)]
    missing_required_modules = [name for name in required_modules if module_status(name) != "available"]
    return {
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "python_minimum": ".".join(str(part) for part in MIN_PYTHON),
        "python_ok": python_ok,
        "tools": tools,
        "python_modules": modules,
        "missing_required_tools": missing_required_tools,
        "missing_required_modules": missing_required_modules,
        "overall_ok": python_ok and not missing_required_tools and not missing_required_modules,
        "notes": [
            "pure Python protocol replay should work with Python alone",
            "node is useful for preserving tiny JS helpers",
            "iv8 or another embedded runtime is useful when JS needs host semantics without a real browser",
            "curl is useful for quick raw request diffs",
        ],
    }


def print_human(report: dict) -> None:
    print("reverse environment")
    print(f"- python_version: {report['python_version']}")
    print(f"- python_minimum: {report['python_minimum']}")
    print(f"- python_ok: {report['python_ok']}")
    print(f"- python: {report['python_executable']}")
    for name, info in report["tools"].items():
        status = info["path"] or "missing"
        required = " required" if info["required"] else ""
        print(f"- {name}: {status}{required}")
    for name, info in report["python_modules"].items():
        required = " required" if info["required"] else ""
        version = info["version"] if info["status"] == "available" else "missing"
        print(f"- python_module_{name}: {info['status']} version={version}{required}")
    print("notes")
    for note in report["notes"]:
        print(f"- {note}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check local protocol reverse environment.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when Python or required items are missing")
    parser.add_argument("--require-tool", action="append", default=[], help="Tool name that must be on PATH. Repeat as needed.")
    parser.add_argument("--require-module", action="append", default=[], help="Python module that must import. Repeat as needed.")
    args = parser.parse_args()

    invalid_modules = [name for name in args.require_module if not MODULE_NAME_RE.fullmatch(name)]
    if invalid_modules:
        parser.error("--require-module accepts top-level module names only: " + ", ".join(invalid_modules))

    report = build_report(args.require_tool, args.require_module)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)

    if args.strict and not report["overall_ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
