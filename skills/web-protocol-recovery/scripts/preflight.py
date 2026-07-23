#!/usr/bin/env python3
"""Skill preflight gate for web-protocol-recovery.

Runs offline checks that should pass before committing skill edits:

1. case hash/registry integrity (verify_case_hashes.py)
2. all case unit tests discovered under references/cases/*/*/tests
3. discipline scans on case entry.py files:
   - bare top-level `import iv8`
   - import-time mkdir/network/request binding
   - module-level live side effects (AST): with-blocks, requests.*,
     _iv8()/JSContext, mkdir, raise RuntimeError for missing live state

Exit 0 when no hard failures. Exit 1 on hash/test failures.
Warnings alone do not fail unless --strict.
With --strict, both WARN and LEGACY_WARN fail the gate.
Legacy classification comes from case.json verificationClass=historical-user-attested,
not a hardcoded path list.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
CASES_ROOT = SKILL_ROOT / "references" / "cases"

HISTORICAL_VERIFICATION_CLASS = "historical-user-attested"

BARE_IV8_IMPORT = re.compile(r"(?m)^\s*import\s+iv8\b|^\s*from\s+iv8\s+import\b")
IMPORT_TIME_MKDIR = re.compile(
    r"(?m)^(CACHE_DIR|SOURCE_DIR|IV8_DIR|Path\.cwd\(\)[^\n]*cache[^\n]*)[^\n]*\n[^\n]*mkdir\("
)
IMPORT_TIME_NETWORK = re.compile(
    r"(?m)^(url\s*=\s*[\"']https?://|response\s*=\s*requests\.|session\s*=\s*requests\.)"
)

# Attribute chains that count as import-time/live side effects.
# Keep this narrow: pure helpers like os.environ.get, urllib.parse.quote,
# Path(...), json.loads must not warn.
SIDE_EFFECT_CALL_PREFIXES = (
    ("requests",),
    ("httpx",),
    ("aiohttp",),
    ("urllib", "request"),
    ("http", "client"),
    ("http", "server"),
)
SIDE_EFFECT_CALL_SUFFIXES = {
    "JSContext",
    "mkdir",
    "urlopen",
}
SIDE_EFFECT_FUNCS = {
    "_iv8",
    "ensure_cache_dir",
}


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


def case_rel_from_entry(path: Path) -> str:
    return path.parent.relative_to(CASES_ROOT).as_posix()


def load_verification_class(case_rel: str) -> str | None:
    case_json = CASES_ROOT / case_rel / "case.json"
    if not case_json.is_file():
        return None
    try:
        data = json.loads(case_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = data.get("verificationClass")
    return value if isinstance(value, str) else None


def is_historical_case(case_rel: str) -> bool:
    return load_verification_class(case_rel) == HISTORICAL_VERIFICATION_CLASS


def _attr_chain(node: ast.AST) -> list[str]:
    parts: list[str] = []
    cur: ast.AST | None = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    return list(reversed(parts))


def is_side_effect_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id in SIDE_EFFECT_FUNCS
    chain = _attr_chain(func)
    if not chain:
        return False
    if any(tuple(chain[: len(prefix)]) == prefix for prefix in SIDE_EFFECT_CALL_PREFIXES):
        return True
    if chain[-1] in SIDE_EFFECT_CALL_SUFFIXES:
        return True
    if "JSContext" in chain:
        return True
    return False


def is_main_guard(node: ast.If) -> bool:
    test = node.test
    if not isinstance(test, ast.Compare) or len(test.ops) != 1 or len(test.comparators) != 1:
        return False
    if not isinstance(test.ops[0], ast.Eq):
        return False
    left, right = test.left, test.comparators[0]

    def const_str(n: ast.AST) -> str | None:
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            return n.value
        return None

    left_name = left.id if isinstance(left, ast.Name) else None
    right_name = right.id if isinstance(right, ast.Name) else None
    left_str = const_str(left)
    right_str = const_str(right)
    if left_name == "__name__" and right_str == "__main__":
        return True
    if right_name == "__name__" and left_str == "__main__":
        return True
    return False


def contains_side_effect_call(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and is_side_effect_call(child):
            return True
        if isinstance(child, ast.Raise):
            return True
    return False


def scan_entry_head(path: Path, text: str) -> list[str]:
    warnings: list[str] = []
    rel = path.relative_to(SKILL_ROOT).as_posix()
    head = text
    m = re.search(r"(?m)^(def |class )", text)
    if m:
        head = text[: m.start()]
    if BARE_IV8_IMPORT.search(head):
        warnings.append(f"bare iv8 import at module level: {rel}")
    if IMPORT_TIME_MKDIR.search(head) or re.search(r"(?m)^\S.*\.mkdir\(", head):
        for line in head.splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if ".mkdir(" in s and "def " not in s:
                warnings.append(f"possible import-time mkdir: {rel}: {s[:120]}")
                break
    if IMPORT_TIME_NETWORK.search(head):
        warnings.append(f"possible import-time network/request binding: {rel}")
    return warnings


def scan_entry_ast(path: Path, text: str) -> list[str]:
    rel = path.relative_to(SKILL_ROOT).as_posix()
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        return [f"syntax error in entry: {rel}: {exc}"]

    warnings: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            else:
                if node.module:
                    names.append(node.module)
                names.extend(alias.name for alias in node.names)
            if any(name == "iv8" or name.startswith("iv8.") for name in names):
                warnings.append(f"bare iv8 import at module level: {rel}:{node.lineno}")
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Pass)):
            continue
        if isinstance(node, ast.If) and is_main_guard(node):
            continue
        if isinstance(node, ast.With):
            warnings.append(f"module-level with-block (import executes body): {rel}:{node.lineno}")
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            if is_side_effect_call(node.value):
                warnings.append(
                    f"module-level call side effect: {rel}:{node.lineno}"
                )
            continue
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and is_side_effect_call(child):
                    warnings.append(
                        f"module-level assign with side-effect call: {rel}:{node.lineno}"
                    )
                    break
            continue
        if isinstance(node, ast.Raise):
            warnings.append(f"module-level raise (import aborts): {rel}:{node.lineno}")
            continue
        if isinstance(node, (ast.For, ast.While, ast.Try, ast.If)):
            if contains_side_effect_call(node):
                warnings.append(
                    f"module-level control-flow side effect: {rel}:{node.lineno}"
                )
            continue
    return warnings


def scan_entry(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    warnings = scan_entry_head(path, text)
    warnings.extend(scan_entry_ast(path, text))
    # de-dupe while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for w in warnings:
        if w not in seen:
            seen.add(w)
            ordered.append(w)
    return ordered


def scan_entries() -> list[tuple[str, str]]:
    """Return list of (case_rel, warning_message)."""
    results: list[tuple[str, str]] = []
    for entry in CASES_ROOT.glob("*/*/entry.py"):
        case_rel = case_rel_from_entry(entry)
        for warning in scan_entry(entry):
            results.append((case_rel, warning))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat WARN and LEGACY_WARN entry discipline findings as failures",
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
    entry_findings = scan_entries()
    if not entry_findings:
        print("no discipline warnings")
    else:
        for case_rel, w in entry_findings:
            if is_historical_case(case_rel):
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
    if args.strict and (warnings or legacy_warnings):
        print("FAIL strict mode with warnings")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
