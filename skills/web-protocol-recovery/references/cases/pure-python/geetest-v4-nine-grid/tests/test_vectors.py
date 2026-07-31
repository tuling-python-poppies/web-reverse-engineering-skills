from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path


CASE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_ROOT))

import entry  # noqa: E402


class GeetestNineGridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vectors = json.loads(
            (CASE_ROOT / "fixtures" / "vectors.json").read_text(encoding="utf-8")
        )

    def test_model_asset_manifest(self) -> None:
        actual = entry.verify_model_assets()
        self.assertEqual(actual, self.vectors["model"])

    def test_indices_to_userresponse(self) -> None:
        vector = self.vectors["indices"]
        self.assertEqual(
            entry.indices_to_userresponse(vector["input"], vector["count"]),
            vector["expected"],
        )

    def test_lot_rule_is_inclusive(self) -> None:
        vector = self.vectors["lot"]
        self.assertEqual(
            entry.resolve_lot_fields(vector["lotNumber"], vector["rules"]),
            vector["expected"],
        )

    def test_decode_uri_preserves_reserved_escape(self) -> None:
        vector = self.vectors["decodeUri"]
        self.assertEqual(
            entry.decode_uri_bytes(vector["input"]).decode("ascii"),
            vector["expectedAscii"],
        )

    def test_djb2_vector(self) -> None:
        vector = self.vectors["djb2"]
        self.assertEqual(entry.djb2_5381(vector["input"]), vector["expected"])

    def test_gct_biht_vector(self) -> None:
        vector = self.vectors["gct"]
        self.assertEqual(entry.calculate_biht(vector["source"]), vector["expectedBiht"])

    def test_aes_ascii_zero_iv_vector(self) -> None:
        vector = self.vectors["aes"]
        ciphertext, _ = entry.encrypt_aes(
            vector["payload"], vector["keyAscii"].encode("ascii")
        )
        self.assertEqual(ciphertext, vector["expectedCiphertextHex"])

    def test_pow_vector(self) -> None:
        vector = self.vectors["pow"]
        self.assertTrue(
            entry.verify_pow_message(vector["message"], vector["digest"], vector["bits"])
        )
        self.assertEqual(
            hashlib.sha256(vector["message"].encode("utf-8")).hexdigest(),
            vector["digest"],
        )

    def test_offline_scope_marker(self) -> None:
        self.assertEqual(self.vectors["activeScope"], "offline-only")
        self.assertTrue(self.vectors["passed"])


if __name__ == "__main__":
    unittest.main()
