from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


CASE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_ROOT))

import entry  # noqa: E402


class PurePythonJdH5stTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vectors = json.loads((CASE_ROOT / "fixtures" / "vectors.json").read_text(encoding="utf-8"))

    def test_body_hash(self) -> None:
        vector = self.vectors["bodySha256"]
        body = entry.build_body(
            page=vector["page"],
            page_count=vector["pageCount"],
            start_pos=vector["startPos"],
        )
        self.assertEqual(entry.body_sha256(body), vector["expected"])

    def test_jd_hash_vectors(self) -> None:
        vector = self.vectors["jdHash"]
        self.assertEqual(entry.jd_se_data("abcdefg"), vector["seDataAbcdefg"])
        self.assertEqual(entry.jd_md5("abc"), vector["md5Abc"])
        self.assertEqual(entry.jd_sha256("abc"), vector["sha256Abc"])

    def test_jd_base64_vectors(self) -> None:
        vector = self.vectors["jdBase64"]
        self.assertEqual(entry.jd_base64_encode(""), vector["empty"])
        self.assertEqual(entry.jd_base64_encode("abc"), vector["abc"])
        self.assertEqual(entry.jd_base64_encode('{"a":1}'), vector["jsonObject"])

    def test_synthetic_h5st_shape(self) -> None:
        vector = self.vectors["syntheticMaterial"]
        body = entry.build_body()
        h5st, meta = entry.sign_h5st(
            body,
            {"tk": vector["tk"], "fp": vector["fp"], "rd": vector["rd"]},
            timestamp_ms=vector["timestampMs"],
            env_timestamp_ms=vector["envTimestampMs"],
            env_random_values=tuple(vector["envRandomValues"]),
        )
        segments = h5st.split(";")
        self.assertEqual(len(segments), vector["h5stSegments"])
        self.assertEqual(segments[1], vector["fp"])
        self.assertEqual(segments[2], entry.APP_ID)
        self.assertEqual(segments[3], vector["tk"])
        self.assertEqual(segments[4], vector["signature"])
        self.assertEqual(meta["signature"], vector["signature"])

    def test_parse_products(self) -> None:
        payload = json.loads((CASE_ROOT / "fixtures" / "response.sample.json").read_text(encoding="utf-8"))
        products = entry.parse_products(payload)
        self.assertEqual(products[0]["sku"], "10000000000001")
        self.assertEqual(products[0]["price"], "99.00")
        self.assertEqual(products[0]["shopId"], 10001)

    def test_redacted_live_proof_summary(self) -> None:
        proof = json.loads(
            (CASE_ROOT / "fixtures" / "live-proof.summary.json").read_text(encoding="utf-8")
        )
        self.assertEqual(proof["caseId"], "pure-python-jd-h5st")
        self.assertEqual(proof["runtime"], "pure-python")
        self.assertTrue(proof["passed"])
        self.assertGreaterEqual(proof["businessRowsObserved"], 1)
        self.assertIn("no live tk", proof["secretPolicy"])


if __name__ == "__main__":
    unittest.main()
