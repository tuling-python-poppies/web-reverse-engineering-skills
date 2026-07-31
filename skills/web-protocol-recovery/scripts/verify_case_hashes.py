#!/usr/bin/env python3
"""Verify hash-bound case artifacts and registry manifests.

Cascade after any hash-bound edit:
  target file bytes
    -> case.json artifacts / preRead sha256
    -> registry.json manifest sha256 for that case.json

Exit 0 when every declared path exists, stays in scope, SHA-256 matches,
and verificationClass contracts hold.
Exit 1 on mismatch, missing path, path escape, orphan case, undeclared case
file, or verificationClass contract failure.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator


ARTIFACT_KEYS = ("process", "entry", "pullLiveState")
VERIFICATION_ARTIFACT_KEYS = ("testArtifact", "evidenceArtifact")
IGNORED_CASE_DIR_NAMES = {".pytest_cache", "__pycache__"}
IGNORED_CASE_FILE_NAMES = {".DS_Store", "Thumbs.db"}
CASE_RUNTIME_DIR_NAMES = {"iv8", "pure-python", "python-node"}
KNOWN_VERIFICATION_CLASSES = {
    "freshly-verified",
    "historical-user-attested",
}
FRESH_VERIFICATION_CLASS = "freshly-verified"
HISTORICAL_VERIFICATION_CLASS = "historical-user-attested"
ARCHIVE_SCHEMA = "web-protocol-recovery-case-live-reference-archive"
ARCHIVE_REL = "references/case-live-reference-archive"
ARCHIVE_DIR_NAME = "case-live-reference-archive"
ARCHIVE_CONTROL_FILES = {"MANIFEST.json", "README.md"}
ACTIVE_CODE_SUFFIXES = {".py", ".js", ".mjs", ".cjs"}
SENSITIVE_NAME_PARTS = (
    "secret",
    "password",
    "passwd",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def schema_findings(schema_path: Path, instance_path: Path) -> list[str]:
    schema = load_json(schema_path)
    instance = load_json(instance_path)
    validator = Draft202012Validator(schema)
    findings: list[str] = []
    for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.path)):
        location = ".".join(map(str, error.path)) or "<root>"
        findings.append(
            f"{instance_path.as_posix()}: schema {location}: {error.message}"
        )
    return findings


def validate_relative_posix_path(
    *, label: str, path_value: Any, mismatches: list[str]
) -> PurePosixPath | None:
    if not isinstance(path_value, str) or not path_value:
        mismatches.append(f"{label}: missing path")
        return None
    if "\\" in path_value:
        mismatches.append(f"{label}: path must use POSIX separators: {path_value}")
        return None
    path = PurePosixPath(path_value)
    if path.is_absolute():
        mismatches.append(f"{label}: absolute paths are forbidden: {path_value}")
        return None
    if any(part in {"", ".", ".."} for part in path.parts):
        mismatches.append(f"{label}: path must not contain empty, '.', or '..' segments: {path_value}")
        return None
    if path.parts and path.parts[0].endswith(":"):
        mismatches.append(f"{label}: drive-qualified paths are forbidden: {path_value}")
        return None
    return path


def resolve_declared_path(
    *,
    label: str,
    base: Path,
    allowed_root: Path,
    path_value: Any,
    mismatches: list[str],
) -> tuple[Path, str] | None:
    path = validate_relative_posix_path(
        label=label, path_value=path_value, mismatches=mismatches
    )
    if path is None:
        return None
    resolved = (base / Path(*path.parts)).resolve()
    allowed = allowed_root.resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError:
        mismatches.append(f"{label}: path escapes allowed root\n  path: {resolved}\n  root: {allowed}")
        return None
    return resolved, path.as_posix()


def check_path_hash(
    *,
    label: str,
    path: Path,
    expected: str | None,
    mismatches: list[str],
    ok: list[str],
) -> None:
    if not expected:
        mismatches.append(f"{label}: missing sha256 field")
        return
    if not path.exists():
        mismatches.append(f"{label}: missing file {path}")
        return
    if not path.is_file():
        mismatches.append(f"{label}: not a file {path}")
        return
    actual = sha256_file(path)
    if actual != expected:
        mismatches.append(
            f"{label}: hash mismatch\n  path: {path}\n  want: {expected}\n  got:  {actual}"
        )
        return
    ok.append(label)


def check_declared_hash(
    *,
    label: str,
    base: Path,
    allowed_root: Path,
    path_value: Any,
    expected: str | None,
    mismatches: list[str],
    ok: list[str],
) -> str | None:
    resolved = resolve_declared_path(
        label=label,
        base=base,
        allowed_root=allowed_root,
        path_value=path_value,
        mismatches=mismatches,
    )
    if resolved is None:
        return None
    path, normalized = resolved
    check_path_hash(label=label, path=path, expected=expected, mismatches=mismatches, ok=ok)
    return normalized


def iter_case_files(case_dir: Path) -> list[str]:
    files: list[str] = []
    for path in sorted(case_dir.rglob("*")):
        if not path.is_file():
            continue
        if any(part in IGNORED_CASE_DIR_NAMES for part in path.parts):
            continue
        if path.name in IGNORED_CASE_FILE_NAMES:
            continue
        files.append(path.relative_to(case_dir).as_posix())
    return files


def find_case_dirs_without_manifest(cases_root: Path) -> list[str]:
    missing: list[str] = []
    for runtime_dir in sorted(cases_root.iterdir()):
        if not runtime_dir.is_dir() or runtime_dir.name not in CASE_RUNTIME_DIR_NAMES:
            continue
        for case_dir in sorted(runtime_dir.iterdir()):
            if not case_dir.is_dir() or case_dir.name in IGNORED_CASE_DIR_NAMES:
                continue
            if (case_dir / "case.json").exists():
                continue
            if iter_case_files(case_dir):
                missing.append(case_dir.relative_to(cases_root).as_posix())
    return missing


def is_true(value: Any) -> bool:
    return value is True or value == "true" or value == 1


def requires_current_proof_binding(data: dict[str, Any]) -> bool:
    return (
        data.get("caseKind") == "implementation"
        and data.get("verificationClass") == FRESH_VERIFICATION_CLASS
    )


def source_provenance_findings(
    skill_root: Path, rel: str, data: dict[str, Any]
) -> list[str]:
    """Keep resolvable commits distinct from provenance text that cannot resolve."""
    findings: list[str] = []
    verification = data.get("verification") or {}
    source_commit = verification.get("sourceCommit")
    source_reference = verification.get("sourceReference")
    resolution = verification.get("sourceReferenceResolution")

    if source_commit and source_reference:
        return [f"{rel}: verification cannot declare both sourceCommit and sourceReference"]
    if data.get("verificationClass") == HISTORICAL_VERIFICATION_CLASS and not (
        source_commit or source_reference
    ):
        findings.append(
            f"{rel}: historical verification requires sourceCommit or sourceReference"
        )

    if source_commit:
        if not isinstance(source_commit, str) or not re.fullmatch(
            r"[0-9a-f]{40}", source_commit
        ):
            findings.append(f"{rel}: verification.sourceCommit must be a full commit id")
        else:
            resolved = subprocess.run(
                [
                    "git",
                    "-C",
                    str(skill_root),
                    "cat-file",
                    "-e",
                    f"{source_commit}^{{commit}}",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if resolved.returncode != 0:
                findings.append(
                    f"{rel}: verification.sourceCommit does not resolve in the current repository"
                )
        if resolution is not None:
            findings.append(
                f"{rel}: resolvable sourceCommit must not carry sourceReferenceResolution"
            )

    if source_reference:
        if not isinstance(source_reference, str):
            findings.append(f"{rel}: verification.sourceReference must be text")
        if not isinstance(resolution, dict):
            findings.append(
                f"{rel}: sourceReference requires sourceReferenceResolution"
            )
        else:
            if resolution.get("status") != "unresolvable-in-current-repository":
                findings.append(
                    f"{rel}: sourceReferenceResolution.status must be unresolvable-in-current-repository"
                )
            for field in ("checkedAt", "reason"):
                if not isinstance(resolution.get(field), str) or not resolution.get(field):
                    findings.append(
                        f"{rel}: sourceReferenceResolution.{field} is required"
                    )
        if isinstance(source_reference, str):
            resolved = subprocess.run(
                [
                    "git",
                    "-C",
                    str(skill_root),
                    "rev-parse",
                    "--verify",
                    f"{source_reference}^{{commit}}",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if resolved.returncode == 0:
                findings.append(
                    f"{rel}: sourceReference resolves and must be recorded as sourceCommit"
                )
    return findings


def evidence_process_claim_findings(text: str) -> list[str]:
    markers = (
        ("entry.py", "references active entry.py"),
        ("freshly-verified", "claims freshly-verified status"),
        ("case_live", "contains active live command"),
        ("bundled implementation", "claims bundled implementation"),
        ("bundled 实现", "claims bundled implementation"),
        ("完整实现位于本目录", "claims complete local implementation"),
    )
    lowered = text.lower()
    return [label for marker, label in markers if marker.lower() in lowered]


def check_verification_contract(
    *,
    rel: str,
    data: dict[str, Any],
    mismatches: list[str],
    ok: list[str],
) -> None:
    verification_class = data.get("verificationClass")
    if not isinstance(verification_class, str) or not verification_class:
        mismatches.append(f"{rel}: missing verificationClass")
        return
    if verification_class not in KNOWN_VERIFICATION_CLASSES:
        mismatches.append(
            f"{rel}: unknown verificationClass {verification_class!r}; "
            f"expected one of {sorted(KNOWN_VERIFICATION_CLASSES)}"
        )
        return

    verification = data.get("verification") or {}
    if not isinstance(verification, dict):
        mismatches.append(f"{rel}: verification must be an object")
        return

    case_kind = data.get("caseKind")
    artifacts = data.get("artifacts") or {}
    implementation = data.get("implementation")
    if case_kind == "evidence":
        if implementation is not None:
            mismatches.append(f"{rel}: evidence case requires implementation=null")
        if artifacts.get("entry") is not None:
            mismatches.append(f"{rel}: evidence case must not declare artifacts.entry")
    elif case_kind == "implementation":
        if not isinstance(implementation, dict) or not implementation.get("mode"):
            mismatches.append(f"{rel}: implementation case requires implementation.mode")
        if not isinstance(artifacts.get("entry"), dict):
            mismatches.append(f"{rel}: implementation case requires artifacts.entry")
    else:
        mismatches.append(f"{rel}: unknown caseKind {case_kind!r}")

    if verification_class == FRESH_VERIFICATION_CLASS:
        for key in VERIFICATION_ARTIFACT_KEYS:
            item = verification.get(key)
            if not isinstance(item, dict):
                mismatches.append(
                    f"{rel}: freshly-verified requires verification.{key} object"
                )
                continue
            if not item.get("path") or not item.get("sha256"):
                mismatches.append(
                    f"{rel}: freshly-verified verification.{key} needs path and sha256"
                )
        if not is_true(verification.get("executed")):
            mismatches.append(f"{rel}: freshly-verified requires verification.executed=true")
        if not is_true(verification.get("passed")):
            mismatches.append(f"{rel}: freshly-verified requires verification.passed=true")
        if not isinstance(verification.get("executedAt"), str):
            mismatches.append(f"{rel}: freshly-verified requires verification.executedAt")
        evidence = verification.get("evidenceArtifact")
        if isinstance(evidence, dict):
            evidence_path = evidence.get("path")
            if isinstance(evidence_path, str) and not evidence_path.endswith(".json"):
                mismatches.append(
                    f"{rel}: freshly-verified evidenceArtifact.path must be JSON: {evidence_path}"
                )
        ok.append(f"{rel}: verificationClass freshly-verified contract")
        if data.get("historicalReferences"):
            proof = verification.get("proof") or {}
            historical = proof.get("historicalLiveProof") or {}
            if proof.get("activeScope") != "offline-only":
                mismatches.append(
                    f"{rel}: archived live provenance requires proof.activeScope=offline-only"
                )
            if historical.get("classification") != "historical-archive-provenance":
                mismatches.append(
                    f"{rel}: missing historicalLiveProof archive classification"
                )
            if historical.get("currentAcceptance") is not False:
                mismatches.append(
                    f"{rel}: historicalLiveProof.currentAcceptance must be false"
                )
        return

    if verification_class == HISTORICAL_VERIFICATION_CLASS:
        if not is_true(data.get("requiresFreshVerification")):
            mismatches.append(
                f"{rel}: historical-user-attested requires requiresFreshVerification=true"
            )
            return
        if case_kind != "evidence":
            mismatches.append(
                f"{rel}: historical-user-attested active cases must be evidence-only"
            )
        if data.get("historicalReferences") and not isinstance(
            verification.get("metadataMigratedAt"), str
        ):
            mismatches.append(
                f"{rel}: archived historical reference requires verification.metadataMigratedAt"
            )
        ok.append(f"{rel}: verificationClass historical-user-attested contract")


def call_name(node: ast.AST) -> str:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def string_constants(node: ast.AST) -> list[str]:
    return [
        child.value
        for child in ast.walk(node)
        if isinstance(child, ast.Constant) and isinstance(child.value, str)
    ]


def active_archive_load_findings(cases_root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(cases_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in ACTIVE_CODE_SUFFIXES:
            continue
        if any(part in IGNORED_CASE_DIR_NAMES for part in path.parts):
            continue
        source = path.read_text(encoding="utf-8")
        if path.suffix.lower() != ".py":
            for lineno, line in enumerate(source.splitlines(), start=1):
                if ARCHIVE_DIR_NAME in line:
                    findings.append(
                        f"{path.relative_to(cases_root).as_posix()}:{lineno}: "
                        "active case code must not reference the live-reference archive"
                    )
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if ARCHIVE_DIR_NAME not in node.value:
                    continue
                findings.append(
                    f"{path.relative_to(cases_root).as_posix()}:{node.lineno}: "
                    "active case code must not reference the live-reference archive"
                )
    return findings


def sensitive_literal_findings(archive_root: Path) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    for path in sorted(archive_root.glob("**/*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = f"{ARCHIVE_REL}/{path.relative_to(archive_root).as_posix()}"
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = node.args.args[-len(node.args.defaults) :] if node.args.defaults else []
                for arg, default in zip(args, node.args.defaults):
                    if not any(part in arg.arg.lower() for part in SENSITIVE_NAME_PARTS):
                        continue
                    if isinstance(default, ast.Constant) and isinstance(default.value, str) and default.value:
                        findings.append((rel, f"function-default:{node.name}.{arg.arg}"))
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                value = node.value
                for target in targets:
                    if not isinstance(target, ast.Name):
                        continue
                    if not any(part in target.id.lower() for part in SENSITIVE_NAME_PARTS):
                        continue
                    if not (
                        isinstance(value, ast.Constant)
                        and isinstance(value.value, str)
                        and value.value
                    ):
                        continue
                    if (target.id.startswith("ENV_") or target.id.endswith("_ENV")) and re.fullmatch(
                        r"[A-Z][A-Z0-9_]+", value.value
                    ):
                        continue
                    findings.append((rel, f"module-constant:{target.id}"))
            elif isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if not (
                        isinstance(key, ast.Constant)
                        and isinstance(key.value, str)
                        and any(part in key.value.lower() for part in SENSITIVE_NAME_PARTS)
                    ):
                        continue
                    if isinstance(value, ast.Constant) and isinstance(value.value, str) and value.value:
                        findings.append((rel, f"dict-value:{key.value}"))
    return findings


def git_blob_at_source(skill_root: Path, source_commit: str, case_relative: str) -> bytes | None:
    try:
        repo = Path(
            subprocess.check_output(
                ["git", "-C", str(skill_root), "rev-parse", "--show-toplevel"],
                text=True,
            ).strip()
        )
        resolved = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", f"{source_commit}^{{commit}}"],
            text=True,
        ).strip()
        if resolved != source_commit:
            return None
        prefix = skill_root.relative_to(repo).as_posix()
        object_path = f"{prefix}/references/cases/{case_relative}"
        return subprocess.check_output(
            ["git", "-C", str(repo), "show", f"{source_commit}:{object_path}"]
        )
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None


def verify_archive(skill_root: Path, mismatches: list[str], ok: list[str]) -> None:
    archive_root = skill_root / ARCHIVE_REL
    manifest_path = archive_root / "MANIFEST.json"
    if not manifest_path.is_file():
        mismatches.append(f"missing archive manifest: {manifest_path}")
        return
    manifest = load_json(manifest_path)
    if manifest.get("schemaVersion") != ARCHIVE_SCHEMA:
        mismatches.append(f"archive schemaVersion must be {ARCHIVE_SCHEMA}")
    source_commit = manifest.get("sourceCommit")
    if not isinstance(source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        mismatches.append("archive sourceCommit must be a full 40-character commit id")
    offline_only_commit = manifest.get("offlineOnlyCommit")
    if not isinstance(offline_only_commit, str) or not re.fullmatch(
        r"[0-9a-f]{40}", offline_only_commit
    ):
        mismatches.append(
            "archive offlineOnlyCommit must be a full 40-character commit id"
        )

    declared: set[str] = set()
    for index, item in enumerate(manifest.get("files") or []):
        archive_path = item.get("archivePath")
        resolved = resolve_declared_path(
            label=f"archive files[{index}]",
            base=skill_root,
            allowed_root=archive_root,
            path_value=archive_path,
            mismatches=mismatches,
        )
        if resolved is None:
            continue
        path, normalized = resolved
        declared.add(path.relative_to(archive_root).as_posix())
        check_path_hash(
            label=f"archive files[{index}]={archive_path}",
            path=path,
            expected=item.get("sha256"),
            mismatches=mismatches,
            ok=ok,
        )
        if path.is_file() and path.stat().st_size != item.get("bytes"):
            mismatches.append(
                f"archive files[{index}] byte size mismatch: {archive_path}"
            )
        if item.get("caseRelative") != normalized.removeprefix(f"{ARCHIVE_REL}/"):
            mismatches.append(
                f"archive files[{index}] caseRelative does not match archivePath"
            )
        if isinstance(source_commit, str) and re.fullmatch(r"[0-9a-f]{40}", source_commit):
            source_bytes = git_blob_at_source(
                skill_root, source_commit, str(item.get("caseRelative", ""))
            )
            if source_bytes is None:
                mismatches.append(
                    f"archive files[{index}] cannot resolve declared source blob"
                )
            elif path.is_file() and path.read_bytes() != source_bytes:
                mismatches.append(
                    f"archive files[{index}] differs from declared source blob: {archive_path}"
                )
            else:
                ok.append(f"archive files[{index}] source provenance")

    disk = {
        path.relative_to(archive_root).as_posix()
        for path in archive_root.rglob("*")
        if path.is_file()
        and path.name not in ARCHIVE_CONTROL_FILES
        and not set(path.parts) & IGNORED_CASE_DIR_NAMES
    }
    for path in sorted(declared - disk):
        mismatches.append(f"archive manifest path missing on disk: {path}")
    for path in sorted(disk - declared):
        mismatches.append(f"undeclared archive file: {path}")

    detected = set(sensitive_literal_findings(archive_root))
    reviewed = {
        (item.get("archivePath"), item.get("finding"))
        for item in manifest.get("reviewedSensitiveLiterals") or []
        if item.get("classification") and item.get("reason")
    }
    for finding in sorted(detected - reviewed):
        mismatches.append(f"unreviewed archive sensitive literal: {finding[0]} {finding[1]}")
    for finding in sorted(reviewed - detected):
        mismatches.append(f"stale archive sensitive-literal review: {finding[0]} {finding[1]}")


def verify_historical_references(
    *,
    skill_root: Path,
    rel: str,
    data: dict[str, Any],
    archive_index: dict[str, dict[str, Any]],
    mismatches: list[str],
    ok: list[str],
) -> None:
    refs = data.get("historicalReferences") or []
    for index, item in enumerate(refs):
        archive_path = item.get("archivePath")
        manifest_item = archive_index.get(str(archive_path))
        if manifest_item is None:
            mismatches.append(f"{rel}: historicalReferences[{index}] is not in archive manifest")
            continue
        for key in ("sha256", "bytes"):
            if item.get(key) != manifest_item.get(key):
                mismatches.append(
                    f"{rel}: historicalReferences[{index}].{key} disagrees with archive manifest"
                )
        if item.get("manifestPath") != f"{ARCHIVE_REL}/MANIFEST.json":
            mismatches.append(f"{rel}: historicalReferences[{index}] has wrong manifestPath")
        if item.get("readPolicy") != "study-only":
            mismatches.append(f"{rel}: historicalReferences[{index}] must be study-only")
        if item.get("sourceCommit") != manifest_item.get("sourceCommit"):
            mismatches.append(f"{rel}: historicalReferences[{index}] sourceCommit mismatch")
        ok.append(f"{rel}: historicalReferences[{index}]")


def verify_case(
    skill_root: Path,
    case_json: Path,
    archive_index: dict[str, dict[str, Any]],
    mismatches: list[str],
    ok: list[str],
) -> None:
    rel = case_json.relative_to(skill_root).as_posix()
    data = load_json(case_json)
    case_dir = case_json.parent
    artifacts = data.get("artifacts") or {}
    declared_case_files = {"case.json"}

    mismatches.extend(source_provenance_findings(skill_root, rel, data))
    check_verification_contract(rel=rel, data=data, mismatches=mismatches, ok=ok)
    verify_historical_references(
        skill_root=skill_root,
        rel=rel,
        data=data,
        archive_index=archive_index,
        mismatches=mismatches,
        ok=ok,
    )

    for key in ARTIFACT_KEYS:
        item = artifacts.get(key)
        if not item:
            continue
        normalized = check_declared_hash(
            label=f"{rel}: artifacts.{key}",
            base=case_dir,
            allowed_root=case_dir,
            path_value=item.get("path"),
            expected=item.get("sha256"),
            mismatches=mismatches,
            ok=ok,
        )
        if normalized:
            declared_case_files.add(normalized)

    if data.get("caseKind") == "evidence":
        process = artifacts.get("process") or {}
        process_path = case_dir / str(process.get("path", ""))
        if process_path.is_file():
            process_text = process_path.read_text(encoding="utf-8", errors="replace")
            for finding in evidence_process_claim_findings(process_text):
                mismatches.append(f"{rel}: evidence PROCESS.md {finding}")

    for index, asset in enumerate(artifacts.get("assets") or []):
        normalized = check_declared_hash(
            label=f"{rel}: artifacts.assets[{index}]",
            base=case_dir,
            allowed_root=case_dir,
            path_value=asset.get("path"),
            expected=asset.get("sha256"),
            mismatches=mismatches,
            ok=ok,
        )
        if normalized:
            declared_case_files.add(normalized)

    for index, pre in enumerate(data.get("preRead") or []):
        path_value = pre.get("path")
        pre_path = validate_relative_posix_path(
            label=f"{rel}: preRead[{index}]", path_value=path_value, mismatches=mismatches
        )
        if pre_path is None:
            continue
        if pre_path.parts and pre_path.parts[0] == "references":
            base = skill_root
            allowed_root = skill_root
        else:
            base = case_dir
            allowed_root = case_dir
            declared_case_files.add(pre_path.as_posix())
        resolved = resolve_declared_path(
            label=f"{rel}: preRead[{index}]={path_value}",
            base=base,
            allowed_root=allowed_root,
            path_value=path_value,
            mismatches=mismatches,
        )
        if resolved is None:
            continue
        check_path_hash(
            label=f"{rel}: preRead[{index}]={path_value}",
            path=resolved[0],
            expected=pre.get("sha256"),
            mismatches=mismatches,
            ok=ok,
        )

    verification = data.get("verification") or {}
    asset_index = {
        item.get("path"): item.get("sha256")
        for item in artifacts.get("assets") or []
        if isinstance(item, dict)
    }
    for key in VERIFICATION_ARTIFACT_KEYS:
        item = verification.get(key)
        if not item:
            continue
        normalized = check_declared_hash(
            label=f"{rel}: verification.{key}",
            base=case_dir,
            allowed_root=case_dir,
            path_value=item.get("path"),
            expected=item.get("sha256"),
            mismatches=mismatches,
            ok=ok,
        )
        if normalized:
            declared_case_files.add(normalized)
            if key == "evidenceArtifact" and asset_index.get(normalized) != item.get("sha256"):
                mismatches.append(
                    f"{rel}: verification.evidenceArtifact must match artifacts.assets"
                )

    test_artifact = verification.get("testArtifact") or {}
    evidence_artifact = verification.get("evidenceArtifact") or {}
    if (
        test_artifact.get("path")
        and test_artifact.get("path") == evidence_artifact.get("path")
    ):
        mismatches.append(f"{rel}: testArtifact and evidenceArtifact must be distinct")

    if requires_current_proof_binding(data):
        proof = verification.get("proof") or {}
        entry = artifacts.get("entry") or {}
        test = verification.get("testArtifact") or {}
        if proof.get("activeScope") != "offline-only":
            mismatches.append(f"{rel}: current implementation proof must be offline-only")
        if proof.get("currentEntrySha256") != entry.get("sha256"):
            mismatches.append(f"{rel}: proof currentEntrySha256 does not bind current entry")
        if proof.get("currentTestArtifactSha256") != test.get("sha256"):
            mismatches.append(
                f"{rel}: proof currentTestArtifactSha256 does not bind current test"
            )
        evidence_path = case_dir / str(evidence_artifact.get("path", ""))
        if evidence_path.is_file():
            try:
                evidence_data = load_json(evidence_path)
            except json.JSONDecodeError as error:
                mismatches.append(f"{rel}: offline proof is invalid JSON: {error}")
            else:
                expected_evidence = {
                    "caseId": data.get("caseId"),
                    "activeScope": "offline-only",
                    "passed": True,
                    "entrySha256": entry.get("sha256"),
                    "testArtifactSha256": test.get("sha256"),
                }
                for field, expected in expected_evidence.items():
                    if evidence_data.get(field) != expected:
                        mismatches.append(
                            f"{rel}: offline proof {field} does not bind current case"
                        )

        historical = proof.get("historicalLiveProof")
        if historical:
            allowed = {
                "historical-archive-provenance",
                "historical-project-provenance",
            }
            if historical.get("classification") not in allowed:
                mismatches.append(f"{rel}: historicalLiveProof classification is invalid")
            if historical.get("currentAcceptance") is not False:
                mismatches.append(
                    f"{rel}: historicalLiveProof.currentAcceptance must be false"
                )

    for file_path in iter_case_files(case_dir):
        if file_path not in declared_case_files:
            mismatches.append(f"{rel}: undeclared case file {file_path}")


def verify_registry(
    skill_root: Path, case_files: list[Path], mismatches: list[str], ok: list[str]
) -> None:
    cases_root = skill_root / "references" / "cases"
    registry_path = cases_root / "registry.json"
    if not registry_path.exists():
        mismatches.append(f"missing registry: {registry_path}")
        return

    registry = load_json(registry_path)
    entries = registry.get("cases") or registry.get("entries") or []
    if not entries:
        mismatches.append("registry.json has no cases")
        return

    registry_case_paths: set[str] = set()
    for entry in entries:
        case_id = entry.get("caseId") or "<unknown>"
        manifest = entry.get("manifest") or {}
        path_value = manifest.get("path")
        resolved = resolve_declared_path(
            label=f"registry {case_id}: manifest",
            base=cases_root,
            allowed_root=cases_root,
            path_value=path_value,
            mismatches=mismatches,
        )
        if resolved is None:
            continue
        path, normalized = resolved
        registry_case_paths.add(normalized)
        check_path_hash(
            label=f"registry {case_id}: manifest",
            path=path,
            expected=manifest.get("sha256"),
            mismatches=mismatches,
            ok=ok,
        )

        case_data = load_json(path)
        case_vc = case_data.get("verificationClass")
        reg_vc = entry.get("verificationClass")
        if not isinstance(reg_vc, str) or not reg_vc:
            mismatches.append(f"registry {case_id}: missing verificationClass")
        elif case_vc != reg_vc:
            mismatches.append(
                f"registry {case_id}: verificationClass {reg_vc!r} "
                f"!= case.json {case_vc!r}"
            )
        else:
            ok.append(f"registry {case_id}: verificationClass")

        selectable_as = entry.get("selectableAs")
        if selectable_as not in {"template", "proof"}:
            mismatches.append(
                f"registry {case_id}: selectableAs must be 'template' or 'proof', "
                f"got {selectable_as!r}"
            )
        elif reg_vc == HISTORICAL_VERIFICATION_CLASS and selectable_as != "template":
            mismatches.append(
                f"registry {case_id}: historical-user-attested must use selectableAs=template"
            )
        elif reg_vc == FRESH_VERIFICATION_CLASS and selectable_as != "proof":
            mismatches.append(
                f"registry {case_id}: freshly-verified must use selectableAs=proof"
            )
        else:
            ok.append(f"registry {case_id}: selectableAs")

    disk_case_paths = {path.relative_to(cases_root).as_posix() for path in case_files}
    for path in sorted(registry_case_paths - disk_case_paths):
        mismatches.append(f"registry manifest path missing on disk: {path}")
    for path in sorted(disk_case_paths - registry_case_paths):
        mismatches.append(f"case.json exists but is not registered: {path}")


def git_revision_findings(skill_root: Path) -> list[str]:
    try:
        repo = Path(
            subprocess.check_output(
                ["git", "-C", str(skill_root), "rev-parse", "--show-toplevel"],
                text=True,
            ).strip()
        )
        prefix = skill_root.relative_to(repo).as_posix()
        cases_prefix = f"{prefix}/references/cases/"
        dirty = subprocess.check_output(
            ["git", "-C", str(repo), "diff", "--name-only", "HEAD", "--", cases_prefix],
            text=True,
        ).splitlines()
        if dirty:
            old_ref = "HEAD"
            changed = dirty
        else:
            old_ref = "HEAD^"
            changed = subprocess.check_output(
                [
                    "git",
                    "-C",
                    str(repo),
                    "diff",
                    "--name-only",
                    "HEAD^",
                    "HEAD",
                    "--",
                    cases_prefix,
                ],
                text=True,
            ).splitlines()
    except (OSError, subprocess.CalledProcessError, ValueError):
        return []

    changed_cases = {
        "/".join(path.removeprefix(cases_prefix).split("/")[:2])
        for path in changed
        if path.startswith(cases_prefix) and path != f"{cases_prefix}registry.json"
    }
    findings: list[str] = []
    for case_rel in sorted(changed_cases):
        case_path = skill_root / "references" / "cases" / case_rel / "case.json"
        if not case_path.is_file():
            continue
        repo_case_path = f"{cases_prefix}{case_rel}/case.json"
        try:
            old_data = json.loads(
                subprocess.check_output(
                    ["git", "-C", str(repo), "show", f"{old_ref}:{repo_case_path}"],
                    text=True,
                )
            )
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            continue
        new_data = load_json(case_path)
        if int(new_data.get("revision", 0)) <= int(old_data.get("revision", 0)):
            findings.append(
                f"{case_rel}: changed case must increment revision above {old_data.get('revision')}"
            )
        old_verification = old_data.get("verification") or {}
        new_verification = new_data.get("verification") or {}
        old_time = old_verification.get("executedAt") or old_verification.get("metadataMigratedAt")
        new_time = new_verification.get("executedAt") or new_verification.get("metadataMigratedAt")
        if not new_time or new_time == old_time:
            findings.append(f"{case_rel}: changed case must refresh verification time")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "skill_root_arg",
        nargs="?",
        type=Path,
        help="optional skill root path; same as --skill-root",
    )
    parser.add_argument(
        "--skill-root",
        type=Path,
        default=None,
        help="skill root containing references/cases (default: parent of scripts/)",
    )
    args = parser.parse_args(argv)
    if args.skill_root and args.skill_root_arg:
        parser.error("pass either positional skill_root or --skill-root, not both")

    skill_root = (args.skill_root or args.skill_root_arg or Path(__file__).resolve().parents[1]).resolve()
    cases_root = skill_root / "references" / "cases"
    if not cases_root.is_dir():
        print(f"cases directory not found: {cases_root}", file=sys.stderr)
        return 1

    mismatches: list[str] = []
    ok: list[str] = []
    archive_manifest = load_json(skill_root / ARCHIVE_REL / "MANIFEST.json")
    archive_index = {
        item["archivePath"]: {
            **item,
            "sourceCommit": archive_manifest.get("sourceCommit"),
        }
        for item in archive_manifest.get("files") or []
    }

    case_files = sorted(cases_root.glob("**/case.json"))
    if not case_files:
        print(f"no case.json under {cases_root}", file=sys.stderr)
        return 1

    for case_dir in find_case_dirs_without_manifest(cases_root):
        mismatches.append(f"case directory missing case.json: {case_dir}")

    case_schema = skill_root / "references" / "schemas" / "case.schema.json"
    registry_schema = skill_root / "references" / "schemas" / "case-registry.schema.json"
    for case_json in case_files:
        mismatches.extend(schema_findings(case_schema, case_json))
    mismatches.extend(schema_findings(registry_schema, cases_root / "registry.json"))

    verify_archive(skill_root, mismatches, ok)
    mismatches.extend(active_archive_load_findings(cases_root))
    mismatches.extend(git_revision_findings(skill_root))

    for case_json in case_files:
        verify_case(skill_root, case_json, archive_index, mismatches, ok)

    verify_registry(skill_root, case_files, mismatches, ok)

    print(f"skill_root={skill_root}")
    print(f"cases={len(case_files)} checks_ok={len(ok)} mismatches={len(mismatches)}")
    if mismatches:
        print("FAIL")
        for item in mismatches:
            print(item)
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
