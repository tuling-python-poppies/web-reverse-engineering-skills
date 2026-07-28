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
WORK_ORDER_DOC = ROOT / "references" / "methodology" / "provider-work-order.md"


def load_schema(name: str) -> dict:
    path = SCHEMAS / name
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


VALID_WORK_ORDER = {
    "schemaVersion": "web-protocol-recovery-provider-work-order/v2",
    "workOrderId": "wo-test",
    "shape": "evidence",
    "gateFamily": "signer",
    "activeProvider": {"id": "chromium-recon", "role": "reconnaissance", "strategy": None, "profile": None},
    "protocolOwner": None,
    "implementation": None,
    "deliveryProvider": None,
    "caseId": None,
    "authorization": {
        "authorizationBasis": "public-unauthenticated",
        "allowedHostsAndRoutes": [
            {
                "scopeId": "primary",
                "scheme": "https",
                "host": "example.com",
                "port": 443,
                "routePrefix": "/api",
                "queryPolicy": {"mode": "deny", "allowedKeys": [], "allowedValues": {}},
            }
        ],
        "actionClass": "read-only",
        "accountOrSessionUse": "none",
        "browserReconAllowed": False,
        "browserNavigationSideEffectsApproved": False,
        "liveReplayAllowed": False,
        "requestBudget": {
            "total": 0,
            "remaining": 0,
            "minDelayMs": 0,
            "concurrency": 1,
            "automaticObservationStopThreshold": 0,
            "observedAutomatic": {
                "total": 0,
                "byKind": {
                    "redirect": 0,
                    "subresource": 0,
                    "xhrFetch": 0,
                    "beaconPing": 0,
                    "eventSource": 0,
                    "websocket": 0,
                },
                "destinations": [],
            },
        },
        "artifactPolicy": {
            "mode": "metadata-only",
            "approvedRawFields": [],
            "retentionDeadline": "none",
            "repositoryExcluded": True,
        },
        "executionPolicy": {
            "targetCodeExecution": "blocked",
            "approvedCodeSha256": [],
            "dependencyInstall": "blocked",
            "approvedCommands": [],
            "approvalEvidence": "none",
            "approvalDeadline": "none",
        },
    },
    "project": {
        "projectRoot": "none",
        "layout": "web-protocol-recovery-simple",
        "writeMode": "no-write",
        "allowedPaths": [],
    },
    "readPlan": {
        "window": "handoff",
        "required": ["references/providers/reconnaissance/chromium-recon/PROVIDER.md"],
        "optional": [],
    },
    "inputs": [],
    "requiredOutputs": ["one precise blocker or evidence"],
    "acceptanceTest": "return bounded offline evidence",
    "runtimeCustody": {
        "providerOwnsBrowser": False,
        "providerOwnsWorker": False,
        "providerOwnsLease": False,
    },
    "runtimeIds": [],
}


VALID_RESULT = {
    "schemaVersion": "web-protocol-recovery-provider-result/v2",
    "workOrderId": "wo-test",
    "provider": {"id": "chromium-recon", "role": "reconnaissance", "strategy": None, "profile": None},
    "protocolOwner": None,
    "shape": "evidence",
    "gateFamily": "signer",
    "status": "complete",
    "artifactBoundary": None,
    "artifacts": [],
    "verification": {"fixedVectorPass": True, "liveReplayPass": False, "semanticSuccess": True},
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


def doc_example_findings(work_order: Draft202012Validator) -> list[str]:
    text = WORK_ORDER_DOC.read_text(encoding="utf-8")
    start = text.find("```json")
    end = text.find("```", start + 7)
    if start < 0 or end < 0:
        return ["provider-work-order.md missing JSON example"]
    try:
        example = json.loads(text[start + 7 : end])
    except json.JSONDecodeError as error:
        return [f"provider-work-order.md example is not valid JSON: {error}"]
    return expect_valid(work_order, example, "provider-work-order.md example")


def main() -> int:
    failures: list[str] = []
    work_order = Draft202012Validator(load_schema("provider-work-order-v2.schema.json"))
    result = Draft202012Validator(load_schema("provider-result-v2.schema.json"))
    Draft202012Validator.check_schema(load_schema("case-v2.schema.json"))
    Draft202012Validator.check_schema(load_schema("case-registry-v2.schema.json"))

    failures.extend(expect_valid(work_order, VALID_WORK_ORDER, "valid offline work order"))
    failures.extend(doc_example_findings(work_order))

    missing_query_policy = copy.deepcopy(VALID_WORK_ORDER)
    del missing_query_policy["authorization"]["allowedHostsAndRoutes"][0]["queryPolicy"]
    failures.extend(expect_invalid(work_order, missing_query_policy, "missing queryPolicy"))

    bad_write_mode = copy.deepcopy(VALID_WORK_ORDER)
    bad_write_mode["project"]["writeMode"] = "none"
    failures.extend(expect_invalid(work_order, bad_write_mode, "invalid writeMode none"))

    bad_read_plan = copy.deepcopy(VALID_WORK_ORDER)
    bad_read_plan["readPlan"] = {"maxDistinctPaths": 24, "windows": []}
    failures.extend(expect_invalid(work_order, bad_read_plan, "legacy readPlan shape"))

    remaining_gt_total = copy.deepcopy(VALID_WORK_ORDER)
    remaining_gt_total["authorization"]["requestBudget"] = {"total": 1, "remaining": 2}
    # schema alone cannot enforce remaining<=total; fixture still validates shape
    failures.extend(expect_valid(work_order, remaining_gt_total, "budget shape still valid"))

    bad_hash = copy.deepcopy(VALID_WORK_ORDER)
    bad_hash["authorization"]["executionPolicy"] = {
        "targetCodeExecution": "approved-reviewed-hash",
        "approvedCodeSha256": ["bad"],
    }
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
        for item in failures:
            print(f"FAIL {item}")
        print(f"summary: failures={len(failures)}")
        return 1
    print("== schema contract ==")
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
