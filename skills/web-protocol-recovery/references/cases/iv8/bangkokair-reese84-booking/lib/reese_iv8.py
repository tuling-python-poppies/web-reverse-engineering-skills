# Offline-only shim. Historical implementation:
# references/case-live-reference-archive/iv8/bangkokair-reese84-booking/lib/reese_iv8.py

from __future__ import annotations


def _reject_case_live_egress(action: str = "live HTTP") -> None:
    raise RuntimeError(
        f"case lib refuses {action}: offline-only. "
        "See references/case-live-reference-archive/iv8/bangkokair-reese84-booking/lib/reese_iv8.py"
    )


def generate_reese84(*args, **kwargs):  # type: ignore[no-untyped-def]
    _reject_case_live_egress("generate_reese84")
