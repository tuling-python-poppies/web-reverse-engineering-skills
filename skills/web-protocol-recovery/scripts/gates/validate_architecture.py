#!/usr/bin/env python3
"""Offline architecture checks for web-protocol-recovery."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = SKILL_ROOT / "scripts"
PREFLIGHT_DOC = SKILL_ROOT / "scripts" / "gates" / "preflight.py"
SCRIPT_CATEGORY_DIRS = {"tools", "gates", "tests", "providers"}
SCRIPTS_ROOT_ALLOWED_FILES = {"README.md"}
PROVIDER_REGISTRY = SKILL_ROOT / "references" / "providers" / "registry.json"
CASES_ROOT = SKILL_ROOT / "references" / "cases"
WORK_ORDER_SCHEMA = SKILL_ROOT / "references" / "schemas" / "provider-work-order.schema.json"
WORK_ORDER_DOC = SKILL_ROOT / "references" / "methodology" / "provider-work-order.md"
READ_BUDGET_DOC = SKILL_ROOT / "references" / "methodology" / "read-budget.md"
README_DOC = SKILL_ROOT / "README.md"
STARTUP_TRIAGE_DOC = SKILL_ROOT / "references" / "startup-triage-playbook.md"

EXPECTED_PROVIDER_IDS = {
    "chromium-recon",
    "camoufox",
    "wechat-miniapp",
    "browser-hooks",
    "ast",
    "verifier",
    "akamai",
    "river-security",
    "reese84",
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
EOL_CHECKED_SUFFIXES = {".md", ".json", ".py", ".js", ".mjs", ".cjs", ".html", ".txt", ".tsv"}
EOL_CHECKED_FILE_NAMES = {".gitignore", ".gitattributes", "license"}
EOL_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}
LARGE_ASSET_READ_HINT_BYTES = 512 * 1024
LARGE_ASSET_STORAGE_POLICY_BYTES = 5 * 1024 * 1024
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
    "web-protocol-recovery-provider-work-order/v2",
    "web-protocol-recovery-provider-result/v1",
    "web-protocol-recovery-provider-result/v2",
    "web-protocol-recovery-case-registry/v1",
    "web-protocol-recovery-case-registry/v2",
    "web-protocol-recovery-case/v1",
    "web-protocol-recovery-case/v2",
    "web-protocol-recovery-provider-registry/v1",
    "Architecture V2",
    "case-v2.schema.json",
    "provider-work-order-v2.schema.json",
    "provider-result-v2.schema.json",
    "case-registry-v2.schema.json",
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
        if pid in {"verifier", "akamai", "river-security", "reese84"}:
            if role != "protocol-recovery":
                findings.append(f"{pid} must have role=protocol-recovery")
            if not provider.get("ownsProtocolAcceptance"):
                findings.append(f"{pid} must own protocol acceptance")
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
    required_routing_tokens = {
        README_DOC: (
            "reese84/PROVIDER.md",
            "reese84 -> iv8/python-node -> python-collector",
        ),
        READ_BUDGET_DOC: (
            "Reese84 -> iv8/python-node -> python-collector",
            "references/providers/protocol-recovery/reese84/PROVIDER.md",
        ),
        STARTUP_TRIAGE_DOC: (
            "references/providers/protocol-recovery/reese84/PROVIDER.md",
            "generic Imperva",
            "not Camoufox criteria",
        ),
    }
    for path, tokens in required_routing_tokens.items():
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in tokens:
            if token not in text:
                findings.append(f"{rel(path)} missing Reese84 routing token: {token}")
    runtime_counts = {"iv8": 0, "python-node": 0, "pure-python": 0}
    for case_path in CASES_ROOT.glob("**/case.json"):
        runtime = str(load_json(case_path).get("runtime") or "")
        if runtime in runtime_counts:
            runtime_counts[runtime] += 1
    expected_inventory = (
        f"The root registry indexes {sum(runtime_counts.values())} hash-bound "
        "`web-protocol-recovery-case` manifests grouped by implementation runtime: "
        f"{runtime_counts['iv8']} `iv8`, {runtime_counts['python-node']} `python-node`, "
        f"and {runtime_counts['pure-python']} `pure-python`."
    )
    if expected_inventory not in README_DOC.read_text(encoding="utf-8", errors="replace"):
        findings.append("README.md case inventory is stale")
    return findings


def case_process_policy_findings(case_id: str, text: str) -> list[str]:
    """Keep selected case instructions inside the hub's secret/layout contract."""
    findings: list[str] = []
    normalized = text.replace("\\", "/")
    if "`verifier/" in normalized:
        findings.append(f"{case_id}: PROCESS.md must not require a verifier/ project root")
    if re.search(r"`js_reverse_cache/(?!private/)[^`]*(?:session|token|cookie)", normalized):
        findings.append(
            f"{case_id}: PROCESS.md must keep persisted session/token/cookie state under js_reverse_cache/private/**"
        )
    if "Keep\n   full request/response bodies" in text or "Keep full request/response bodies" in text:
        findings.append(
            f"{case_id}: PROCESS.md must not make raw request/response retention the default"
        )
    return findings


def case_process_contract_findings() -> list[str]:
    findings: list[str] = []
    for case_path in sorted(CASES_ROOT.glob("**/case.json")):
        data = load_json(case_path)
        process = (data.get("artifacts") or {}).get("process") or {}
        process_rel = process.get("path")
        if not isinstance(process_rel, str) or not process_rel:
            continue
        process_path = case_path.parent / process_rel
        if not process_path.is_file():
            findings.append(f"{rel(case_path)}: declared PROCESS.md is missing")
            continue
        findings.extend(
            case_process_policy_findings(
                str(data.get("caseId") or rel(case_path)),
                process_path.read_text(encoding="utf-8", errors="replace"),
            )
        )
    return findings


def read_plan_contract_findings() -> list[str]:
    findings: list[str] = []
    schema = load_json(WORK_ORDER_SCHEMA)
    required = set(schema.get("required", []))
    if "readPlan" not in schema.get("properties", {}):
        findings.append("provider-work-order schema must define readPlan")
    if "activeProvider" not in required:
        findings.append("provider-work-order schema must require activeProvider")

    work_order_text = WORK_ORDER_DOC.read_text(encoding="utf-8", errors="replace")
    read_budget_text = READ_BUDGET_DOC.read_text(encoding="utf-8", errors="replace")
    for token in (
        '"schemaVersion": "web-protocol-recovery-provider-work-order"',
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

    layout_text = (SKILL_ROOT / "references" / "methodology" / "project-layout.md").read_text(
        encoding="utf-8", errors="replace"
    )
    skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    report_text = (SKILL_ROOT / "references" / "report-templates.md").read_text(
        encoding="utf-8", errors="replace"
    )
    for token in ("分析报告.md", "compact-replay", "collector"):
        if token not in layout_text:
            findings.append(f"project-layout.md missing delivery report token: {token}")
    if "分析报告.md" not in skill_text:
        findings.append("SKILL.md must require 分析报告.md for Full compact-replay/collector completion")
    if "## 分析报告.md" not in report_text:
        findings.append("report-templates.md must define ## 分析报告.md section")

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
        "references/cases/iv8/geetest-v4-slider/pull_live_state.py",
    ]
    reese84_case = [
        "references/cases/iv8/bangkokair-reese84-booking/case.json",
        "references/cases/iv8/bangkokair-reese84-booking/PROCESS.md",
        "references/cases/iv8/bangkokair-reese84-booking/pull_live_state.py",
        "references/cases/iv8/bangkokair-reese84-booking/fixtures/vectors.json",
        "references/cases/iv8/bangkokair-reese84-booking/fixtures/response.sample.json",
        "references/cases/iv8/bangkokair-reese84-booking/fixtures/live-proof.summary.json",
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
        "chromium ast env-patch collector": [
            ("initial dispatch", 3, initial),
            ("recon handoff", 3, [
                "references/providers/registry.json",
                "references/methodology/provider-work-order.md",
                "references/providers/reconnaissance/chromium-recon/PROVIDER.md",
            ]),
            ("protocol handoff", 3, [
                "references/providers/protocol-recovery/ast/PROVIDER.md",
                "references/providers/protocol-recovery/ast/references/control-flow-patterns.md",
                "references/methodology/read-budget.md",
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
            ("iv8 api inventory gate", 3, [
                "references/methodology/provider-work-order.md",
                "references/providers/implementation/iv8/PROVIDER.md",
                "references/providers/implementation/iv8/references/api-inventory.md",
            ]),
            ("case selection", 1, case_selection),
            ("selected case bundle", 8, gt4_case),
            ("implementation handoff", 3, [
                "references/methodology/provider-work-order.md",
                "references/providers/implementation/iv8/PROVIDER.md",
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
            ("iv8 api inventory gate", 3, [
                "references/methodology/provider-work-order.md",
                "references/providers/implementation/iv8/PROVIDER.md",
                "references/providers/implementation/iv8/references/api-inventory.md",
            ]),
            ("case selection", 1, case_selection),
            ("selected case bundle", 8, iv8_case),
            ("implementation handoff", 3, [
                "references/methodology/provider-work-order.md",
                "references/providers/implementation/iv8/PROVIDER.md",
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
            ("iv8 api inventory gate", 3, [
                "references/methodology/provider-work-order.md",
                "references/providers/implementation/iv8/PROVIDER.md",
                "references/providers/implementation/iv8/references/api-inventory.md",
            ]),
            ("implementation handoff", 3, [
                "references/methodology/provider-work-order.md",
                "references/providers/implementation/iv8/PROVIDER.md",
                "references/providers/implementation/iv8/references/runtime-cheatsheet.md",
            ]),
            ("delivery handoff", 3, delivery),
            ("write gate", 1, write_gate),
        ],
        "river-security env-patch collector": [
            ("initial dispatch", 3, initial),
            ("river handoff", 3, [
                "references/providers/protocol-recovery/river-security/PROVIDER.md",
                "references/methodology/provider-work-order.md",
                "references/challenge-state-envelope-playbook.md",
            ]),
            ("implementation handoff", 3, [
                "references/providers/implementation/python-node/PROVIDER.md",
                "references/providers/implementation/python-node/strategies/env-patch/STRATEGY.md",
                "references/providers/implementation/python-node/strategies/env-patch/references/verification-and-replay.md",
            ]),
            ("delivery handoff", 3, delivery),
            ("write gate", 1, write_gate),
        ],
        "reese84 iv8 collector": [
            ("initial dispatch", 3, initial),
            ("reese84 handoff", 3, [
                "references/providers/protocol-recovery/reese84/PROVIDER.md",
                "references/transport-pre-gate-playbook.md",
                "references/methodology/provider-work-order.md",
            ]),
            ("iv8 api inventory gate", 3, [
                "references/methodology/provider-work-order.md",
                "references/providers/implementation/iv8/PROVIDER.md",
                "references/providers/implementation/iv8/references/api-inventory.md",
            ]),
            ("case selection", 1, case_selection),
            ("selected case bundle", 8, reese84_case),
            ("implementation handoff", 3, [
                "references/methodology/provider-work-order.md",
                "references/providers/implementation/iv8/PROVIDER.md",
                "references/providers/implementation/iv8/references/browser-iv8-bridge.md",
            ]),
            ("delivery handoff", 3, delivery),
            ("write gate", 1, write_gate),
        ],
        "api-inventory selected case": [
            ("initial dispatch", 3, initial),
            ("provider handoff", 3, registry_handoff),
            ("iv8 api inventory gate", 3, [
                "references/methodology/provider-work-order.md",
                "references/providers/implementation/iv8/PROVIDER.md",
                "references/providers/implementation/iv8/references/api-inventory.md",
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
                "references/methodology/provider-work-order.md",
                "references/providers/implementation/python-node/PROVIDER.md",
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


def required_signal_group_findings(
    case_id: str,
    match: dict,
    required_names: set[str] | None = None,
) -> list[str]:
    findings: list[str] = []
    required_names = required_names or set()
    groups = match.get("requiredSignalGroups", [])
    if not groups:
        if required_names:
            findings.append(f"{case_id}: requiredSignalGroups missing")
        return findings
    if not isinstance(groups, list):
        return [f"{case_id}: requiredSignalGroups must be an array"]

    declared_signals = set(map(str, match.get("signals", [])))
    group_names: set[str] = set()
    grouped_signals: set[str] = set()
    for index, group in enumerate(groups):
        if not isinstance(group, dict):
            findings.append(f"{case_id}: requiredSignalGroups[{index}] must be an object")
            continue
        name = group.get("name")
        if not isinstance(name, str) or not name:
            findings.append(f"{case_id}: requiredSignalGroups[{index}] needs a name")
        elif name in group_names:
            findings.append(f"{case_id}: duplicate required signal group {name!r}")
        else:
            group_names.add(name)
        values = group.get("anyOf", [])
        if not isinstance(values, list) or not values:
            findings.append(f"{case_id}: requiredSignalGroups[{index}].anyOf must be non-empty")
            continue
        value_set = set(map(str, values))
        label_values = sorted(
            value for value in value_set if value.startswith(("vendor:", "alias:"))
        )
        if required_names and label_values:
            findings.append(
                f"{case_id}: labels cannot satisfy required signal groups: "
                + ", ".join(label_values)
            )
        undeclared = sorted(value_set - declared_signals)
        if undeclared:
            findings.append(
                f"{case_id}: requiredSignalGroups[{index}] uses undeclared signals: "
                + ", ".join(undeclared)
            )
        overlap = sorted(value_set & grouped_signals)
        if overlap:
            findings.append(
                f"{case_id}: required signal groups overlap: " + ", ".join(overlap)
            )
        grouped_signals.update(value_set)

    missing_names = sorted(required_names - group_names)
    if missing_names:
        findings.append(f"{case_id}: missing required signal groups: {', '.join(missing_names)}")
    minimum = match.get("minimumIndependentSignals")
    if isinstance(minimum, int) and minimum < len(groups):
        findings.append(
            f"{case_id}: minimumIndependentSignals must be >= required signal group count"
        )
    return findings


def case_asset_contract_findings(case_id: str, artifacts: dict) -> list[str]:
    findings: list[str] = []
    assets = artifacts.get("assets", [])
    if not isinstance(assets, list):
        return [f"{case_id}: artifacts.assets must be an array"]
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        path = str(asset.get("path", ""))
        size = asset.get("bytes")
        if isinstance(size, int) and size >= LARGE_ASSET_READ_HINT_BYTES:
            if not isinstance(asset.get("readHint"), str) or not asset["readHint"].strip():
                findings.append(
                    f"{case_id}: large asset {path!r} requires a non-empty readHint"
                )
        if isinstance(size, int) and size >= LARGE_ASSET_STORAGE_POLICY_BYTES:
            if asset.get("storagePolicy") not in {
                "regular-git-self-contained",
                "git-lfs",
            }:
                findings.append(
                    f"{case_id}: large asset {path!r} requires an explicit storagePolicy"
                )
        if path.lower().endswith(".pt"):
            if asset.get("serializationRisk") != "executable-pickle":
                findings.append(
                    f"{case_id}: PyTorch checkpoint {path!r} must declare "
                    "serializationRisk=executable-pickle"
                )
            if asset.get("executionPolicy") != "explicit-opt-in-after-hash-verification":
                findings.append(
                    f"{case_id}: PyTorch checkpoint {path!r} must declare "
                    "executionPolicy=explicit-opt-in-after-hash-verification"
                )
    return findings


def current_camoufox_findings(case_id: str, current_chain: list) -> list[str]:
    """A case may not demand camoufox on the current target by inheritance.

    SKILL.md Phase 2 and Do Not both state that historical case provenance is not
    a camoufox selection criterion: only explicit Camoufox/SpiderMonkey/engine-level
    wording or a recorded Chromium/Cloak observer-effect blocker selects it. Four
    cases used to copy `historicalProviderChain` verbatim into
    `requiredCurrentProviderChain`, so selecting one of them by signal match told
    the model to open a second recon engine the hub had forbidden. Fail closed:
    camoufox stays legal in the historical chain, but a current-chain stage must
    name the criterion that survives without that history.
    """
    findings: list[str] = []
    for index, stage in enumerate(current_chain):
        if not isinstance(stage, dict) or stage.get("provider") != "camoufox":
            continue
        criterion = stage.get("camoufoxCriterion")
        if not isinstance(criterion, str) or not criterion.strip():
            findings.append(
                f"{case_id}: requiredCurrentProviderChain[{index}] selects camoufox "
                "without a camoufoxCriterion; historical provenance is not a criterion"
            )
    return findings


def case_manifest_findings() -> list[str]:
    findings: list[str] = []
    for path in sorted(CASES_ROOT.glob("**/case.json")):
        data = load_json(path)
        case_id = data.get("caseId")
        schema = data.get("schemaVersion")
        if schema != "web-protocol-recovery-case":
            findings.append(f"{rel(path)}: schemaVersion must be web-protocol-recovery-case")
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
        product = data.get("product") or {}
        required_group_names: set[str] = set()
        if product.get("product") == "Reese84":
            required_group_names = {"reese84-native", "independent-corroboration"}
        elif product.get("vendor") == "Geetest" and product.get("subtype") == "nine-grid":
            required_group_names = {
                "gt4-request-subtype",
                "gt4-response-subtype",
                "nine-grid-shape",
            }
        findings.extend(
            required_signal_group_findings(
                str(case_id), data.get("match") or {}, required_group_names
            )
        )
        findings.extend(
            case_asset_contract_findings(str(case_id), data.get("artifacts") or {})
        )
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
        findings.extend(
            current_camoufox_findings(
                str(case_id), data.get("requiredCurrentProviderChain") or []
            )
        )
    return findings


def tracked_text_paths() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=SKILL_ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("could not enumerate tracked files for LF validation")
    return [
        SKILL_ROOT / Path(raw.decode("utf-8", errors="surrogateescape"))
        for raw in result.stdout.split(b"\0")
        if raw
    ]


def line_ending_findings(extra_paths: tuple[Path, ...] = ()) -> list[str]:
    """No tracked text file may carry CRLF.

    Case manifests hash file bytes, so a CRLF worktree hashes differently from the
    committed LF blob. That defect passed every gate for the life of the hash
    system because the generator wrote CRLF on Windows and the checker read back
    with universal newlines, leaving both blind to the same byte. This check reads
    raw bytes so it cannot inherit that blindness, and `.gitattributes` pins
    `text eol=lf` so a compliant checkout is CRLF-free on every platform.
    """
    findings: list[str] = []
    try:
        paths = {path.resolve() for path in tracked_text_paths()}
    except RuntimeError as error:
        return [str(error)]
    paths.update(path.resolve() for path in extra_paths)
    for path in sorted(paths):
        if not path.is_file() or (
            path.suffix.lower() not in EOL_CHECKED_SUFFIXES
            and path.name.lower() not in EOL_CHECKED_FILE_NAMES
        ):
            continue
        if any(part in EOL_SKIP_DIRS for part in path.parts):
            continue
        if b"\r" in path.read_bytes():
            findings.append(f"CR byte in tracked text file: {rel(path)}")
    return findings


def residue_findings() -> list[str]:
    findings: list[str] = []
    for path in SKILL_ROOT.rglob("*"):
        if path.name in RESIDUE_NAMES:
            findings.append(f"residue directory present: {rel(path)}")
        elif path.is_file() and path.suffix.lower() in RESIDUE_SUFFIXES:
            findings.append(f"residue file present: {rel(path)}")
    return findings


def _python_http_call_lines(path: Path) -> list[int]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []
    lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Attribute) and target.attr in {
                "get",
                "post",
                "put",
                "delete",
                "patch",
                "request",
            }:
                base = target.value
                name = base.id if isinstance(base, ast.Name) else None
                if name in {"requests", "session", "httpx", "client"}:
                    lines.append(node.lineno)
    return lines


def _imports_curl_cffi(path: Path) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "curl_cffi" or alias.name.startswith("curl_cffi."):
                    return True
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "curl_cffi" or node.module.startswith("curl_cffi."):
                return True
    return False


def python_live_egress_findings(path: Path) -> list[str]:
    if "delivery" in path.parts:
        return []
    # Historical study copies may contain live HTTP; they are not case entry points.
    if "case-live-reference-archive" in path.parts:
        return []
    findings: list[str] = []
    # Active case library must stay offline-only: no curl_cffi imports and no live HTTP calls.
    if "cases" in path.parts and _imports_curl_cffi(path):
        findings.append(
            f"{rel(path)}: curl_cffi import is forbidden in cases; offline-only case library"
        )
    lines = _python_http_call_lines(path)
    for line in lines:
        if "cases" in path.parts:
            findings.append(
                f"{rel(path)}: case live HTTP at line {line} is forbidden; "
                "cases are offline-only and final live egress belongs to python-collector"
            )
        else:
            findings.append(f"{rel(path)}: possible non-delivery live HTTP call at line {line}")
    return findings


def live_egress_findings() -> list[str]:
    findings: list[str] = []
    if (SKILL_ROOT / "references" / "cases" / "historical-live-egress.json").is_file():
        findings.append(
            "references/cases/historical-live-egress.json must be removed; cases are offline-only"
        )
    for path in SKILL_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in CODE_SUFFIXES:
            continue
        if set(path.parts) & RESIDUE_NAMES:
            continue
        if "case-live-reference-archive" in path.parts:
            continue
        if path.suffix.lower() == ".py":
            findings.extend(python_live_egress_findings(path))
            continue
        if "delivery" in path.parts or "cases" in path.parts or "env" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if NETWORK_JS.search(text):
            findings.append(f"{rel(path)}: possible non-delivery JS network primitive")
    return findings


def script_placement_findings(
    scripts_root: Path = SCRIPTS_ROOT,
    preflight_path: Path = PREFLIGHT_DOC,
) -> list[str]:
    """Every script must be categorized. Fail closed on scatter and missed registration.

    1. No Python file may sit directly under scripts/. It must go in
       tools/ (task diagnostics), gates/ (skill gates), tests/ (gate unit
       tests), or providers/ (provider-scoped helpers). scripts/README.md
       documents the taxonomy.
    2. Any scripts/tools/*.py that exposes a --self-test option must be
       registered in scripts/gates/preflight.py DIAGNOSTIC_SELF_TESTS, so a
       new diagnostic cannot be added and then silently skipped by the gate.
    """
    findings: list[str] = []
    if not scripts_root.is_dir():
        return findings

    for entry in sorted(scripts_root.iterdir()):
        if entry.is_file() and entry.suffix == ".py":
            findings.append(
                f"scripts/{entry.name}: scripts root must not hold scripts; "
                "move it under tools/, gates/, tests/, or providers/ (see scripts/README.md)"
            )

    preflight_text = (
        preflight_path.read_text(encoding="utf-8", errors="replace")
        if preflight_path.is_file()
        else ""
    )
    tools_root = scripts_root / "tools"
    if tools_root.is_dir():
        for path in sorted(tools_root.glob("*.py")):
            text = path.read_text(encoding="utf-8", errors="replace")
            if "--self-test" not in text:
                continue
            registration = f"scripts/tools/{path.name}"
            if registration not in preflight_text:
                findings.append(
                    f"{registration}: exposes --self-test but is not registered in "
                    "scripts/gates/preflight.py DIAGNOSTIC_SELF_TESTS"
                )
    return findings


def main() -> int:
    checks = [
        ("provider registry", provider_registry_findings),
        ("route literals", route_literal_findings),
        ("documentation contract", documentation_contract_findings),
        ("case process contract", case_process_contract_findings),
        ("read-plan contract", read_plan_contract_findings),
        ("case manifests", case_manifest_findings),
        ("live egress", live_egress_findings),
        ("residue", residue_findings),
        ("line endings", line_ending_findings),
        ("script placement", script_placement_findings),
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
