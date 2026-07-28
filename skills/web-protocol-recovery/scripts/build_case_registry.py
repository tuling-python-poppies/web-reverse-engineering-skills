#!/usr/bin/env python3
"""Build or verify the v2 case registry projection."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
CASES_ROOT = SKILL_ROOT / "references" / "cases"
REGISTRY_PATH = CASES_ROOT / "registry.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def registry_row(path: Path) -> dict:
    data = load_json(path)
    rel = path.relative_to(CASES_ROOT).as_posix()
    verification_class = data.get("verificationClass")
    selectable_as = "proof" if verification_class == "freshly-verified" else "template"
    return {
        "caseId": data["caseId"],
        "family": data["family"],
        "status": data["status"],
        "runtime": data["runtime"],
        "caseKind": data["caseKind"],
        "implementation": data.get("implementation"),
        "exactScopes": data.get("exactScopes", []),
        "match": data.get("match", {}),
        "providerPlan": data.get("requiredCurrentProviderChain", []),
        "manifest": {"path": rel, "sha256": sha256(path)},
        "verificationClass": verification_class,
        "selectableAs": selectable_as,
    }


def scope_key(scope: dict) -> tuple[str, str, int, str]:
    return (
        str(scope.get("scheme", "")).lower(),
        str(scope.get("host", "")).lower(),
        int(scope.get("port", 0)),
        str(scope.get("routePrefix") or "/"),
    )


def scopes_overlap(left: dict, right: dict) -> bool:
    l_scheme, l_host, l_port, l_prefix = scope_key(left)
    r_scheme, r_host, r_port, r_prefix = scope_key(right)
    if (l_scheme, l_host, l_port) != (r_scheme, r_host, r_port):
        return False
    l_prefix = l_prefix.rstrip("/") or "/"
    r_prefix = r_prefix.rstrip("/") or "/"
    return l_prefix == r_prefix or l_prefix.startswith(r_prefix + "/") or r_prefix.startswith(l_prefix + "/")


def signal_set(row: dict, field: str) -> set[str]:
    values = row.get("match", {}).get(field, [])
    return set(map(str, values))


def rows_disambiguated(left: dict, right: dict) -> bool:
    left_signals = signal_set(left, "signals")
    right_signals = signal_set(right, "signals")
    left_negative = signal_set(left, "negativeSignals")
    right_negative = signal_set(right, "negativeSignals")
    return bool(left_negative & right_signals) or bool(right_negative & left_signals)


def minimum_signals(row: dict) -> int:
    try:
        return int(row.get("match", {}).get("minimumIndependentSignals", 2))
    except (TypeError, ValueError):
        return 2


def signal_sets_ambiguous(left: dict, right: dict) -> bool:
    left_signals = signal_set(left, "signals")
    right_signals = signal_set(right, "signals")
    if not left_signals or not right_signals:
        return False
    shared = left_signals & right_signals
    threshold = max(minimum_signals(left), minimum_signals(right))
    return len(shared) >= threshold


def ambiguity_findings(rows: list[dict]) -> list[str]:
    findings: list[str] = []
    for index, left in enumerate(rows):
        for right in rows[index + 1 :]:
            if left["family"] != right["family"]:
                continue
            scope_overlap = any(
                scopes_overlap(l_scope, r_scope)
                for l_scope in left["exactScopes"]
                for r_scope in right["exactScopes"]
            )
            signal_overlap = signal_sets_ambiguous(left, right)
            if not scope_overlap and not signal_overlap:
                continue
            if rows_disambiguated(left, right):
                continue
            kind = "exactScopes" if scope_overlap else "minimum-signal set"
            findings.append(
                f"ambiguous {kind} without negative-signal discriminator: "
                f"{left['caseId']} <-> {right['caseId']}"
            )
    return findings


def build_registry() -> dict:
    rows = [registry_row(path) for path in sorted(CASES_ROOT.glob("**/case.json"))]
    rows.sort(key=lambda item: item["caseId"])
    findings = ambiguity_findings(rows)
    if findings:
        raise ValueError("\n".join(findings))
    return {"schemaVersion": "web-protocol-recovery-case-registry", "cases": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify registry.json instead of writing it")
    args = parser.parse_args()

    try:
        registry = build_registry()
    except ValueError as error:
        print(str(error))
        return 1
    payload = json.dumps(registry, ensure_ascii=False, indent=4) + "\n"
    if args.check:
        current = REGISTRY_PATH.read_text(encoding="utf-8") if REGISTRY_PATH.exists() else ""
        if current != payload:
            print("registry.json is not the generated v2 projection")
            return 1
        print("registry.json matches generated v2 projection")
        return 0
    REGISTRY_PATH.write_text(payload, encoding="utf-8")
    print(f"wrote {REGISTRY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
