#!/usr/bin/env python3
"""Validate route regression eval metadata for web-protocol-recovery."""

from __future__ import annotations

import json
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
EVAL_PATH = SKILL_ROOT / "evals" / "route-regression.json"
REGISTRY_PATH = SKILL_ROOT / "references" / "providers" / "registry.json"
SCHEMA_VERSION = "web-protocol-recovery-route-regression/v1"
REQUIRED_CASE_IDS = {
    "douyin-abogus-native-profile",
    "jd-h5st-pure-python-case",
    "node-env-patch-strategy",
    "gt4-verifier-owner",
    "proved-protocol-python-delivery",
}
OBSOLETE_ROUTES = {"env-patch", "douyin-abogus-native"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    findings: list[str] = []
    if not EVAL_PATH.is_file():
        print(f"FAIL missing eval file: {EVAL_PATH.relative_to(SKILL_ROOT).as_posix()}")
        return 1

    registry = load_json(REGISTRY_PATH)
    valid_routes = {provider["id"] for provider in registry.get("providers", [])}
    valid_routes.update(registry.get("routeSentinels", []))
    data = load_json(EVAL_PATH)
    if data.get("schemaVersion") != SCHEMA_VERSION:
        findings.append(f"schemaVersion must be {SCHEMA_VERSION}")
    cases = data.get("cases")
    if not isinstance(cases, list) or len(cases) < len(REQUIRED_CASE_IDS):
        findings.append("cases must include the required route regression set")
        cases = [] if not isinstance(cases, list) else cases

    seen_ids: set[str] = set()
    for index, item in enumerate(cases):
        case_id = item.get("id")
        if not isinstance(case_id, str) or not case_id:
            findings.append(f"cases[{index}].id is required")
            continue
        if case_id in seen_ids:
            findings.append(f"duplicate eval id: {case_id}")
        seen_ids.add(case_id)
        if not item.get("prompt"):
            findings.append(f"{case_id}: prompt is required")
        expect = item.get("expect") or {}
        route = expect.get("route")
        if route not in valid_routes:
            findings.append(f"{case_id}: invalid expected route {route!r}")
        if route in OBSOLETE_ROUTES:
            findings.append(f"{case_id}: obsolete route {route!r}")
        if expect.get("strategy") == "env-patch" and route != "python-node":
            findings.append(f"{case_id}: env-patch strategy requires route python-node")
        if expect.get("profile") == "douyin-abogus-native" and route != "pure-python":
            findings.append(f"{case_id}: douyin profile requires route pure-python")
        for bad_route in expect.get("notRoute", []):
            if bad_route not in OBSOLETE_ROUTES:
                findings.append(f"{case_id}: notRoute should only name obsolete route values")

    missing = sorted(REQUIRED_CASE_IDS - seen_ids)
    if missing:
        findings.append(f"missing required eval ids: {', '.join(missing)}")

    if findings:
        for finding in findings:
            print(f"FAIL {finding}")
        print(f"summary: failures={len(findings)}")
        return 1
    print(f"PASS route regression evals: cases={len(cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
