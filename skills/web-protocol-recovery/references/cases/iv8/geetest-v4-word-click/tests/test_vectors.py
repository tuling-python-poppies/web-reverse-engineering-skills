from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

CASE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_ROOT))

import entry


class GeetestWordClickTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vectors = json.loads((CASE_ROOT / "fixtures" / "vectors.json").read_text(encoding="utf-8"))

    def test_import_is_offline_and_vectors_are_bound(self) -> None:
        self.assertTrue(self.vectors["passed"])
        self.assertEqual(self.vectors["activeScope"], "offline-only")

    def test_normalize_text(self) -> None:
        vector = self.vectors["text"]
        self.assertEqual(entry.normalize_text(vector["input"]), vector["expected"])

    def test_load_shape(self) -> None:
        data = {key: value for key, value in ((field, "fixture") for field in self.vectors["loadShape"]["requiredFields"])}
        data["captcha_type"] = "word"
        data["imgs"] = "fixture.jpg"
        data["ques"] = ["q0.png", "q1.png"]
        self.assertEqual(entry.validate_word_load(data), data)
        data["captcha_type"] = "nine"
        with self.assertRaisesRegex(ValueError, "captcha_type=word"):
            entry.validate_word_load(data)

    def test_pixel_to_wire(self) -> None:
        vector = self.vectors["points"]
        self.assertEqual(entry.pixel_points_to_wire(vector["pixels"], *vector["imageSize"]), vector["wire"])

    def test_answer_shape(self) -> None:
        vector = self.vectors["answer"]
        self.assertEqual(entry.build_answer(vector["passtime"], self.vectors["points"]["pixels"], 300, 200), vector["expected"])

    def test_invalid_points_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "outside image"):
            entry.pixel_points_to_wire([[300, 0]], 300, 200)

    def test_semantic_success(self) -> None:
        self.assertTrue(entry.verify_success(self.vectors["success"]))
        self.assertFalse(entry.verify_success({"status": "success", "data": {"result": "fail", "fail_count": 1}}))


if __name__ == "__main__":
    unittest.main()
