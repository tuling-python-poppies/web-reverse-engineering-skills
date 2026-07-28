#!/usr/bin/env python3
"""Validate local Markdown links and heading anchors."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#", "<http://", "<https://")


def slug(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"[^\w\s\-\u4e00-\u9fff]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")


def anchors(path: Path) -> set[str]:
    found: set[str] = set()
    seen: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = HEADING.match(line)
        if not match:
            continue
        base = slug(match.group(2))
        count = seen.get(base, 0)
        seen[base] = count + 1
        found.add(base if count == 0 else f"{base}-{count}")
    return found


def split_target(raw: str) -> tuple[str, str]:
    target = raw.strip().strip("<>")
    path, _, anchor = target.partition("#")
    return path, anchor


def validate_file(path: Path) -> list[str]:
    findings: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for match in LINK.finditer(text):
        raw = match.group(1).strip()
        if raw.startswith(SKIP_PREFIXES):
            continue
        target_path, target_anchor = split_target(raw)
        if target_path and not (
            target_path.startswith(("./", "../", "/"))
            or "/" in target_path
            or "." in Path(target_path).name
        ):
            continue
        if target_path and re.search(r"[\s,]", target_path):
            continue
        if not target_path:
            target_file = path
        else:
            target_file = (path.parent / target_path).resolve()
        try:
            target_file.relative_to(ROOT.resolve())
        except ValueError:
            findings.append(f"{path.relative_to(ROOT).as_posix()}: link escapes skill root: {raw}")
            continue
        if not target_file.exists():
            findings.append(f"{path.relative_to(ROOT).as_posix()}: missing link target: {raw}")
            continue
        if target_anchor and target_file.suffix.lower() == ".md":
            target_anchors = anchors(target_file)
            if target_anchor not in target_anchors:
                findings.append(f"{path.relative_to(ROOT).as_posix()}: missing anchor {raw}")
    return findings


def main() -> int:
    findings: list[str] = []
    for path in sorted(ROOT.rglob("*.md")):
        if set(path.parts) & {"__pycache__", ".pytest_cache"}:
            continue
        findings.extend(validate_file(path))
    print("== markdown links ==")
    if findings:
        for finding in findings:
            print(f"FAIL {finding}")
        print(f"summary: failures={len(findings)}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
