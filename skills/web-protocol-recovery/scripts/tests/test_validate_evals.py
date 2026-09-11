from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "gates"))

import validate_evals  # noqa: E402


class ValidateEvalsTests(unittest.TestCase):
    def test_current_route_regression_passes(self) -> None:
        self.assertEqual(validate_evals.validate_route_regression(), [])

    def test_current_test_prompts_pass(self) -> None:
        self.assertEqual(validate_evals.validate_test_prompts(), [])

    def test_missing_file_fails_closed(self) -> None:
        missing = Path(tempfile.gettempdir()) / "missing-test-prompts.json"
        findings = self._findings_for_path(missing)
        self.assertEqual(len(findings), 1)
        self.assertIn("missing test prompt fixture", findings[0])

    def test_missing_type_fails(self) -> None:
        findings = self._findings(
            [{"id": "x", "prompt": "p", "expected": "e"}]
        )
        self.assertTrue(any(".type is required" in item for item in findings))

    def test_unknown_type_fails(self) -> None:
        findings = self._findings(
            [{"id": "x", "prompt": "p", "expected": "e", "type": "maybe"}]
        )
        self.assertTrue(any("must be one of" in item for item in findings))

    def test_duplicate_id_fails(self) -> None:
        item = {"id": "x", "prompt": "p", "expected": "e", "type": "should-trigger"}
        findings = self._findings([item, dict(item)])
        self.assertTrue(any("duplicate test prompt id" in item for item in findings))

    def test_non_array_fails_closed(self) -> None:
        findings = self._findings({"id": "x"})
        self.assertEqual(findings, ["test-prompts.json must be a non-empty JSON array"])

    def _findings(self, payload: object) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test-prompts.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return self._findings_for_path(path)

    def _findings_for_path(self, path: Path) -> list[str]:
        original = validate_evals.TEST_PROMPTS_PATH
        validate_evals.TEST_PROMPTS_PATH = path
        try:
            return validate_evals.validate_test_prompts()
        finally:
            validate_evals.TEST_PROMPTS_PATH = original


if __name__ == "__main__":
    unittest.main()
