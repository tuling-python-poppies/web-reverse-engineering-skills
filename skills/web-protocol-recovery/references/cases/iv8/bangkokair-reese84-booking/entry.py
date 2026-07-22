"""Bangkok Air Reese84 booking availability (sanitized case entry).

Import-safe: no network and no file I/O on import.
Live run requires an approved liveState export (reese84) and work-order gates.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

# Import-safe: optional deps resolved only when run() is called.


CASE_ID = "iv8-bangkokair-reese84-booking"
API_HOST = "https://api-des.bangkokair.com"
BOOKING_ORIGIN = "https://digital.bangkokair.com"
DEFAULT_ORIGIN = "BKK"
DEFAULT_DEST = "CNX"
DEFAULT_DAYS = 21
# Public SPA client ids are site-specific; override via env for rotation.
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
                    message = message.format(*args)
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


def run(
    *,
    reese84: str | None = None,
    origin: str = DEFAULT_ORIGIN,
    dest: str = DEFAULT_DEST,
    depart_in_days: int = DEFAULT_DAYS,
    client_id: str | None = None,
    client_secret: str | None = None,
    live: bool = False,
) -> dict[str, Any]:
    """Run offline parse demo or approved live search.

    live=False (default): no network; returns empty flights with status offline.
    live=True: requires reese84 (arg or REESE84 env) and curl_cffi; performs OAuth + search.
    """
    log = _logger()
    if not live:
        return {
            "status": "offline",
            "caseId": CASE_ID,
            "flights": [],
            "note": "pass live=True with approved reese84 to execute live egress",
        }

    token_cookie = reese84 or os.environ.get(ENV_REESE)
    if not token_cookie:
        raise RuntimeError("reese84 missing: pass reese84= or set REESE84")

    cid = client_id or os.environ.get(ENV_CLIENT_ID)
    csec = client_secret or os.environ.get(ENV_CLIENT_SECRET)
    if not cid or not csec:
        raise RuntimeError(
            f"oauth client missing: set {ENV_CLIENT_ID} and {ENV_CLIENT_SECRET}"
        )

    from curl_cffi import requests  # type: ignore

    session = requests.Session(impersonate="chrome136")
    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    )
    base_headers = {
        "User-Agent": ua,
        "Accept-Language": "en-GB,en;q=0.9",
        "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Origin": BOOKING_ORIGIN,
        "Referer": f"{BOOKING_ORIGIN}/booking/availability/0",
        "x-d-token": token_cookie,
    }
    session.cookies.set("reese84", token_cookie, domain="bangkokair.com", path="/")

    log.info("Getting OAuth token...")
    oauth = session.post(
        f"{API_HOST}/v1/security/oauth2/token",
        headers={
            **base_headers,
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": f"{BOOKING_ORIGIN}/",
        },
        data=urllib.parse.urlencode(
            {
                "client_id": cid,
                "client_secret": csec,
                "grant_type": "client_credentials",
            }
        ),
        timeout=30,
    )
    oauth.raise_for_status()
    access = oauth.json().get("access_token")
    if not access:
        raise RuntimeError("oauth missing access_token")

    depart_date = (
        datetime.now(timezone.utc) + timedelta(days=depart_in_days)
    ).strftime("%Y-%m-%d")
    payload = build_search_payload(origin, dest, depart_date)

    log.info("Searching air-bounds {} -> {} {}", origin, dest, depart_date)
    search = session.post(
        f"{API_HOST}/v2/search/air-bounds",
        headers={
            **base_headers,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access}",
            "Ama-Client-Ref": f"case/{uuid.uuid4()}",
        },
        json=payload,
        timeout=60,
    )
    if search.status_code >= 400:
        raise RuntimeError(f"search failed {search.status_code}")
    data = search.json()
    if data.get("errors") and not data.get("data"):
        raise RuntimeError(f"search errors: {data.get('errors')}")

    rows = parse_flights(data)
    return {
        "status": "success",
        "caseId": CASE_ID,
        "origin": origin,
        "destination": dest,
        "date": depart_date,
        "count": len(rows),
        "flights": rows,
    }


def main() -> None:
    # Default offline path for import/compile safety demos.
    live = os.environ.get("CASE_LIVE", "").strip() in {"1", "true", "yes"}
    result = run(live=live)
    print(json.dumps({"status": result.get("status"), "count": result.get("count", 0)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
