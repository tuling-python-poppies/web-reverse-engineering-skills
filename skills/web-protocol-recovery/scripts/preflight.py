#!/usr/bin/env python3
"""Skill preflight gate for web-protocol-recovery.

Runs offline checks that should pass before committing skill edits:

1. case hash/registry integrity (verify_case_hashes.py)
2. all case unit tests discovered under references/cases/*/*/tests
3. discipline scans on case entry.py files:
   - bare top-level `import iv8` in new-style deliveries (warn)
   - import-time mkdir/network hints (warn/fail configurable)

Exit 0 when no hard failures. Exit 1 on hash/test failures.
Warnings alone do not fail unless --strict.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
CASES_ROOT = SKILL_ROOT / "references" / "cases"

LEGACY_DISCIPLINE_WARNING_CASES = {
    "iv8/chinatax-ruishu",
    "iv8/chng-ruishu-announcement",
    "iv8/cqvip-journal-search",
    "iv8/customs-ruishu",
    "iv8/douyin-bdms",
    "iv8/geetest-v4-slider",
    "iv8/geetest-v4-word-click",
    "iv8/nmpa-md5-cookie",
    "iv8/ouyeel-202-cookie-url",
    "iv8/pdd-anti-content",
    "iv8/tencent-tdc-slider",
    "iv8/xhs-homefeed",
    "iv8/zhipin-stoken",
}

BARE_IV8_IMPORT = re.compile(r"(?m)^\s*import\s+iv8\b|^\s*from\s+iv8\s+import\b")
IMPORT_TIME_MKDIR = re.compile(
    r"(?m)^(CACHE_DIR|SOURCE_DIR|IV8_DIR|Path\.cwd\(\)[^\n]*cache[^\n]*)[^\n]*\n[^\n]*mkdir\("
)
IMPORT_TIME_NETWORK = re.compile(
    r"(?m)^(url\s*=\s*[\"']https?://|response\s*=\s*requests\.|session\s*=\s*requests\.)"
)


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def check_hashes() -> tuple[bool, str]:
    code, out = run([sys.executable, "scripts/verify_case_hashes.py"], SKILL_ROOT)
    return code == 0, out.strip()


def discover_test_cases() -> tuple[str, ...]:
    rel_cases: list[str] = []
    for tests_dir in sorted(CASES_ROOT.glob("*/*/tests")):
        if not tests_dir.is_dir():
            continue
        if not any(tests_dir.glob("test*.py")):
            continue
        rel_cases.append(tests_dir.parent.relative_to(CASES_ROOT).as_posix())
    return tuple(rel_cases)


def check_case_tests(rel_case: str) -> tuple[bool, str]:
    case_dir = CASES_ROOT / rel_case
    tests_dir = case_dir / "tests"
    if not tests_dir.is_dir():
        return True, f"SKIP tests missing: {rel_case}"
    code, out = run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        case_dir,
    )
    return code == 0, f"{rel_case}\n{out.strip()}"


def scan_entry(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    warnings: list[str] = []
    # Only scan top portion for import-time side effects (before first def/class)
    head = text
    m = re.search(r"(?m)^(def |class )", text)
    if m:
        head = text[: m.start()]
    if BARE_IV8_IMPORT.search(head):
        warnings.append(f"bare iv8 import at module level: {path.relative_to(SKILL_ROOT).as_posix()}")
    if IMPORT_TIME_MKDIR.search(head) or re.search(r"(?m)^\S.*\.mkdir\(", head):
        # allow comments
        for line in head.splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if ".mkdir(" in s and "def " not in s:
                warnings.append(
                    f"possible import-time mkdir: {path.relative_to(SKILL_ROOT).as_posix()}: {s[:120]}"
                )
                break
    if IMPORT_TIME_NETWORK.search(head):
        warnings.append(
            f"possible import-time network/request binding: {path.relative_to(SKILL_ROOT).as_posix()}"
        )
    return warnings


def scan_entries() -> list[str]:
    warnings: list[str] = []
    for entry in CASES_ROOT.glob("*/*/entry.py"):
        warnings.extend(scan_entry(entry))
    return warnings


def is_legacy_discipline_warning(warning: str) -> bool:
    return any(
        f"references/cases/{case}/entry.py" in warning
        for case in LEGACY_DISCIPLINE_WARNING_CASES
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat entry discipline warnings as failures",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="skip case unit tests",
    )
    args = parser.parse_args(argv)

    failures: list[str] = []
    warnings: list[str] = []
    legacy_warnings: list[str] = []

    print("== hash verify ==")
    ok, out = check_hashes()
    print(out)
    if not ok:
        failures.append("verify_case_hashes failed")

    if not args.skip_tests:
        print("\n== case unit tests ==")
        test_cases = discover_test_cases()
        if not test_cases:
            print("SKIP no case tests discovered")
        for rel in test_cases:
            ok, out = check_case_tests(rel)
            print(out)
            print("---")
            if not ok:
                failures.append(f"tests failed: {rel}")

    print("\n== entry discipline scan ==")
    entry_warnings = scan_entries()
    if not entry_warnings:
        print("no discipline warnings")
    else:
        for w in entry_warnings:
            if is_legacy_discipline_warning(w):
                print(f"LEGACY_WARN {w}")
                legacy_warnings.append(w)
            else:
                print(f"WARN {w}")
                warnings.append(w)

    print("\n== summary ==")
    print(
        f"failures={len(failures)} warnings={len(warnings)} "
        f"legacy_warnings={len(legacy_warnings)} strict={args.strict}"
    )
    if failures:
        for f in failures:
            print(f"FAIL {f}")
        return 1
    if args.strict and warnings:
        print("FAIL strict mode with warnings")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
