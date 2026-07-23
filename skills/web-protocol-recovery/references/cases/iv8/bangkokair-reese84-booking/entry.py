"""Bangkok Air Reese84 booking availability (sanitized case entry).

Import-safe: no network and no file I/O on import.

Modes:
  - offline (default): no network; status=offline
  - l1 live: requires reese84 cookie + oauth client env; business search only
  - l2 live: pure iv8 generates reese84 then business search
  - l3 live: two cold pure-iv8 sessions

Env:
  CASE_LIVE=1|true|yes
  CASE_MODE=l1|l2|l3   (default l3 when live)
  REESE84 / BANGKOKAIR_CLIENT_ID / BANGKOKAIR_CLIENT_SECRET
"""

from __future__ import annotations

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


def _business_search(
    session: Any,
    reese: str,
    *,
    origin: str,
    dest: str,
    depart_in_days: int,
    client_id: str,
    client_secret: str,
    log: Any,
) -> dict[str, Any]:
    from lib.http_session import browser_headers, install_reese_cookie  # type: ignore

    install_reese_cookie(session, reese)
    base_headers = browser_headers(reese=reese)

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
                "client_id": client_id,
                "client_secret": client_secret,
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
        "reese_len": len(reese),
        "token_sha256": hashlib.sha256(reese.encode()).hexdigest(),
    }


def _run_l1(
    *,
    reese84: str | None,
    origin: str,
    dest: str,
    depart_in_days: int,
    client_id: str | None,
    client_secret: str | None,
    log: Any,
) -> dict[str, Any]:
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
    out = _business_search(
        session,
        token_cookie,
        origin=origin,
        dest=dest,
        depart_in_days=depart_in_days,
        client_id=cid,
        client_secret=csec,
        log=log,
    )
    out["mode"] = "l1"
    return out


def _run_l2_iv8(
    *,
    origin: str,
    dest: str,
    depart_in_days: int,
    client_id: str | None,
    client_secret: str | None,
    log: Any,
) -> dict[str, Any]:
    cid = client_id or os.environ.get(ENV_CLIENT_ID)
    csec = client_secret or os.environ.get(ENV_CLIENT_SECRET)
    if not cid or not csec:
        raise RuntimeError(
            f"oauth client missing: set {ENV_CLIENT_ID} and {ENV_CLIENT_SECRET}"
        )

    # ensure case dir import path for lib/
    if str(CASE_DIR) not in sys.path:
        sys.path.insert(0, str(CASE_DIR))

    from lib.challenge_discover import discover_challenge  # type: ignore
    from lib.http_session import ENTRY_URL, browser_headers, make_session  # type: ignore
    from lib.reese_iv8 import generate_reese84  # type: ignore

    session = make_session()
    headers = browser_headers({"Accept": "text/html"})
    entry = session.get(ENTRY_URL, headers=headers, timeout=30)
    log.info("entry status={} bytes={}", entry.status_code, len(entry.content))
    challenge_url, challenge_js = discover_challenge(session, entry, headers)
    log.info(
        "challenge url={} size={} sha={}",
        challenge_url,
        len(challenge_js),
        hashlib.sha256(challenge_js.encode("utf-8", errors="ignore")).hexdigest()[:16],
    )
    gen = generate_reese84(
        session,
        entry_url=str(entry.url),
        entry_html=entry.text,
        challenge_url=challenge_url,
        challenge_js=challenge_js,
    )
    reese = gen["token"]
    out = _business_search(
        session,
        reese,
        origin=origin,
        dest=dest,
        depart_in_days=depart_in_days,
        client_id=cid,
        client_secret=csec,
        log=log,
    )
    out["mode"] = "l2-iv8"
    out["challenge_url"] = gen.get("challenge_url")
    out["challenge_sha256"] = gen.get("challenge_sha256")
    out["exchange_count"] = len(gen.get("exchanges") or [])
    return out


def _run_l3_iv8(**kwargs: Any) -> dict[str, Any]:
    import time

    log = kwargs.get("log") or _logger()
    runs = []
    for i in range(2):
        log.info("==== L3 cold session {}/2 ====", i + 1)
        t0 = time.time()
        try:
            one = _run_l2_iv8(**kwargs)
            one["session_index"] = i + 1
            one["elapsed_s"] = round(time.time() - t0, 2)
            runs.append(one)
        except Exception as e:
            runs.append(
                {
                    "session_index": i + 1,
                    "status": "fail",
                    "error": f"{type(e).__name__}: {e}"[:500],
                    "elapsed_s": round(time.time() - t0, 2),
                }
            )
        time.sleep(1.0)
    ok = all(r.get("status") == "success" and r.get("count", 0) > 0 for r in runs)
    tokens = [r.get("token_sha256") for r in runs if r.get("token_sha256")]
    distinct = len(set(tokens)) == len(tokens) and len(tokens) == 2
    return {
        "status": "success" if ok else "fail",
        "caseId": CASE_ID,
        "mode": "l3-iv8",
        "sessions_ok": sum(1 for r in runs if r.get("status") == "success"),
        "distinct_tokens": distinct,
        "count": sum(int(r.get("count") or 0) for r in runs if r.get("status") == "success"),
        "runs": [
            {
                "session_index": r.get("session_index"),
                "status": r.get("status"),
                "count": r.get("count"),
                "reese_len": r.get("reese_len"),
                "token_sha256": r.get("token_sha256"),
                "challenge_sha256": r.get("challenge_sha256"),
                "elapsed_s": r.get("elapsed_s"),
                "error": r.get("error"),
            }
            for r in runs
        ],
        # keep offline-test friendly key
        "flights": (runs[0].get("flights") if runs and runs[0].get("status") == "success" else []),
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
    mode: str | None = None,
) -> dict[str, Any]:
    """Run offline demo or approved live path.

    live=False (default): no network.
    live=True:
      mode=l1 cookie replay
      mode=l2 pure iv8 generate + search
      mode=l3 two cold pure-iv8 sessions (default when live and mode omitted)
    """
    log = _logger()
    if not live:
        return {
            "status": "offline",
            "caseId": CASE_ID,
            "flights": [],
            "note": "pass live=True; CASE_MODE=l1|l2|l3 (default l3 for pure iv8)",
        }

    resolved = (mode or os.environ.get("CASE_MODE") or "l3").strip().lower()
    if resolved not in {"l1", "l2", "l3"}:
        resolved = "l3"

    kwargs = {
        "origin": origin,
        "dest": dest,
        "depart_in_days": depart_in_days,
        "client_id": client_id,
        "client_secret": client_secret,
        "log": log,
    }
    if resolved == "l1":
        return _run_l1(reese84=reese84, **kwargs)
    if resolved == "l2":
        return _run_l2_iv8(**kwargs)
    return _run_l3_iv8(**kwargs)


def main() -> None:
    live = os.environ.get("CASE_LIVE", "").strip().lower() in {"1", "true", "yes"}
    mode = os.environ.get("CASE_MODE")
    result = run(live=live, mode=mode)
    print(
        json.dumps(
            {
                "status": result.get("status"),
                "mode": result.get("mode"),
                "count": result.get("count", 0),
                "sessions_ok": result.get("sessions_ok"),
                "distinct_tokens": result.get("distinct_tokens"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
