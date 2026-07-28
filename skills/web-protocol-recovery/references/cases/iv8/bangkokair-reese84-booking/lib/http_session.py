# Offline-only shim. Historical implementation:
# references/case-live-reference-archive/iv8/bangkokair-reese84-booking/lib/http_session.py

from __future__ import annotations

BOOKING_ORIGIN = "https://digital.bangkokair.com"
ENTRY_URL = f"{BOOKING_ORIGIN}/booking/availability/0"
API_HOST = "https://api-des.bangkokair.com"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36"
)

BASE_HEADERS = {
    "User-Agent": UA,
    "Accept-Language": "en-GB,en;q=0.9",
    "Origin": BOOKING_ORIGIN,
    "Referer": ENTRY_URL,
}


def _reject_case_live_egress(action: str = "live HTTP") -> None:
    raise RuntimeError(
        f"case lib refuses {action}: offline-only. "
        "See references/case-live-reference-archive/iv8/bangkokair-reese84-booking/lib/http_session.py"
    )


def make_session():  # type: ignore[no-untyped-def]
    _reject_case_live_egress("make_session")


def browser_headers(extra: dict | None = None, reese: str | None = None) -> dict:
    h = dict(BASE_HEADERS)
    if reese:
        h["x-d-token"] = reese
    if extra:
        h.update(extra)
    return h


def install_reese_cookie(session, token: str, cookie_domain: str = "bangkokair.com") -> None:  # type: ignore[no-untyped-def]
    _reject_case_live_egress("install_reese_cookie")
