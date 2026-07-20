#!/usr/bin/env python3
"""
Skill Packager - Creates a distributable .skill file of a skill folder

Usage:
    python scripts/package_skill.py <path/to/skill-folder> [output-directory] --confirm

Example:
    python scripts/package_skill.py skills/public/my-skill --confirm
    python scripts/package_skill.py skills/public/my-skill ./dist --confirm
"""

import argparse
import fnmatch
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.quick_validate import validate_skill

# Patterns to exclude when packaging skills.
EXCLUDE_DIRS = {"__pycache__", "node_modules"}
EXCLUDE_GLOBS = {"*.pyc"}
EXCLUDE_FILES = {".DS_Store"}
# Directories excluded only at the skill root (not when nested deeper).
ROOT_EXCLUDE_DIRS = {"evals"}
ROOT_EXCLUDE_FILES = {"test-prompts.json", "history.json"}
ROOT_INCLUDE_DIRS = {"agents", "assets", "references", "scripts"}
ROOT_INCLUDE_FILES = {"SKILL.md", "LICENSE", "LICENSE.md", "README.md"}
SECRET_FILE_GLOBS = {
    ".env",
    ".env.*",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.pem",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "secrets.json",
}
RAW_ARTIFACT_GLOBS = {
    "*.har",
    "*.heapsnapshot",
    "*.log",
    "*.pcap",
    "*.pcapng",
    "*.trace",
    "benchmark.json",
    "benchmark.md",
    "eval-results.json",
    "eval_results.json",
    "feedback.json",
    "eval_metadata.json",
    "grading.json",
    "history.json",
    "results.json",
    "timing.json",
    "transcript.md",
    "transcript.json",
    "review_manifest.json",
}
SECRET_PATTERNS = (
    ("private key", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("API token", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    (
        "credential assignment",
        re.compile(
            r"(?im)^\s*(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|"
            r"password|secret[_-]?key)\s*[:=]\s*[\"']?([^\s\"'#]{8,})"
        ),
    ),
    ("authorization header", re.compile(r"(?im)^\s*(?:authorization|proxy-authorization)\s*:\s*\S+")),
    ("cookie header", re.compile(r"(?im)^\s*(?:cookie|set-cookie)\s*:\s*\S+")),
)
PLACEHOLDER_MARKERS = (
    "example",
    "placeholder",
    "redacted",
    "changeme",
    "your_",
    "${",
    "{{",
    "os.environ",
    "getenv(",
)


def is_reparse_point(path: Path) -> bool:
    try:
        attributes = getattr(os.stat(path, follow_symlinks=False), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    return bool(attributes & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT


def should_exclude(rel_path: Path) -> bool:
    """Check if a path should be excluded from packaging."""
    parts = rel_path.parts
    if any(part in EXCLUDE_DIRS for part in parts):
        return True
    # rel_path is relative to skill_path.parent, so parts[0] is the skill
    # folder name and parts[1] (if present) is the first subdir.
    if len(parts) > 1 and parts[1] in ROOT_EXCLUDE_DIRS:
        return True
    if len(parts) > 1:
        top_level = parts[1]
        if top_level not in ROOT_INCLUDE_DIRS and top_level not in ROOT_INCLUDE_FILES:
            return True
    name = rel_path.name
    if name in EXCLUDE_FILES:
        return True
    if len(parts) == 2 and parts[1] in ROOT_EXCLUDE_FILES:
        return True
    return any(fnmatch.fnmatch(name, pat) for pat in EXCLUDE_GLOBS)


def _matches_any(name: str, patterns) -> bool:
    lowered = name.lower()
    return any(fnmatch.fnmatch(lowered, pattern) for pattern in patterns)


def scan_package_file(file_path: Path, arcname: Path, data=None):
    """Return a package-safety error for one file, or None when safe."""
    if _matches_any(file_path.name, SECRET_FILE_GLOBS):
        return f"secret-bearing filename: {arcname}"
    if _matches_any(file_path.name, RAW_ARTIFACT_GLOBS):
        return f"raw evaluation/capture artifact: {arcname}"

    data = file_path.read_bytes() if data is None else data
    decoded_candidates = [data.decode("utf-8", errors="ignore")]
    if b"\x00" in data[:4096]:
        decoded_candidates.extend([
            data.decode("utf-16-le", errors="ignore"),
            data.decode("utf-16-be", errors="ignore"),
        ])
    for text in decoded_candidates:
        for label, pattern in SECRET_PATTERNS:
            match = pattern.search(text)
            if not match:
                continue
            if label == "credential assignment":
                value = match.group(1).lower()
                if any(marker in value for marker in PLACEHOLDER_MARKERS):
                    continue
            return f"possible {label}: {arcname}"
    return None


def collect_package_files(skill_path: Path):
    """Collect and scan every regular file that would enter the archive."""
    files = []
    for current, directories, filenames in os.walk(skill_path, topdown=True, followlinks=False):
        current_path = Path(current)
        if current_path.is_symlink() or is_reparse_point(current_path):
            raise ValueError(f"reparse point is not allowed in package input: {current_path}")
        for directory in list(directories):
            candidate = current_path / directory
            if candidate.is_symlink() or is_reparse_point(candidate):
                raise ValueError(f"reparse point is not allowed in package input: {candidate}")
        for filename in filenames:
            file_path = current_path / filename
            if file_path.is_symlink() or is_reparse_point(file_path):
                raise ValueError(f"reparse point is not allowed in package input: {file_path}")
            stat_result = os.stat(file_path, follow_symlinks=False)
            if stat_result.st_nlink != 1:
                raise ValueError(f"hard-linked file is not allowed in package input: {file_path}")
            arcname = file_path.relative_to(skill_path.parent)
            if should_exclude(arcname):
                print(f"  Skipped: {arcname}")
                continue
            data = file_path.read_bytes()
            after = os.stat(file_path, follow_symlinks=False)
            if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (
                stat_result.st_dev, stat_result.st_ino, stat_result.st_size, stat_result.st_mtime_ns
            ):
                raise ValueError(f"file changed during package scan: {file_path}")
            safety_error = scan_package_file(file_path, arcname, data)
            if safety_error:
                raise ValueError(safety_error)
            files.append((arcname, data))
    return files


def package_skill(skill_path, output_dir=None):
    """
    Package a skill folder into a .skill file.

    Args:
        skill_path: Path to the skill folder
        output_dir: Optional output directory for the .skill file (defaults to current directory)

    Returns:
        Path to the created .skill file, or None if error
    """
    requested_skill_path = Path(skill_path).absolute()
    if requested_skill_path.is_symlink() or is_reparse_point(requested_skill_path):
        print(f"Error: reparse-point skill root is not allowed: {requested_skill_path}")
        return None
    skill_path = requested_skill_path.resolve()

    # Validate skill folder exists
    if not skill_path.exists():
        print(f"Error: Skill folder not found: {skill_path}")
        return None

    if not skill_path.is_dir():
        print(f"Error: Path is not a directory: {skill_path}")
        return None

    # Validate SKILL.md exists
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        print(f"Error: SKILL.md not found in {skill_path}")
        return None

    # Run validation before packaging
    print("Validating skill...")
    valid, message = validate_skill(skill_path)
    if not valid:
        print(f"Validation failed: {message}")
        print("Please fix the validation errors before packaging.")
        return None
    print(f"{message}\n")

    try:
        package_files = collect_package_files(skill_path)
    except Exception as e:
        print(f"Package safety scan failed: {e}")
        return None

    # Determine output location
    skill_name = skill_path.name
    if output_dir:
        output_path = Path(output_dir).resolve()
    else:
        output_path = Path.cwd()

    if output_path == skill_path or skill_path in output_path.parents:
        print("Error: output directory must not be inside the skill directory")
        return None
    output_path.mkdir(parents=True, exist_ok=True)

    skill_filename = output_path / f"{skill_name}.skill"
    if skill_filename.exists():
        print(f"Error: refusing to overwrite existing archive: {skill_filename}")
        return None

    # Create the .skill file (zip format)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{skill_name}.", suffix=".tmp", dir=output_path, delete=False
        ) as temp_file:
            temp_name = Path(temp_file.name)
        with zipfile.ZipFile(temp_name, "w", zipfile.ZIP_DEFLATED) as zipf:
            for arcname, data in package_files:
                zipf.writestr(str(arcname).replace("\\", "/"), data)
                print(f"  Added: {arcname}")

        os.link(temp_name, skill_filename)
        temp_name.unlink()

        print(f"\nSuccessfully packaged skill to: {skill_filename}")
        return skill_filename

    except Exception as e:
        if temp_name and temp_name.exists():
            temp_name.unlink()
        print(f"Error creating .skill file: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Validate and package an OpenCode skill")
    parser.add_argument("skill_path")
    parser.add_argument("output_dir", nargs="?", default=None)
    parser.add_argument("--confirm", action="store_true", help="Confirm creation of the package artifact")
    args = parser.parse_args()
    if not args.confirm:
        print("Error: refusing to create a package without --confirm")
        sys.exit(2)

    skill_path = args.skill_path
    output_dir = args.output_dir

    print(f"Packaging skill: {skill_path}")
    if output_dir:
        print(f"Output directory: {output_dir}")
    print()

    result = package_skill(skill_path, output_dir)

    if result:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
