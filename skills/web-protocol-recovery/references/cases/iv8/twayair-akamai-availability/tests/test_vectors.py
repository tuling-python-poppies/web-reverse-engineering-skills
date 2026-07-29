# Offline vector tests for the T'way Akamai case.
# Parser test uses a synthetic availability fragment; no network on import/run.

import hashlib
import json
import re
import unittest
from pathlib import Path


CASE_DIR = Path(__file__).resolve().parents[1]

FARE_NAMES = {
    "EventFare": "event",
    "SmartFare": "smart",
    "NormalFare": "normal",
}
SOLD_OUT_TEXT = "매진"
CHECKED_BAGGAGE_PATTERN = re.compile(r"묵료\s*위탁수하물\s*:\s*([^\s]+)|묻료\s*위탁수하물\s*:\s*([^\s]+)|위탁수하물\s*:\s*([^\s]+)")

HTML = """
<ul>
  <li class="price_list section_list_item">
    <button class="bul_air_info" data-dispflightnumber="TW303"></button>
    <div class="segmentInfo"
         data-aircraftprovider="B737-8"
         data-flightdate="2026-07-16"
         data-departureairportcode="ICN"
         data-departuretime="10:50"
         data-arrivalairportcode="KIX"
         data-arrivaltime="13:00"
         data-journeytime="02:10"
         data-stops="0"></div>
    <div class="rate_box">
      <input class="tripInfo" data-faretype="SmartFare">
      <div class="segmentInfo" data-bookingclass="W"></div>
      <div class="rate_price">KRW 302,400 3석</div>
      <div>묻료 위탁수하물 : 15KG</div>
    </div>
    <div class="rate_box soldout">
      <input class="tripInfo" data-faretype="EventFare">
      <div class="segmentInfo" data-bookingclass="D"></div>
      <div class="rate_price">매진</div>
      <div>묻료 위탁수하물 : 없음</div>
    </div>
  </li>
</ul>
"""


def _text(node):
    return node.get_text(" ", strip=True) if node else ""


def _integer(value):
    return int(value.replace(",", "")) if value else None


def parse_availability(page_html):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(page_html, "lxml")
    flights = []
    for item in soup.select("li.price_list.section_list_item"):
        button = item.select_one("button.bul_air_info")
        segments = item.select(".segmentInfo")
        if not button or not segments:
            continue
        primary = segments[0]
        inputs = item.select("input.tripInfo")
        fares = []
        for index, box in enumerate(item.select(".rate_box")):
            fare_input = inputs[index] if index < len(inputs) else None
            segment = box.select_one(".segmentInfo")
            price_text = _text(box.select_one(".rate_price"))
            box_text = _text(box)
            price_match = re.search(r"([A-Z]{3})\s*([\d,]+)", price_text)
            seats_match = re.search(r"(\d+)\s*석", price_text)
            baggage_match = CHECKED_BAGGAGE_PATTERN.search(box_text)
            baggage = next(
                (group for group in (baggage_match.groups() if baggage_match else []) if group),
                None,
            )
            raw_fare_type = str(fare_input.get("data-faretype") or "") if fare_input else ""
            fares.append(
                {
                    "fare_type": FARE_NAMES.get(raw_fare_type, raw_fare_type),
                    "booking_class": str(segment.get("data-bookingclass") or "") if segment else None,
                    "currency": price_match.group(1) if price_match else "KRW",
                    "price": _integer(price_match.group(2)) if price_match else None,
                    "seats": int(seats_match.group(1)) if seats_match else 0,
                    "sold_out": bool(box.select_one(".soldout, .soldout_txt") or SOLD_OUT_TEXT in price_text),
                    "cabin_baggage_kg": 10,
                    "checked_baggage": baggage,
                }
            )
        flights.append(
            {
                "flight_number": button.get("data-dispflightnumber") or _text(button),
                "aircraft": primary.get("data-aircraftprovider"),
                "date": primary.get("data-flightdate"),
                "departure": {
                    "airport": primary.get("data-departureairportcode"),
                    "time": primary.get("data-departuretime"),
                },
                "arrival": {
                    "airport": primary.get("data-arrivalairportcode"),
                    "time": primary.get("data-arrivaltime"),
                },
                "duration": str(primary.get("data-journeytime") or ""),
                "stops": int(str(primary.get("data-stops") or "0")),
                "fares": fares,
            }
        )
    return flights


class AvailabilityParserTest(unittest.TestCase):
    def test_parses_available_and_sold_out_fares(self):
        flights = parse_availability(HTML)

        self.assertEqual(len(flights), 1)
        self.assertEqual(flights[0]["flight_number"], "TW303")
        self.assertEqual(flights[0]["departure"], {"airport": "ICN", "time": "10:50"})
        self.assertEqual(flights[0]["arrival"], {"airport": "KIX", "time": "13:00"})
        self.assertEqual(
            flights[0]["fares"][0],
            {
                "fare_type": "smart",
                "booking_class": "W",
                "currency": "KRW",
                "price": 302400,
                "seats": 3,
                "sold_out": False,
                "cabin_baggage_kg": 10,
                "checked_baggage": "15KG",
            },
        )
        self.assertTrue(flights[0]["fares"][1]["sold_out"])
        self.assertEqual(flights[0]["fares"][1]["checked_baggage"], "없음")


class OfflineVectorShapeTest(unittest.TestCase):
    def test_vectors_file_shape(self):
        vectors = json.loads(
            (CASE_DIR / "fixtures" / "vectors.json").read_text(
                encoding="utf-8"
            )
        )
        expected = vectors["offline_bridge"]["expected"]
        self.assertEqual(expected["post_count"], 1)
        self.assertEqual(expected["signal_count"], 116)
        self.assertEqual(expected["worker_message_count"], 1)
        self.assertEqual(expected["runtime_error_count"], 0)


class OfflineBridgeProbeTest(unittest.TestCase):
    def test_run_offline_probe(self):
        import subprocess
        import sys

        try:
            import iv8  # noqa: F401
        except ImportError:
            self.skipTest("iv8 runtime not installed")

        completed = subprocess.run(
            [sys.executable, "entry.py"],
            cwd=CASE_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
        json_start = completed.stdout.rfind("{")
        self.assertGreaterEqual(json_start, 0, completed.stdout)
        result = json.loads(completed.stdout[json_start:])
        self.assertEqual(result["post_count"], 1)
        self.assertEqual(result["signal_count"], 116)
        self.assertEqual(result["worker_message_count"], 1)
        self.assertEqual(result["runtime_error_count"], 0)


class OfflineProofBindingTest(unittest.TestCase):
    def test_offline_proof_binds_current_entry_and_test(self):
        proof = json.loads(
            (CASE_DIR / "fixtures" / "offline-proof.summary.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(proof["caseId"], "iv8-twayair-akamai-availability")
        self.assertEqual(proof["activeScope"], "offline-only")
        self.assertTrue(proof["passed"])
        self.assertFalse(proof["historicalLiveProofIsCurrentAcceptance"])
        self.assertEqual(
            proof["entrySha256"],
            hashlib.sha256((CASE_DIR / "entry.py").read_bytes()).hexdigest(),
        )
        self.assertEqual(
            proof["testArtifactSha256"],
            hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
