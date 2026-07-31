#!/usr/bin/env python3
"""Validate route regression eval metadata for web-protocol-recovery."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
EVAL_PATH = SKILL_ROOT / "evals" / "route-regression.json"
SKILL_EVALS_PATH = SKILL_ROOT / "evals" / "evals.json"
TRIGGER_EVALS_PATH = SKILL_ROOT / "evals" / "trigger-evals.json"
SKILL_MD_PATH = SKILL_ROOT / "SKILL.md"
TEST_PROMPTS_PATH = SKILL_ROOT / "test-prompts.json"
REGISTRY_PATH = SKILL_ROOT / "references" / "providers" / "registry.json"
SCHEMA_VERSION = "web-protocol-recovery-route-regression"
REQUIRED_CASE_IDS = {
    "douyin-abogus-native-profile",
    "jd-h5st-pure-python-case",
    "node-env-patch-strategy",
    "gt4-verifier-owner",
    "proved-protocol-python-delivery",
}
OBSOLETE_ROUTES = {"env-patch", "douyin-abogus-native"}
PROMPT_TYPES = {"should-trigger", "near-miss", "anti-pattern"}
TRIGGER_ARTIFACT_SCHEMA = "web-protocol-recovery-trigger-fulltest"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_skill_creator_evals() -> list[str]:
    findings: list[str] = []
    if not SKILL_EVALS_PATH.is_file():
        return ["missing evals/evals.json"]
    data = load_json(SKILL_EVALS_PATH)
    if data.get("skill_name") != "web-protocol-recovery":
        findings.append("evals/evals.json skill_name must be web-protocol-recovery")
    benchmark = data.get("benchmark") or {}
    expected_benchmark = {
        "mode": "with-skill-vs-baseline",
        "rounds": 3,
        "workers": 2,
        "timeout_seconds": 180,
        "executor_model": "deepseek/deepseek-v4-pro",
        "reviewer_model": "grok/grok-4.5",
    }
    for key, value in expected_benchmark.items():
        if benchmark.get(key) != value:
            findings.append(f"evals/evals.json benchmark.{key} must be {value!r}")
    evals = data.get("evals")
    if not isinstance(evals, list) or len(evals) < 10:
        findings.append("evals/evals.json must include at least 10 behavioral evals")
        evals = [] if not isinstance(evals, list) else evals
    seen_ids: set[int] = set()
    confirmations = 0
    for index, item in enumerate(evals):
        eval_id = item.get("id")
        if not isinstance(eval_id, int):
            findings.append(f"evals[{index}].id must be integer")
            continue
        if eval_id in seen_ids:
            findings.append(f"duplicate eval id: {eval_id}")
        seen_ids.add(eval_id)
        for field in ("prompt", "expected_output"):
            if not isinstance(item.get(field), str) or not item.get(field):
                findings.append(f"evals[{index}].{field} is required")
        if not isinstance(item.get("confirmation_required"), bool):
            findings.append(f"evals[{index}].confirmation_required must be boolean")
        elif item["confirmation_required"]:
            confirmations += 1
        expectations = item.get("expectations")
        if not isinstance(expectations, list) or not expectations or not all(isinstance(value, str) and value for value in expectations):
            findings.append(f"evals[{index}].expectations must be a non-empty string array")
    if confirmations < 3:
        findings.append("behavioral evals must include confirmation-required protocol/tool cases")

    trigger = data.get("trigger_benchmark")
    if not isinstance(trigger, dict):
        findings.append("evals/evals.json must declare trigger_benchmark")
    else:
        for field in (
            "prompt_file",
            "artifact",
            "status_ledger",
            "retry_granularity",
            "retry_policy",
            "standard_note",
        ):
            if not isinstance(trigger.get(field), str) or not trigger.get(field):
                findings.append(f"evals/evals.json trigger_benchmark.{field} is required")
        runs = trigger.get("runs_per_query")
        if not isinstance(runs, int) or runs < 3:
            findings.append(
                "evals/evals.json trigger_benchmark.runs_per_query must be at least 3: "
                "one run cannot separate a routing decision from wall-clock noise"
            )
        if trigger.get("threshold") != 1.0:
            findings.append("evals/evals.json trigger_benchmark.threshold must be 1.0")
        if trigger.get("single_model_required") is not True:
            findings.append("evals/evals.json trigger_benchmark.single_model_required must be true")
        if trigger.get("retry_granularity") != "failed-attempt":
            findings.append(
                "evals/evals.json trigger_benchmark.retry_granularity must be failed-attempt"
            )
        if trigger.get("prompt_file") != "evals/trigger-evals.json":
            findings.append("evals/evals.json trigger_benchmark.prompt_file must be the trigger corpus")
    return findings


def validate_trigger_evals() -> list[str]:
    findings: list[str] = []
    if not TRIGGER_EVALS_PATH.is_file():
        return ["missing evals/trigger-evals.json"]
    data = json.loads(TRIGGER_EVALS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list) or len(data) < 10:
        return ["trigger-evals.json must include at least 10 entries"]
    positives = 0
    negatives = 0
    for index, item in enumerate(data):
        if not isinstance(item.get("query"), str) or not item.get("query"):
            findings.append(f"trigger-evals[{index}].query is required")
        if not isinstance(item.get("should_trigger"), bool):
            findings.append(f"trigger-evals[{index}].should_trigger must be boolean")
        elif item["should_trigger"]:
            positives += 1
        else:
            negatives += 1
    if positives < 5 or negatives < 5:
        findings.append("trigger-evals must cover at least 5 positives and 5 negatives")
    required_negative_markers = ("skill", "opencode")
    negative_queries = "\n".join(item.get("query", "") for item in data if item.get("should_trigger") is False).lower()
    for marker in required_negative_markers:
        if marker not in negative_queries:
            findings.append(f"trigger-evals negatives must include {marker} handoff")
    return findings


def _trigger_standard() -> dict:
    if not SKILL_EVALS_PATH.is_file():
        return {}
    try:
        return load_json(SKILL_EVALS_PATH).get("trigger_benchmark") or {}
    except (OSError, json.JSONDecodeError):
        return {}


def _validate_trigger_provenance(artifact: dict, standard: dict) -> list[str]:
    """Provenance must be independently checkable, not self-asserted."""
    findings: list[str] = []
    if artifact.get("schemaVersion") != TRIGGER_ARTIFACT_SCHEMA:
        findings.append(f"trigger artifact schemaVersion must be {TRIGGER_ARTIFACT_SCHEMA}")
    for field, length in (
        ("run_base_commit", 40),
        ("evaluated_skill_md_sha256", 64),
        ("prompt_file_sha256", 64),
    ):
        value = artifact.get(field)
        if not isinstance(value, str) or len(value) != length:
            findings.append(f"trigger artifact {field} is missing or malformed")
    if not isinstance(artifact.get("run_worktree_dirty"), bool):
        findings.append("trigger artifact run_worktree_dirty must be boolean")
    if not isinstance(artifact.get("model"), str) or not artifact.get("model"):
        findings.append("trigger artifact model is required")

    # An accepted run must still describe the bytes that are checked out now.
    # This is the check that makes a stale acceptance claim impossible to leave
    # behind: editing SKILL.md or the corpus fails the gate until the run is
    # repeated or current_acceptance is withdrawn.
    if artifact.get("current_acceptance") is True:
        if artifact.get("run_worktree_dirty") is not False:
            findings.append("accepted trigger run must come from a clean worktree")
        if SKILL_MD_PATH.is_file():
            live = sha256_file(SKILL_MD_PATH)
            if artifact.get("evaluated_skill_md_sha256") != live:
                findings.append(
                    "accepted trigger run does not match current SKILL.md "
                    f"(recorded {str(artifact.get('evaluated_skill_md_sha256'))[:8]}, live {live[:8]}): "
                    "re-run the trigger eval or set current_acceptance false"
                )
        if TRIGGER_EVALS_PATH.is_file():
            live_prompts = sha256_file(TRIGGER_EVALS_PATH)
            if artifact.get("prompt_file_sha256") != live_prompts:
                findings.append(
                    "accepted trigger run does not match current trigger-evals.json "
                    f"(recorded {str(artifact.get('prompt_file_sha256'))[:8]}, live {live_prompts[:8]})"
                )
        if standard.get("single_model_required") is True:
            retry_model = artifact.get("retry_model")
            if retry_model is not None and retry_model != artifact.get("model"):
                findings.append(
                    "accepted trigger score must come from one model: "
                    f"model={artifact.get('model')!r} retry_model={retry_model!r}"
                )
    return findings


def _validate_trigger_arithmetic(artifact: dict, corpus: list) -> list[str]:
    """The headline score must be recomputable from the retained per-query grades."""
    findings: list[str] = []
    summary = artifact.get("summary") or {}
    union = artifact.get("union_results")
    if not isinstance(union, list) or not union:
        return ["trigger artifact union_results must be a non-empty array"]

    if corpus and len(union) != len(corpus):
        findings.append(
            f"trigger artifact covers {len(union)} queries but the corpus has {len(corpus)}"
        )
    passed = sum(1 for row in union if row.get("pass") is True)
    if summary.get("total") != len(union):
        findings.append(f"trigger summary.total must equal {len(union)}")
    if summary.get("passed") != passed:
        findings.append(f"trigger summary.passed must equal {passed} recomputed from union_results")
    if summary.get("failed") != len(union) - passed:
        findings.append(f"trigger summary.failed must equal {len(union) - passed}")
    if summary.get("score") != f"{passed}/{len(union)}":
        findings.append(f"trigger summary.score must equal {passed}/{len(union)}")

    threshold = artifact.get("trigger_threshold")
    if not isinstance(threshold, (int, float)):
        findings.append("trigger artifact trigger_threshold must be numeric")
    elif artifact.get("current_acceptance") is True and passed < len(union) * threshold:
        findings.append(
            f"trigger artifact claims acceptance at {passed}/{len(union)} below threshold {threshold}"
        )

    # Retained-grade discipline: first pass and retry must stay separable, and a
    # retry is legitimate only for the exact n-run attempt that failed first pass.
    first_pass = artifact.get("first_pass_results")
    retries = artifact.get("retry_results")
    retried_ids = artifact.get("retried_ids")
    retried_attempts = artifact.get("retried_attempts")
    attempt_first_pass = artifact.get("attempt_first_pass_results")
    attempt_retries = artifact.get("attempt_retry_results")
    attempt_results = artifact.get("attempt_results")
    has_attempt_retries = isinstance(attempt_retries, list) and bool(attempt_retries)

    if has_attempt_retries and (not isinstance(retried_ids, list) or not retried_ids):
        findings.append(
            "trigger artifact attempt_retry_results requires non-empty retried_ids"
        )

    runs_per_query = artifact.get("runs_per_query")
    if isinstance(attempt_results, list) and isinstance(runs_per_query, int) and corpus:
        expected_attempts = len(corpus) * runs_per_query
        if len(attempt_results) != expected_attempts:
            findings.append(
                f"trigger artifact attempt_results must cover {expected_attempts} attempts"
            )
        attempt_passed = sum(1 for row in attempt_results if row.get("pass") is True)
        if summary.get("attempts_final") != f"{attempt_passed}/{len(attempt_results)}":
            findings.append(
                f"trigger summary.attempts_final must equal {attempt_passed}/{len(attempt_results)}"
            )
        attempts_by_id: dict = {}
        for row in attempt_results:
            attempts_by_id.setdefault(row.get("id"), []).append(row)
        for row in union:
            group = attempts_by_id.get(row.get("id"), [])
            if group and row.get("pass") is not all(item.get("pass") is True for item in group):
                findings.append(
                    f"trigger union result id {row.get('id')} does not match retained attempt grades"
                )

    if isinstance(attempt_first_pass, list) and isinstance(runs_per_query, int) and corpus:
        expected_first_pass = len(corpus) * runs_per_query
        if len(attempt_first_pass) != expected_first_pass:
            findings.append(
                f"trigger artifact attempt_first_pass_results must cover {expected_first_pass} attempts"
            )

    if isinstance(retried_ids, list) and retried_ids:
        if not isinstance(first_pass, list) or not first_pass:
            findings.append("trigger artifact must retain first_pass_results when a retry ran")
        if len(set(retried_ids)) != len(retried_ids):
            findings.append("trigger artifact retried_ids must contain unique query ids")
        if not isinstance(retries, list) or len(retries) != len(retried_ids):
            findings.append("trigger artifact retry_results must have one row per retried id")
        else:
            retry_result_ids = [row.get("id") for row in retries]
            if len(set(retry_result_ids)) != len(retry_result_ids):
                findings.append("trigger artifact retry_results must contain unique query ids")
            if set(retry_result_ids) != set(retried_ids):
                findings.append("trigger artifact retry_results must match retried_ids")
        if isinstance(attempt_retries, list) and attempt_retries:
            retry_keys = {(row.get("attempt"), row.get("id")) for row in attempt_retries}
            if len(retry_keys) != len(attempt_retries):
                findings.append("trigger artifact attempt_retry_results must not duplicate attempt/id rows")
            if not isinstance(retried_attempts, list):
                findings.append("trigger artifact retried_attempts must be an array")
            else:
                declared_retry_keys = {
                    (row.get("attempt"), row.get("id"))
                    for row in retried_attempts
                    if isinstance(row, dict)
                }
                if len(declared_retry_keys) != len(retried_attempts):
                    findings.append(
                        "trigger artifact retried_attempts must contain unique attempt/id rows"
                    )
                if declared_retry_keys != retry_keys:
                    findings.append(
                        "trigger artifact retried_attempts must match attempt_retry_results"
                    )
            actual_retry_ids = {row.get("id") for row in attempt_retries}
            if not isinstance(retried_ids, list) or set(retried_ids) != actual_retry_ids:
                findings.append(
                    "trigger artifact retried_ids must match attempt_retry_results query ids"
                )
        if isinstance(first_pass, list):
            first_by_id = {row.get("id"): row for row in first_pass}
            for retry_id in retried_ids:
                original = first_by_id.get(retry_id)
                if original is None:
                    findings.append(f"retried id {retry_id} has no first_pass_results row")
                elif not isinstance(attempt_retries, list) and original.get("pass") is True:
                    findings.append(f"retried id {retry_id} already passed the first pass")

        if isinstance(attempt_retries, list) and attempt_retries:
            first_by_attempt = {
                (row.get("attempt"), row.get("id")): row for row in (attempt_first_pass or [])
            }
            for retry in attempt_retries:
                key = (retry.get("attempt"), retry.get("id"))
                original = first_by_attempt.get(key)
                if original is None:
                    findings.append(
                        f"retried attempt {key!r} has no attempt_first_pass_results row"
                    )
                elif original.get("pass") is True:
                    findings.append(f"retried attempt {key!r} already passed the first pass")

    if corpus and isinstance(union, list):
        by_index = {index + 1: item for index, item in enumerate(corpus)}
        for row in union:
            source = by_index.get(row.get("id"))
            if source is None:
                findings.append(f"trigger result id {row.get('id')!r} is not in the corpus")
                continue
            if row.get("query") != source.get("query"):
                findings.append(f"trigger result id {row.get('id')} query drifted from the corpus")
            if row.get("should_trigger") != source.get("should_trigger"):
                findings.append(
                    f"trigger result id {row.get('id')} should_trigger drifted from the corpus"
                )
    return findings


def _validate_trigger_bookkeeping(artifact: dict, standard: dict) -> list[str]:
    """A declared timeout that no run respected is a bookkeeping error, not a detail.

    A duration above the declared limit means the number in the artifact is not the
    number the runner enforced, so every later reader draws the wrong conclusion
    about why a query failed. Such a row is allowed only with an explicit
    timeout_accounting entry that says what really happened.
    """
    findings: list[str] = []
    required_granularity = standard.get("retry_granularity")
    actual_granularity = artifact.get("retry_granularity")
    if required_granularity != "failed-attempt":
        findings.append("trigger standard retry_granularity must be failed-attempt")
    if actual_granularity != required_granularity:
        findings.append(
            "trigger artifact retry_granularity must match the declared standard "
            f"({required_granularity!r})"
        )
    accounting = artifact.get("timeout_accounting")
    explained: set = set()
    if accounting is not None:
        if not isinstance(accounting, dict):
            findings.append("trigger artifact timeout_accounting must be an object")
        else:
            for phase in ("first_pass", "retry"):
                entry = accounting.get(phase) or {}
                if not isinstance(entry, dict):
                    findings.append(f"timeout_accounting.{phase} must be an object")
                    continue
                ids = entry.get("over_declared_ids")
                if ids is not None and not isinstance(ids, list):
                    findings.append(f"timeout_accounting.{phase}.over_declared_ids must be an array")
                    continue
                for value in ids or []:
                    explained.add((phase, value))
                if ids and not entry.get("explanation"):
                    findings.append(
                        f"timeout_accounting.{phase} lists ids but gives no explanation"
                    )

    first_pass_rows = artifact.get("attempt_first_pass_results") or artifact.get("first_pass_results")
    retry_rows = artifact.get("attempt_retry_results") or artifact.get("retry_results")
    phases = (
        ("first_pass", first_pass_rows, artifact.get("timeout_seconds")),
        ("retry", retry_rows, artifact.get("retry_timeout_seconds")),
    )
    for phase, rows, limit in phases:
        if not isinstance(rows, list) or not isinstance(limit, (int, float)):
            continue
        for row in rows:
            duration = row.get("duration_ms")
            if not isinstance(duration, (int, float)):
                continue
            if duration > limit * 1000 and (phase, row.get("id")) not in explained:
                findings.append(
                    f"trigger {phase} id {row.get('id')} ran {duration / 1000:.1f}s over the "
                    f"declared {limit}s timeout without a timeout_accounting entry"
                )

    required = standard.get("runs_per_query")
    actual = artifact.get("runs_per_query")
    if not isinstance(actual, int) or actual < 1:
        findings.append("trigger artifact runs_per_query must be a positive integer")
    elif isinstance(required, int) and actual < required:
        caveat = artifact.get("statistical_caveat")
        if not isinstance(caveat, str) or not caveat.strip():
            findings.append(
                f"trigger artifact ran runs_per_query={actual} below the declared standard "
                f"{required} and must carry statistical_caveat naming the shortfall"
            )
    return findings


def validate_trigger_artifact() -> list[str]:
    standard = _trigger_standard()
    rel_artifact = standard.get("artifact")
    if not rel_artifact:
        return ["evals/evals.json trigger_benchmark.artifact is required"]
    artifact_path = SKILL_ROOT / rel_artifact
    if not artifact_path.is_file():
        return [f"missing trigger benchmark artifact: {rel_artifact}"]
    try:
        artifact = load_json(artifact_path)
    except (OSError, json.JSONDecodeError) as error:
        return [f"trigger benchmark artifact unreadable: {error}"]
    if not isinstance(artifact.get("current_acceptance"), bool):
        return ["trigger artifact current_acceptance must be boolean"]

    corpus: list = []
    if TRIGGER_EVALS_PATH.is_file():
        try:
            loaded = json.loads(TRIGGER_EVALS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded = []
        if isinstance(loaded, list):
            corpus = loaded

    findings = _validate_trigger_provenance(artifact, standard)
    findings.extend(_validate_trigger_arithmetic(artifact, corpus))
    findings.extend(_validate_trigger_bookkeeping(artifact, standard))

    ledger_rel = standard.get("status_ledger")
    if ledger_rel:
        ledger = SKILL_ROOT / ledger_rel
        if not ledger.is_file():
            findings.append(f"missing trigger status ledger: {ledger_rel}")
        else:
            text = ledger.read_text(encoding="utf-8")
            skill_hash = artifact.get("evaluated_skill_md_sha256")
            if isinstance(skill_hash, str) and skill_hash[:8] not in text:
                findings.append(
                    f"{ledger_rel} does not cite the evaluated SKILL.md hash {skill_hash[:8]}"
                )
            summary = artifact.get("summary") or {}
            score = summary.get("score")
            if isinstance(score, str) and score not in text:
                findings.append(f"{ledger_rel} does not record the artifact score {score}")
    return findings


def validate_test_prompts() -> list[str]:
    findings: list[str] = []
    if not TEST_PROMPTS_PATH.is_file():
        return ["missing test-prompts.json"]
    data = json.loads(TEST_PROMPTS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list) or len(data) < 10:
        return ["test-prompts.json must be a list with at least 10 entries"]
    seen_ids: set[int] = set()
    types_seen: set[str] = set()
    confirmation_count = 0
    for index, item in enumerate(data):
        item_id = item.get("id")
        if not isinstance(item_id, int):
            findings.append(f"test-prompts[{index}].id must be integer")
            continue
        if item_id in seen_ids:
            findings.append(f"duplicate test prompt id: {item_id}")
        seen_ids.add(item_id)
        for field in ("prompt", "expected"):
            if not isinstance(item.get(field), str) or not item.get(field):
                findings.append(f"test-prompts[{index}].{field} is required")
        prompt_type = item.get("type")
        if prompt_type not in PROMPT_TYPES:
            findings.append(f"test-prompts[{index}].type must be one of {sorted(PROMPT_TYPES)}")
        else:
            types_seen.add(prompt_type)
        if not isinstance(item.get("confirmation_required"), bool):
            findings.append(f"test-prompts[{index}].confirmation_required must be boolean")
        elif item["confirmation_required"]:
            confirmation_count += 1
    missing_types = sorted(PROMPT_TYPES - types_seen)
    if missing_types:
        findings.append("test-prompts.json missing type coverage: " + ", ".join(missing_types))
    if confirmation_count == 0:
        findings.append("test-prompts.json must mark tool/write/live prompts confirmation_required")
    return findings


def main() -> int:
    findings: list[str] = []
    if not EVAL_PATH.is_file():
        print(f"FAIL missing eval file: {EVAL_PATH.relative_to(SKILL_ROOT).as_posix()}")
        return 1

    registry = load_json(REGISTRY_PATH)
    valid_routes = {provider["id"] for provider in registry.get("providers", [])}
    valid_routes.update(registry.get("routeSentinels", []))
    data = load_json(EVAL_PATH)
    if data.get("schemaVersion") != SCHEMA_VERSION:
        findings.append(f"schemaVersion must be {SCHEMA_VERSION}")
    cases = data.get("cases")
    if not isinstance(cases, list) or len(cases) < len(REQUIRED_CASE_IDS):
        findings.append("cases must include the required route regression set")
        cases = [] if not isinstance(cases, list) else cases

    seen_ids: set[str] = set()
    for index, item in enumerate(cases):
        case_id = item.get("id")
        if not isinstance(case_id, str) or not case_id:
            findings.append(f"cases[{index}].id is required")
            continue
        if case_id in seen_ids:
            findings.append(f"duplicate eval id: {case_id}")
        seen_ids.add(case_id)
        if not item.get("prompt"):
            findings.append(f"{case_id}: prompt is required")
        expect = item.get("expect") or {}
        route = expect.get("route")
        if route not in valid_routes:
            findings.append(f"{case_id}: invalid expected route {route!r}")
        if route in OBSOLETE_ROUTES:
            findings.append(f"{case_id}: obsolete route {route!r}")
        if expect.get("strategy") == "env-patch" and route != "python-node":
            findings.append(f"{case_id}: env-patch strategy requires route python-node")
        if expect.get("profile") == "douyin-abogus-native" and route != "pure-python":
            findings.append(f"{case_id}: douyin profile requires route pure-python")
        for bad_route in expect.get("notRoute", []):
            if bad_route not in OBSOLETE_ROUTES:
                findings.append(f"{case_id}: notRoute should only name obsolete route values")

    missing = sorted(REQUIRED_CASE_IDS - seen_ids)
    if missing:
        findings.append(f"missing required eval ids: {', '.join(missing)}")

    # Every routable provider needs at least one declared routing assertion.
    # Without this, a provider can be added to the registry and documented while
    # no eval ever states where it is supposed to win, which is how akamai,
    # river-security, and chromium-recon sat uncovered.
    expected_routes = {expect.get("route") for expect in (item.get("expect") or {} for item in cases)}
    uncovered = sorted(
        {provider["id"] for provider in registry.get("providers", [])} - expected_routes
    )
    if uncovered:
        findings.append(
            "providers with no route regression case: " + ", ".join(uncovered)
        )
    findings.extend(validate_skill_creator_evals())
    findings.extend(validate_trigger_evals())
    findings.extend(validate_trigger_artifact())
    findings.extend(validate_test_prompts())

    if findings:
        for finding in findings:
            print(f"FAIL {finding}")
        print(f"summary: failures={len(findings)}")
        return 1
    results_dir = SKILL_ROOT / "evals" / "benchmark-results"
    results_file = results_dir / "iteration-1-full10.json"
    acceptance_file = results_dir / "ACCEPTANCE.md"
    if results_file.is_file() and acceptance_file.is_file():
        try:
            results = load_json(results_file)
        except (OSError, json.JSONDecodeError) as error:
            findings.append(f"benchmark results unreadable: {error}")
            print(f"summary: failures={len(findings)}")
            return 1
        if results.get("eval_mode") != "reported_full_test_summary":
            findings.append(
                "benchmark results eval_mode must be reported_full_test_summary"
            )
        integrity = results.get("integrity") or {}
        if integrity.get("classification") != "historical-summary-only":
            findings.append("benchmark results must classify retained evidence integrity")
        if integrity.get("current_acceptance") is not False:
            findings.append("summary-only benchmark must not claim current acceptance")
        if integrity.get("raw_outputs_available") is not False:
            findings.append("benchmark summary must state raw output availability")
        for field in ("benchmark_base_commit", "record_commit", "prompt_file_sha256"):
            value = results.get(field)
            expected_length = 40 if field.endswith("commit") else 64
            if not isinstance(value, str) or len(value) != expected_length:
                findings.append(f"benchmark results {field} is missing or malformed")
        if results.get("summary", {}).get("comparison") != "with_skill_clear_win":
            findings.append("benchmark results must record with_skill_clear_win for acceptance")
        cases_ran = results.get("cases") or []
        if len(cases_ran) < 10:
            findings.append("benchmark results must cover 10 behavioral cases")
        if findings:
            for finding in findings:
                print(f"FAIL {finding}")
            print(f"summary: failures={len(findings)}")
            return 1
        print(
            f"PASS route regression evals: cases={len(cases)}; "
            "behavioral_evals=metadata_ok; trigger_evals=metadata_ok; "
            "full_model_benchmark=historical_summary_only_round1_full10"
        )
        return 0
    print(
        f"PASS route regression evals: cases={len(cases)}; "
        "behavioral_evals=metadata_ok; trigger_evals=metadata_ok; "
        "full_model_benchmark=deferred"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
