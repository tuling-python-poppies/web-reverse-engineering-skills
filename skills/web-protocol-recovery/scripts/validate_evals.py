#!/usr/bin/env python3
"""Validate route regression eval metadata for web-protocol-recovery."""

from __future__ import annotations

import json
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
EVAL_PATH = SKILL_ROOT / "evals" / "route-regression.json"
SKILL_EVALS_PATH = SKILL_ROOT / "evals" / "evals.json"
TRIGGER_EVALS_PATH = SKILL_ROOT / "evals" / "trigger-evals.json"
TEST_PROMPTS_PATH = SKILL_ROOT / "test-prompts.json"
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
PROMPT_TYPES = {"should-trigger", "near-miss", "anti-pattern"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_skill_creator_evals() -> list[str]:
    findings: list[str] = []
    if not SKILL_EVALS_PATH.is_file():
        return ["missing evals/evals.json"]
    data = load_json(SKILL_EVALS_PATH)
    if data.get("skill_name") != "web-protocol-recovery":
        findings.append("evals/evals.json skill_name must be web-protocol-recovery")
    benchmark = data.get("benchmark") or {}
    expected_benchmark = {
        "mode": "with-skill-vs-baseline",
        "rounds": 3,
        "workers": 2,
        "timeout_seconds": 180,
        "executor_model": "deepseek/deepseek-v4-pro",
        "reviewer_model": "grok/grok-4.5",
    }
    for key, value in expected_benchmark.items():
        if benchmark.get(key) != value:
            findings.append(f"evals/evals.json benchmark.{key} must be {value!r}")
    evals = data.get("evals")
    if not isinstance(evals, list) or len(evals) < 10:
        findings.append("evals/evals.json must include at least 10 behavioral evals")
        evals = [] if not isinstance(evals, list) else evals
    seen_ids: set[int] = set()
    confirmations = 0
    for index, item in enumerate(evals):
        eval_id = item.get("id")
        if not isinstance(eval_id, int):
            findings.append(f"evals[{index}].id must be integer")
            continue
        if eval_id in seen_ids:
            findings.append(f"duplicate eval id: {eval_id}")
        seen_ids.add(eval_id)
        for field in ("prompt", "expected_output"):
            if not isinstance(item.get(field), str) or not item.get(field):
                findings.append(f"evals[{index}].{field} is required")
        if not isinstance(item.get("confirmation_required"), bool):
            findings.append(f"evals[{index}].confirmation_required must be boolean")
        elif item["confirmation_required"]:
            confirmations += 1
        expectations = item.get("expectations")
        if not isinstance(expectations, list) or not expectations or not all(isinstance(value, str) and value for value in expectations):
            findings.append(f"evals[{index}].expectations must be a non-empty string array")
    if confirmations < 3:
        findings.append("behavioral evals must include confirmation-required protocol/tool cases")
    return findings


def validate_trigger_evals() -> list[str]:
    findings: list[str] = []
    if not TRIGGER_EVALS_PATH.is_file():
        return ["missing evals/trigger-evals.json"]
    data = json.loads(TRIGGER_EVALS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list) or len(data) < 10:
        return ["trigger-evals.json must include at least 10 entries"]
    positives = 0
    negatives = 0
    for index, item in enumerate(data):
        if not isinstance(item.get("query"), str) or not item.get("query"):
            findings.append(f"trigger-evals[{index}].query is required")
        if not isinstance(item.get("should_trigger"), bool):
            findings.append(f"trigger-evals[{index}].should_trigger must be boolean")
        elif item["should_trigger"]:
            positives += 1
        else:
            negatives += 1
    if positives < 5 or negatives < 5:
        findings.append("trigger-evals must cover at least 5 positives and 5 negatives")
    required_negative_markers = ("skill", "opencode")
    negative_queries = "\n".join(item.get("query", "") for item in data if item.get("should_trigger") is False).lower()
    for marker in required_negative_markers:
        if marker not in negative_queries:
            findings.append(f"trigger-evals negatives must include {marker} handoff")
    return findings


def validate_test_prompts() -> list[str]:
    findings: list[str] = []
    if not TEST_PROMPTS_PATH.is_file():
        return ["missing test-prompts.json"]
    data = json.loads(TEST_PROMPTS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list) or len(data) < 10:
        return ["test-prompts.json must be a list with at least 10 entries"]
    seen_ids: set[int] = set()
    types_seen: set[str] = set()
    confirmation_count = 0
    for index, item in enumerate(data):
        item_id = item.get("id")
        if not isinstance(item_id, int):
            findings.append(f"test-prompts[{index}].id must be integer")
            continue
        if item_id in seen_ids:
            findings.append(f"duplicate test prompt id: {item_id}")
        seen_ids.add(item_id)
        for field in ("prompt", "expected"):
            if not isinstance(item.get(field), str) or not item.get(field):
                findings.append(f"test-prompts[{index}].{field} is required")
        prompt_type = item.get("type")
        if prompt_type not in PROMPT_TYPES:
            findings.append(f"test-prompts[{index}].type must be one of {sorted(PROMPT_TYPES)}")
        else:
            types_seen.add(prompt_type)
        if not isinstance(item.get("confirmation_required"), bool):
            findings.append(f"test-prompts[{index}].confirmation_required must be boolean")
        elif item["confirmation_required"]:
            confirmation_count += 1
    missing_types = sorted(PROMPT_TYPES - types_seen)
    if missing_types:
        findings.append("test-prompts.json missing type coverage: " + ", ".join(missing_types))
    if confirmation_count == 0:
        findings.append("test-prompts.json must mark tool/write/live prompts confirmation_required")
    return findings


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
    findings.extend(validate_skill_creator_evals())
    findings.extend(validate_trigger_evals())
    findings.extend(validate_test_prompts())

    if findings:
        for finding in findings:
            print(f"FAIL {finding}")
        print(f"summary: failures={len(findings)}")
        return 1
    print(f"PASS route regression evals: cases={len(cases)}; behavioral_evals=ok; trigger_evals=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
