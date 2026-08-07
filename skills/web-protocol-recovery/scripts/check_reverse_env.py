#!/usr/bin/env python3
"""
Quick environment check for protocol-first reverse work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import importlib.util
import importlib.metadata
import os
import pathlib
import sys
import re
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Any


TOOLS = [
    "node",
    "npm",
    "curl",
    "git",
]

PYTHON_MODULES = [
    "iv8",
    "curl_cffi",
]

MIN_PYTHON = (3, 9)
MODULE_NAME_RE = re.compile(r"^[A-Za-z_]\w*$")
PUBLIC_LOCKFILES = frozenset(
    {
        "package-lock.json",
        "npm-shrinkwrap.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "bun.lock",
        "poetry.lock",
        "uv.lock",
        "pipfile.lock",
    }
)
MAX_LOCKFILE_BYTES = 16 * 1024 * 1024


class EnvironmentInputError(ValueError):
    """Raised when an explicitly selected diagnostic input is unsafe."""


@dataclass(frozen=True)
class LockfileFingerprint:
    relative_path: str
    byte_length: int
    sha256: str


@dataclass(frozen=True)
class PythonEnvironment:
    active: bool
    kind: str
    project_venv_exists: bool
    project_venv_active: bool


def resolve_project_root(value: str | pathlib.Path) -> pathlib.Path:
    try:
        root = pathlib.Path(value).expanduser().resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise EnvironmentInputError("project root does not exist or cannot be resolved") from exc
    if not root.is_dir():
        raise EnvironmentInputError("project root must be a directory")
    return root


def _within(path: pathlib.Path, root: pathlib.Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except (ValueError, OSError, RuntimeError):
        return False
    return True


def _reject_linked_components(root: pathlib.Path, candidate: pathlib.Path) -> None:
    root_lexical = pathlib.Path(os.path.abspath(root))
    candidate_lexical = pathlib.Path(os.path.abspath(candidate))
    try:
        relative = candidate_lexical.relative_to(root_lexical)
    except ValueError as exc:
        raise EnvironmentInputError("helper lockfile must stay under project root") from exc
    current = root_lexical
    for part in relative.parts:
        current /= part
        try:
            metadata = os.lstat(current)
        except OSError as exc:
            raise EnvironmentInputError("helper lockfile path cannot be inspected") from exc
        reparse = bool(
            getattr(metadata, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        )
        if stat.S_ISLNK(metadata.st_mode) or reparse:
            raise EnvironmentInputError("helper lockfile path must not use symlinks or reparse points")


def fingerprint_helper_lockfile(
    project_root: pathlib.Path,
    value: str | pathlib.Path,
    *,
    max_bytes: int = MAX_LOCKFILE_BYTES,
) -> LockfileFingerprint:
    root = resolve_project_root(project_root)
    candidate = pathlib.Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    _reject_linked_components(root, candidate)
    try:
        candidate = candidate.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise EnvironmentInputError("helper lockfile does not exist or cannot be resolved") from exc
    if not _within(candidate, root):
        raise EnvironmentInputError("helper lockfile must stay under project root")
    if candidate.name.lower() not in PUBLIC_LOCKFILES:
        raise EnvironmentInputError("helper lockfile name is not a supported public lockfile")
    if not candidate.is_file():
        raise EnvironmentInputError("helper lockfile must be a regular non-symlink file")
    if max_bytes < 1:
        raise EnvironmentInputError("helper lockfile byte limit must be positive")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(candidate, flags)
    except OSError as exc:
        raise EnvironmentInputError("helper lockfile cannot be opened safely") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise EnvironmentInputError("helper lockfile must be a regular file")
        if before.st_nlink != 1:
            raise EnvironmentInputError("helper lockfile must not be a hardlink")
        if before.st_size > max_bytes:
            raise EnvironmentInputError(f"helper lockfile exceeds the {max_bytes}-byte limit")
        first = os.read(descriptor, max_bytes + 1)
        os.lseek(descriptor, 0, os.SEEK_SET)
        second = os.read(descriptor, max_bytes + 1)
        after = os.fstat(descriptor)
        path_after = os.stat(candidate, follow_symlinks=False)
    except OSError as exc:
        raise EnvironmentInputError("helper lockfile cannot be read safely") from exc
    finally:
        os.close(descriptor)
    if (
        len(first) > max_bytes
        or first != second
        or len(first) != before.st_size
        or not os.path.samestat(before, after)
        or not os.path.samestat(after, path_after)
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
    ):
        raise EnvironmentInputError("helper lockfile changed during validation")
    return LockfileFingerprint(
        relative_path=candidate.relative_to(root).as_posix(),
        byte_length=len(first),
        sha256=hashlib.sha256(first).hexdigest(),
    )


def discover_tool(name: str, project_root: pathlib.Path) -> str | None:
    """Resolve tools from absolute PATH entries without executing candidates."""
    if pathlib.Path(name).name != name or "/" in name or "\\" in name:
        return None
    for raw in os.environ.get("PATH", "").split(os.pathsep):
        if not raw:
            continue
        directory = pathlib.Path(raw.strip().strip('"')).expanduser()
        if not directory.is_absolute():
            continue
        try:
            directory = directory.resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        names = [name]
        if os.name == "nt" and pathlib.Path(name).suffix.lower() not in {".exe", ".cmd", ".bat", ".com"}:
            names = [f"{name}{suffix}" for suffix in (".exe", ".cmd", ".bat", ".com")]
        for candidate_name in names:
            candidate = directory / candidate_name
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
    return None


def command_version(path: str | None) -> str:
    if not path:
        return "missing"
    try:
        environment = {"PATH": str(pathlib.Path(path).parent), "NO_COLOR": "1"}
        for name in ("SystemRoot", "WINDIR", "COMSPEC", "PATHEXT"):
            if os.getenv(name):
                environment[name] = os.environ[name]
        completed = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
            env=environment,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    value = (completed.stdout or completed.stderr or "").strip().splitlines()
    return value[0][:128] if value else "unavailable"


def detect_python_environment(project_root: pathlib.Path) -> PythonEnvironment:
    prefix = pathlib.Path(sys.prefix).resolve()
    base_prefix = pathlib.Path(getattr(sys, "base_prefix", sys.prefix)).resolve()
    active = bool(getattr(sys, "real_prefix", None)) or prefix != base_prefix or bool(os.getenv("VIRTUAL_ENV"))
    kind = "conda" if os.getenv("CONDA_PREFIX") else ("venv" if active else "system")
    project_venv = project_root / ".venv"
    try:
        executable = pathlib.Path(sys.executable).resolve()
        project_venv_resolved = project_venv.resolve(strict=False)
        project_active = executable == project_venv_resolved or project_venv_resolved in executable.parents
    except (OSError, RuntimeError):
        project_active = False
    return PythonEnvironment(
        active=active,
        kind=kind,
        project_venv_exists=project_venv.is_dir(),
        project_venv_active=project_active,
    )


def module_status(name: str) -> str:
    try:
        return "available" if importlib.util.find_spec(name) else "missing"
    except (AttributeError, ImportError, ValueError):
        return "unavailable"


def module_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"
    except Exception:
        return "unavailable"


def build_report(
    required_tools: list[str],
    required_modules: list[str],
    *,
    project_root: pathlib.Path | str = ".",
    helper_lockfiles: list[str] | None = None,
    require_project_venv: bool = False,
) -> dict:
    root = resolve_project_root(project_root)
    tool_map: dict[str, str | None] = {"python": sys.executable}
    tool_map.update({name: discover_tool(name, root) for name in TOOLS})
    module_names = sorted(set(PYTHON_MODULES) | set(required_modules))
    tools: dict[str, dict[str, Any]] = {}
    for name, path in tool_map.items():
        project_owned = bool(path and name != "python" and _within(pathlib.Path(path), root))
        if name == "python":
            version = sys.version.split()[0]
        elif project_owned:
            version = "not-executed-project-path"
        elif name in {"node", "npm"}:
            version = command_version(path)
        else:
            version = None
        tools[name] = {
            "path": path,
            "available": bool(path),
            "required": name in required_tools,
            "project_owned": project_owned,
            "version": version,
        }
    modules = {
        name: {
            "status": module_status(name),
            "version": module_version(name) if module_status(name) == "available" else "missing",
            "required": name in required_modules,
        }
        for name in module_names
    }
    python_ok = sys.version_info >= MIN_PYTHON
    missing_required_tools = [name for name in required_tools if not tool_map.get(name)]
    missing_required_modules = [name for name in required_modules if module_status(name) != "available"]
    environment = detect_python_environment(root)
    fingerprints = [
        fingerprint_helper_lockfile(root, value)
        for value in (helper_lockfiles or [])
    ]
    proxy_flags = {
        name: bool(os.getenv(name) or os.getenv(name.lower()))
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY")
    }
    venv_ok = not require_project_venv or environment.project_venv_active
    return {
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "python_minimum": ".".join(str(part) for part in MIN_PYTHON),
        "python_ok": python_ok,
        "tools": tools,
        "python_modules": modules,
        "missing_required_tools": missing_required_tools,
        "missing_required_modules": missing_required_modules,
        "project_root": str(root),
        "python_environment": {
            "active": environment.active,
            "kind": environment.kind,
            "project_venv_exists": environment.project_venv_exists,
            "project_venv_active": environment.project_venv_active,
            "require_project_venv": require_project_venv,
        },
        "helper_lockfiles": [
            {
                "relative_path": item.relative_path,
                "byte_length": item.byte_length,
                "sha256": item.sha256,
            }
            for item in fingerprints
        ],
        "proxy_environment": proxy_flags,
        "overall_ok": python_ok and not missing_required_tools and not missing_required_modules and venv_ok,
        "notes": [
            "pure Python protocol replay should work with Python alone",
            "node is useful for preserving tiny JS helpers",
            "iv8 or another embedded runtime is useful when JS needs host semantics without a real browser",
            "curl is useful for quick raw request diffs",
            "PATH tools inside project root are reported as available but are not executed for version discovery",
        ],
    }


def print_human(report: dict) -> None:
    print("reverse environment")
    print(f"- python_version: {report['python_version']}")
    print(f"- python_minimum: {report['python_minimum']}")
    print(f"- python_ok: {report['python_ok']}")
    print(f"- python: {report['python_executable']}")
    print(f"- project_root: {report['project_root']}")
    environment = report["python_environment"]
    print(f"- virtual_environment_active: {'yes' if environment['active'] else 'no'}")
    print(f"- virtual_environment_kind: {environment['kind']}")
    print(f"- project_dot_venv_exists: {'yes' if environment['project_venv_exists'] else 'no'}")
    print(f"- project_dot_venv_active: {'yes' if environment['project_venv_active'] else 'no'}")
    print(f"- project_dot_venv_requirement: {'strict' if environment['require_project_venv'] else 'advisory'}")
    for name, info in report["tools"].items():
        status = info["path"] or "missing"
        required = " required" if info["required"] else ""
        print(f"- {name}: {status}{required}")
        print(f"- {name}_project_owned: {'yes' if info['project_owned'] else 'no'}")
        if info["version"] is not None:
            print(f"- {name}_version: {info['version']}")
    for name, info in report["python_modules"].items():
        required = " required" if info["required"] else ""
        version = info["version"] if info["status"] == "available" else "missing"
        print(f"- python_module_{name}: {info['status']} version={version}{required}")
    print("helper lockfile fingerprints")
    if report["helper_lockfiles"]:
        for item in report["helper_lockfiles"]:
            print(
                f"- helper_lockfile: {item['relative_path']} "
                f"bytes={item['byte_length']} sha256={item['sha256']}"
            )
    else:
        print("- helper_lockfiles: none_requested")
    print("proxy environment")
    for name, configured in report["proxy_environment"].items():
        print(f"- proxy_env_{name}: {'set' if configured else 'unset'}")
    print("notes")
    for note in report["notes"]:
        print(f"- {note}")


def self_test() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory) / "project"
        root.mkdir()
        lockfile = root / "package-lock.json"
        lockfile.write_text('{"name":"public-helper"}', encoding="utf-8")
        result = fingerprint_helper_lockfile(root, lockfile)
        if result.relative_path != "package-lock.json":
            raise RuntimeError("lockfile relative path self-test failed")
        if result.byte_length != lockfile.stat().st_size:
            raise RuntimeError("lockfile byte length self-test failed")
        outside = pathlib.Path(directory) / "package-lock.json"
        outside.write_text("{}", encoding="utf-8")
        try:
            fingerprint_helper_lockfile(root, outside)
        except EnvironmentInputError:
            pass
        else:
            raise AssertionError("outside lockfile was accepted")
    print("check_reverse_env_self_test=PASS")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check local protocol reverse environment.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when Python or required items are missing")
    parser.add_argument("--require-tool", action="append", default=[], help="Tool name that must be on PATH. Repeat as needed.")
    parser.add_argument("--require-module", action="append", default=[], help="Python module that must import. Repeat as needed.")
    parser.add_argument("--project-root", default=".", help="Existing project directory (default: current directory)")
    parser.add_argument("--helper-lockfile", action="append", default=[], help="Explicit public lockfile under project root; repeat as needed")
    parser.add_argument("--require-project-venv", action="store_true", help="Fail unless the active interpreter is under project-root/.venv")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic local checks")
    args = parser.parse_args(argv)

    if args.self_test:
        self_test()
        return 0

    invalid_modules = [name for name in args.require_module if not MODULE_NAME_RE.fullmatch(name)]
    if invalid_modules:
        parser.error("--require-module accepts top-level module names only: " + ", ".join(invalid_modules))

    try:
        report = build_report(
            args.require_tool,
            args.require_module,
            project_root=args.project_root,
            helper_lockfiles=args.helper_lockfile,
            require_project_venv=args.require_project_venv,
        )
    except EnvironmentInputError as exc:
        print(f"environment_check_error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)

    if args.strict and not report["overall_ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
