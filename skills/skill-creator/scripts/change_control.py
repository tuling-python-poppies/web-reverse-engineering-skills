#!/usr/bin/env python3
"""Create and verify an explicit, hash-based skill edit allowlist.

The manifest is a local control artifact. It contains paths and SHA-256 hashes,
not file contents. A user must pass --confirm before a manifest is created.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


EXCLUDED_PARTS = {".git", "__pycache__", "node_modules"}


def absolute_no_resolve(path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def is_reparse_point(path: Path) -> bool:
    try:
        attributes = getattr(os.stat(path, follow_symlinks=False), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    return bool(attributes & 0x400)


def validate_external_file_path(path: Path, *, allow_missing: bool) -> Path:
    path = absolute_no_resolve(path)
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if not current.exists() and not current.is_symlink():
            continue
        if current.is_symlink() or is_reparse_point(current):
            raise ValueError(f"controlled external path contains a reparse point: {current}")
    if not path.exists():
        if allow_missing:
            return path
        raise ValueError(f"controlled external file is missing: {path}")
    if not path.is_file():
        raise ValueError(f"controlled external path is not a regular file: {path}")
    if os.stat(path, follow_symlinks=False).st_nlink != 1:
        raise ValueError(f"hard-linked controlled external file is not allowed: {path}")
    return path


def validate_missing_skill_root(path: Path) -> Path:
    root = absolute_no_resolve(path)
    if root.exists() or root.is_symlink():
        raise ValueError(f"missing-target skill path already exists: {root}")
    if not root.parent.is_dir():
        raise ValueError(f"missing-target parent directory does not exist: {root.parent}")
    current = root.parent
    while True:
        if current.is_symlink() or is_reparse_point(current):
            raise ValueError(f"missing-target parent contains a reparse point: {current}")
        if current.parent == current:
            break
        current = current.parent
    return root


def iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.is_symlink() or is_reparse_point(path):
            raise ValueError(f"symlink is not allowed: {path}")
        if path.is_file():
            if os.stat(path, follow_symlinks=False).st_nlink != 1:
                raise ValueError(f"hard-linked skill file is not allowed: {path}")
            yield path


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect(root: Path) -> dict[str, str]:
    return {str(path.relative_to(root)): file_hash(path) for path in iter_files(root)}


def allowed_state_hash(root: Path, allowed: list[str], ledger_paths=None) -> str:
    state = {}
    for relative in sorted(allowed):
        target = contained_path(root, relative)
        if target.is_dir():
            raise ValueError(f"allowlisted path is a directory: {relative}")
        if target.is_file() and os.stat(target, follow_symlinks=False).st_nlink != 1:
            raise ValueError(f"hard-linked allowlisted file is not allowed: {relative}")
        state[relative] = file_hash(target) if target.is_file() else None
    for ledger in sorted(validate_external_file_path(Path(item), allow_missing=True) for item in (ledger_paths or [])):
        state[f"ledger:{ledger}"] = file_hash(ledger) if ledger.is_file() else None
    payload = json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def find_git_root(path: Path):
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(path),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def _git_bytes(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"git {' '.join(args)} failed: {message}")
    return result.stdout


def _repo_relative(repo: Path, path: Path):
    try:
        return path.resolve().relative_to(repo)
    except ValueError:
        return None


def repo_state_hash(repo: Path, worktree_excluded_paths=(), index_excluded_paths=()) -> str:
    """Hash index entries plus tracked/untracked worktree bytes outside exclusions."""
    worktree_excluded = {
        str(relative).replace("\\", "/")
        for path in worktree_excluded_paths
        for relative in [_repo_relative(repo, Path(path))]
        if relative is not None
    }
    index_excluded = {
        str(relative).replace("\\", "/")
        for path in index_excluded_paths
        for relative in [_repo_relative(repo, Path(path))]
        if relative is not None
    }

    index_entries = []
    for entry in _git_bytes(repo, "ls-files", "--stage", "-z").split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        relative = raw_path.decode("utf-8", errors="surrogateescape").replace("\\", "/")
        if relative not in index_excluded:
            index_entries.append((relative, metadata.decode("ascii")))

    worktree = {}
    raw_files = _git_bytes(repo, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    for raw_path in raw_files.split(b"\0"):
        if not raw_path:
            continue
        relative = raw_path.decode("utf-8", errors="surrogateescape").replace("\\", "/")
        if relative in worktree_excluded:
            continue
        target = repo / Path(relative)
        if target.is_symlink():
            worktree[relative] = f"symlink:{os.readlink(target)}"
        elif target.is_file():
            worktree[relative] = file_hash(target)
        else:
            worktree[relative] = None

    payload = json.dumps(
        {"index": sorted(index_entries), "worktree": worktree},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def readonly_state_hash(root: Path) -> str:
    """Return a no-write fingerprint suitable for evaluate/history-only checks."""
    requested_root = root.absolute()
    if requested_root.is_symlink():
        raise ValueError(f"read-only root must not be a symlink: {requested_root}")
    root = requested_root.resolve()
    tree_state = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if ".git" in relative.parts:
            continue
        key = str(relative).replace("\\", "/")
        if path.is_symlink():
            raise ValueError(f"read-only scope contains a symlink: {path}")
        elif path.is_file():
            tree_state[key] = f"file:{file_hash(path)}"
        elif path.is_dir():
            tree_state[key] = "dir"
    repo = find_git_root(root)
    payload = json.dumps(
        {"tree": tree_state, "repo": repo_state_hash(repo) if repo is not None else None},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def normalize_relative(value: str) -> str:
    path = Path(value)
    if path.is_absolute() or path.drive or path.root or path.anchor or ".." in path.parts or not path.parts:
        raise ValueError(f"allowlist path must be relative and contained: {value}")
    return str(path)


def contained_path(root: Path, relative: str) -> Path:
    candidate = root / normalize_relative(relative)
    probe = candidate
    while probe != root:
        if probe.is_symlink() or is_reparse_point(probe):
            raise ValueError(f"symlink is not allowed in controlled path: {relative}")
        if probe.parent == probe:
            raise ValueError(f"path escapes skill root: {relative}")
        probe = probe.parent
    target = candidate.resolve()
    if target == root or root not in target.parents:
        raise ValueError(f"path escapes skill root: {relative}")
    return target


def canonical_existing_relative(root: Path, relative: str) -> str:
    parts = list(Path(normalize_relative(relative)).parts)
    current = root
    actual_parts = []
    for index, part in enumerate(parts):
        if not current.is_dir():
            actual_parts.extend(parts[index:])
            break
        matches = [entry for entry in current.iterdir() if os.path.normcase(entry.name) == os.path.normcase(part)]
        if len(matches) > 1:
            raise ValueError(f"skill tree contains case-alias entries below: {current}")
        if not matches:
            actual_parts.extend(parts[index:])
            break
        match = matches[0]
        if match.is_symlink() or is_reparse_point(match):
            raise ValueError(f"symlink is not allowed in controlled path: {relative}")
        actual_parts.append(match.name)
        current = match
    return str(Path(*actual_parts))


def canonicalize_allowed_paths(root: Path, allowed: list[str]) -> list[str]:
    seen = {}
    result = []
    for relative in allowed:
        canonical = canonical_existing_relative(root, relative)
        key = os.path.normcase(canonical)
        if key in seen and seen[key] != canonical:
            raise ValueError(f"allowlist contains case-alias paths: {seen[key]} / {canonical}")
        seen[key] = canonical
        if canonical not in result:
            result.append(canonical)
    return sorted(result)


def unexpected_missing_target_entries(root: Path, allowed: set[str]) -> list[str]:
    if not root.exists():
        return []
    allowed_files = {os.path.normcase(normalize_relative(item)) for item in allowed}
    allowed_directories = set()
    for relative in allowed:
        parent = Path(normalize_relative(relative)).parent
        while parent != Path("."):
            allowed_directories.add(os.path.normcase(str(parent)))
            parent = parent.parent
    unexpected = []
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        key = os.path.normcase(relative)
        if path.is_symlink() or is_reparse_point(path):
            unexpected.append(relative)
        elif path.is_dir():
            if key not in allowed_directories:
                unexpected.append(relative + os.sep)
        elif path.is_file() and key not in allowed_files:
            unexpected.append(relative)
    return unexpected


def publish_exclusive(path: Path, data: bytes) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.link(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 2 or data.get("confirmed") is not True:
        raise ValueError("manifest must be a confirmed version-2 manifest; recreate legacy manifests")
    for field in (
        "skill_root", "allowed_paths", "baseline_files", "baseline_allowed_files",
        "ledger_paths", "git_root", "baseline_repo_state_sha256",
        "baseline_archive", "baseline_archive_sha256",
    ):
        if field not in data:
            raise ValueError(f"manifest missing required field: {field}")
    data["allowed_paths"] = [normalize_relative(item) for item in data["allowed_paths"]]
    data["baseline_files"] = {
        normalize_relative(path): digest for path, digest in data["baseline_files"].items()
    }
    data["baseline_allowed_files"] = {
        normalize_relative(path): digest for path, digest in data["baseline_allowed_files"].items()
    }
    data["ledger_paths"] = [str(validate_external_file_path(Path(item), allow_missing=True)) for item in data["ledger_paths"]]
    data.setdefault("skill_root_existed", True)
    if not isinstance(data["skill_root_existed"], bool):
        raise ValueError("manifest has invalid skill_root_existed flag")
    canonical_allowed = canonicalize_allowed_paths(absolute_no_resolve(data["skill_root"]), data["allowed_paths"])
    if canonical_allowed != sorted(data["allowed_paths"]):
        raise ValueError("manifest allowlist casing does not match the skill tree; recreate the manifest")
    for field in ("baseline_archive_sha256",):
        if not isinstance(data[field], str) or len(data[field]) != 64:
            raise ValueError(f"manifest has invalid hash field: {field}")
    if data["git_root"] is not None and (
        not isinstance(data["baseline_repo_state_sha256"], str)
        or len(data["baseline_repo_state_sha256"]) != 64
    ):
        raise ValueError("manifest has invalid baseline_repo_state_sha256")
    return data


def verify_manifest_digest(path: Path, expected: str) -> None:
    if not isinstance(expected, str) or len(expected) != 64 or file_hash(path) != expected.lower():
        raise ValueError("manifest SHA-256 does not match the externally retained digest")


def snapshot(args: argparse.Namespace) -> int:
    if not args.confirm:
        print("refusing to create a manifest without --confirm", file=sys.stderr)
        return 2
    try:
        allowed = sorted({normalize_relative(item) for item in (args.allow or [])})
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    if not allowed:
        print("provide at least one --allow relative path", file=sys.stderr)
        return 2
    requested_root = absolute_no_resolve(args.skill_path)
    root_existed = requested_root.exists()
    if root_existed:
        root = requested_root.resolve()
        if not root.is_dir() or not (root / "SKILL.md").is_file():
            print(f"missing SKILL.md: {root}", file=sys.stderr)
            return 2
    else:
        if not getattr(args, "allow_missing_target", False):
            print(f"missing SKILL.md: {requested_root}", file=sys.stderr)
            return 2
        try:
            root = validate_missing_skill_root(requested_root)
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 2
        if "SKILL.md" not in allowed:
            print("missing-target snapshot must allow SKILL.md", file=sys.stderr)
            return 2
    try:
        files = collect(root)
        allowed = canonicalize_allowed_paths(root, allowed)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    allowed_baseline = {}
    try:
        for relative in allowed:
            target = contained_path(root, relative)
            if target.is_dir():
                raise ValueError(f"allowlisted path is a directory: {relative}")
            if target.is_file():
                if os.stat(target, follow_symlinks=False).st_nlink != 1:
                    raise ValueError(f"hard-linked allowlisted file is not allowed: {relative}")
                allowed_baseline[relative] = file_hash(target)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    try:
        ledgers = [str(validate_external_file_path(Path(item), allow_missing=True)) for item in (getattr(args, "ledger", None) or [])]
        for ledger in ledgers:
            target = Path(ledger)
            validate_external_file_path(target, allow_missing=True)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    output = Path(args.manifest).resolve()
    archive = output.with_suffix(".baseline.zip")
    repo = find_git_root(root if root_existed else root.parent)
    repo_exclusions = [contained_path(root, item) for item in allowed]
    repo_exclusions.extend(Path(item) for item in ledgers)
    repo_exclusions.extend([output, archive])
    manifest = {
        "version": 2,
        "confirmed": True,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
        "skill_root": str(root),
        "skill_root_existed": root_existed,
        "allowed_paths": allowed,
        "baseline_files": files,
        "baseline_allowed_files": allowed_baseline,
        "ledger_paths": ledgers,
        "git_root": str(repo) if repo else None,
        "baseline_repo_state_sha256": repo_state_hash(repo, repo_exclusions) if repo else None,
    }
    if output == root or root in output.parents:
        print("manifest must be outside the skill directory", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or archive.exists():
        print(f"refusing to overwrite change-control artifacts: {output}", file=sys.stderr)
        return 2
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".zip.tmp", delete=False) as handle:
        temp_archive = Path(handle.name)
    try:
        with zipfile.ZipFile(temp_archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for relative in allowed_baseline:
                bundle.write(contained_path(root, relative), relative)
        os.link(temp_archive, archive)
    except Exception:
        archive.unlink(missing_ok=True)
        raise
    finally:
        temp_archive.unlink(missing_ok=True)
    manifest["baseline_archive"] = str(archive)
    manifest["baseline_archive_sha256"] = file_hash(archive)
    try:
        publish_exclusive(output, (json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    except Exception:
        archive.unlink(missing_ok=True)
        raise
    print(f"wrote change-control manifest: {output}")
    print(f"manifest_sha256={file_hash(output)}")
    return 0


def check(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).resolve()
    try:
        verify_manifest_digest(manifest_path, args.manifest_sha256)
        manifest = load_manifest(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    root = Path(args.skill_path).resolve()
    if str(root) != manifest.get("skill_root"):
        print("skill root does not match the confirmed manifest", file=sys.stderr)
        return 2
    before = manifest["baseline_files"]
    try:
        after = collect(root)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    changed = sorted(set(before) | set(after))
    changed = [path for path in changed if before.get(path) != after.get(path)]
    allowed = set(manifest["allowed_paths"])
    unexpected = [path for path in changed if path not in allowed]
    if unexpected:
        print("unexpected changed paths:", file=sys.stderr)
        for path in unexpected:
            print(f"  {path}", file=sys.stderr)
        return 1
    try:
        if manifest.get("git_root"):
            repo = Path(manifest["git_root"]).resolve()
            exclusions = [contained_path(root, item) for item in manifest["allowed_paths"]]
            exclusions.extend(Path(item) for item in manifest["ledger_paths"])
            exclusions.extend([manifest_path, Path(manifest["baseline_archive"]).resolve()])
            if repo_state_hash(repo, exclusions) != manifest.get("baseline_repo_state_sha256"):
                print("git index or non-allowlisted worktree state changed after snapshot", file=sys.stderr)
                return 1
        state_hash = allowed_state_hash(root, manifest["allowed_paths"], manifest["ledger_paths"])
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    expected_state = getattr(args, "expected_state", None)
    if expected_state and state_hash != expected_state:
        print("allowlisted or ledger state changed after the caller's last check", file=sys.stderr)
        return 2
    print(f"change-control ok: {len(changed)} changed path(s), all allowlisted")
    print(f"current_state_sha256={state_hash}")
    return 0


def verify_readonly(args: argparse.Namespace) -> int:
    try:
        current_state = readonly_state_hash(Path(args.root))
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    if args.expected_state and current_state != args.expected_state:
        print("read-only state changed", file=sys.stderr)
        print(f"current_state_sha256={current_state}", file=sys.stderr)
        return 1
    print(f"current_state_sha256={current_state}")
    return 0


def append_ledger(args: argparse.Namespace) -> int:
    """Recheck and append one ledger row under a cooperative cross-process lock."""
    manifest_path = Path(args.manifest).resolve()
    try:
        verify_manifest_digest(manifest_path, args.manifest_sha256)
        manifest = load_manifest(manifest_path)
        ledger = validate_external_file_path(Path(args.ledger), allow_missing=True)
        if str(ledger) not in manifest["ledger_paths"]:
            raise ValueError("ledger is not in the confirmed manifest")
        lock_name = hashlib.sha256(str(ledger).encode("utf-8")).hexdigest() + ".lock"
        lock_path = Path(tempfile.gettempdir()) / f"skill-ledger-{lock_name}"
        lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        print("ledger is locked by another writer", file=sys.stderr)
        return 2
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2

    try:
        os.close(lock_fd)
        check_args = argparse.Namespace(
            manifest=str(manifest_path),
            manifest_sha256=args.manifest_sha256,
            skill_path=args.skill_path,
            expected_state=args.expected_state,
        )
        if check(check_args) != 0:
            return 2
        ledger.parent.mkdir(parents=True, exist_ok=True)
        validate_external_file_path(ledger, allow_missing=True)
        row = args.line.rstrip("\r\n") + "\n"
        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        ledger_fd = os.open(str(ledger), flags, 0o600)
        opened_stat = os.fstat(ledger_fd)
        path_stat = os.stat(ledger, follow_symlinks=False)
        if opened_stat.st_nlink != 1 or (opened_stat.st_dev, opened_stat.st_ino) != (path_stat.st_dev, path_stat.st_ino):
            os.close(ledger_fd)
            raise ValueError("ledger changed identity or became hard-linked during append")
        with os.fdopen(ledger_fd, "ab") as handle:
            handle.write(row.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        state_hash = allowed_state_hash(
            Path(args.skill_path).resolve(), manifest["allowed_paths"], manifest["ledger_paths"]
        )
        print(f"current_state_sha256={state_hash}")
        return 0
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    finally:
        lock_path.unlink(missing_ok=True)


def restore(args: argparse.Namespace) -> int:
    if not args.confirm:
        print("refusing to restore without --confirm", file=sys.stderr)
        return 2
    manifest_path = Path(args.manifest).resolve()
    try:
        verify_manifest_digest(manifest_path, args.manifest_sha256)
        manifest = load_manifest(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    root = Path(args.skill_path).resolve()
    if str(root) != manifest.get("skill_root"):
        print("skill root does not match the confirmed manifest", file=sys.stderr)
        return 2
    try:
        current_state = allowed_state_hash(root, manifest["allowed_paths"], manifest["ledger_paths"])
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    if current_state != args.expected_state:
        print("current allowlisted state changed after confirmation; refusing restore", file=sys.stderr)
        return 2
    if manifest.get("git_root"):
        repo = Path(manifest["git_root"]).resolve()
        exclusions = [contained_path(root, item) for item in manifest["allowed_paths"]]
        exclusions.extend(Path(item) for item in manifest["ledger_paths"])
        exclusions.extend([manifest_path, Path(manifest["baseline_archive"]).resolve()])
        if repo_state_hash(repo, exclusions) != manifest.get("baseline_repo_state_sha256"):
            print("git index or non-allowlisted worktree state changed after snapshot; refusing restore", file=sys.stderr)
            return 2
    archive = Path(manifest["baseline_archive"]).resolve()
    if archive.parent != manifest_path.parent:
        print("baseline archive must be beside the manifest", file=sys.stderr)
        return 2
    if not archive.is_file():
        print(f"baseline archive not found: {archive}", file=sys.stderr)
        return 2
    if file_hash(archive) != manifest.get("baseline_archive_sha256"):
        print("baseline archive hash does not match the manifest", file=sys.stderr)
        return 2
    allowed = set(manifest["allowed_paths"])
    baseline = manifest["baseline_allowed_files"]
    if not manifest["skill_root_existed"]:
        try:
            unexpected = unexpected_missing_target_entries(root, allowed)
        except (OSError, ValueError) as error:
            print(str(error), file=sys.stderr)
            return 2
        if unexpected:
            print("missing-target skill contains non-allowlisted files; refusing restore", file=sys.stderr)
            for relative in unexpected:
                print(f"  {relative}", file=sys.stderr)
            return 2
    with tempfile.TemporaryDirectory(prefix="skill-restore-") as temp_dir:
        staging = Path(temp_dir)
        with zipfile.ZipFile(archive) as bundle:
            members = {normalize_relative(member.filename): member for member in bundle.infolist() if not member.is_dir()}
            if set(members) != set(baseline):
                raise ValueError("baseline archive members do not match the confirmed allowlist snapshot")
            for member in bundle.infolist():
                target = (staging / member.filename).resolve()
                if staging not in target.parents:
                    raise ValueError(f"unsafe path in baseline archive: {member.filename}")
            bundle.extractall(staging)
        for relative in allowed:
            target = contained_path(root, relative)
            if relative not in baseline:
                if target.is_dir():
                    raise ValueError(f"allowlisted file path is now a directory: {relative}")
                target.unlink(missing_ok=True)
                continue
            source = contained_path(staging, relative)
            if file_hash(source) != baseline[relative]:
                raise ValueError(f"baseline file hash mismatch: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
                temp_target = Path(handle.name)
            try:
                shutil.copy2(source, temp_target)
                os.replace(temp_target, target)
            finally:
                temp_target.unlink(missing_ok=True)
    if not manifest["skill_root_existed"]:
        directories = {root}
        for relative in allowed:
            parent = (root / normalize_relative(relative)).parent
            while parent != root.parent:
                directories.add(parent)
                if parent == root:
                    break
                parent = parent.parent
        for directory in sorted(directories, key=lambda item: len(item.parts), reverse=True):
            try:
                directory.rmdir()
            except FileNotFoundError:
                pass
            except OSError:
                # A non-empty directory is outside the allowlisted restore scope.
                pass
        if root.exists():
            print("missing-target restore left the skill root in place", file=sys.stderr)
            return 2
    print(f"restored confirmed baseline: {root}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    snap = subparsers.add_parser("snapshot")
    snap.add_argument("--skill-path", required=True)
    snap.add_argument("--manifest", required=True)
    snap.add_argument("--allow", action="append", required=True)
    snap.add_argument("--ledger", action="append", help="Session ledger path guarded against concurrent changes")
    snap.add_argument(
        "--allow-missing-target",
        action="store_true",
        help="Snapshot an explicitly confirmed new skill path before its directory or SKILL.md exists",
    )
    snap.add_argument("--confirm", action="store_true")
    snap.set_defaults(func=snapshot)

    verify = subparsers.add_parser("check")
    verify.add_argument("--skill-path", required=True)
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--manifest-sha256", required=True, help="Digest printed by snapshot")
    verify.add_argument("--expected-state", help="Fail if allowlisted files or ledgers changed since this state hash")
    verify.set_defaults(func=check)

    rollback = subparsers.add_parser("restore")
    rollback.add_argument("--skill-path", required=True)
    rollback.add_argument("--manifest", required=True)
    rollback.add_argument("--manifest-sha256", required=True, help="Digest printed by snapshot")
    rollback.add_argument("--confirm", action="store_true")
    rollback.add_argument("--expected-state", required=True, help="current_state_sha256 printed by the latest check")
    rollback.set_defaults(func=restore)

    readonly = subparsers.add_parser("readonly", help="Fingerprint or verify a read-only tree without writing artifacts")
    readonly.add_argument("--root", required=True)
    readonly.add_argument("--expected-state")
    readonly.set_defaults(func=verify_readonly)

    append = subparsers.add_parser("append-ledger", help="Atomically guard and append one session-ledger row")
    append.add_argument("--skill-path", required=True)
    append.add_argument("--manifest", required=True)
    append.add_argument("--manifest-sha256", required=True)
    append.add_argument("--ledger", required=True)
    append.add_argument("--expected-state", required=True)
    append.add_argument("--line", required=True)
    append.set_defaults(func=append_ledger)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
