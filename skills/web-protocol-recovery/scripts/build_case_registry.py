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


def build_registry() -> dict:
    rows = [registry_row(path) for path in sorted(CASES_ROOT.glob("**/case.json"))]
    rows.sort(key=lambda item: item["caseId"])
    return {"schemaVersion": "web-protocol-recovery-case-registry/v2", "cases": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify registry.json instead of writing it")
    args = parser.parse_args()

    registry = build_registry()
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
