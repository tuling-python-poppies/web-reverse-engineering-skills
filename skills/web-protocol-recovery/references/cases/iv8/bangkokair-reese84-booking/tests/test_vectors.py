"""Offline tests for bangkokair-reese84-booking (no network)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(CASE_DIR))

from entry import build_search_payload, parse_flights, run  # noqa: E402
from pull_live_state import select_cookies, select_reese84  # noqa: E402


class VectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vectors = json.loads(
            (CASE_DIR / "fixtures" / "vectors.json").read_text(encoding="utf-8")
        )

    def test_import_safe_offline_run(self):
        result = run(live=False)
        self.assertEqual(result["status"], "offline")
        self.assertEqual(result["flights"], [])

    def test_build_search_payload_shape(self):
        payload = build_search_payload("BKK", "CNX", "2026-08-12")
        expected = self.vectors["searchRequestShape"]
        self.assertEqual(payload["commercialFareFamilies"], expected["commercialFareFamilies"])
        self.assertEqual(
            payload["itineraries"][0]["originLocationCode"],
            expected["itineraries"][0]["originLocationCode"],
        )
        self.assertTrue(payload["itineraries"][0]["isRequestedBound"])

    def test_parse_flights_from_sample(self):
        sample = self.vectors["searchResponseSample"]
        rows = parse_flights(sample)
        self.assertGreaterEqual(len(rows), 1)
        first = rows[0]
        exp = self.vectors["expectedParsedFirstRow"]
        self.assertEqual(first["flight"], exp["flight"])
        self.assertEqual(first["origin"], exp["origin"])
        self.assertEqual(first["destination"], exp["destination"])
        self.assertEqual(first["depart"], exp["depart"])
        self.assertEqual(first["arrive"], exp["arrive"])
        self.assertEqual(first["fare_family"], exp["fare_family"])
        self.assertEqual(first["total"], exp["total"])
        self.assertEqual(first["currency"], exp["currency"])

    def test_pull_live_state_requires_reese(self):
        with self.assertRaises(KeyError):
            select_cookies({"cookies": [{"name": "other", "value": "x"}]})
        state = {
            "cookies": [
                {"name": "reese84", "value": "dummy-token"},
                {"name": "visid_incap_1", "value": "v"},
            ]
        }
        self.assertEqual(select_reese84(state), "dummy-token")
        selected = select_cookies(state)
        self.assertIn("reese84", selected)
        self.assertIn("visid_incap_1", selected)


if __name__ == "__main__":
    unittest.main()
