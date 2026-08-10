from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path


CASE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_ROOT))

import entry  # noqa: E402


class BandaiMiniappGoodsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vectors = json.loads(
            (CASE_ROOT / "fixtures" / "vectors.json").read_text(encoding="utf-8")
        )

    def test_signature_vector(self) -> None:
        vector = self.vectors["signature"]
        self.assertEqual(
            entry.build_signature(vector["serverTime"]), vector["expectedBase64"]
        )

    def test_request_vector(self) -> None:
        vector = self.vectors["request"]
        params = entry.build_goods_params(
            page=vector["page"],
            limit=vector["limit"],
            category_id=vector["categoryId"],
            is_home=vector["isHome"],
        )
        self.assertEqual(params, vector["expected"])

    def test_header_vector(self) -> None:
        vector = self.vectors["headers"]
        headers = entry.build_headers(vector["serverTime"], vector["miniVersion"])
        self.assertEqual(headers["Mini-User-Agent"], vector["expectedMiniUserAgent"])
        self.assertEqual(headers["signature"], self.vectors["signature"]["expectedBase64"])

    def test_parse_response(self) -> None:
        payload = json.loads(
            (CASE_ROOT / "fixtures" / "response.sample.json").read_text(encoding="utf-8")
        )
        parsed = entry.parse_goods_response(payload)
        self.assertEqual(parsed["code"], 200)
        self.assertEqual(parsed["count"], 2)
        self.assertEqual(parsed["goods"][0]["id"], 1001)
        self.assertEqual(parsed["goods"][0]["name"], "Synthetic Starter Deck")

    def test_offline_proof_binds_entry_and_test(self) -> None:
        proof = json.loads(
            (CASE_ROOT / "fixtures" / "offline-proof.summary.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(proof["activeScope"], "offline-only")
        self.assertFalse(proof["historicalLiveProofIsCurrentAcceptance"])
        self.assertEqual(
            proof["entrySha256"],
            hashlib.sha256((CASE_ROOT / "entry.py").read_bytes()).hexdigest(),
        )
        self.assertEqual(
            proof["testArtifactSha256"],
            hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        )

    def test_live_entry_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "offline-only"):
            entry.run(live=True)


if __name__ == "__main__":
    unittest.main()
