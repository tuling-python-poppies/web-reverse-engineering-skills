#!/usr/bin/env python3
"""Provider-owned bounded process launcher for narrow JS/WASM artifacts.

The launcher runs exactly one approved command shape: the node executable plus
one hash-bound asset path, inside the project cache directory, with bounded
stdin/stdout/stderr and a hard timeout. It does not implement an OS-level
capability sandbox and does not claim to be one.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

ALLOWED_OPERATIONS = frozenset({"data_builder", "pzds_wasm_sign"})
OPERATION_SCRIPTS = {
    "data_builder": "data_builder.js",
    "pzds_wasm_sign": "pzds_wasm_sign.mjs",
}
OPERATION_OUTPUT_FIELDS = {
    "data_builder": frozenset({"output"}),
    "pzds_wasm_sign": frozenset({"sign", "timestamp", "random"}),
}
DEFAULT_INPUT_BYTE_CAP = 1024 * 1024
DEFAULT_OUTPUT_BYTE_CAP = 1024 * 1024
DEFAULT_TIMEOUT_MS = 30000
REQUIRED_CACHE_COMPONENT = "js_reverse_cache"


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


def _ensure_launcher_cwd(cwd: Path) -> Path:
    cwd = Path(os.path.abspath(os.fspath(cwd)))
    if not cwd.is_dir() or cwd.is_symlink():
        raise ApprovedRunnerError(f"launcher cwd must be a plain directory: {cwd}")
    if REQUIRED_CACHE_COMPONENT not in {part.lower() for part in cwd.parts}:
        raise ApprovedRunnerError(
            f"launcher cwd must stay under a {REQUIRED_CACHE_COMPONENT} subtree"
        )
    return cwd


class ApprovedProcessLauncher:
    """Execute one approved asset through a bounded, timed subprocess."""

    def __init__(
        self,
        cwd: Path,
        *,
        node_executable: str = "node",
        allowed_scripts: Optional[Mapping[str, Path]] = None,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        output_byte_cap: int = DEFAULT_OUTPUT_BYTE_CAP,
    ) -> None:
        if not isinstance(node_executable, str) or not node_executable.strip():
            raise ApprovedRunnerError("node executable is required")
        if timeout_ms < 1 or output_byte_cap < 1:
            raise ApprovedRunnerError("launcher timeout and output cap must be positive")
        self.cwd = _ensure_launcher_cwd(cwd)
        self.node_executable = node_executable
        self.allowed_scripts = {
            str(name): Path(os.path.abspath(os.fspath(path)))
            for name, path in (allowed_scripts or {}).items()
        }
        self.timeout_ms = timeout_ms
        self.output_byte_cap = output_byte_cap
        self.closed = False

    def execute(
        self,
        script_path: Path,
        payload: Mapping[str, Any],
        policy: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        if self.closed:
            raise ApprovedRunnerError("launcher is already closed")
        script = Path(os.path.abspath(os.fspath(script_path)))
        if self.allowed_scripts and script not in self.allowed_scripts.values():
            raise ApprovedRunnerError("launcher script path is outside the approved asset set")
        if script.is_symlink() or not script.is_file():
            raise ApprovedRunnerError(f"target asset must be a plain file: {script}")
        sandbox = policy.get("sandbox") or {}
        timeout_ms = int(sandbox.get("timeoutMs", self.timeout_ms))
        output_byte_cap = int(sandbox.get("outputByteCap", self.output_byte_cap))
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(encoded) > DEFAULT_INPUT_BYTE_CAP:
            raise ApprovedRunnerError("target input exceeds the approved byte cap")
        try:
            process = subprocess.run(
                [self.node_executable, str(script)],
                cwd=str(self.cwd),
                input=encoded,
                capture_output=True,
                timeout=max(1, timeout_ms // 1000),
            )
        except subprocess.TimeoutExpired as error:
            raise ApprovedRunnerError("target process exceeded the approved timeout") from error
        if process.returncode != 0:
            detail = process.stderr[:512].decode("utf-8", errors="replace").strip()
            raise ApprovedRunnerError(f"target process failed: {detail or process.returncode}")
        if len(process.stdout) > output_byte_cap:
            raise ApprovedRunnerError("target process output exceeds the approved byte cap")
        try:
            output = json.loads(process.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ApprovedRunnerError("target process output is not JSON") from error
        if not isinstance(output, Mapping):
            raise ApprovedRunnerError("target process output must be an object")
        return output

    def close(self) -> None:
        self.closed = True


class ApprovedArtifactRunner:
    """Validate the execution envelope and delegate bounded artifact operations."""

    def __init__(
        self,
        work_order: Mapping[str, Any],
        asset_paths: Mapping[str, str | Path],
        launcher: Optional[ApprovedProcessLauncher] = None,
    ) -> None:
        self.work_order = work_order
        self.asset_paths = {str(name): Path(path) for name, path in asset_paths.items()}
        self.launcher = launcher or self._default_launcher()
        self.closed = False
        self.asset_hashes = self._validate_envelope()

    def _default_launcher(self) -> ApprovedProcessLauncher:
        project = self.work_order.get("project") or {}
        root = project.get("projectRoot")
        if not isinstance(root, str) or not root:
            raise ApprovedRunnerError("project.projectRoot is required for a default launcher")
        cwd = Path(root) / "js_reverse_cache" / "approved"
        return ApprovedProcessLauncher(cwd, allowed_scripts=dict(self.asset_paths))

    def _validate_envelope(self) -> dict[str, str]:
        policy = ((self.work_order.get("authorization") or {}).get("executionPolicy") or {})
        mode = policy.get("targetCodeExecution")
        if mode not in {"local-only", "approved-reviewed-hash"}:
            raise ApprovedRunnerError("target-code execution requires local-only or approved-reviewed-hash")
        if mode == "approved-reviewed-hash" and not _deadline_is_valid(policy.get("approvalDeadline")):
            raise ApprovedRunnerError("target-code approval deadline is expired or invalid")
        approved = set(map(str, policy.get("approvedCodeSha256") or []))
        if not self.asset_paths or not approved:
            raise ApprovedRunnerError("approved target asset hashes are required")
        hashes = {name: sha256_file(path) for name, path in self.asset_paths.items()}
        if not set(hashes.values()) <= approved:
            raise ApprovedRunnerError("target asset hash is not approved")
        if not callable(getattr(self.launcher, "execute", None)):
            raise ApprovedRunnerError("launcher must provide execute()")
        if not callable(getattr(self.launcher, "close", None)):
            raise ApprovedRunnerError("launcher must provide close()")
        return hashes

    def execute(self, operation: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if self.closed:
            raise ApprovedRunnerError("approved runner is already closed")
        script_name = OPERATION_SCRIPTS.get(operation)
        if script_name is None:
            raise ApprovedRunnerError(f"unsupported target operation: {operation}")
        if script_name not in self.asset_paths:
            raise ApprovedRunnerError(f"target asset is not provided: {script_name}")
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(encoded) > DEFAULT_INPUT_BYTE_CAP:
            raise ApprovedRunnerError("target input exceeds the approved byte cap")
        policy = ((self.work_order.get("authorization") or {}).get("executionPolicy") or {})
        output = self.launcher.execute(self.asset_paths[script_name], payload, policy)
        if not isinstance(output, Mapping):
            raise ApprovedRunnerError("launcher output must be an object")
        allowed = OPERATION_OUTPUT_FIELDS[operation]
        if set(output) - allowed:
            raise ApprovedRunnerError("launcher returned an unexpected field")
        output_bytes = json.dumps(dict(output), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        sandbox = policy.get("sandbox") or {}
        output_byte_cap = int(sandbox.get("outputByteCap", DEFAULT_OUTPUT_BYTE_CAP))
        if len(output_bytes) > output_byte_cap:
            raise ApprovedRunnerError("launcher output exceeds the byte cap")
        return dict(output)

    def close(self) -> None:
        if not self.closed:
            try:
                self.launcher.close()
            finally:
                self.closed = True


def run_blocked_without_launcher() -> None:
    """Document the default: no bounded launcher means no target-code execution."""
    raise ApprovedRunnerError(
        "no bounded process launcher is configured; target-code execution is blocked"
    )
