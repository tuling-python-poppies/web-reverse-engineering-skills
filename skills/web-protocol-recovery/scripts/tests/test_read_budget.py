from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "gates"))

from read_budget import ReadBudget, validate_read_plan


class ReadBudgetTests(unittest.TestCase):
    def test_path_aliases_are_deduplicated(self) -> None:
        budget = ReadBudget()
        budget.add_base(["References/A.md", "references/a.md"])
        self.assertEqual(budget.checkpoint()["taskUsed"], 1)

    def test_extension_is_one_shot_and_bounded(self) -> None:
        budget = ReadBudget()
        budget.add_base([f"references/{index}.md" for index in range(24)])
        budget.add_extension(
            ["references/extra-a.md"],
            blocker_id="b1",
            reason="missing protocol boundary",
            acceptance_impact="required for first divergence",
        )
        with self.assertRaises(ValueError):
            budget.add_extension(
                ["references/extra-b.md"],
                blocker_id="b2",
                reason="second",
                acceptance_impact="not allowed",
            )

    def test_plan_rejects_duplicate_and_overflow(self) -> None:
        findings = validate_read_plan(
            {
                "required": ["a.md"],
                "optional": ["a.md"],
                "consumedPaths": [],
                "readBudgetExtension": None,
            }
        )
        self.assertTrue(findings)
        findings = validate_read_plan(
            {
                "required": [f"{index}.md" for index in range(24)],
                "optional": [],
                "consumedPaths": [],
                "readBudgetExtension": {
                    "additionalPaths": ["extra.md"],
                    "blockerId": "b1",
                    "reason": "missing fact",
                    "acceptanceImpact": "needed",
                },
            }
        )
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
