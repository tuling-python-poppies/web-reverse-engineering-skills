#!/usr/bin/env python3
"""Fail-closed tests for line-ending discipline and trigger-eval integrity.

Every defect these cover shares one shape: a gate reported PASS while measuring
the wrong thing. The hash system hashed CRLF worktree bytes for its whole life
because the generator wrote CRLF and the checker read back with universal
newlines, and the accepted trigger artifact carried a score, a provenance claim,
and a timeout that nothing compared against reality. A gate that cannot fail is
not a gate, so each test here asserts the failing direction.
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

import build_case_registry
import validate_architecture
import validate_evals


ARTIFACT_PATH = (
    validate_evals.SKILL_ROOT
    / "evals"
    / "benchmark-results"
    / "trigger-deepseek-v4-pro-current.json"
)


def load_artifact() -> dict:
    return json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))


class LineEndingDisciplineTests(unittest.TestCase):
    def test_crlf_text_file_is_detected(self) -> None:
        with tempfile.TemporaryDirectory(dir=validate_architecture.SKILL_ROOT) as tmp:
            path = Path(tmp) / "sample.json"
            path.write_bytes(b'{\r\n  "a": 1\r\n}\r\n')
            findings = validate_architecture.line_ending_findings()
            self.assertTrue(any("sample.json" in item for item in findings))

    def test_lf_text_file_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory(dir=validate_architecture.SKILL_ROOT) as tmp:
            path = Path(tmp) / "sample.json"
            path.write_bytes(b'{\n  "a": 1\n}\n')
            findings = validate_architecture.line_ending_findings()
            self.assertFalse(any("sample.json" in item for item in findings))

    def test_repository_worktree_is_crlf_free(self) -> None:
        self.assertEqual(validate_architecture.line_ending_findings(), [])

    def test_case_registry_generator_writes_lf(self) -> None:
        """The exact write path that shipped CRLF and broke every clean clone."""
        original_path = build_case_registry.REGISTRY_PATH
        original_argv = sys.argv
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "registry.json"
            build_case_registry.REGISTRY_PATH = target
            sys.argv = ["build_case_registry.py"]
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(build_case_registry.main(), 0)
            finally:
                build_case_registry.REGISTRY_PATH = original_path
                sys.argv = original_argv
            written = target.read_bytes()
        self.assertNotIn(b"\r\n", written)
        self.assertIn(b"\n", written)


class TriggerProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.standard = validate_evals._trigger_standard()
        self.artifact = load_artifact()

    def test_live_artifact_passes(self) -> None:
        self.assertEqual(validate_evals.validate_trigger_artifact(), [])

    def test_stale_acceptance_after_skill_md_change_is_rejected(self) -> None:
        """Acceptance must be bound to the SKILL.md bytes that are checked out."""
        artifact = copy.deepcopy(self.artifact)
        artifact["evaluated_skill_md_sha256"] = "0" * 64
        findings = validate_evals._validate_trigger_provenance(artifact, self.standard)
        self.assertTrue(any("does not match current SKILL.md" in item for item in findings))

    def test_stale_acceptance_after_corpus_change_is_rejected(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        artifact["prompt_file_sha256"] = "1" * 64
        findings = validate_evals._validate_trigger_provenance(artifact, self.standard)
        self.assertTrue(
            any("does not match current trigger-evals.json" in item for item in findings)
        )

    def test_dirty_worktree_cannot_be_accepted(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        artifact["run_worktree_dirty"] = True
        findings = validate_evals._validate_trigger_provenance(artifact, self.standard)
        self.assertTrue(any("clean worktree" in item for item in findings))

    def test_two_model_union_cannot_be_accepted(self) -> None:
        """A score assembled from two models is not one model's score."""
        artifact = copy.deepcopy(self.artifact)
        artifact["retry_model"] = "deepseek/deepseek-v4-flash"
        findings = validate_evals._validate_trigger_provenance(artifact, self.standard)
        self.assertTrue(any("must come from one model" in item for item in findings))

    def test_withdrawn_acceptance_relaxes_binding(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        artifact["current_acceptance"] = False
        artifact["evaluated_skill_md_sha256"] = "0" * 64
        findings = validate_evals._validate_trigger_provenance(artifact, self.standard)
        self.assertEqual(findings, [])

    def test_malformed_provenance_fields_are_rejected(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        artifact["run_base_commit"] = "abc123"
        findings = validate_evals._validate_trigger_provenance(artifact, self.standard)
        self.assertTrue(any("run_base_commit" in item for item in findings))


class TriggerArithmeticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.artifact = load_artifact()
        self.corpus = json.loads(
            validate_evals.TRIGGER_EVALS_PATH.read_text(encoding="utf-8")
        )

    def test_headline_score_must_be_recomputable(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        artifact["union_results"][0]["pass"] = False
        findings = validate_evals._validate_trigger_arithmetic(artifact, self.corpus)
        self.assertTrue(any("summary.passed must equal" in item for item in findings))

    def test_inflated_score_string_is_rejected(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        artifact["summary"]["score"] = "22/20"
        findings = validate_evals._validate_trigger_arithmetic(artifact, self.corpus)
        self.assertTrue(any("summary.score must equal" in item for item in findings))

    def test_partial_corpus_coverage_is_rejected(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        artifact["union_results"] = artifact["union_results"][:-1]
        findings = validate_evals._validate_trigger_arithmetic(artifact, self.corpus)
        self.assertTrue(any("but the corpus has" in item for item in findings))

    def test_query_drift_from_corpus_is_detected(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        artifact["union_results"][0]["query"] = "an easier question"
        findings = validate_evals._validate_trigger_arithmetic(artifact, self.corpus)
        self.assertTrue(any("query drifted from the corpus" in item for item in findings))

    def test_retry_of_a_passing_query_is_rejected(self) -> None:
        """A retry is only legitimate where the first pass actually failed."""
        artifact = copy.deepcopy(self.artifact)
        for row in artifact["first_pass_results"]:
            if row["id"] == artifact["retried_ids"][0]:
                row["pass"] = True
        findings = validate_evals._validate_trigger_arithmetic(artifact, self.corpus)
        self.assertTrue(any("already passed the first pass" in item for item in findings))

    def test_dropped_first_pass_grades_are_rejected(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        artifact["first_pass_results"] = []
        findings = validate_evals._validate_trigger_arithmetic(artifact, self.corpus)
        self.assertTrue(any("must retain first_pass_results" in item for item in findings))

    def test_acceptance_below_threshold_is_rejected(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        artifact["union_results"][0]["pass"] = False
        artifact["summary"]["passed"] = 21
        artifact["summary"]["failed"] = 1
        artifact["summary"]["score"] = "21/22"
        findings = validate_evals._validate_trigger_arithmetic(artifact, self.corpus)
        self.assertTrue(any("below threshold" in item for item in findings))


class TriggerBookkeepingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.standard = validate_evals._trigger_standard()
        self.artifact = load_artifact()

    def test_unexplained_over_timeout_run_is_rejected(self) -> None:
        """A duration above the declared limit means the declared limit is wrong."""
        artifact = copy.deepcopy(self.artifact)
        artifact.pop("timeout_accounting", None)
        findings = validate_evals._validate_trigger_bookkeeping(artifact, self.standard)
        self.assertTrue(any("without a timeout_accounting entry" in item for item in findings))

    def test_accounting_without_explanation_is_rejected(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        artifact["timeout_accounting"]["first_pass"]["explanation"] = ""
        findings = validate_evals._validate_trigger_bookkeeping(artifact, self.standard)
        self.assertTrue(any("gives no explanation" in item for item in findings))

    def test_accounting_does_not_excuse_other_ids(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        artifact["timeout_accounting"]["first_pass"]["over_declared_ids"] = [99]
        findings = validate_evals._validate_trigger_bookkeeping(artifact, self.standard)
        self.assertTrue(any("without a timeout_accounting entry" in item for item in findings))

    def test_retry_over_its_raised_limit_is_detected(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        artifact["retry_results"][0]["duration_ms"] = 900000
        findings = validate_evals._validate_trigger_bookkeeping(artifact, self.standard)
        self.assertTrue(any("trigger retry id" in item for item in findings))

    def test_below_standard_runs_require_a_caveat(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        artifact.pop("statistical_caveat", None)
        findings = validate_evals._validate_trigger_bookkeeping(artifact, self.standard)
        self.assertTrue(any("must carry statistical_caveat" in item for item in findings))

    def test_meeting_the_standard_needs_no_caveat(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        artifact["runs_per_query"] = self.standard["runs_per_query"]
        artifact.pop("statistical_caveat", None)
        findings = validate_evals._validate_trigger_bookkeeping(artifact, self.standard)
        self.assertFalse(any("statistical_caveat" in item for item in findings))

    def test_every_provider_has_a_route_regression_case(self) -> None:
        """A provider nobody asserts a route for is a provider nobody tests."""
        registry = json.loads(validate_evals.REGISTRY_PATH.read_text(encoding="utf-8"))
        cases = json.loads(validate_evals.EVAL_PATH.read_text(encoding="utf-8"))["cases"]
        routes = {(case.get("expect") or {}).get("route") for case in cases}
        uncovered = {provider["id"] for provider in registry["providers"]} - routes
        self.assertEqual(uncovered, set())

    def test_declared_standard_must_require_repetition(self) -> None:
        """The standard itself is gated, so it cannot be quietly lowered to 1."""
        data = json.loads(validate_evals.SKILL_EVALS_PATH.read_text(encoding="utf-8"))
        self.assertGreaterEqual(data["trigger_benchmark"]["runs_per_query"], 3)
        self.assertEqual(data["trigger_benchmark"]["threshold"], 1.0)
        self.assertIs(data["trigger_benchmark"]["single_model_required"], True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
