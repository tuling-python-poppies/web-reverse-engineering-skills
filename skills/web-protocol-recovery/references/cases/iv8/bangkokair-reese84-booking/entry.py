# Offline-only case entry for unit tests and local proof.
# Historical full implementation (including live L1/L2/L3 paths):
#   references/case-live-reference-archive/iv8/bangkokair-reese84-booking/
# Final live egress: projectRoot main.py + python-collector work-order.

"""Bangkok Air Reese84 booking availability (offline case entry).

Import-safe: no network and no file I/O on import.
Live modes are archived; case library only supports offline fixture helpers.
"""
from __future__ import annotations


def _reject_case_live_egress(action: str = "live HTTP") -> None:
    raise RuntimeError(
        f"case entry refuses {action}: offline-only. "
        "Historical code: references/case-live-reference-archive/iv8/bangkokair-reese84-booking/. "
        "Use project main.py + python-collector for live egress."
    )

import hashlib
import json
import os
import sys
import urllib.parse
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

CASE_ID = "iv8-bangkokair-reese84-booking"
CASE_DIR = Path(__file__).resolve().parent
API_HOST = "https://api-des.bangkokair.com"
BOOKING_ORIGIN = "https://digital.bangkokair.com"
DEFAULT_ORIGIN = "BKK"
DEFAULT_DEST = "CNX"
DEFAULT_DAYS = 21
ENV_CLIENT_ID = "BANGKOKAIR_CLIENT_ID"
ENV_CLIENT_SECRET = "BANGKOKAIR_CLIENT_SECRET"
ENV_REESE = "REESE84"


def _logger():
    try:
        from utils.logger import logger  # type: ignore

        return logger
    except Exception:

        class _PrintLogger:
            @staticmethod
            def info(message, *args):
                if args:
                    try:
                        message = message.format(*args)
                    except Exception:
                        message = str(message) + " " + " ".join(map(str, args))
                out = getattr(sys.stdout, "buffer", None)
                if out:
                    out.write((message + "\n").encode("utf-8", errors="replace"))
                    out.flush()
                else:
                    print(message)

        return _PrintLogger()


def parse_flights(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse air-bounds JSON into compact flight rows (offline-safe)."""
    groups = ((data.get("data") or {}).get("airBoundGroups")) or []
    flights_dict = ((data.get("dictionaries") or {}).get("flight")) or {}
    rows: list[dict[str, Any]] = []
    for g in groups:
        bd = g.get("boundDetails") or {}
        origin = bd.get("originLocationCode")
        dest = bd.get("destinationLocationCode")
        duration_sec = bd.get("duration") or 0
        for ab in g.get("airBounds") or []:
            av = (ab.get("availabilityDetails") or [{}])[0]
            flight_id = av.get("flightId")
            fmeta = flights_dict.get(flight_id) or {}
            dep = (fmeta.get("departure") or {}).get("dateTime")
            arr = (fmeta.get("arrival") or {}).get("dateTime")
            flight_no = None
            if fmeta:
                flight_no = (
                    f"{fmeta.get('marketingAirlineCode', '')}"
                    f"{fmeta.get('marketingFlightNumber', '')}"
                )
            total_prices = ((ab.get("prices") or {}).get("totalPrices")) or []
            price = total_prices[0] if total_prices else {}
            rows.append(
                {
                    "flight": flight_no or flight_id,
                    "origin": origin,
                    "destination": dest,
                    "depart": dep,
                    "arrive": arr,
                    "duration_min": int(duration_sec) // 60 if duration_sec else None,
                    "fare_family": ab.get("fareFamilyCode"),
                    "cabin": av.get("cabin"),
                    "booking_class": av.get("bookingClass"),
                    "quota": av.get("quota"),
                    "base": price.get("base"),
                    "taxes": price.get("totalTaxes"),
                    "total": price.get("total"),
                    "currency": price.get("currencyCode"),
                    "cheapest": ab.get("isCheapestOffer"),
                }
            )
    rows.sort(
        key=lambda x: (
            x.get("total") is None,
            x.get("total") or 10**12,
            x.get("depart") or "",
        )
    )
    return rows


def build_search_payload(
    origin: str,
    dest: str,
    depart_date: str,
    fare_families: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "commercialFareFamilies": fare_families or ["PGPROMO"],
        "itineraries": [
            {
                "originLocationCode": origin,
                "destinationLocationCode": dest,
                "departureDateTime": f"{depart_date}T00:00:00.000",
                "isRequestedBound": True,
            }
        ],
        "travelers": [{"passengerTypeCode": "ADT"}],
        "searchPreferences": {"showSoldOut": False, "showMilesPrice": False},
    }


def _business_search(*args, **kwargs):
    _reject_case_live_egress('_business_search')


def _run_l1(*args, **kwargs):
    _reject_case_live_egress('_run_l1')


def _run_l2_iv8(*args, **kwargs):
    _reject_case_live_egress('_run_l2_iv8')


def _run_l3_iv8(*args, **kwargs):
    _reject_case_live_egress('_run_l3_iv8')


def run(
    *,
    reese84: str | None = None,
    origin: str = DEFAULT_ORIGIN,
    dest: str = DEFAULT_DEST,
    depart_in_days: int = DEFAULT_DAYS,
    client_id: str | None = None,
    client_secret: str | None = None,
    live: bool = False,
    mode: str | None = None,
) -> dict[str, Any]:
    """Run offline demo or approved live path.

    live=False (default): no network.
    live=True:
      mode=l1 cookie replay
      mode=l2 pure iv8 generate + search
      mode=l3 two cold pure-iv8 sessions (default when live and mode omitted)
    """
    if live:
        _reject_case_live_egress("run(live=True)")
    return {
        "status": "offline",
        "caseId": CASE_ID,
        "flights": [],
        "note": "offline-only; historical live under case-live-reference-archive",
    }


def main() -> None:
    result = run(live=False)
    print(
        json.dumps(
            {
                "status": result.get("status"),
                "note": result.get("note"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
