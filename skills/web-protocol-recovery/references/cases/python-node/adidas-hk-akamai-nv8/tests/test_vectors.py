from __future__ import annotations

import contextlib
import importlib.util
import io
import unittest
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parents[1]
ENTRY_PATH = CASE_DIR / "entry.py"
SPEC = importlib.util.spec_from_file_location("adidas_hk_akamai_nv8_entry", ENTRY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load case entry")
entry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(entry)


class AdidasHkAkamaiNv8CaseTests(unittest.TestCase):
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
        result = entry.run(live=False, with_nv8=False)
        self.assertEqual(result["status"], "offline")
        self.assertEqual(result["caseId"], "adidas-hk-akamai-nv8")
        self.assertEqual(result["productCount"], 3)
        self.assertTrue(result["acceptance"]["rejectsLiveEgress"])

    def test_live_egress_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "offline-only"):
            entry.run(live=True)

    def test_run_reports_nv8_availability(self) -> None:
        result = entry.run(live=False, with_nv8=True)
        self.assertIn(result["nv8"]["status"], {"executed", "unavailable"})

    def test_console_report_prints_data(self) -> None:
        result = entry.run(live=False, with_nv8=False)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            entry._print_report(result)
        output = buffer.getvalue()
        self.assertIn("[1]", output)
        self.assertIn("[3]", output)
        self.assertIn("pomCpnC--BzlJThIWBEYnu9r", output)
        self.assertIn("JI1234", output)
        self.assertIn("Classic Track Pants", output)

    def test_nv8_chain_produces_validated_sensor_artifact(self) -> None:
        """NV8 executor segment; skips when no NV8 install / supported Node is available.

        Case code carries no local absolute paths: the install root must come
        from `NV8_ROOT` (or a case-local `node_modules/nv8`).
        """
        available, detail = entry.nv8_availability()
        if not available:
            self.skipTest(detail)
        artifact = entry.run_nv8_chain()
        self.assertEqual(artifact["status"], "executed")
        self.assertIn("pomCpnC", artifact["sensorEndpoint"])
        self.assertGreaterEqual(int(artifact["bodyByteLength"]), 4000)
        self.assertIn(artifact["outcome"], {"replayed", "replay-miss:missing"})


if __name__ == "__main__":
    unittest.main()
