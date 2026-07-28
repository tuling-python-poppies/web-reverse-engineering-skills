#!/usr/bin/env python3
"""Execute JSON Schema contract fixtures for Architecture V2."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "references" / "schemas"


def load_schema(name: str) -> dict:
    path = SCHEMAS / name
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


VALID_WORK_ORDER = {
    "schemaVersion": "web-protocol-recovery-provider-work-order/v2",
    "workOrderId": "wo-test",
    "shape": "collector",
    "gateFamily": "verifier",
    "activeProvider": {"id": "python-collector", "role": "delivery"},
    "protocolOwner": "verifier",
    "deliveryProvider": "python-collector",
    "authorization": {
        "liveReplayAllowed": True,
        "actionClass": "verifier-submit",
        "allowedHostsAndRoutes": [
            {
                "scheme": "https",
                "host": "gcaptcha4.geetest.com",
                "port": 443,
                "routePrefix": "/load",
                "queryPolicy": {"mode": "allow-listed", "allowedKeys": ["captcha_id", "callback"]},
            }
        ],
        "requestBudget": {"remaining": 5, "maxRequests": 5, "redirects": 0, "retries": 0, "concurrency": 1},
        "artifactPolicy": {
            "mode": "allowlisted-raw",
            "repositoryExcluded": True,
            "approvedRawFields": ["gt4.load.json"],
            "retentionDeadline": "2026-08-01T00:00:00Z",
        },
        "executionPolicy": {"targetCodeExecution": "blocked", "approvedCodeSha256": []},
    },
    "project": {"projectRoot": "C:/tmp/wpr", "allowedPaths": ["js_reverse_cache"], "writeMode": "create-only"},
    "readPlan": {"maxDistinctPaths": 24, "windows": [{"name": "initial", "paths": ["SKILL.md"]}]},
    "acceptanceTest": "semantic body shape and cleanup complete",
    "runtimeCustody": {"owner": "python-collector", "cleanupRequired": True},
    "runtimeIds": [],
}


VALID_RESULT = {
    "schemaVersion": "web-protocol-recovery-provider-result/v2",
    "workOrderId": "wo-test",
    "provider": {"id": "python-collector", "role": "delivery"},
    "shape": "collector",
    "gateFamily": "verifier",
    "status": "complete",
    "verification": {"fixedVectorPass": True, "liveReplayPass": True, "semanticSuccess": True},
    "requestBudget": {"remaining": 0},
    "execution": {"targetCodeExecution": "blocked"},
    "runtimeIds": [],
    "cleanup": {"complete": True, "runtimeIdsClosed": True},
}


def expect_valid(validator: Draft202012Validator, value: dict, label: str) -> list[str]:
    try:
        validator.validate(value)
    except ValidationError as error:
        return [f"{label}: expected valid but failed: {error.message}"]
    return []


def expect_invalid(validator: Draft202012Validator, value: dict, label: str) -> list[str]:
    try:
        validator.validate(value)
    except ValidationError:
        return []
    return [f"{label}: expected invalid but passed"]


def main() -> int:
    failures: list[str] = []
    work_order = Draft202012Validator(load_schema("provider-work-order-v2.schema.json"))
    result = Draft202012Validator(load_schema("provider-result-v2.schema.json"))
    Draft202012Validator.check_schema(load_schema("case-v2.schema.json"))
    Draft202012Validator.check_schema(load_schema("case-registry-v2.schema.json"))

    failures.extend(expect_valid(work_order, VALID_WORK_ORDER, "valid work order"))
    missing_query_policy = copy.deepcopy(VALID_WORK_ORDER)
    del missing_query_policy["authorization"]["allowedHostsAndRoutes"][0]["queryPolicy"]
    failures.extend(expect_invalid(work_order, missing_query_policy, "missing queryPolicy"))
    missing_project_bounds = copy.deepcopy(VALID_WORK_ORDER)
    missing_project_bounds["project"].pop("allowedPaths")
    failures.extend(expect_invalid(work_order, missing_project_bounds, "missing project.allowedPaths"))
    bad_hash = copy.deepcopy(VALID_WORK_ORDER)
    bad_hash["authorization"]["executionPolicy"] = {"targetCodeExecution": "approved-reviewed-hash", "approvedCodeSha256": ["bad"]}
    failures.extend(expect_invalid(work_order, bad_hash, "invalid approvedCodeSha256"))

    failures.extend(expect_valid(result, VALID_RESULT, "valid provider result"))
    missing_cleanup = copy.deepcopy(VALID_RESULT)
    missing_cleanup["cleanup"].pop("runtimeIdsClosed")
    failures.extend(expect_invalid(result, missing_cleanup, "missing cleanup.runtimeIdsClosed"))
    missing_semantic = copy.deepcopy(VALID_RESULT)
    missing_semantic["verification"].pop("semanticSuccess")
    failures.extend(expect_invalid(result, missing_semantic, "missing semanticSuccess"))

    if failures:
        print("== schema contract ==")
        for failure in failures:
            print(f"FAIL {failure}")
        print(f"summary: failures={len(failures)}")
        return 1
    print("== schema contract ==")
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
