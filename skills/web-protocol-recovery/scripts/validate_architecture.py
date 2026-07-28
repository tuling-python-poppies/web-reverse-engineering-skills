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
    r"\bfetch\s*\(|new\s+(?:XMLHttpRequest|WebSocket)\s*\(|\brequire\(['\"](?:http|https)['\"]\)"
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
    if "api-examples" in path.parts:
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
        if "reconnaissance" in path.parts or "env" in path.parts or "api-examples" in path.parts:
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
