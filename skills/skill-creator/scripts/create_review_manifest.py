#!/usr/bin/env python3
"""Create an integrity manifest for an independently reviewed benchmark run."""

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_manifest(run_dir: Path, reviewer: str) -> Path:
    run_dir = run_dir.resolve()
    grading = run_dir / "grading.json"
    transcript = run_dir / "transcript.md"
    outputs = run_dir / "outputs"
    metadata = next(
        (parent / "eval_metadata.json" for parent in [run_dir, *run_dir.parents] if (parent / "eval_metadata.json").is_file()),
        None,
    )
    if metadata is None:
        raise ValueError(f"eval_metadata.json not found above run directory: {run_dir}")
    for required in (grading, transcript, metadata):
        if required.is_symlink() or not required.is_file():
            raise ValueError(f"required regular file missing: {required}")
    eval_metadata = json.loads(metadata.read_text(encoding="utf-8"))
    executor_id = eval_metadata.get("executor_id")
    if (
        not isinstance(executor_id, str)
        or not executor_id.strip()
        or not reviewer.strip()
        or reviewer.strip().casefold() == executor_id.strip().casefold()
    ):
        raise ValueError("reviewer must be non-empty and independent from executor_id")

    artifacts = [
        {"path": "transcript.md", "role": "transcript", "sha256": file_sha256(transcript)}
    ]
    if outputs.is_symlink() or not outputs.is_dir():
        raise ValueError(f"outputs directory missing or unsafe: {outputs}")
    for path in sorted(outputs.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlink is not allowed in reviewed outputs: {path}")
        if path.is_file():
            artifacts.append({
                "path": str(path.relative_to(run_dir)).replace("\\", "/"),
                "role": "output",
                "sha256": file_sha256(path),
            })
    if len(artifacts) == 1:
        raise ValueError("reviewed outputs directory contains no files")
    timing = run_dir / "timing.json"
    if timing.exists():
        if timing.is_symlink() or not timing.is_file():
            raise ValueError(f"timing evidence is unsafe: {timing}")
        artifacts.append({"path": "timing.json", "role": "timing", "sha256": file_sha256(timing)})

    payload = {
        "schema_version": 1,
        "reviewer": reviewer.strip(),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "grading_sha256": file_sha256(grading),
        "eval_metadata_sha256": file_sha256(metadata),
        "artifacts": artifacts,
    }
    destination = run_dir / "review_manifest.json"
    if destination.exists():
        raise ValueError(f"refusing to overwrite review manifest: {destination}")
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=run_dir, delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir")
    parser.add_argument("--reviewer", required=True, help="Independent grader/model identifier")
    parser.add_argument("--confirm", action="store_true", help="Acknowledge creation of the review artifact")
    args = parser.parse_args()
    if not args.confirm:
        parser.error("--confirm is required")
    try:
        print(create_manifest(Path(args.run_dir), args.reviewer))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
