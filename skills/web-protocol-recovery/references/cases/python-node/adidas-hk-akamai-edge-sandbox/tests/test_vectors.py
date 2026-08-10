from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


CASE_DIR = Path(__file__).resolve().parents[1]
ENTRY_PATH = CASE_DIR / "entry.py"
SPEC = importlib.util.spec_from_file_location("adidas_hk_akamai_case_entry", ENTRY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load case entry")
entry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(entry)


class AdidasHkAkamaiEdgeSandboxCaseTests(unittest.TestCase):
    def test_sensor_endpoint_derivation_removes_query_data(self) -> None:
        url = (
            "https://www.adidas.com.hk/pomCpnC--BzlJThIWBEYnu9r/"
            "example/sensor.js?v=00000000-0000-4000-8000-000000000000"
        )
        self.assertEqual(
            entry.sensor_endpoint_from_script_url(url),
            "https://www.adidas.com.hk/pomCpnC--BzlJThIWBEYnu9r/example/sensor.js",
        )

    def test_sensor_request_shape_validates(self) -> None:
        sample = entry.load_fixture("request.sample.json")
        validated = entry.validate_sensor_request(sample)
        self.assertEqual(validated["method"], "POST")
        self.assertGreaterEqual(validated["observedBytesApprox"], 4000)
        self.assertIn("pomCpnC", validated["endpoint"])

    def test_product_fixture_parses(self) -> None:
        response = entry.load_fixture("response.sample.json")
        products = entry.parse_products_from_html(response["html"])
        self.assertEqual(len(products), response["expected"]["productCount"])
        self.assertEqual(products[0]["sku"], response["expected"]["firstSku"])
        self.assertEqual(products[2]["name"], "Classic Track Pants")

    def test_run_offline(self) -> None:
        result = entry.run(live=False)
        self.assertEqual(result["status"], "offline")
        self.assertEqual(result["caseId"], "adidas-hk-akamai-edge-sandbox")
        self.assertEqual(result["productCount"], 3)
        self.assertTrue(result["acceptance"]["rejectsLiveEgress"])

    def test_live_egress_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "offline-only"):
            entry.run(live=True)


if __name__ == "__main__":
    unittest.main()
