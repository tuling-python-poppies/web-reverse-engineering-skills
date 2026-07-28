#!/usr/bin/env python3
"""Offline architecture checks for web-protocol-recovery v2."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
PROVIDER_REGISTRY = SKILL_ROOT / "references" / "providers" / "registry.json"
CASES_ROOT = SKILL_ROOT / "references" / "cases"
WORK_ORDER_SCHEMA = SKILL_ROOT / "references" / "schemas" / "provider-work-order-v2.schema.json"
WORK_ORDER_DOC = SKILL_ROOT / "references" / "methodology" / "provider-work-order.md"
READ_BUDGET_DOC = SKILL_ROOT / "references" / "methodology" / "read-budget.md"

EXPECTED_PROVIDER_IDS = {
    "chromium-recon",
    "camoufox",
    "wechat-miniapp",
    "browser-hooks",
    "ast",
    "verifier",
    "akamai",
    "river-security",
    "iv8",
    "python-node",
    "pure-python",
    "python-collector",
}
IMPLEMENTATION_MODES = {"iv8", "python-node", "pure-python"}
ROUTE_SENTINELS = {"evidence-reuse"}
GATE_FAMILIES = {"signer", "challenge", "verifier", "decode", "session", "transport"}
OBSOLETE_ROUTE_VALUES = {"env-patch", "douyin-abogus-native"} | {f"{gate}-gated" for gate in GATE_FAMILIES}
TEXT_SUFFIXES = {".md", ".json", ".py", ".js", ".mjs", ".cjs"}
CODE_SUFFIXES = {".py", ".js", ".mjs", ".cjs"}
RESIDUE_NAMES = {"__pycache__", ".pytest_cache"}
RESIDUE_SUFFIXES = {".pyc", ".pyo"}
OBSOLETE_PROVIDER_PATHS = (
    "providers/implementation/env-patch/PROVIDER.md",
    "providers/implementation/verifier/PROVIDER.md",
    "providers/implementation/akamai/PROVIDER.md",
    "providers/implementation/river-security/PROVIDER.md",
    "providers/implementation/browser-hooks/PROVIDER.md",
    "providers/implementation/ast/PROVIDER.md",
    "providers/implementation/python-collector/PROVIDER.md",
    "providers/implementation/douyin-abogus-native/PROVIDER.md",
    "scripts/providers/python-collector/scaffold_project.py",
)
OBSOLETE_SCHEMA_STRINGS = (
    "web-protocol-recovery-provider-work-order/v1",
    "web-protocol-recovery-provider-result/v1",
    "web-protocol-recovery-case/v1",
)
OBSOLETE_CONTRACT_TEXT = (
    "providerChain:",
    "route to `challenge-gated`",
    "route to `signer-gated`",
    "route to `verifier-gated`",
    "route to `decode-gated`",
    "route to `session-gated`",
    "route to `transport-gated`",
)

NETWORK_JS = re.compile(
    r"\bfetch\s*\(|new\s+(?:XMLHttpRequest|WebSocket)\s*\(|"
    r"\brequire\(['\"](?:http|https|axios|got|node:http|node:https)['\"]\)|"
    r"\baxios\.(?:get|post|put|delete|patch|request)\s*\(|"
    r"\bgot\.(?:get|post|put|delete|patch)\s*\("
)
ROUTE_LITERAL = re.compile(r"route:[^\S\r\n]*`?([A-Za-z0-9_-]+)")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    return path.relative_to(SKILL_ROOT).as_posix()


def provider_registry_findings() -> list[str]:
    findings: list[str] = []
    registry = load_json(PROVIDER_REGISTRY)
    providers = registry.get("providers", [])
    ids = [item.get("id") for item in providers]
    if set(ids) != EXPECTED_PROVIDER_IDS:
        findings.append(f"provider IDs mismatch: got={sorted(ids)} expected={sorted(EXPECTED_PROVIDER_IDS)}")
    if set(registry.get("implementationModes", [])) != IMPLEMENTATION_MODES:
        findings.append("implementationModes must be exactly iv8/python-node/pure-python")
    for provider in providers:
        pid = provider.get("id")
        entry = provider.get("entry")
        role = provider.get("role")
        if not isinstance(entry, str) or not (SKILL_ROOT / entry).is_file():
            findings.append(f"provider {pid}: entry missing: {entry}")
        if pid == "python-collector" and role != "delivery":
            findings.append("python-collector must have role=delivery")
        if pid in {"iv8", "python-node", "pure-python"} and role != "implementation":
            findings.append(f"{pid} must have role=implementation")
        if provider.get("mayOwnFinalLiveEgress") and pid != "python-collector":
            findings.append(f"{pid}: only python-collector may own final live egress")
        if pid == "python-node" and "env-patch" not in provider.get("strategies", []):
            findings.append("python-node must declare env-patch strategy")
        if pid == "pure-python" and "douyin-abogus-native" not in provider.get("profiles", []):
            findings.append("pure-python must declare douyin-abogus-native profile")
    return findings


def route_literal_findings() -> list[str]:
    valid_routes = EXPECTED_PROVIDER_IDS | ROUTE_SENTINELS
    findings: list[str] = []
    for path in SKILL_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        if set(path.parts) & RESIDUE_NAMES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in ROUTE_LITERAL.finditer(text):
            value = match.group(1)
            if value in OBSOLETE_ROUTE_VALUES:
                findings.append(f"{rel(path)}: obsolete or gate-family route literal: {value}")
            elif value not in valid_routes and value not in {"selected", "current", "Provider"}:
                findings.append(f"{rel(path)}: unknown route literal: {value}")
    return findings


def documentation_contract_findings() -> list[str]:
    findings: list[str] = []
    for path in SKILL_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        if set(path.parts) & RESIDUE_NAMES:
            continue
        if "references" in path.parts and "cases" in path.parts and path.name != "README.md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        normalized = text.replace("\\", "/")
        for needle in OBSOLETE_PROVIDER_PATHS:
            if needle in normalized:
                findings.append(f"{rel(path)}: obsolete provider path: {needle}")
        for needle in OBSOLETE_SCHEMA_STRINGS:
            if needle in text:
                findings.append(f"{rel(path)}: obsolete schema string: {needle}")
        for needle in OBSOLETE_CONTRACT_TEXT:
            if needle in text:
                findings.append(f"{rel(path)}: obsolete contract text: {needle}")
    return findings


def read_plan_contract_findings() -> list[str]:
    findings: list[str] = []
    schema = load_json(WORK_ORDER_SCHEMA)
    required = set(schema.get("required", []))
    if "readPlan" not in schema.get("properties", {}):
        findings.append("provider-work-order-v2 schema must define readPlan")
    if "activeProvider" not in required:
        findings.append("provider-work-order-v2 schema must require activeProvider")

    work_order_text = WORK_ORDER_DOC.read_text(encoding="utf-8", errors="replace")
    read_budget_text = READ_BUDGET_DOC.read_text(encoding="utf-8", errors="replace")
    for token in (
        '"schemaVersion": "web-protocol-recovery-provider-work-order/v2"',
        '"activeProvider"',
        '"readPlan"',
        '"required"',
        '"optional"',
    ):
        if token not in work_order_text:
            findings.append(f"provider-work-order.md missing token: {token}")
    for token in ("| Whole task | 24 distinct paths |", "`readPlan`", "required", "optional"):
        if token not in read_budget_text:
            findings.append(f"read-budget.md missing token: {token}")

    whole_task_cap = 24
    initial = [
        "README.md",
        "references/startup-triage-playbook.md",
        "references/tool-playbook.md",
    ]
    registry_handoff = [
        "references/providers/registry.json",
        "references/methodology/provider-work-order.md",
        "references/methodology/read-budget.md",
    ]
    case_selection = ["references/cases/registry.json"]
    delivery = [
        "references/providers/delivery/python-collector/PROVIDER.md",
        "scripts/providers/delivery/python-collector/scaffold_project.py",
        "references/report-templates.md",
    ]
    write_gate = ["references/methodology/project-layout.md"]
    pure_python_case = [
        "references/cases/pure-python/jd-h5st/case.json",
        "references/cases/pure-python/jd-h5st/PROCESS.md",
        "references/cases/pure-python/jd-h5st/entry.py",
        "references/cases/pure-python/jd-h5st/tests/test_vectors.py",
        "references/cases/pure-python/jd-h5st/fixtures/vectors.json",
        "references/cases/pure-python/jd-h5st/fixtures/response.sample.json",
        "references/cases/pure-python/jd-h5st/fixtures/live-proof.summary.json",
    ]
    python_node_case = [
        "references/cases/python-node/pzds-aliyun-v2-goods-public/case.json",
        "references/cases/python-node/pzds-aliyun-v2-goods-public/PROCESS.md",
        "references/cases/python-node/pzds-aliyun-v2-goods-public/entry.py",
        "references/cases/python-node/pzds-aliyun-v2-goods-public/tests/test_vectors.py",
        "references/cases/python-node/pzds-aliyun-v2-goods-public/fixtures/vectors.json",
        "references/cases/python-node/pzds-aliyun-v2-goods-public/fixtures/request.sample.json",
        "references/cases/python-node/pzds-aliyun-v2-goods-public/fixtures/response.sample.json",
        "references/cases/python-node/pzds-aliyun-v2-goods-public/fixtures/live-proof.summary.json",
    ]
    iv8_case = [
        "references/cases/iv8/twayair-akamai-availability/case.json",
        "references/cases/iv8/twayair-akamai-availability/PROCESS.md",
        "references/cases/iv8/twayair-akamai-availability/entry.py",
        "references/cases/iv8/twayair-akamai-availability/tests/test_vectors.py",
        "references/cases/iv8/twayair-akamai-availability/fixtures/vectors.json",
        "references/cases/iv8/twayair-akamai-availability/fixtures/response.sample.json",
    ]
    gt4_case = [
        "references/cases/iv8/geetest-v4-slider/case.json",
        "references/cases/iv8/geetest-v4-slider/PROCESS.md",
        "references/cases/iv8/geetest-v4-slider/entry.py",
        "references/cases/iv8/geetest-v4-slider/pull_live_state.py",
    ]

    official_chains = {
        "evidence-reuse local-proof": [
            ("initial dispatch", 3, initial),
            ("provider handoff", 3, registry_handoff),
            ("case selection", 1, case_selection),
            ("selected case bundle", 8, pure_python_case),
            ("implementation handoff", 3, [
                "references/providers/implementation/pure-python/PROVIDER.md",
                "references/providers/implementation/pure-python/profiles/douyin-abogus-native.md",
                "references/methodology/success-shape-scripts.md",
            ]),
            ("write gate", 1, write_gate),
        ],
        "chromium hooks pure-python collector": [
            ("initial dispatch", 3, initial),
            ("recon handoff", 3, [
                "references/providers/registry.json",
                "references/methodology/provider-work-order.md",
                "references/providers/reconnaissance/chromium-recon/PROVIDER.md",
            ]),
            ("protocol handoff", 3, [
                "references/providers/protocol-recovery/browser-hooks/PROVIDER.md",
                "references/providers/protocol-recovery/browser-hooks/references/network.md",
                "references/providers/protocol-recovery/browser-hooks/references/crypto.md",
            ]),
            ("implementation handoff", 3, [
                "references/providers/implementation/pure-python/PROVIDER.md",
                "references/methodology/success-shape-scripts.md",
                "references/methodology/read-budget.md",
            ]),
            ("delivery handoff", 3, delivery),
            ("write gate", 1, write_gate),
        ],
        "ast env-patch collector": [
            ("initial dispatch", 3, initial),
            ("protocol handoff", 3, [
                "references/providers/registry.json",
                "references/providers/protocol-recovery/ast/PROVIDER.md",
                "references/providers/protocol-recovery/ast/references/template-usage.md",
            ]),
            ("implementation handoff", 3, [
                "references/providers/implementation/python-node/PROVIDER.md",
                "references/providers/implementation/python-node/strategies/env-patch/STRATEGY.md",
                "references/providers/implementation/python-node/strategies/env-patch/references/env-modules.md",
            ]),
            ("delivery handoff", 3, delivery),
            ("write gate", 1, write_gate),
        ],
        "verifier iv8 collector": [
            ("initial dispatch", 3, initial),
            ("verifier handoff", 3, [
                "references/providers/protocol-recovery/verifier/PROVIDER.md",
                "references/providers/protocol-recovery/verifier/references/geetest-gt4-workflow.md",
                "references/providers/protocol-recovery/verifier/references/replay-playbook.md",
            ]),
            ("case selection", 1, case_selection),
            ("selected case bundle", 8, gt4_case),
            ("implementation handoff", 3, [
                "references/providers/implementation/iv8/PROVIDER.md",
                "references/providers/implementation/iv8/references/api-inventory.md",
                "references/providers/implementation/iv8/references/script-writing-rules.md",
            ]),
            ("delivery handoff", 3, delivery),
        ],
        "verifier python-node collector": [
            ("initial dispatch", 3, initial),
            ("verifier handoff", 3, [
                "references/providers/protocol-recovery/verifier/PROVIDER.md",
                "references/providers/protocol-recovery/verifier/references/geetest-gt4-workflow.md",
                "references/methodology/provider-work-order.md",
            ]),
            ("implementation handoff", 3, [
                "references/providers/implementation/python-node/PROVIDER.md",
                "references/providers/implementation/python-node/scripts/gt4_bundle_helper.js",
                "references/methodology/read-budget.md",
            ]),
            ("delivery handoff", 3, delivery),
            ("write gate", 1, write_gate),
        ],
        "verifier pure-python collector": [
            ("initial dispatch", 3, initial),
            ("verifier handoff", 3, [
                "references/providers/protocol-recovery/verifier/PROVIDER.md",
                "references/providers/protocol-recovery/verifier/references/geetest-gt4-workflow.md",
                "references/providers/protocol-recovery/verifier/references/slide-captcha-overview.md",
            ]),
            ("implementation handoff", 3, [
                "references/providers/implementation/pure-python/PROVIDER.md",
                "references/providers/delivery/python-collector/scripts/verifier/gt4_pure_replay.py",
                "references/methodology/success-shape-scripts.md",
            ]),
            ("delivery handoff", 3, delivery),
            ("write gate", 1, write_gate),
        ],
        "akamai iv8 collector": [
            ("initial dispatch", 3, initial),
            ("akamai handoff", 3, [
                "references/providers/protocol-recovery/akamai/PROVIDER.md",
                "references/providers/protocol-recovery/akamai/references/workflow.md",
                "references/providers/protocol-recovery/akamai/references/cookie-state-machine.md",
            ]),
            ("case selection", 1, case_selection),
            ("selected case bundle", 8, iv8_case),
            ("implementation handoff", 3, [
                "references/providers/implementation/iv8/PROVIDER.md",
                "references/providers/implementation/iv8/references/api-inventory.md",
                "references/providers/implementation/iv8/references/browser-iv8-bridge.md",
            ]),
            ("delivery handoff", 3, delivery),
        ],
        "river-security iv8 collector": [
            ("initial dispatch", 3, initial),
            ("river handoff", 3, [
                "references/providers/protocol-recovery/river-security/PROVIDER.md",
                "references/transport-pre-gate-playbook.md",
                "references/methodology/provider-work-order.md",
            ]),
            ("implementation handoff", 3, [
                "references/providers/implementation/iv8/PROVIDER.md",
                "references/providers/implementation/iv8/references/api-inventory.md",
                "references/providers/implementation/iv8/references/runtime-cheatsheet.md",
            ]),
            ("delivery handoff", 3, delivery),
            ("write gate", 1, write_gate),
        ],
        "api-inventory selected case": [
            ("initial dispatch", 3, initial),
            ("provider handoff", 3, registry_handoff),
            ("iv8 api inventory gate", 3, [
                "references/providers/implementation/iv8/PROVIDER.md",
                "references/providers/implementation/iv8/references/api-inventory.md",
                "references/providers/implementation/iv8/references/case-ingestion-rules.md",
            ]),
            ("case selection", 1, case_selection),
            ("selected case bundle", 8, iv8_case),
            ("write gate", 1, write_gate),
        ],
        "python-node selected case collector": [
            ("initial dispatch", 3, initial),
            ("provider handoff", 3, registry_handoff),
            ("case selection", 1, case_selection),
            ("selected case bundle", 8, python_node_case),
            ("implementation handoff", 3, [
                "references/providers/implementation/python-node/PROVIDER.md",
                "references/providers/implementation/python-node/strategies/env-patch/STRATEGY.md",
                "references/methodology/success-shape-scripts.md",
            ]),
            ("delivery handoff", 3, delivery),
        ],
    }
    for chain_name, windows in official_chains.items():
        distinct_paths: set[str] = set()
        for window_name, cap, paths in windows:
            if len(paths) > cap:
                findings.append(
                    f"read-plan sim window exceeds cap: {chain_name}/{window_name} "
                    f"used={len(paths)} cap={cap}"
                )
            for rel_path in paths:
                if not (SKILL_ROOT / rel_path).exists():
                    findings.append(f"read-plan sim path missing: {chain_name}: {rel_path}")
                distinct_paths.add(rel_path)
        if len(distinct_paths) > whole_task_cap:
            findings.append(
                f"read-plan sim exceeds whole-task cap: {chain_name} "
                f"used={len(distinct_paths)} cap={whole_task_cap}"
            )
    return findings


def case_manifest_findings() -> list[str]:
    findings: list[str] = []
    for path in sorted(CASES_ROOT.glob("**/case.json")):
        data = load_json(path)
        case_id = data.get("caseId")
        schema = data.get("schemaVersion")
        if schema != "web-protocol-recovery-case/v2":
            findings.append(f"{rel(path)}: schemaVersion must be web-protocol-recovery-case/v2")
            continue
        implementation = data.get("implementation")
        if data.get("caseKind") == "evidence" and implementation is not None:
            findings.append(f"{case_id}: evidence case must not declare implementation")
        if data.get("caseKind") == "implementation" and not isinstance(implementation, dict):
            findings.append(f"{case_id}: implementation case must declare implementation object")
        if isinstance(implementation, dict):
            mode = implementation.get("mode")
            strategy = implementation.get("strategy")
            profile = implementation.get("profile")
            if mode not in IMPLEMENTATION_MODES:
                findings.append(f"{case_id}: invalid implementation mode {mode!r}")
            if strategy == "env-patch" and mode != "python-node":
                findings.append(f"{case_id}: env-patch strategy requires mode=python-node")
            if profile == "douyin-abogus-native" and mode != "pure-python":
                findings.append(f"{case_id}: douyin-abogus-native profile requires mode=pure-python")
        for field in ("historicalProviderChain", "requiredCurrentProviderChain"):
            for index, stage in enumerate(data.get(field, [])):
                provider = stage.get("provider")
                role = stage.get("role")
                if provider not in EXPECTED_PROVIDER_IDS:
                    findings.append(f"{case_id}: {field}[{index}] invalid provider {provider!r}")
                if provider == "python-collector" and role != "delivery":
                    findings.append(f"{case_id}: python-collector stage must be delivery")
                if stage.get("strategy") == "env-patch" and provider != "python-node":
                    findings.append(f"{case_id}: env-patch strategy must be on python-node stage")
                if stage.get("profile") == "douyin-abogus-native" and provider != "pure-python":
                    findings.append(f"{case_id}: douyin-abogus-native profile must be on pure-python stage")
    return findings


def residue_findings() -> list[str]:
    findings: list[str] = []
    for path in SKILL_ROOT.rglob("*"):
        if path.name in RESIDUE_NAMES:
            findings.append(f"residue directory present: {rel(path)}")
        elif path.is_file() and path.suffix.lower() in RESIDUE_SUFFIXES:
            findings.append(f"residue file present: {rel(path)}")
    return findings


def python_live_egress_findings(path: Path) -> list[str]:
    if "delivery" in path.parts:
        return []
    if "cases" in path.parts:
        return []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []
    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Attribute) and target.attr in {"get", "post", "put", "delete", "patch", "request"}:
                base = target.value
                name = base.id if isinstance(base, ast.Name) else None
                if name in {"requests", "session", "httpx", "client"}:
                    findings.append(f"{rel(path)}: possible non-delivery live HTTP call at line {node.lineno}")
    return findings


def live_egress_findings() -> list[str]:
    findings: list[str] = []
    for path in SKILL_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in CODE_SUFFIXES:
            continue
        if set(path.parts) & RESIDUE_NAMES:
            continue
        if "cases" in path.parts:
            continue
        if path.suffix.lower() == ".py":
            findings.extend(python_live_egress_findings(path))
            continue
        if "delivery" in path.parts:
            continue
        if "env" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if NETWORK_JS.search(text):
            findings.append(f"{rel(path)}: possible non-delivery JS network primitive")
    return findings


def main() -> int:
    checks = [
        ("provider registry", provider_registry_findings),
        ("route literals", route_literal_findings),
        ("documentation contract", documentation_contract_findings),
        ("read-plan contract", read_plan_contract_findings),
        ("case manifests", case_manifest_findings),
        ("live egress", live_egress_findings),
        ("residue", residue_findings),
    ]
    failures: list[str] = []
    for name, func in checks:
        findings = func()
        print(f"== {name} ==")
        if findings:
            for finding in findings:
                print(f"FAIL {finding}")
            failures.extend(findings)
        else:
            print("PASS")
    print(f"summary: failures={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
