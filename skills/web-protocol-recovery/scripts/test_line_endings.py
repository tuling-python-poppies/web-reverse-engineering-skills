#!/usr/bin/env python3
"""Regression tests for LF-only hash-bound text surfaces."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

import build_case_registry
import validate_architecture


class LineEndingDisciplineTests(unittest.TestCase):
    def test_crlf_text_file_is_detected(self) -> None:
        with tempfile.TemporaryDirectory(dir=validate_architecture.SKILL_ROOT) as tmp:
            path = Path(tmp) / "sample.json"
            path.write_bytes(b'{\r\n  "a": 1\r\n}\r\n')
            findings = validate_architecture.line_ending_findings((path,))
        self.assertTrue(any("sample.json" in item for item in findings))

    def test_lf_text_file_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory(dir=validate_architecture.SKILL_ROOT) as tmp:
            path = Path(tmp) / "sample.json"
            path.write_bytes(b'{\n  "a": 1\n}\n')
            findings = validate_architecture.line_ending_findings((path,))
        self.assertFalse(any("sample.json" in item for item in findings))

    def test_crlf_extensionless_gitignore_is_detected(self) -> None:
        with tempfile.TemporaryDirectory(dir=validate_architecture.SKILL_ROOT) as tmp:
            path = Path(tmp) / ".gitignore"
            path.write_bytes(b"js_reverse_cache/**\r\n")
            findings = validate_architecture.line_ending_findings((path,))
        self.assertTrue(any(".gitignore" in item for item in findings))

    def test_bare_cr_text_file_is_detected(self) -> None:
        with tempfile.TemporaryDirectory(dir=validate_architecture.SKILL_ROOT) as tmp:
            path = Path(tmp) / "sample.md"
            path.write_bytes(b"line one\rline two\n")
            findings = validate_architecture.line_ending_findings((path,))
        self.assertTrue(any("sample.md" in item for item in findings))

    def test_bare_cr_extensionless_license_is_detected(self) -> None:
        with tempfile.TemporaryDirectory(dir=validate_architecture.SKILL_ROOT) as tmp:
            path = Path(tmp) / "LICENSE"
            path.write_bytes(b"license\rtext\n")
            findings = validate_architecture.line_ending_findings((path,))
        self.assertTrue(any("LICENSE" in item for item in findings))

    def test_repository_worktree_is_crlf_free(self) -> None:
        self.assertEqual(validate_architecture.line_ending_findings(), [])

    def test_case_registry_generator_writes_lf(self) -> None:
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
