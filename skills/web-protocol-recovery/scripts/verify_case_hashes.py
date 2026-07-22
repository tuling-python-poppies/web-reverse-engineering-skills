#!/usr/bin/env python3
"""Verify hash-bound case artifacts and registry manifests.

Cascade after any hash-bound edit:
  target file bytes
    -> case.json artifacts / preRead sha256
    -> registry.json manifest sha256 for that case.json

Exit 0 when every declared path exists and SHA-256 matches.
Exit 1 on mismatch or missing path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ARTIFACT_KEYS = ("process", "entry", "pullLiveState")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def verify_case(skill_root: Path, case_json: Path, mismatches: list[str], ok: list[str]) -> None:
    rel = case_json.relative_to(skill_root).as_posix()
    data = load_json(case_json)
    case_dir = case_json.parent
    artifacts = data.get("artifacts") or {}

    for key in ARTIFACT_KEYS:
        item = artifacts.get(key)
        if not item:
            continue
        path_value = item.get("path")
        if not path_value:
            mismatches.append(f"{rel}: artifacts.{key} missing path")
            continue
        check_path_hash(
            label=f"{rel}: artifacts.{key}",
            path=case_dir / path_value,
            expected=item.get("sha256"),
            mismatches=mismatches,
            ok=ok,
        )

    for index, asset in enumerate(artifacts.get("assets") or []):
        path_value = asset.get("path")
        if not path_value:
            mismatches.append(f"{rel}: artifacts.assets[{index}] missing path")
            continue
        check_path_hash(
            label=f"{rel}: artifacts.assets[{index}]={path_value}",
            path=case_dir / path_value,
            expected=asset.get("sha256"),
            mismatches=mismatches,
            ok=ok,
        )

    for index, pre in enumerate(data.get("preRead") or []):
        path_value = pre.get("path")
        if not path_value:
            mismatches.append(f"{rel}: preRead[{index}] missing path")
            continue
        candidate = skill_root / path_value
        if not candidate.exists():
            candidate = case_dir / path_value
        check_path_hash(
            label=f"{rel}: preRead[{index}]={path_value}",
            path=candidate,
            expected=pre.get("sha256"),
            mismatches=mismatches,
            ok=ok,
        )


def verify_registry(skill_root: Path, mismatches: list[str], ok: list[str]) -> None:
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

    for entry in entries:
        case_id = entry.get("caseId") or "<unknown>"
        manifest = entry.get("manifest") or {}
        path_value = manifest.get("path")
        if not path_value:
            mismatches.append(f"registry {case_id}: missing manifest.path")
            continue
        check_path_hash(
            label=f"registry {case_id}: manifest",
            path=cases_root / path_value,
            expected=manifest.get("sha256"),
            mismatches=mismatches,
            ok=ok,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skill-root",
        type=Path,
        default=None,
        help="skill root containing references/cases (default: parent of scripts/)",
    )
    args = parser.parse_args(argv)

    skill_root = (args.skill_root or Path(__file__).resolve().parents[1]).resolve()
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

    verify_registry(skill_root, mismatches, ok)

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
