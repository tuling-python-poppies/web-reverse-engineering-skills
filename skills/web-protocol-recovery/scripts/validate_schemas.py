#!/usr/bin/env python3
"""Execute JSON Schema contract fixtures for current architecture."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

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
    "schemaVersion": "web-protocol-recovery-provider-work-order",
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
        "actionApproval": "standing-read-only",
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
        "projectRoot": "C:/absolute/project-root",
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
    "schemaVersion": "web-protocol-recovery-provider-result",
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


def work_order_semantic_findings(value: dict, label: str) -> list[str]:
    findings: list[str] = []
    project = value.get("project") or {}
    project_root = project.get("projectRoot")
    write_mode = project.get("writeMode")
    allowed_paths = project.get("allowedPaths") or []
    if write_mode != "no-write":
        is_absolute = isinstance(project_root, str) and (
            PurePosixPath(project_root).is_absolute()
            or PureWindowsPath(project_root).is_absolute()
        )
        if not is_absolute:
            findings.append(f"{label}: writable projectRoot must be absolute")
        if not allowed_paths:
            findings.append(f"{label}: writable work order requires allowedPaths")
    elif allowed_paths:
        findings.append(f"{label}: no-write work order must have empty allowedPaths")

    provider = value.get("activeProvider") or {}
    if provider.get("role") == "reconnaissance":
        invalid_paths = [
            path
            for path in allowed_paths
            if not (
                path.startswith("js_reverse_cache/recon/")
                or path.startswith("js_reverse_cache/source/")
            )
        ]
        if invalid_paths:
            findings.append(
                f"{label}: reconnaissance allowedPaths contain stable/non-recon paths"
            )

    budget = ((value.get("authorization") or {}).get("requestBudget") or {})
    total = budget.get("total")
    remaining = budget.get("remaining")
    if isinstance(total, int) and isinstance(remaining, int) and remaining > total:
        findings.append(f"{label}: requestBudget.remaining cannot exceed total")
    observed = budget.get("observedAutomatic") or {}
    by_kind = observed.get("byKind") or {}
    observed_total = observed.get("total")
    if isinstance(observed_total, int) and isinstance(by_kind, dict):
        kind_sum = sum(value for value in by_kind.values() if isinstance(value, int))
        if observed_total != kind_sum:
            findings.append(f"{label}: observedAutomatic.total must equal sum(byKind)")
    return findings


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
    findings = expect_valid(work_order, example, "provider-work-order.md example")
    findings.extend(work_order_semantic_findings(example, "provider-work-order.md example"))
    return findings


def main() -> int:
    failures: list[str] = []
    work_order = Draft202012Validator(load_schema("provider-work-order.schema.json"))
    result = Draft202012Validator(load_schema("provider-result.schema.json"))
    Draft202012Validator.check_schema(load_schema("case.schema.json"))
    Draft202012Validator.check_schema(load_schema("case-registry.schema.json"))

    failures.extend(expect_valid(work_order, VALID_WORK_ORDER, "valid offline work order"))
    failures.extend(work_order_semantic_findings(VALID_WORK_ORDER, "valid offline work order"))
    failures.extend(doc_example_findings(work_order))

    missing_query_policy = copy.deepcopy(VALID_WORK_ORDER)
    del missing_query_policy["authorization"]["allowedHostsAndRoutes"][0]["queryPolicy"]
    failures.extend(expect_invalid(work_order, missing_query_policy, "missing queryPolicy"))

    bad_write_mode = copy.deepcopy(VALID_WORK_ORDER)
    bad_write_mode["project"]["writeMode"] = "none"
    failures.extend(expect_invalid(work_order, bad_write_mode, "invalid writeMode none"))

    relative_write_root = copy.deepcopy(VALID_WORK_ORDER)
    relative_write_root["project"] = {
        "projectRoot": "cwd-default",
        "layout": "web-protocol-recovery-simple",
        "writeMode": "create-only",
        "allowedPaths": ["js_reverse_cache/recon/chrome/**"],
    }
    relative_findings = work_order_semantic_findings(
        relative_write_root, "relative writable root"
    )
    if not any("must be absolute" in item for item in relative_findings):
        failures.append("relative writable root: expected absolute-path guard to fail")

    broad_recon_paths = copy.deepcopy(VALID_WORK_ORDER)
    broad_recon_paths["project"] = {
        "projectRoot": "C:/absolute/project-root",
        "layout": "web-protocol-recovery-simple",
        "writeMode": "create-only",
        "allowedPaths": ["js_reverse_cache/recon/chrome/**", "main.py"],
    }
    broad_findings = work_order_semantic_findings(
        broad_recon_paths, "broad reconnaissance paths"
    )
    if not any("stable/non-recon" in item for item in broad_findings):
        failures.append("broad reconnaissance paths: expected least-privilege guard to fail")

    bad_read_plan = copy.deepcopy(VALID_WORK_ORDER)
    bad_read_plan["readPlan"] = {"maxDistinctPaths": 24, "windows": []}
    failures.extend(expect_invalid(work_order, bad_read_plan, "legacy readPlan shape"))

    remaining_gt_total = copy.deepcopy(VALID_WORK_ORDER)
    remaining_gt_total["authorization"]["requestBudget"] = {"total": 1, "remaining": 2}
    failures.extend(expect_valid(work_order, remaining_gt_total, "budget shape still valid"))
    if not work_order_semantic_findings(remaining_gt_total, "budget semantic guard"):
        failures.append("budget semantic guard: expected remaining>total to fail")

    bad_hash = copy.deepcopy(VALID_WORK_ORDER)
    bad_hash["authorization"]["executionPolicy"] = {
        "targetCodeExecution": "approved-reviewed-hash",
        "approvedCodeSha256": ["bad"],
    }
    failures.extend(expect_invalid(work_order, bad_hash, "invalid approvedCodeSha256"))

    unapproved_mutation = copy.deepcopy(VALID_WORK_ORDER)
    unapproved_mutation["authorization"]["actionClass"] = "mutation-submit"
    unapproved_mutation["authorization"].pop("actionApproval")
    failures.extend(
        expect_invalid(
            work_order,
            unapproved_mutation,
            "mutation-submit without user-confirmed actionApproval",
        )
    )

    approved_mutation = copy.deepcopy(VALID_WORK_ORDER)
    approved_mutation["authorization"]["actionClass"] = "mutation-submit"
    approved_mutation["authorization"]["actionApproval"] = (
        "user-confirmed-mutation"
    )
    failures.extend(
        expect_valid(
            work_order,
            approved_mutation,
            "mutation-submit with user-confirmed actionApproval",
        )
    )

    # The forward rule alone let a read-only order carry a mutation approval, so a
    # stale or copy-pasted approval could sit on a routine work order and read as
    # if the user had confirmed a business mutation. Bind the pair both ways.
    overclaimed_approval = copy.deepcopy(VALID_WORK_ORDER)
    overclaimed_approval["authorization"]["actionClass"] = "read-only"
    overclaimed_approval["authorization"]["actionApproval"] = "user-confirmed-mutation"
    failures.extend(
        expect_invalid(
            work_order,
            overclaimed_approval,
            "read-only action carrying user-confirmed-mutation approval",
        )
    )

    mismatched_verifier = copy.deepcopy(VALID_WORK_ORDER)
    mismatched_verifier["authorization"]["actionClass"] = "read-only"
    mismatched_verifier["authorization"]["actionApproval"] = "standing-verifier-submit"
    failures.extend(
        expect_invalid(
            work_order,
            mismatched_verifier,
            "read-only action carrying standing-verifier-submit approval",
        )
    )

    understated_verifier = copy.deepcopy(VALID_WORK_ORDER)
    understated_verifier["authorization"]["actionClass"] = "verifier-submit"
    understated_verifier["authorization"]["actionApproval"] = "standing-read-only"
    failures.extend(
        expect_invalid(
            work_order,
            understated_verifier,
            "verifier-submit understated as standing-read-only",
        )
    )

    approved_verifier = copy.deepcopy(VALID_WORK_ORDER)
    approved_verifier["authorization"]["actionClass"] = "verifier-submit"
    approved_verifier["authorization"]["actionApproval"] = "standing-verifier-submit"
    failures.extend(
        expect_valid(
            work_order,
            approved_verifier,
            "verifier-submit with standing-verifier-submit approval",
        )
    )

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
