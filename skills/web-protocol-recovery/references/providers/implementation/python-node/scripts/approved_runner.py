#!/usr/bin/env python3
"""Contract wrapper for approved narrow JS/WASM artifact adapters.

This module deliberately does not launch Node or claim to be a sandbox. A real
capability-denied adapter must be supplied by the runtime environment. Without
one, construction or execution fails closed.
"""

# Provider contract fields: assetSha256 and cleanup are recorded by the caller.

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol


ALLOWED_OPERATIONS = frozenset({"data_builder", "pzds_wasm_sign"})
DEFAULT_INPUT_BYTE_CAP = 1024 * 1024


class CapabilityDeniedAdapter(Protocol):
    capability_denied: bool
    adapter_id: str
    adapter_sha256: str

    def execute(
        self, operation: str, payload: Mapping[str, Any], policy: Mapping[str, Any]
    ) -> Mapping[str, Any]: ...

    def close(self) -> None: ...


class ApprovedRunnerError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ApprovedRunnerError(f"target asset must be a plain file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _deadline_is_valid(value: Any) -> bool:
    try:
        deadline = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    return deadline.tzinfo is not None and deadline > datetime.now(timezone.utc)


class ApprovedArtifactRunner:
    """Validate approval and delegate only bounded artifact operations."""

    def __init__(
        self,
        work_order: Mapping[str, Any],
        asset_paths: Mapping[str, str | Path],
        adapter: CapabilityDeniedAdapter,
    ) -> None:
        self.work_order = work_order
        self.asset_paths = {str(name): Path(path) for name, path in asset_paths.items()}
        self.adapter = adapter
        self.closed = False
        self.asset_hashes = self._validate_envelope()

    def _validate_envelope(self) -> dict[str, str]:
        policy = ((self.work_order.get("authorization") or {}).get("executionPolicy") or {})
        if policy.get("targetCodeExecution") != "approved-reviewed-hash":
            raise ApprovedRunnerError("target-code execution requires approved-reviewed-hash")
        if not _deadline_is_valid(policy.get("approvalDeadline")):
            raise ApprovedRunnerError("target-code approval deadline is expired or invalid")
        sandbox = policy.get("sandbox") or {}
        required = {"backend", "adapterId", "adapterSha256", "capabilityEvidence", "timeoutMs", "outputByteCap"}
        if sandbox.get("backend") != "capability-denied-external" or not required <= set(sandbox):
            raise ApprovedRunnerError("capability-denied-external sandbox declaration is required")
        if not getattr(self.adapter, "capability_denied", False):
            raise ApprovedRunnerError("adapter must attest capability denial")
        if getattr(self.adapter, "adapter_id", None) != sandbox["adapterId"]:
            raise ApprovedRunnerError("adapter identity does not match work order")
        if getattr(self.adapter, "adapter_sha256", None) != sandbox["adapterSha256"]:
            raise ApprovedRunnerError("adapter hash does not match work order")
        if not callable(getattr(self.adapter, "execute", None)) or not callable(getattr(self.adapter, "close", None)):
            raise ApprovedRunnerError("adapter must provide execute() and close()")
        approved = set(map(str, policy.get("approvedCodeSha256") or []))
        if not self.asset_paths or not approved:
            raise ApprovedRunnerError("approved target asset hashes are required")
        hashes = {name: sha256_file(path) for name, path in self.asset_paths.items()}
        if not set(hashes.values()) <= approved:
            raise ApprovedRunnerError("target asset hash is not approved")
        return hashes

    def execute(self, operation: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if self.closed:
            raise ApprovedRunnerError("approved runner is already closed")
        if operation not in ALLOWED_OPERATIONS:
            raise ApprovedRunnerError(f"unsupported target operation: {operation}")
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(encoded) > DEFAULT_INPUT_BYTE_CAP:
            raise ApprovedRunnerError("target input exceeds the approved byte cap")
        policy = ((self.work_order.get("authorization") or {}).get("executionPolicy") or {})
        output = self.adapter.execute(operation, payload, policy)
        if not isinstance(output, Mapping):
            raise ApprovedRunnerError("approved adapter output must be an object")
        allowed = {"data_builder": {"output"}, "pzds_wasm_sign": {"sign", "timestamp", "random"}}[operation]
        if set(output) - allowed:
            raise ApprovedRunnerError("approved adapter returned an unexpected field")
        output_bytes = json.dumps(dict(output), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(output_bytes) > int(policy["sandbox"]["outputByteCap"]):
            raise ApprovedRunnerError("approved adapter output exceeds the byte cap")
        return dict(output)

    def close(self) -> None:
        if not self.closed:
            try:
                self.adapter.close()
            finally:
                self.closed = True


def run_blocked_without_adapter() -> None:
    """Document the default: no adapter means no target-code execution."""
    raise ApprovedRunnerError(
        "no reviewed capability-denied adapter is bundled; target-code execution is blocked"
    )
