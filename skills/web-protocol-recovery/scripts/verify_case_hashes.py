#!/usr/bin/env python3
"""Verify hash-bound case artifacts and registry manifests.

Cascade after any hash-bound edit:
  target file bytes
    -> case.json artifacts / preRead sha256
    -> registry.json manifest sha256 for that case.json

Exit 0 when every declared path exists, stays in scope, and SHA-256 matches.
Exit 1 on mismatch, missing path, path escape, orphan case, or undeclared case file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any


ARTIFACT_KEYS = ("process", "entry", "pullLiveState")
VERIFICATION_ARTIFACT_KEYS = ("testArtifact", "evidenceArtifact")
IGNORED_CASE_DIR_NAMES = {".pytest_cache", "__pycache__"}
IGNORED_CASE_FILE_NAMES = {".DS_Store", "Thumbs.db"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_relative_posix_path(
    *, label: str, path_value: Any, mismatches: list[str]
) -> PurePosixPath | None:
    if not isinstance(path_value, str) or not path_value:
        mismatches.append(f"{label}: missing path")
        return None
    if "\\" in path_value:
        mismatches.append(f"{label}: path must use POSIX separators: {path_value}")
        return None
    path = PurePosixPath(path_value)
    if path.is_absolute():
        mismatches.append(f"{label}: absolute paths are forbidden: {path_value}")
        return None
    if any(part in {"", ".", ".."} for part in path.parts):
        mismatches.append(f"{label}: path must not contain empty, '.', or '..' segments: {path_value}")
        return None
    if path.parts and path.parts[0].endswith(":"):
        mismatches.append(f"{label}: drive-qualified paths are forbidden: {path_value}")
        return None
    return path


def resolve_declared_path(
    *,
    label: str,
    base: Path,
    allowed_root: Path,
    path_value: Any,
    mismatches: list[str],
) -> tuple[Path, str] | None:
    path = validate_relative_posix_path(
        label=label, path_value=path_value, mismatches=mismatches
    )
    if path is None:
        return None
    resolved = (base / Path(*path.parts)).resolve()
    allowed = allowed_root.resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError:
        mismatches.append(f"{label}: path escapes allowed root\n  path: {resolved}\n  root: {allowed}")
        return None
    return resolved, path.as_posix()


def check_path_hash(
    *,
    label: str,
    path: Path,
    expected: str | None,
    mismatches: list[str],
    ok: list[str],
) -> None:
    if not expected:
        mismatches.append(f"{label}: missing sha256 field")
        return
    if not path.exists():
        mismatches.append(f"{label}: missing file {path}")
        return
    if not path.is_file():
        mismatches.append(f"{label}: not a file {path}")
        return
    actual = sha256_file(path)
    if actual != expected:
        mismatches.append(
            f"{label}: hash mismatch\n  path: {path}\n  want: {expected}\n  got:  {actual}"
        )
        return
    ok.append(label)


def check_declared_hash(
    *,
    label: str,
    base: Path,
    allowed_root: Path,
    path_value: Any,
    expected: str | None,
    mismatches: list[str],
    ok: list[str],
) -> str | None:
    resolved = resolve_declared_path(
        label=label,
        base=base,
        allowed_root=allowed_root,
        path_value=path_value,
        mismatches=mismatches,
    )
    if resolved is None:
        return None
    path, normalized = resolved
    check_path_hash(label=label, path=path, expected=expected, mismatches=mismatches, ok=ok)
    return normalized


def iter_case_files(case_dir: Path) -> list[str]:
    files: list[str] = []
    for path in sorted(case_dir.rglob("*")):
        if not path.is_file():
            continue
        if any(part in IGNORED_CASE_DIR_NAMES for part in path.parts):
            continue
        if path.name in IGNORED_CASE_FILE_NAMES:
            continue
        files.append(path.relative_to(case_dir).as_posix())
    return files


def verify_case(skill_root: Path, case_json: Path, mismatches: list[str], ok: list[str]) -> None:
    rel = case_json.relative_to(skill_root).as_posix()
    data = load_json(case_json)
    case_dir = case_json.parent
    artifacts = data.get("artifacts") or {}
    declared_case_files = {"case.json"}

    for key in ARTIFACT_KEYS:
        item = artifacts.get(key)
        if not item:
            continue
        normalized = check_declared_hash(
            label=f"{rel}: artifacts.{key}",
            base=case_dir,
            allowed_root=case_dir,
            path_value=item.get("path"),
            expected=item.get("sha256"),
            mismatches=mismatches,
            ok=ok,
        )
        if normalized:
            declared_case_files.add(normalized)

    for index, asset in enumerate(artifacts.get("assets") or []):
        normalized = check_declared_hash(
            label=f"{rel}: artifacts.assets[{index}]",
            base=case_dir,
            allowed_root=case_dir,
            path_value=asset.get("path"),
            expected=asset.get("sha256"),
            mismatches=mismatches,
            ok=ok,
        )
        if normalized:
            declared_case_files.add(normalized)

    for index, pre in enumerate(data.get("preRead") or []):
        path_value = pre.get("path")
        pre_path = validate_relative_posix_path(
            label=f"{rel}: preRead[{index}]", path_value=path_value, mismatches=mismatches
        )
        if pre_path is None:
            continue
        if pre_path.parts and pre_path.parts[0] == "references":
            base = skill_root
            allowed_root = skill_root
        else:
            base = case_dir
            allowed_root = case_dir
            declared_case_files.add(pre_path.as_posix())
        resolved = resolve_declared_path(
            label=f"{rel}: preRead[{index}]={path_value}",
            base=base,
            allowed_root=allowed_root,
            path_value=path_value,
            mismatches=mismatches,
        )
        if resolved is None:
            continue
        check_path_hash(
            label=f"{rel}: preRead[{index}]={path_value}",
            path=resolved[0],
            expected=pre.get("sha256"),
            mismatches=mismatches,
            ok=ok,
        )

    verification = data.get("verification") or {}
    for key in VERIFICATION_ARTIFACT_KEYS:
        item = verification.get(key)
        if not item:
            continue
        normalized = check_declared_hash(
            label=f"{rel}: verification.{key}",
            base=case_dir,
            allowed_root=case_dir,
            path_value=item.get("path"),
            expected=item.get("sha256"),
            mismatches=mismatches,
            ok=ok,
        )
        if normalized:
            declared_case_files.add(normalized)

    for file_path in iter_case_files(case_dir):
        if file_path not in declared_case_files:
            mismatches.append(f"{rel}: undeclared case file {file_path}")


def verify_registry(
    skill_root: Path, case_files: list[Path], mismatches: list[str], ok: list[str]
) -> None:
    cases_root = skill_root / "references" / "cases"
    registry_path = cases_root / "registry.json"
    if not registry_path.exists():
        mismatches.append(f"missing registry: {registry_path}")
        return

    registry = load_json(registry_path)
    entries = registry.get("cases") or registry.get("entries") or []
    if not entries:
        mismatches.append("registry.json has no cases")
        return

    registry_case_paths: set[str] = set()
    for entry in entries:
        case_id = entry.get("caseId") or "<unknown>"
        manifest = entry.get("manifest") or {}
        path_value = manifest.get("path")
        resolved = resolve_declared_path(
            label=f"registry {case_id}: manifest",
            base=cases_root,
            allowed_root=cases_root,
            path_value=path_value,
            mismatches=mismatches,
        )
        if resolved is None:
            continue
        path, normalized = resolved
        registry_case_paths.add(normalized)
        check_path_hash(
            label=f"registry {case_id}: manifest",
            path=path,
            expected=manifest.get("sha256"),
            mismatches=mismatches,
            ok=ok,
        )

    disk_case_paths = {path.relative_to(cases_root).as_posix() for path in case_files}
    for path in sorted(registry_case_paths - disk_case_paths):
        mismatches.append(f"registry manifest path missing on disk: {path}")
    for path in sorted(disk_case_paths - registry_case_paths):
        mismatches.append(f"case.json exists but is not registered: {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "skill_root_arg",
        nargs="?",
        type=Path,
        help="optional skill root path; same as --skill-root",
    )
    parser.add_argument(
        "--skill-root",
        type=Path,
        default=None,
        help="skill root containing references/cases (default: parent of scripts/)",
    )
    args = parser.parse_args(argv)
    if args.skill_root and args.skill_root_arg:
        parser.error("pass either positional skill_root or --skill-root, not both")

    skill_root = (args.skill_root or args.skill_root_arg or Path(__file__).resolve().parents[1]).resolve()
    cases_root = skill_root / "references" / "cases"
    if not cases_root.is_dir():
        print(f"cases directory not found: {cases_root}", file=sys.stderr)
        return 1

    mismatches: list[str] = []
    ok: list[str] = []

    case_files = sorted(cases_root.glob("**/case.json"))
    if not case_files:
        print(f"no case.json under {cases_root}", file=sys.stderr)
        return 1

    for case_json in case_files:
        verify_case(skill_root, case_json, mismatches, ok)

    verify_registry(skill_root, case_files, mismatches, ok)

    print(f"skill_root={skill_root}")
    print(f"cases={len(case_files)} checks_ok={len(ok)} mismatches={len(mismatches)}")
    if mismatches:
        print("FAIL")
        for item in mismatches:
            print(item)
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
