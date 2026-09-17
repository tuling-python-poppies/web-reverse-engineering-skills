#!/usr/bin/env python3
"""Fail-closed read-budget accounting for Provider work orders."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Iterable


BASE_CAP = 24
EXTENSION_CAP = 8


def canonical_read_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("read path must be a nonempty POSIX relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"read path must be contained: {value!r}")
    if path.parts and path.parts[0].endswith(":"):
        raise ValueError(f"read path must not be drive-qualified: {value!r}")
    return "/".join(path.parts).lower()


@dataclass
class ReadBudget:
    base_cap: int = BASE_CAP
    extension_cap: int = EXTENSION_CAP
    consumed: set[str] = field(default_factory=set)
    extension_paths: set[str] = field(default_factory=set)
    extension_used: bool = False

    def add_base(self, paths: Iterable[str]) -> None:
        normalized = {canonical_read_path(path) for path in paths}
        new_paths = normalized - self.consumed
        active_cap = self.base_cap + (self.extension_cap if self.extension_used else 0)
        if len(self.consumed) + len(new_paths) > active_cap:
            raise ValueError("whole-task read budget exceeded")
        self.consumed.update(new_paths)

    def add_extension(
        self,
        paths: Iterable[str],
        *,
        blocker_id: str,
        reason: str,
        acceptance_impact: str,
    ) -> None:
        if self.extension_used:
            raise ValueError("read-budget extension can only be used once")
        if not blocker_id or not reason or not acceptance_impact:
            raise ValueError("read-budget extension requires blocker_id, reason, and acceptance_impact")
        normalized = {canonical_read_path(path) for path in paths}
        new_paths = normalized - self.consumed
        if not new_paths:
            raise ValueError("read-budget extension must add new paths")
        if len(new_paths) > self.extension_cap:
            raise ValueError("read-budget extension exceeds eight paths")
        if len(self.consumed) + len(new_paths) > self.base_cap + self.extension_cap:
            raise ValueError("read budget including extension exceeds 32 paths")
        self.extension_paths = new_paths
        self.consumed.update(new_paths)
        self.extension_used = True

    def checkpoint(self) -> dict[str, Any]:
        return {
            "taskUsed": len(self.consumed),
            "baseCap": self.base_cap,
            "extensionUsed": self.extension_used,
            "extensionCap": self.extension_cap,
            "consumedPaths": sorted(self.consumed),
        }


def validate_read_plan(plan: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    required = plan.get("required") or []
    optional = plan.get("optional") or []
    consumed = plan.get("consumedPaths") or []
    declared_paths: list[str] = []
    consumed_paths: list[str] = []
    try:
        declared_paths.extend(canonical_read_path(path) for path in required)
        declared_paths.extend(canonical_read_path(path) for path in optional)
        consumed_paths.extend(canonical_read_path(path) for path in consumed)
    except ValueError as error:
        return [str(error)]
    if len(declared_paths) != len(set(declared_paths)):
        findings.append("readPlan required and optional paths must be unique")
    if len(consumed_paths) != len(set(consumed_paths)):
        findings.append("readPlan consumedPaths must be unique")
    if not set(consumed_paths) <= set(declared_paths):
        findings.append("readPlan consumedPaths must be declared in required or optional")
    if len(set(declared_paths)) > BASE_CAP:
        findings.append("readPlan base paths must not exceed 24")
    extension = plan.get("readBudgetExtension")
    if extension is not None:
        if not isinstance(extension, dict):
            findings.append("readBudgetExtension must be an object or null")
        else:
            paths = extension.get("additionalPaths") or []
            try:
                extension_paths = [canonical_read_path(path) for path in paths]
            except ValueError as error:
                findings.append(str(error))
                extension_paths = []
            if len(extension_paths) != len(set(extension_paths)):
                findings.append("readBudgetExtension paths must be unique")
            if set(extension_paths) & (set(declared_paths) | set(consumed_paths)):
                findings.append("readBudgetExtension cannot repeat a declared or consumed path")
            if len(extension_paths) > EXTENSION_CAP:
                findings.append("readBudgetExtension cannot exceed eight paths")
            for key in ("blockerId", "reason", "acceptanceImpact"):
                if not isinstance(extension.get(key), str) or not extension[key]:
                    findings.append(f"readBudgetExtension.{key} is required")
            if len(set(declared_paths) | set(extension_paths)) > BASE_CAP + EXTENSION_CAP:
                findings.append("readPlan including extension cannot exceed 32 paths")
    return findings


def run_self_test() -> None:
    budget = ReadBudget()
    budget.add_base(f"references/file{index}.md" for index in range(BASE_CAP))
    assert budget.checkpoint()["taskUsed"] == BASE_CAP
    try:
        budget.add_base(["references/overflow.md"])
    except ValueError:
        pass
    else:
        raise AssertionError("base cap not enforced")

    extension = ReadBudget()
    extension.add_base(["references/a.md"])
    extension.add_extension(
        ["references/b.md"],
        blocker_id="blocker-1",
        reason="missing rule",
        acceptance_impact="vector proof",
    )
    assert extension.checkpoint()["taskUsed"] == 2
    try:
        extension.add_extension(
            ["references/c.md"],
            blocker_id="blocker-2",
            reason="second attempt",
            acceptance_impact="none",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("second extension allowed")

    assert validate_read_plan(
        {"required": ["references/a.md"], "optional": [], "consumedPaths": ["references/a.md"]}
    ) == []
    assert validate_read_plan(
        {"required": ["references/a.md", "references/a.md"], "consumedPaths": ["references/b.md"]}
    )
    print("read_budget_self_test=PASS")


if __name__ == "__main__":
    try:
        run_self_test()
    except AssertionError as error:
        print(f"read_budget_self_test=FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
