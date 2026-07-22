"""Select approved live state for bangkokair-reese84-booking (memory-only).

Import-safe. Does not open network. Does not write files.
Caller supplies a browser storage_state-like dict (cookies list).
"""

from __future__ import annotations

from typing import Any


REQUIRED_COOKIE_NAMES = ("reese84",)
OPTIONAL_COOKIE_NAME_PREFIXES = (
    "visid_incap_",
    "incap_ses_",
    "nlbi_",
)
OPTIONAL_COOKIE_NAMES = ("___utmvc", "prxCookie", "xctrc")


def select_cookies(storage_state: dict[str, Any]) -> dict[str, str]:
    """Return name->value for required/optional cookies from a Playwright-like state."""
    out: dict[str, str] = {}
    for c in storage_state.get("cookies") or []:
        name = c.get("name") or ""
        value = c.get("value") or ""
        if not name or not value:
            continue
        if name in REQUIRED_COOKIE_NAMES or name in OPTIONAL_COOKIE_NAMES:
            out[name] = value
            continue
        if any(name.startswith(p) for p in OPTIONAL_COOKIE_NAME_PREFIXES):
            out[name] = value
    missing = [n for n in REQUIRED_COOKIE_NAMES if n not in out]
    if missing:
        raise KeyError(f"missing required cookies: {missing}")
    return out


def select_reese84(storage_state: dict[str, Any]) -> str:
    cookies = select_cookies(storage_state)
    return cookies["reese84"]


def redact_cookie_names(names: list[str]) -> list[str]:
    """Helper for reports: return names only."""
    return sorted(set(names))
