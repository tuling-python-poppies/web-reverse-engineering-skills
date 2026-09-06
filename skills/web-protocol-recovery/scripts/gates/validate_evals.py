#!/usr/bin/env python3
"""Validate offline route-regression metadata for web-protocol-recovery."""

from __future__ import annotations

import json
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
EVAL_PATH = SKILL_ROOT / "evals" / "route-regression.json"
REGISTRY_PATH = SKILL_ROOT / "references" / "providers" / "registry.json"
CASE_REGISTRY_PATH = SKILL_ROOT / "references" / "cases" / "registry.json"
SCHEMA_VERSION = "web-protocol-recovery-route-regression"
REQUIRED_CASE_IDS = {
    "aliyun-feilin-generation-ambiguous",
    "aliyun-rpc-not-verifier",
    "aliyun-v3-verifier-family",
    "douyin-abogus-native-profile",
    "jd-h5st-pure-python-case",
    "node-env-patch-strategy",
    "gt4-verifier-owner",
    "gt4-word-click-verifier",
    "gt4-nine-grid-verifier",
    "proved-protocol-python-delivery",
    "gt4-work-order-scope-contract",
    "pzds-target-code-execution-gate",
    "transport-only-source-complete",
    "read-budget-extension-one-shot",
}
REQUIRED_CASE_EXPECTATIONS = {
    "aliyun-feilin-generation-ambiguous": {
        "route": "verifier",
        "familyDecision": "clarify-before-reference-read",
    },
    "aliyun-rpc-not-verifier": {
        "route": "evidence-reuse",
        "notProtocolOwner": "verifier",
    },
    "aliyun-v3-verifier-family": {
        "route": "verifier",
        "familyReference": "aliyun-captcha-v3-workflow.md",
    },
    "gt4-word-click-verifier": {
        "route": "verifier",
        "familyReference": "geetest-gt4-word-workflow.md",
    },
    "gt4-nine-grid-verifier": {
        "route": "verifier",
        "familyReference": "geetest-gt4-nine-grid-workflow.md",
    },
    "gt4-work-order-scope-contract": {
        "route": "verifier",
        "scopePolicy": "exact-gt4-endpoints-only",
    },
    "pzds-target-code-execution-gate": {
        "route": "verifier",
        "executionPolicy": "blocked-without-approved-runner",
    },
    "transport-only-source-complete": {
        "route": "chromium-recon",
        "gateFamily": "transport",
        "jsReverseHalf": "not-required",
    },
    "read-budget-extension-one-shot": {
        "route": "evidence-reuse",
        "readBudget": "one-extension-only",
    },
}
OBSOLETE_ROUTES = {"env-patch", "douyin-abogus-native"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_route_regression() -> list[str]:
    findings: list[str] = []
    if not EVAL_PATH.is_file():
        return [f"missing eval file: {EVAL_PATH.relative_to(SKILL_ROOT).as_posix()}"]
    if not REGISTRY_PATH.is_file():
        return [f"missing provider registry: {REGISTRY_PATH.relative_to(SKILL_ROOT).as_posix()}"]
    if not CASE_REGISTRY_PATH.is_file():
        return [f"missing case registry: {CASE_REGISTRY_PATH.relative_to(SKILL_ROOT).as_posix()}"]

    registry = load_json(REGISTRY_PATH)
    case_registry = load_json(CASE_REGISTRY_PATH)
    verified_cases = {
        row.get("caseId"): row
        for row in case_registry.get("cases", [])
        if row.get("status") == "verified"
    }
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
        if not isinstance(item.get("prompt"), str) or not item["prompt"]:
            findings.append(f"{case_id}: prompt is required")
        expect = item.get("expect") or {}
        route = expect.get("route")
        if route not in valid_routes:
            findings.append(f"{case_id}: invalid expected route {route!r}")
        for field, required_value in REQUIRED_CASE_EXPECTATIONS.get(case_id, {}).items():
            if expect.get(field) != required_value:
                findings.append(f"{case_id}: expect.{field} must be {required_value!r}")
        if route in OBSOLETE_ROUTES:
            findings.append(f"{case_id}: obsolete route {route!r}")
        expected_case_id = expect.get("caseId")
        if expected_case_id is not None:
            case_row = verified_cases.get(expected_case_id)
            if case_row is None:
                findings.append(f"{case_id}: expect.caseId does not resolve to a verified case manifest")
            elif case_row.get("selectableAs") not in {"proof", "template"}:
                findings.append(f"{case_id}: expect.caseId has invalid selectableAs")
        if expect.get("strategy") == "env-patch" and route != "python-node":
            findings.append(f"{case_id}: env-patch strategy requires route python-node")
        if expect.get("profile") == "douyin-abogus-native" and route != "pure-python":
            findings.append(f"{case_id}: douyin profile requires route pure-python")
        if expect.get("jsReverseHalf") == "not-required" and expect.get("gateFamily") != "transport":
            findings.append(f"{case_id}: jsReverseHalf=not-required requires gateFamily=transport")
        for bad_route in expect.get("notRoute", []):
            if bad_route not in OBSOLETE_ROUTES:
                findings.append(f"{case_id}: notRoute should only name obsolete route values")

    missing = sorted(REQUIRED_CASE_IDS - seen_ids)
    if missing:
        findings.append(f"missing required eval ids: {', '.join(missing)}")
    expected_routes = {expect.get("route") for expect in (item.get("expect") or {} for item in cases)}
    uncovered = sorted({provider["id"] for provider in registry.get("providers", [])} - expected_routes)
    if uncovered:
        findings.append("providers with no route regression case: " + ", ".join(uncovered))
    return findings


def main() -> int:
    findings = validate_route_regression()
    if findings:
        for finding in findings:
            print(f"FAIL {finding}")
        print(f"summary: failures={len(findings)}")
        return 1
    count = len(load_json(EVAL_PATH).get("cases", []))
    print(f"PASS route regression metadata: cases={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
