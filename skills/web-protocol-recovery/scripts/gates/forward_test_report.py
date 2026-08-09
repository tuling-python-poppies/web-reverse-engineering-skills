#!/usr/bin/env python3
"""Validate an externally produced WPR fresh-agent forward-test report."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[2]
SUITE_PATH = SKILL_ROOT / "references" / "official-self-test-task-suite.md"
SKILL_PATH = SKILL_ROOT / "SKILL.md"
MAX_REPORT_BYTES = 2 * 1024 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_PACKAGE_FILE_BYTES = 256 * 1024 * 1024
MAX_PACKAGE_BYTES = 1024 * 1024 * 1024
MIN_RATIONALE_CHARS = 12
MIN_QUOTE_CHARS = 8
PACKAGE_IGNORED_PARTS = frozenset({".git", ".pytest_cache", "__pycache__"})
SEMANTIC_STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "be", "by", "do", "does", "for", "from",
        "in", "is", "it", "must", "not", "of", "on", "or", "only", "that", "the",
        "this", "to", "use", "with", "should", "require", "prove", "keep", "same",
        "first", "current", "local", "one", "response", "request", "evidence",
        "protocol", "success", "failure", "result", "field", "body", "route",
    }
)
WINDOWS_RESERVED_NAMES = frozenset(
    {"AUX", "CON", "NUL", "PRN", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
)
TASK_RE = re.compile(
    r"^## (?P<heading>Task [^\r\n]+)\r?\n(?P<body>.*?)(?=^## Task |^## Failure signals|\Z)",
    re.MULTILINE | re.DOTALL,
)
PROMPT_RE = re.compile(r"Prompt:\s*```text\s*(?P<prompt>.*?)\s*```", re.DOTALL)
ROUTES_RE = re.compile(r"Expected route:\s*(?P<body>.*?)(?=\nMust conclude:)", re.DOTALL)
CONCLUSIONS_RE = re.compile(r"Must conclude:\s*(?P<body>.*?)(?=\n## |\Z)", re.DOTALL)
BULLET_RE = re.compile(r"^- (.+)$", re.MULTILINE)


class ForwardTestError(ValueError):
    """Raised when a report artifact cannot be inspected safely."""


@dataclass(frozen=True)
class SuiteTask:
    heading: str
    prompt: str
    routes: tuple[str, ...]
    conclusions: tuple[str, ...]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _is_reparse(metadata: os.stat_result) -> bool:
    return bool(
        getattr(metadata, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _read_plain_file(path: Path, *, label: str, max_bytes: int) -> tuple[bytes, tuple[int, int]]:
    try:
        absolute = Path(os.path.abspath(path))
    except (OSError, ValueError) as exc:
        raise ForwardTestError(f"{label}: invalid path") from exc
    current = absolute
    while True:
        try:
            metadata = os.lstat(current)
        except (OSError, ValueError) as exc:
            raise ForwardTestError(f"{label}: cannot inspect path") from exc
        if stat.S_ISLNK(metadata.st_mode) or _is_reparse(metadata):
            raise ForwardTestError(f"{label}: symlink or reparse-point paths are not allowed")
        if current.parent == current:
            break
        current = current.parent

    try:
        metadata = os.lstat(absolute)
    except (OSError, ValueError) as exc:
        raise ForwardTestError(f"{label}: cannot inspect file") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise ForwardTestError(f"{label}: expected a regular file")
    if metadata.st_nlink != 1:
        raise ForwardTestError(f"{label}: hard-linked files are not allowed")
    if metadata.st_size > max_bytes:
        raise ForwardTestError(f"{label}: input exceeds {max_bytes} bytes")
    try:
        payload = absolute.read_bytes()
    except (OSError, ValueError) as exc:
        raise ForwardTestError(f"{label}: read failed") from exc
    try:
        after = os.lstat(absolute)
    except (OSError, ValueError) as exc:
        raise ForwardTestError(f"{label}: cannot re-inspect file") from exc
    if (
        metadata.st_dev != after.st_dev
        or metadata.st_ino != after.st_ino
        or metadata.st_size != after.st_size
        or len(payload) != after.st_size
    ):
        raise ForwardTestError(f"{label}: file changed during read")
    return payload, (int(after.st_dev), int(after.st_ino))


def _decode_utf8(payload: bytes, *, label: str) -> str:
    try:
        return payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ForwardTestError(f"{label}: input is not valid UTF-8") from exc


def _response_relative_path(raw_path: str) -> PurePosixPath:
    if any(
        ord(character) < 32
        or ord(character) == 127
        or 0xD800 <= ord(character) <= 0xDFFF
        for character in raw_path
    ):
        raise ForwardTestError("response path contains control or surrogate characters")
    relative = PurePosixPath(raw_path)
    if relative.is_absolute() or not relative.parts or relative.parts[0] != "responses":
        raise ForwardTestError("response path must stay under responses/")
    for part in relative.parts:
        stem = part.split(".", 1)[0].upper()
        if (
            part in {".", ".."}
            or "\\" in part
            or ":" in part
            or part.endswith((".", " "))
            or stem in WINDOWS_RESERVED_NAMES
        ):
            raise ForwardTestError("response path contains an unsafe component")
    return relative


def _semantic_terms(text: str) -> set[str]:
    words = {
        token.lower()
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}|\b\d{2,}\b", text)
    }
    words.difference_update(SEMANTIC_STOPWORDS)
    cjk = re.findall(r"[\u3400-\u9fff]{2,}", text)
    bigrams = {part[index : index + 2] for part in cjk for index in range(len(part) - 1)}
    return words | bigrams


def _conclusion_quote_has_signal(expected: str, quote: str) -> bool:
    expected_terms = _semantic_terms(expected)
    quote_terms = _semantic_terms(quote)
    overlap = expected_terms & quote_terms
    required = 1 if len(expected_terms) <= 3 else 2
    return bool(expected_terms) and len(overlap) >= required


def _bullet_values(section: str, *, unwrap_code: bool) -> tuple[str, ...]:
    values: list[str] = []
    for match in BULLET_RE.finditer(section):
        value = match.group(1).strip()
        if unwrap_code and len(value) >= 2 and value.startswith("`") and value.endswith("`"):
            value = value[1:-1]
        values.append(value)
    return tuple(values)


def parse_suite(text: str) -> tuple[SuiteTask, ...]:
    tasks: list[SuiteTask] = []
    for match in TASK_RE.finditer(text):
        body = match.group("body")
        prompt_match = PROMPT_RE.search(body)
        routes_match = ROUTES_RE.search(body)
        conclusions_match = CONCLUSIONS_RE.search(body)
        if not prompt_match or not routes_match or not conclusions_match:
            raise ForwardTestError(f"suite task is incomplete: {match.group('heading')}")
        routes = _bullet_values(routes_match.group("body"), unwrap_code=True)
        conclusions = _bullet_values(conclusions_match.group("body"), unwrap_code=False)
        if not routes or not conclusions:
            raise ForwardTestError(f"suite task has empty expectations: {match.group('heading')}")
        tasks.append(
            SuiteTask(
                heading=match.group("heading"),
                prompt=prompt_match.group("prompt").strip(),
                routes=routes,
                conclusions=conclusions,
            )
        )
    if not tasks or len({task.heading for task in tasks}) != len(tasks):
        raise ForwardTestError("suite has no tasks or duplicate headings")
    return tuple(tasks)


def suite_contract(tasks: tuple[SuiteTask, ...]) -> str:
    payload = [
        {
            "heading": task.heading,
            "prompt": task.prompt,
            "routes": task.routes,
            "conclusions": task.conclusions,
        }
        for task in tasks
    ]
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(encoded)


def package_contract() -> str:
    digest = hashlib.sha256(b"WPR-PACKAGE-v1\0")
    total_bytes = 0
    files = sorted(
        (path for path in SKILL_ROOT.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(SKILL_ROOT).as_posix(),
    )
    for path in files:
        relative = path.relative_to(SKILL_ROOT)
        if set(relative.parts) & PACKAGE_IGNORED_PARTS or path.suffix.lower() in {".pyc", ".pyo"}:
            continue
        payload, _ = _read_plain_file(
            path,
            label=f"package file {relative.as_posix()}",
            max_bytes=MAX_PACKAGE_FILE_BYTES,
        )
        total_bytes += len(payload)
        if total_bytes > MAX_PACKAGE_BYTES:
            raise ForwardTestError("skill package exceeds bounded hash limit")
        relative_bytes = relative.as_posix().encode("utf-8")
        digest.update(len(relative_bytes).to_bytes(4, "big"))
        digest.update(relative_bytes)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


@lru_cache(maxsize=1)
def current_contract() -> dict[str, Any]:
    suite_payload, _ = _read_plain_file(SUITE_PATH, label="official suite", max_bytes=MAX_REPORT_BYTES)
    skill_payload, _ = _read_plain_file(SKILL_PATH, label="SKILL.md", max_bytes=MAX_REPORT_BYTES)
    tasks = parse_suite(_decode_utf8(suite_payload, label="official suite"))
    return {
        "suite": {
            "path": "references/official-self-test-task-suite.md",
            "contract_sha256": suite_contract(tasks),
            "task_count": len(tasks),
        },
        "skill": {
            "path": "SKILL.md",
            "sha256": sha256_bytes(skill_payload),
            "package_sha256": package_contract(),
        },
    }


def _check_review_rows(
    rows: Any,
    expected: tuple[str, ...],
    response_text: str,
    *,
    kind: str,
    errors: list[str],
) -> None:
    if not isinstance(rows, list) or len(rows) != len(expected):
        errors.append(f"{kind}: expected {len(expected)} review rows")
        return
    for index, expected_value in enumerate(expected):
        row = rows[index]
        label = f"{kind}[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label}: expected object")
            continue
        if row.get("expected") != expected_value:
            errors.append(f"{label}: expected value mismatch")
        if row.get("passed") is not True:
            errors.append(f"{label}: passed must be true")
        rationale = row.get("rationale")
        rationale_text = rationale.strip() if isinstance(rationale, str) else ""
        if not isinstance(rationale, str) or len(rationale.strip()) < MIN_RATIONALE_CHARS:
            errors.append(f"{label}: rationale is too short")
        evidence = row.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{label}: evidence is required")
            continue
        valid_span = False
        for span in evidence:
            if not isinstance(span, dict):
                continue
            quote = span.get("quote")
            start = span.get("start")
            end = span.get("end")
            if (
                isinstance(quote, str)
                and isinstance(start, int)
                and isinstance(end, int)
                and 0 <= start < end <= len(response_text)
                and response_text[start:end] == quote
                and len(quote.strip()) >= MIN_QUOTE_CHARS
                and (
                    (kind == "routes" and expected_value in quote)
                    or (
                        kind == "conclusions"
                        and expected_value in rationale_text
                        and quote.strip() in rationale_text
                        and _conclusion_quote_has_signal(expected_value, quote)
                    )
                )
            ):
                valid_span = True
                break
        if not valid_span:
            errors.append(f"{label}: no valid verbatim evidence span")


def validate_report(report_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    report_payload, _ = _read_plain_file(report_path, label="report", max_bytes=MAX_REPORT_BYTES)
    try:
        document = json.loads(_decode_utf8(report_payload, label="report"))
    except json.JSONDecodeError as exc:
        raise ForwardTestError("report: invalid JSON") from exc
    if not isinstance(document, dict):
        raise ForwardTestError("report: root must be an object")

    report_dir = Path(os.path.abspath(report_path)).parent
    try:
        report_dir.resolve().relative_to(SKILL_ROOT.resolve())
    except ValueError:
        pass
    else:
        errors.append("report directory must stay outside the skill root")

    contract = current_contract()
    suite_payload, _ = _read_plain_file(SUITE_PATH, label="official suite", max_bytes=MAX_REPORT_BYTES)
    tasks = parse_suite(_decode_utf8(suite_payload, label="official suite"))
    by_heading = {task.heading: task for task in tasks}

    if document.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if document.get("suite") != contract["suite"]:
        errors.append("suite contract does not match current official suite")
    if document.get("skill") != contract["skill"]:
        errors.append("skill contract does not match current SKILL.md")

    runner = document.get("runner")
    reviewer = document.get("reviewer")
    for label, agent in (("runner", runner), ("reviewer", reviewer)):
        if not isinstance(agent, dict):
            errors.append(f"{label}: object required")
            continue
        if not isinstance(agent.get("id"), str) or not agent["id"].strip():
            errors.append(f"{label}: non-empty id required")
        if agent.get("fresh_context") is not True or agent.get("independent") is not True:
            errors.append(f"{label}: fresh_context and independent must be true")
    if isinstance(runner, dict) and isinstance(reviewer, dict) and runner.get("id") == reviewer.get("id"):
        errors.append("runner and reviewer ids must differ")

    scope = document.get("scope")
    items = document.get("items")
    if not isinstance(scope, dict) or scope.get("kind") not in {"smoke", "full"}:
        errors.append("scope.kind must be smoke or full")
    if not isinstance(items, list) or not items:
        errors.append("items must be a non-empty list")
        items = []
    if isinstance(scope, dict) and scope.get("task_count") != len(items):
        errors.append("scope.task_count must equal item count")

    seen_headings: set[str] = set()
    seen_files: set[tuple[int, int]] = set()
    total_response_bytes = 0
    for index, item in enumerate(items):
        label = f"items[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: expected object")
            continue
        heading = item.get("heading")
        if not isinstance(heading, str) or heading not in by_heading:
            errors.append(f"{label}: unknown heading")
            continue
        task = by_heading[heading]
        if heading in seen_headings:
            errors.append(f"{label}: duplicate heading")
        seen_headings.add(heading)
        if item.get("prompt_sha256") != sha256_bytes(task.prompt.encode("utf-8")):
            errors.append(f"{label}: prompt hash mismatch")

        response = item.get("response")
        raw_path = response.get("path") if isinstance(response, dict) else None
        if not isinstance(raw_path, str):
            errors.append(f"{label}: response.path required")
            continue
        try:
            relative = _response_relative_path(raw_path)
        except ForwardTestError as exc:
            errors.append(f"{label}: {exc}")
            continue
        response_path = report_dir.joinpath(*relative.parts)
        try:
            response_payload, identity = _read_plain_file(
                response_path,
                label=f"{label} response",
                max_bytes=MAX_RESPONSE_BYTES,
            )
            response_text = _decode_utf8(response_payload, label=f"{label} response")
        except ForwardTestError as exc:
            errors.append(str(exc))
            continue
        total_response_bytes += len(response_payload)
        if identity in seen_files:
            errors.append(f"{label}: response file reused")
        seen_files.add(identity)
        if not isinstance(response, dict) or response.get("sha256") != sha256_bytes(response_payload):
            errors.append(f"{label}: response hash mismatch")

        review = item.get("review")
        if not isinstance(review, dict):
            errors.append(f"{label}: review object required")
            continue
        if review.get("passed") is not True:
            errors.append(f"{label}: review.passed must be true")
        if not isinstance(reviewer, dict) or review.get("reviewer_id") != reviewer.get("id"):
            errors.append(f"{label}: reviewer_id mismatch")
        _check_review_rows(review.get("routes"), task.routes, response_text, kind="routes", errors=errors)
        _check_review_rows(
            review.get("conclusions"),
            task.conclusions,
            response_text,
            kind="conclusions",
            errors=errors,
        )

    if total_response_bytes > MAX_TOTAL_RESPONSE_BYTES:
        errors.append("aggregate response bytes exceed limit")
    scope_kind = scope.get("kind") if isinstance(scope, dict) else None
    if scope_kind == "full" and [item.get("heading") for item in items if isinstance(item, dict)] != [task.heading for task in tasks]:
        errors.append("full scope requires every official task exactly once in order")

    valid = not errors
    return {
        "valid": valid,
        "scope": scope_kind,
        "reported_items": len(items),
        "official_tasks": len(tasks),
        "full_pass": valid and scope_kind == "full" and len(items) == len(tasks),
        "errors": errors,
    }


def _review_rows(values: tuple[str, ...], response: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cursor = 0
    for value in values:
        start = response.find(value, cursor)
        if start < 0:
            raise RuntimeError(f"self-test response is missing expected value: {value}")
        end = start + len(value)
        quote = response[start:end]
        rows.append(
            {
                "expected": value,
                "passed": True,
                "rationale": f"Expected {value} is supported by response quote {quote}.",
                "evidence": [{"quote": quote, "start": start, "end": end}],
            }
        )
        cursor = end
    return rows


def self_test() -> None:
    suite_payload, _ = _read_plain_file(SUITE_PATH, label="official suite", max_bytes=MAX_REPORT_BYTES)
    tasks = parse_suite(_decode_utf8(suite_payload, label="official suite"))
    task = tasks[0]
    response_text = "\n".join((*task.routes, *task.conclusions)) + "\n"
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        responses = root / "responses"
        responses.mkdir()
        response_path = responses / "task-000.md"
        response_path.write_bytes(response_text.encode("utf-8"))
        document = {
            "schema_version": 1,
            "scope": {"kind": "smoke", "task_count": 1},
            **current_contract(),
            "runner": {"id": "fresh-runner", "fresh_context": True, "independent": True},
            "reviewer": {"id": "independent-reviewer", "fresh_context": True, "independent": True},
            "items": [
                {
                    "heading": task.heading,
                    "prompt_sha256": sha256_bytes(task.prompt.encode("utf-8")),
                    "response": {"path": "responses/task-000.md", "sha256": sha256_bytes(response_path.read_bytes())},
                    "review": {
                        "passed": True,
                        "reviewer_id": "independent-reviewer",
                        "routes": _review_rows(task.routes, response_text),
                        "conclusions": _review_rows(task.conclusions, response_text),
                    },
                }
            ],
        }
        report_path = root / "forward-test-report.json"
        report_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        result = validate_report(report_path)
        if not result["valid"] or result["full_pass"]:
            raise RuntimeError(f"valid smoke control failed: {result['errors']}")
        document["items"][0]["response"]["sha256"] = "0" * 64
        report_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        if validate_report(report_path)["valid"]:
            raise RuntimeError("tampered response hash was accepted")
        document["items"][0]["response"]["sha256"] = sha256_bytes(response_path.read_bytes())
        document["items"][0]["review"]["conclusions"][0]["evidence"] = [
            {"quote": task.routes[0], "start": 0, "end": len(task.routes[0])}
        ]
        document["items"][0]["review"]["conclusions"][0]["rationale"] = (
            f"Expected {task.conclusions[0]} is supported by response quote {task.routes[0]}."
        )
        report_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        if validate_report(report_path)["valid"]:
            raise RuntimeError("irrelevant conclusion evidence was accepted")
        document["items"][0]["review"]["conclusions"] = _review_rows(task.conclusions, response_text)
        document["items"][0]["response"]["path"] = "responses/\u0000.md"
        report_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        if validate_report(report_path)["valid"]:
            raise RuntimeError("control-character response path was accepted")
    print(f"forward_test_report_self_test=PASS official_tasks={len(tasks)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", nargs="?", help="Existing forward-test report JSON")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable result")
    parser.add_argument("--print-contract", action="store_true", help="Print current suite and skill binding")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic internal controls")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            self_test()
            return 0
        if args.print_contract:
            print(json.dumps(current_contract(), ensure_ascii=False, indent=2))
            return 0
        if not args.report:
            parser.error("report is required unless --self-test or --print-contract is used")
        result = validate_report(Path(args.report))
    except ForwardTestError as exc:
        print(f"forward_test_error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"forward_test valid={str(result['valid']).lower()} "
            f"scope={result['scope']} items={result['reported_items']}/{result['official_tasks']} "
            f"full_pass={str(result['full_pass']).lower()}"
        )
        for error in result["errors"]:
            print(f"- {error}")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
