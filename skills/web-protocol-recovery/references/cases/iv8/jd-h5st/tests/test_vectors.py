"""Offline tests for iv8-jd-h5st (no network)."""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR))

from entry import (  # noqa: E402
    APP_ID,
    DEFAULT_BODY,
    _load_sign_materials,
    body_sha256,
    parse_products,
    run,
    sign_h5st,
)


class JdH5stVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vectors = json.loads(
            (CASE_DIR / "fixtures" / "vectors.json").read_text(encoding="utf-8")
        )
        cls.sample = json.loads(
            (CASE_DIR / "fixtures" / "response.sample.json").read_text(encoding="utf-8")
        )

    def test_import_safe_offline_run(self) -> None:
        result = run(live=False)
        self.assertEqual(result["status"], "offline")
        self.assertGreaterEqual(result["product_count"], 1)

    def test_body_sha256_matches_vector(self) -> None:
        raw = self.vectors["signInput"]["bodyRaw"]
        expected = self.vectors["signInput"]["bodySha256"]
        self.assertEqual(body_sha256(raw), expected)
        self.assertEqual(
            hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            expected,
        )

    def test_parse_products_from_sample(self) -> None:
        products = parse_products(self.sample["response"])
        self.assertEqual(len(products), 2)
        first = products[0]
        self.assertEqual(first["sku"], "10000000000001")
        self.assertEqual(first["name"], "Sample Product A")
        self.assertEqual(first["price"], "99.00")
        self.assertIn("item.m.jd.com", first["link"])
        self.assertTrue(first["img"].startswith("//") or first["img"].startswith("http"))
        self.assertEqual(first["shopId"], 10001)

    def test_h5st_shape_rules_documented(self) -> None:
        shape = self.vectors["h5stShape"]
        self.assertGreaterEqual(shape["minLength"], 200)
        self.assertEqual(shape["containsAppIdSegment"], "2088b")
        self.assertEqual(shape["segmentSeparator"], ";")

    def test_frozen_bundle_generates_h5st(self) -> None:
        js_code, index_html, source = _load_sign_materials(prefer_live=False)
        h5st = sign_h5st(js_code, index_html, DEFAULT_BODY)
        shape = self.vectors["h5stShape"]

        self.assertEqual(source, "frozen-assets")
        self.assertGreaterEqual(len(h5st), shape["minLength"])
        self.assertIn(APP_ID, h5st.split(shape["segmentSeparator"]))

    def test_acceptance_matrix_documents_frozen_vs_live(self) -> None:
        matrix = self.vectors["acceptanceMatrix"]
        self.assertGreaterEqual(len(matrix), 2)
        by_key = {(row["bundle"], row["functionId"]): row for row in matrix}
        frozen_rec = by_key[("historical-frozen-assets", "recommend_like_m")]
        live_rec = by_key[("live-js_security_v3_main", "recommend_like_m")]
        self.assertTrue(frozen_rec["expectSignNonEmpty"])
        self.assertEqual(frozen_rec["expectHttp"], 403)
        self.assertFalse(frozen_rec["expectProducts"])
        self.assertEqual(live_rec["expectHttp"], 200)
        self.assertTrue(live_rec["expectProducts"])
        self.assertTrue(self.vectors["invalidation"]["nonEmptyH5stNotEnough"])

    def test_offline_proof_binds_current_entry_and_test(self) -> None:
        proof = json.loads(
            (CASE_DIR / "fixtures" / "offline-proof.summary.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(proof["activeScope"], "offline-only")
        self.assertFalse(proof["historicalLiveProofIsCurrentAcceptance"])
        self.assertEqual(
            proof["entrySha256"],
            hashlib.sha256((CASE_DIR / "entry.py").read_bytes()).hexdigest(),
        )
        self.assertEqual(
            proof["testArtifactSha256"],
            hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        )

    def test_live_run_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "offline-only"):
            run(live=True)


if __name__ == "__main__":
    unittest.main()
