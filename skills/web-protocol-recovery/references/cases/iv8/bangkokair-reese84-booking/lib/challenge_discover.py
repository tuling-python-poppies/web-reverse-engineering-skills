# Offline-only shim. Historical implementation:
# references/case-live-reference-archive/iv8/bangkokair-reese84-booking/lib/challenge_discover.py

from __future__ import annotations


def _reject_case_live_egress(action: str = "live HTTP") -> None:
    raise RuntimeError(
        f"case lib refuses {action}: offline-only. "
        "See references/case-live-reference-archive/iv8/bangkokair-reese84-booking/lib/challenge_discover.py"
    )


def discover_challenge(*args, **kwargs):  # type: ignore[no-untyped-def]
    _reject_case_live_egress("discover_challenge")
