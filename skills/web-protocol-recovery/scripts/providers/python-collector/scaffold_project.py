#!/usr/bin/env python3
"""Create only the requested paths for a web-protocol-recovery-simple/v1 project."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import secrets
import tempfile
from pathlib import Path

PROVIDERS_DIR = Path(__file__).resolve().parents[1]
PATH_SAFETY_PATH = PROVIDERS_DIR / "path_safety.py"
PATH_SAFETY_SPEC = importlib.util.spec_from_file_location("wpr_path_safety", PATH_SAFETY_PATH)
if PATH_SAFETY_SPEC is None or PATH_SAFETY_SPEC.loader is None:
    raise RuntimeError(f"could not load path safety helper: {PATH_SAFETY_PATH}")
PATH_SAFETY = importlib.util.module_from_spec(PATH_SAFETY_SPEC)
PATH_SAFETY_SPEC.loader.exec_module(PATH_SAFETY)
PlainPathGuard = PATH_SAFETY.PlainPathGuard
absolute_no_resolve = PATH_SAFETY.absolute_no_resolve
is_reparse_point = PATH_SAFETY.is_reparse_point


CACHE_NAMESPACES = ("recon", "source", "ast", "env", "iv8", "samples", "private")
REQUIRED_GITIGNORE_RULES = {
    "config.local.json",
    "js_reverse_cache/**",
    "output/**",
    "__pycache__/",
    "*.pyc",
}
IV8_SILENT_PY = '''import contextlib
import importlib
import io
import os
import sys


@contextlib.contextmanager
def silent_import():
    sys.stdout.flush()
    sys.stderr.flush()
    stdout = sys.__stdout__ or sys.stdout
    stderr = sys.__stderr__ or sys.stderr
    saved_stdout = os.dup(stdout.fileno())
    saved_stderr = os.dup(stderr.fileno())
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, stdout.fileno())
        os.dup2(devnull, stderr.fileno())
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            yield
    finally:
        os.dup2(saved_stdout, stdout.fileno())
        os.dup2(saved_stderr, stderr.fileno())
        os.close(saved_stdout)
        os.close(saved_stderr)
        os.close(devnull)


def import_iv8_silent():
    with silent_import():
        return importlib.import_module("iv8")
'''

LOGGER_PY = '''import sys

try:
    from loguru import logger
except ImportError:
    class PrintLogger:
        @staticmethod
        def info(message, *args):
            if args:
                message = message.format(*args)
            out = getattr(sys.stdout, "buffer", None)
            if out:
                out.write((message + "\\n").encode("utf-8", errors="replace"))
                out.flush()
            else:
                print(message)

    logger = PrintLogger()
'''


def ensure_plain_path(path: Path) -> None:
    path = absolute_no_resolve(path)
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink() or is_reparse_point(current):
            raise ValueError(f"reparse path is not allowed: {current}")


def validate_existing_file(path: Path, guard: PlainPathGuard | None = None) -> None:
    ensure_plain_path(path)
    if guard is not None:
        guard.lock_file(path)
    if path.is_dir() or not path.is_file():
        raise ValueError(f"expected regular file: {path}")
    if os.stat(path, follow_symlinks=False).st_nlink != 1:
        raise ValueError(f"hard-linked file is not allowed: {path}")


def write_new(path: Path, content: str, guard: PlainPathGuard | None = None) -> bool:
    if guard is None:
        with PlainPathGuard() as local_guard:
            return write_new(path, content, local_guard)
    guard.lock_directory(path.parent)
    if os.path.lexists(path):
        validate_existing_file(path, guard)
        return False

    guard.verify_directory(path.parent)
    if os.name != "nt":
        parent_fd = guard.directory_fd(path.parent)
        temporary_name = f".{path.name}.{os.getpid()}.{secrets.token_hex(8)}.tmp"
        descriptor = None
        try:
            descriptor = os.open(
                temporary_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=parent_fd,
            )
            data = content.encode("utf-8")
            offset = 0
            while offset < len(data):
                offset += os.write(descriptor, data[offset:])
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            os.link(
                temporary_name,
                path.name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
                follow_symlinks=False,
            )
        finally:
            if descriptor is not None:
                os.close(descriptor)
            try:
                os.unlink(temporary_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
        return True

    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.link(temporary, path)
    except FileExistsError:
        validate_existing_file(path, guard)
        return False
    finally:
        temporary.unlink(missing_ok=True)
    return True


def parse_gitignore(path: Path, guard: PlainPathGuard) -> list[str]:
    active_lines = []
    for line in guard.read_text(path, encoding="utf-8").splitlines():
        if not line:
            continue
        if line != line.strip():
            raise ValueError(f".gitignore rules with surrounding whitespace are not accepted: {path}")
        if line.startswith("#"):
            continue
        active_lines.append(line)
    return active_lines


def validate_gitignore(path: Path, guard: PlainPathGuard) -> None:
    validate_existing_file(path, guard)
    active_lines = parse_gitignore(path, guard)
    negations = [line for line in active_lines if line.startswith("!")]
    if negations:
        raise ValueError("existing .gitignore contains negation rules; cache protection cannot be proven")
    rules = set(active_lines)
    missing = sorted(REQUIRED_GITIGNORE_RULES - rules)
    if missing:
        raise ValueError(f"existing .gitignore is missing required rules: {', '.join(missing)}")


def validate_nested_gitignores(root: Path, guard: PlainPathGuard) -> None:
    for current_value, directory_names, file_names in os.walk(root, followlinks=False):
        current = Path(current_value)
        guard.lock_directory(current)
        for name in directory_names:
            candidate = current / name
            if candidate.is_symlink() or is_reparse_point(candidate):
                raise ValueError(f"reparse path is not allowed: {candidate}")
        matches = [name for name in file_names if name.casefold() == ".gitignore"]
        if len(matches) > 1:
            raise ValueError(f"case-alias .gitignore files are not allowed: {current}")
        if not matches or current == root:
            continue
        path = current / matches[0]
        validate_existing_file(path, guard)
        active_lines = parse_gitignore(path, guard)
        if any(line.startswith("!") for line in active_lines):
            raise ValueError(f"nested .gitignore contains negation rules: {path}")


def build(root: Path, args: argparse.Namespace) -> list[str]:
    if not root.is_absolute():
        raise ValueError("project root must be absolute")
    unknown_namespaces = [name for name in args.cache_namespace if name not in CACHE_NAMESPACES]
    if unknown_namespaces:
        raise ValueError(f"unknown cache namespace: {unknown_namespaces[0]}")
    if (args.cache or args.output) and not args.gitignore:
        raise ValueError("cache and output paths require --gitignore protection")
    directories = []
    if args.cache:
        directories.append("js_reverse_cache")
        directories.extend(f"js_reverse_cache/{name}" for name in args.cache_namespace)
    want_logger = args.logger or args.iv8_silent
    if args.utils or args.iv8_silent or want_logger:
        directories.append("utils")
    if args.tests:
        directories.append("tests")
    if args.output:
        directories.append("output")

    files = []
    if args.entry:
        files.append(("main.py", '"""web-protocol-recovery project entry."""\n\n\ndef main():\n    raise NotImplementedError("implementation not generated yet")\n\n\nif __name__ == "__main__":\n    main()\n'))
    if args.iv8_silent:
        files.append(("utils/iv8_silent.py", IV8_SILENT_PY))
    if want_logger:
        files.append(("utils/logger.py", LOGGER_PY))
    if args.requirements:
        files.append(("requirements.txt", ""))
    if args.readme:
        files.append(
            (
                "README.md",
                "# web-protocol-recovery Project\n\n"
                "Run with `python main.py`.\n\n"
                "Dynamic evidence stays under `js_reverse_cache/` (never OS temp as primary storage).\n"
                "Optional: install `loguru` for richer logs; `utils/logger.py` falls back to print.\n",
            )
        )
    if args.gitignore:
        files.append((".gitignore", "config.local.json\njs_reverse_cache/**\noutput/**\n__pycache__/\n*.pyc\n"))

    created: list[str] = []
    with PlainPathGuard() as guard:
        ensure_plain_path(root)
        ensure_plain_path(root.parent)
        guard.lock_directory(root.parent)
        if not root.exists():
            if os.name == "nt":
                root.mkdir()
            else:
                os.mkdir(root.name, dir_fd=guard.directory_fd(root.parent))
        guard.lock_directory(root)
        if not root.is_dir():
            raise ValueError(f"project root is not a directory: {root}")

        gitignore = root / ".gitignore"
        if args.gitignore and os.path.lexists(gitignore):
            validate_gitignore(gitignore, guard)
        if args.gitignore:
            validate_nested_gitignores(root, guard)

        # Validate every requested destination before creating the first one.
        for relative in directories:
            target = root / relative
            ensure_plain_path(target)
            if target.exists():
                guard.lock_directory(target)
            elif os.path.lexists(target):
                raise ValueError(f"reparse path is not allowed: {target}")
        for relative, _ in files:
            target = root / relative
            if os.path.lexists(target):
                validate_existing_file(target, guard)

        for relative in directories:
            target = root / relative
            if not target.exists():
                guard.lock_directory(target.parent)
                guard.verify_directory(target.parent)
                if os.name == "nt":
                    target.mkdir()
                else:
                    os.mkdir(target.name, dir_fd=guard.directory_fd(target.parent))
                guard.lock_directory(target)
                created.append(relative.replace("\\", "/") + "/")
        for relative, content in files:
            if write_new(root / relative, content, guard):
                created.append(relative)
    return created


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--entry", action="store_true")
    parser.add_argument("--cache", action="store_true")
    parser.add_argument("--cache-namespace", action="append", default=[])
    parser.add_argument("--utils", action="store_true")
    parser.add_argument(
        "--iv8-silent",
        action="store_true",
        help="create utils/iv8_silent.py for silent iv8 package import (also creates utils/logger.py)",
    )
    parser.add_argument(
        "--logger",
        action="store_true",
        help="create utils/logger.py (optional loguru + PrintLogger fallback)",
    )
    parser.add_argument("--tests", action="store_true")
    parser.add_argument("--output", action="store_true")
    parser.add_argument("--requirements", action="store_true")
    parser.add_argument("--readme", action="store_true")
    parser.add_argument("--gitignore", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.confirm:
        raise SystemExit("refusing filesystem changes without --confirm")
    if not args.root.is_absolute():
        raise SystemExit("project root must be absolute")
    root = absolute_no_resolve(args.root)
    created = build(root, args)
    print(json.dumps({"layout": "web-protocol-recovery-simple/v1", "root": str(root), "created": created}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
