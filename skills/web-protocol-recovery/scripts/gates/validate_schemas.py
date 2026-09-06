#!/usr/bin/env python3
"""Execute JSON Schema contract fixtures for current architecture."""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

from jsonschema import Draft202012Validator, FormatChecker, ValidationError


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "references" / "schemas"
WORK_ORDER_DOC = ROOT / "references" / "methodology" / "provider-work-order.md"
sys.path.insert(0, str(ROOT / "scripts" / "gates"))
from read_budget import validate_read_plan


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
        "discoveryScopes": [
            {
                "scheme": "https",
                "host": "api.example.com",
                "port": 443,
                "routePrefix": "/",
                "queryPolicy": {"mode": "deny"},
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
            "rawSecretHandling": "blocked",
        },
        "executionPolicy": {
            "targetCodeExecution": "blocked",
            "approvedCodeSha256": [],
            "dependencyInstall": "blocked",
            "approvedCommands": [],
            "approvalEvidence": "none",
            "approvalDeadline": None,
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
        "leaseMode": "observe-external",
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
    "verification": {
        "fixedVectorPass": True,
        "liveReplayPass": False,
        "semanticSuccess": True,
        "firstDivergence": None,
    },
    "requestBudget": {
        "total": 0,
        "priorRemaining": 0,
        "consumed": 0,
        "remaining": 0,
        "byKind": {
            "navigation": 0,
            "request": 0,
            "retry": 0,
            "websocketHandshake": 0,
            "websocketFrame": 0,
        },
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
        "minDelayMsApplied": 0,
        "maxConcurrencyObserved": 1,
    },
    "execution": {
        "targetCodeExecution": "blocked",
        "executedCodeSha256": [],
        "installedCommands": [],
    },
    "runtimeIds": [],
    "diagnostics": [],
    "sideEffects": [],
    "cleanup": {"complete": True, "remainingResources": []},
    "residualRisks": [],
}

VALID_CHECKPOINT = {
    "schemaVersion": "web-protocol-recovery-checkpoint",
    "checkpointId": "cp-test",
    "createdAt": "2026-09-06T12:00:00Z",
    "phase": 2,
    "shape": "local-proof",
    "route": "python-node",
    "gateFamily": "signer",
    "workOrderId": "wo-test",
    "scopeDigest": "0" * 64,
    "budget": {"total": 100, "priorRemaining": 100, "consumed": 2, "remaining": 98},
    "readBudget": {
        "taskUsed": 4,
        "baseCap": 24,
        "extensionUsed": False,
        "extensionCap": 8,
        "consumedPaths": ["references/a.md", "references/b.md", "references/c.md", "references/d.md"],
        "extension": None,
    },
    "acceptedEvidence": [{"path": "js_reverse_cache/samples/proof.json", "sha256": "1" * 64}],
    "blocker": None,
    "nextStep": "return narrow artifact",
    "firstDivergence": None,
    "stageSettle": {"stageCount": 1, "stageOrder": ["sign"], "stateTransition": "none"},
    "runtimeIds": [],
    "browserState": {"residualProcess": "none", "ownership": "none", "cleanupState": "not-applicable"},
}


def checkpoint_semantic_findings(value: dict, label: str) -> list[str]:
    findings: list[str] = []
    budget = value.get("budget") or {}
    if budget.get("remaining") != budget.get("priorRemaining", 0) - budget.get("consumed", 0):
        findings.append(f"{label}: checkpoint budget remaining must equal priorRemaining-consumed")
    read_budget = value.get("readBudget") or {}
    paths = read_budget.get("consumedPaths") or []
    if read_budget.get("taskUsed") != len(paths):
        findings.append(f"{label}: readBudget.taskUsed must equal consumedPaths length")
    cap = read_budget.get("baseCap", 24) + (read_budget.get("extensionCap", 8) if read_budget.get("extensionUsed") else 0)
    if read_budget.get("taskUsed", 0) > cap:
        findings.append(f"{label}: read budget exceeds active cap")
    return findings


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
    read_plan = value.get("readPlan") or {}
    findings.extend(f"{label}: {item}" for item in validate_read_plan(read_plan))
    custody = value.get("runtimeCustody") or {}
    if custody.get("leaseMode") == "observe-external" and custody.get("providerOwnsLease") is True:
        findings.append(f"{label}: observe-external lease mode requires providerOwnsLease=false")
    authorization = value.get("authorization") or {}
    discovery_scopes = authorization.get("discoveryScopes") or []
    if discovery_scopes and authorization.get("actionClass") in {"verifier-submit", "mutation-submit"}:
        findings.append(f"{label}: discoveryScopes authorize observation only, not verifier or mutation submits")
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

    authorization = value.get("authorization") or {}
    live_replay = authorization.get("liveReplayAllowed")
    scopes = authorization.get("allowedHostsAndRoutes") or []
    if live_replay is True:
        if not scopes:
            findings.append(f"{label}: live replay requires at least one route scope")
        if not isinstance(total, int) or total < 1:
            findings.append(f"{label}: live replay requires a positive total budget")
        if not isinstance(remaining, int) or remaining < 1:
            findings.append(f"{label}: live replay requires a positive remaining budget")

    ledger_id = budget.get("budgetLedgerId")
    ledger_path = budget.get("ledgerPath")
    if bool(ledger_id) != bool(ledger_path):
        findings.append(f"{label}: budget ledger id and path must appear together")
    if ledger_path:
        if not isinstance(ledger_path, str) or Path(ledger_path).is_absolute() or ".." in Path(ledger_path).parts:
            findings.append(f"{label}: budget ledger path must be relative and contained")
        if write_mode != "modify-allowlisted":
            findings.append(f"{label}: persistent budget ledger requires modify-allowlisted")
        ledger_allowed = any(
            isinstance(path, str)
            and path.endswith("/**")
            and ledger_path.startswith(path[:-3] + "/")
            for path in allowed_paths
        )
        if not ledger_allowed:
            findings.append(f"{label}: budget ledger path must stay under an allowed ledger subtree")
    return findings


def provider_result_semantic_findings(
    work_order_value: dict, result_value: dict, label: str
) -> list[str]:
    findings: list[str] = []
    for field in ("workOrderId", "shape", "gateFamily", "protocolOwner"):
        if result_value.get(field) != work_order_value.get(field):
            findings.append(f"{label}: {field} must match the work order")
    if result_value.get("provider") != work_order_value.get("activeProvider"):
        findings.append(f"{label}: provider must match activeProvider")

    incoming_runtime_ids = {
        item.get("resourceId"): item
        for item in (work_order_value.get("runtimeIds") or [])
        if isinstance(item, dict) and item.get("resourceId")
    }
    result_runtime_ids = {
        item.get("resourceId"): item
        for item in (result_value.get("runtimeIds") or [])
        if isinstance(item, dict) and item.get("resourceId")
    }
    for resource_id, incoming in incoming_runtime_ids.items():
        returned = result_runtime_ids.get(resource_id)
        if not isinstance(returned, dict):
            findings.append(f"{label}: result omitted incoming runtime ID {resource_id}")
            continue
        for field in ("engine", "contextId", "targetId", "navigationEpoch", "owner"):
            if returned.get(field) != incoming.get(field):
                findings.append(
                    f"{label}: runtime ID {resource_id} changed immutable {field}"
                )

    work_budget = (work_order_value.get("authorization") or {}).get("requestBudget") or {}
    result_budget = result_value.get("requestBudget") or {}
    total = work_budget.get("total")
    prior = work_budget.get("remaining")
    if result_budget.get("total") != total:
        findings.append(f"{label}: requestBudget.total must match the work order")
    if result_budget.get("priorRemaining") != prior:
        findings.append(f"{label}: requestBudget.priorRemaining must match the work order")
    by_kind = result_budget.get("byKind") or {}
    consumed = result_budget.get("consumed")
    if isinstance(consumed, int) and consumed != sum(by_kind.values()):
        findings.append(f"{label}: requestBudget.consumed must equal sum(byKind)")
    remaining = result_budget.get("remaining")
    if isinstance(prior, int) and isinstance(consumed, int) and remaining != prior - consumed:
        findings.append(f"{label}: requestBudget.remaining must equal priorRemaining - consumed")
    if isinstance(total, int) and isinstance(remaining, int) and not 0 <= remaining <= total:
        findings.append(f"{label}: requestBudget.remaining must stay within total")
    if result_budget.get("observedAutomatic") != work_budget.get("observedAutomatic"):
        findings.append(f"{label}: observedAutomatic must match the immutable work order")
    required_min_delay = work_budget.get("minDelayMs")
    applied_min_delay = result_budget.get("minDelayMsApplied")
    if (
        isinstance(required_min_delay, int)
        and isinstance(applied_min_delay, int)
        and applied_min_delay < required_min_delay
    ):
        findings.append(f"{label}: minDelayMsApplied must meet the work-order minimum")
    allowed_concurrency = work_budget.get("concurrency")
    observed_concurrency = result_budget.get("maxConcurrencyObserved")
    if (
        isinstance(allowed_concurrency, int)
        and isinstance(observed_concurrency, int)
        and observed_concurrency > allowed_concurrency
    ):
        findings.append(f"{label}: maxConcurrencyObserved must not exceed the work-order limit")

    execution_policy = (work_order_value.get("authorization") or {}).get("executionPolicy") or {}
    execution = result_value.get("execution") or {}
    if execution.get("targetCodeExecution") != execution_policy.get("targetCodeExecution"):
        findings.append(f"{label}: execution targetCodeExecution must match the work order")
    approved_hashes = set(execution_policy.get("approvedCodeSha256") or [])
    if not set(execution.get("executedCodeSha256") or []) <= approved_hashes:
        findings.append(f"{label}: executed code hashes must be approved")
    approved_commands = set(execution_policy.get("approvedCommands") or [])
    if not set(execution.get("installedCommands") or []) <= approved_commands:
        findings.append(f"{label}: installed commands must be approved")

    runtime_ids = result_value.get("runtimeIds") or []
    resource_ids = {item.get("resourceId") for item in runtime_ids if isinstance(item, dict)}
    retained = {
        item.get("resourceId")
        for item in runtime_ids
        if isinstance(item, dict) and item.get("lifecycle") == "retained"
    }
    live = {
        item.get("resourceId")
        for item in runtime_ids
        if isinstance(item, dict) and item.get("lifecycle") == "live"
    }
    cleanup = result_value.get("cleanup") or {}
    remaining_resources = set(cleanup.get("remainingResources") or [])
    if not remaining_resources <= resource_ids:
        findings.append(f"{label}: cleanup remaining resources must be known runtime IDs")
    if remaining_resources != retained:
        findings.append(f"{label}: cleanup remaining resources must equal retained IDs")
    if result_value.get("status") == "complete" and (live or not cleanup.get("complete")):
        findings.append(f"{label}: complete result cannot retain live resources or incomplete cleanup")
    return findings


def doc_examples() -> list[dict]:
    text = WORK_ORDER_DOC.read_text(encoding="utf-8")
    return [json.loads(block) for block in re.findall(r"```json\s*\n(.*?)\n```", text, re.S)]


def doc_example_findings(
    work_order: Draft202012Validator, result: Draft202012Validator
) -> list[str]:
    try:
        examples = doc_examples()
    except json.JSONDecodeError as error:
        return [f"provider-work-order.md JSON example is invalid: {error}"]
    if len(examples) != 2:
        return [f"provider-work-order.md must contain exactly two JSON examples, got {len(examples)}"]
    work_order_example, result_example = examples
    findings = expect_valid(work_order, work_order_example, "provider-work-order.md work order example")
    findings.extend(
        work_order_semantic_findings(
            work_order_example, "provider-work-order.md work order example"
        )
    )
    findings.extend(expect_valid(result, result_example, "provider-work-order.md result example"))
    findings.extend(
        provider_result_semantic_findings(
            work_order_example,
            result_example,
            "provider-work-order.md result example",
        )
    )
    return findings


def main() -> int:
    failures: list[str] = []
    work_order = Draft202012Validator(
        load_schema("provider-work-order.schema.json"), format_checker=FormatChecker()
    )
    result = Draft202012Validator(
        load_schema("provider-result.schema.json"), format_checker=FormatChecker()
    )
    Draft202012Validator.check_schema(load_schema("case.schema.json"))
    Draft202012Validator.check_schema(load_schema("case-registry.schema.json"))
    checkpoint_validator = Draft202012Validator(
        load_schema("checkpoint.schema.json"), format_checker=FormatChecker()
    )

    failures.extend(expect_valid(work_order, VALID_WORK_ORDER, "valid offline work order"))
    failures.extend(work_order_semantic_findings(VALID_WORK_ORDER, "valid offline work order"))
    failures.extend(expect_valid(checkpoint_validator, VALID_CHECKPOINT, "valid checkpoint"))
    failures.extend(checkpoint_semantic_findings(VALID_CHECKPOINT, "valid checkpoint"))
    bad_checkpoint = copy.deepcopy(VALID_CHECKPOINT)
    bad_checkpoint["budget"]["remaining"] = 100
    checkpoint_findings = checkpoint_semantic_findings(
        bad_checkpoint, "checkpoint budget conservation"
    )
    if not any("checkpoint budget remaining" in item for item in checkpoint_findings):
        failures.append("checkpoint budget conservation: expected semantic failure")
    failures.extend(doc_example_findings(work_order, result))

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
    failures.extend(expect_invalid(work_order, relative_write_root, "relative writable root schema"))
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

    discovery_with_submit = copy.deepcopy(VALID_WORK_ORDER)
    discovery_with_submit["authorization"]["actionClass"] = "verifier-submit"
    discovery_with_submit["authorization"]["actionApproval"] = "standing-verifier-submit"
    discovery_findings = work_order_semantic_findings(discovery_with_submit, "discovery submit guard")
    if not any("discoveryScopes authorize observation only" in item for item in discovery_findings):
        failures.append("discovery submit guard: expected verifier-submit with discoveryScopes to fail")

    observe_lease_conflict = copy.deepcopy(VALID_WORK_ORDER)
    observe_lease_conflict["runtimeCustody"]["providerOwnsLease"] = True
    lease_findings = work_order_semantic_findings(observe_lease_conflict, "observe lease guard")
    if not any("observe-external lease mode requires providerOwnsLease=false" in item for item in lease_findings):
        failures.append("observe lease guard: expected providerOwnsLease=true with observe-external to fail")

    remaining_gt_total = copy.deepcopy(VALID_WORK_ORDER)
    remaining_gt_total["authorization"]["requestBudget"]["total"] = 1
    remaining_gt_total["authorization"]["requestBudget"]["remaining"] = 2
    failures.extend(expect_valid(work_order, remaining_gt_total, "budget shape still valid"))
    if not work_order_semantic_findings(remaining_gt_total, "budget semantic guard"):
        failures.append("budget semantic guard: expected remaining>total to fail")

    bad_hash = copy.deepcopy(VALID_WORK_ORDER)
    bad_hash["authorization"]["executionPolicy"] = {
        "targetCodeExecution": "approved-reviewed-hash",
        "approvedCodeSha256": ["bad"],
    }
    failures.extend(expect_invalid(work_order, bad_hash, "invalid approvedCodeSha256"))

    expired_shape = copy.deepcopy(VALID_WORK_ORDER)
    expired_shape["authorization"]["executionPolicy"] = {
        "targetCodeExecution": "approved-reviewed-hash",
        "approvedCodeSha256": ["0" * 64],
        "dependencyInstall": "blocked",
        "approvedCommands": [],
        "approvalEvidence": "approved target-code review",
        "approvalDeadline": "not-a-date",
        "sandbox": {
            "backend": "capability-denied-external",
            "adapterId": "reviewed-adapter",
            "adapterSha256": "1" * 64,
            "capabilityEvidence": "review record",
            "timeoutMs": 1000,
            "outputByteCap": 1024,
        },
    }
    failures.extend(expect_invalid(work_order, expired_shape, "invalid target-code approval deadline"))

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

    missing_read_only_approval = copy.deepcopy(VALID_WORK_ORDER)
    missing_read_only_approval["authorization"].pop("actionApproval")
    failures.extend(
        expect_invalid(
            work_order,
            missing_read_only_approval,
            "read-only without standing-read-only actionApproval",
        )
    )

    missing_verifier_approval = copy.deepcopy(VALID_WORK_ORDER)
    missing_verifier_approval["authorization"]["actionClass"] = "verifier-submit"
    missing_verifier_approval["authorization"].pop("actionApproval")
    failures.extend(
        expect_invalid(
            work_order,
            missing_verifier_approval,
            "verifier-submit without actionApproval",
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

    approved_verifier_mutation = copy.deepcopy(VALID_WORK_ORDER)
    approved_verifier_mutation["authorization"]["actionClass"] = "verifier-submit"
    approved_verifier_mutation["authorization"]["actionApproval"] = (
        "user-confirmed-mutation"
    )
    failures.extend(
        expect_valid(
            work_order,
            approved_verifier_mutation,
            "verifier-submit with user-confirmed mutation approval",
        )
    )

    invalid_live_budget = copy.deepcopy(VALID_WORK_ORDER)
    invalid_live_budget["authorization"]["liveReplayAllowed"] = True
    invalid_live_budget["authorization"]["requestBudget"]["total"] = 0
    invalid_live_budget["authorization"]["requestBudget"]["remaining"] = 0
    failures.extend(expect_invalid(work_order, invalid_live_budget, "live replay without positive budget"))
    live_budget_findings = work_order_semantic_findings(
        invalid_live_budget, "live replay budget semantic guard"
    )
    if not any("positive total budget" in item for item in live_budget_findings):
        failures.append("live replay budget semantic guard: expected positive budget failure")

    invalid_ledger = copy.deepcopy(VALID_WORK_ORDER)
    invalid_ledger["authorization"]["requestBudget"]["budgetLedgerId"] = "gt4-ledger"
    invalid_ledger["authorization"]["requestBudget"]["ledgerPath"] = "js_reverse_cache/private/gt4.sqlite3"
    invalid_ledger["project"]["writeMode"] = "create-only"
    invalid_ledger["project"]["allowedPaths"] = ["js_reverse_cache/private/gt4.sqlite3"]
    ledger_findings = work_order_semantic_findings(
        invalid_ledger, "persistent ledger semantic guard"
    )
    if not any("modify-allowlisted" in item for item in ledger_findings):
        failures.append("persistent ledger semantic guard: expected write mode failure")

    failures.extend(expect_valid(result, VALID_RESULT, "valid provider result"))
    missing_cleanup = copy.deepcopy(VALID_RESULT)
    missing_cleanup["cleanup"].pop("remainingResources")
    failures.extend(expect_invalid(result, missing_cleanup, "missing cleanup.remainingResources"))
    missing_semantic = copy.deepcopy(VALID_RESULT)
    missing_semantic["verification"].pop("semanticSuccess")
    failures.extend(expect_invalid(result, missing_semantic, "missing semanticSuccess"))

    result_budget_drift = copy.deepcopy(VALID_RESULT)
    result_budget_drift["requestBudget"]["consumed"] = 1
    semantic_findings = provider_result_semantic_findings(
        VALID_WORK_ORDER, result_budget_drift, "provider result budget semantic guard"
    )
    if not any("consumed must equal" in item for item in semantic_findings):
        failures.append("provider result budget semantic guard: expected conservation failure")

    result_timing_drift = copy.deepcopy(VALID_RESULT)
    timing_order = copy.deepcopy(VALID_WORK_ORDER)
    timing_order["authorization"]["requestBudget"]["minDelayMs"] = 50
    timing_order["authorization"]["requestBudget"]["concurrency"] = 1
    result_timing_drift["requestBudget"]["minDelayMsApplied"] = 0
    result_timing_drift["requestBudget"]["maxConcurrencyObserved"] = 2
    timing_findings = provider_result_semantic_findings(
        timing_order, result_timing_drift, "provider result timing semantic guard"
    )
    if not any("minDelayMsApplied" in item for item in timing_findings):
        failures.append("provider result timing semantic guard: expected min delay failure")
    if not any("maxConcurrencyObserved" in item for item in timing_findings):
        failures.append("provider result timing semantic guard: expected concurrency failure")

    result_runtime_drop = copy.deepcopy(VALID_RESULT)
    runtime_order = copy.deepcopy(VALID_WORK_ORDER)
    runtime_order["runtimeIds"] = [
        {
            "resourceId": "worker-1",
            "engine": "chromium",
            "contextId": 1,
            "targetId": "target-1",
            "navigationEpoch": 0,
            "owner": "provider",
            "lifecycle": "live",
        }
    ]
    runtime_findings = provider_result_semantic_findings(
        runtime_order, result_runtime_drop, "provider result runtime reconciliation guard"
    )
    if not any("omitted incoming runtime ID" in item for item in runtime_findings):
        failures.append("provider result runtime reconciliation guard: expected missing ID failure")

    result_observed_drift = copy.deepcopy(VALID_RESULT)
    observed_order = copy.deepcopy(VALID_WORK_ORDER)
    observed_order["authorization"]["requestBudget"]["observedAutomatic"]["total"] = 1
    observed_findings = provider_result_semantic_findings(
        observed_order, result_observed_drift, "provider result automatic-traffic guard"
    )
    if not any("observedAutomatic" in item for item in observed_findings):
        failures.append("provider result automatic-traffic guard: expected observedAutomatic failure")

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
