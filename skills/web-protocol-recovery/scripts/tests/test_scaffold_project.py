#!/usr/bin/env python3
"""Safety tests for python-collector project scaffold."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCAFFOLD = ROOT / "scripts" / "providers" / "delivery" / "python-collector" / "scaffold_project.py"


def run_scaffold(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(SCAFFOLD), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


class ScaffoldProjectTests(unittest.TestCase):
    def test_requires_confirm_before_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = run_scaffold(str(Path(temporary) / "project"), "--entry")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("without --confirm", result.stderr + result.stdout)

    def test_cache_requires_gitignore(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = run_scaffold(str(Path(temporary) / "project"), "--cache", "--confirm")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("require --gitignore", result.stderr + result.stdout)

    def test_existing_entry_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            project.mkdir()
            entry = project / "main.py"
            entry.write_text("print('user file')\n", encoding="utf-8")

            result = run_scaffold(str(project), "--entry", "--confirm")

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(entry.read_text(encoding="utf-8"), "print('user file')\n")


if __name__ == "__main__":
    unittest.main()
