# Offline-only case entry.
# Historical full implementation (may include former live paths):
#   references/case-live-reference-archive/iv8/geetest-v4-word-click/entry.py
# Final live egress: projectRoot main.py + python-collector work-order.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CASE_ID = 'iv8-geetest-v4-word-click'
CASE_DIR = Path(__file__).resolve().parent


def _reject_case_live_egress(action: str = "live HTTP") -> None:
    raise RuntimeError(
        f"case entry refuses {action}: offline-only. "
        f"Historical code: references/case-live-reference-archive/iv8/geetest-v4-word-click/entry.py. "
        "Use project main.py + python-collector for live egress."
    )


def run(*, live: bool = False) -> dict[str, Any]:
    """Import-safe offline placeholder for the case library."""
    if live:
        _reject_case_live_egress("run(live=True)")
    sample = CASE_DIR / "fixtures" / "response.sample.json"
    note = "offline-only case library entry; full historical script in case-live-reference-archive"
    if sample.exists():
        return {"status": "offline", "caseId": CASE_ID, "hasSample": True, "note": note}
    return {"status": "offline", "caseId": CASE_ID, "hasSample": False, "note": note}


def main() -> None:
    print(json.dumps(run(live=False), ensure_ascii=False))


if __name__ == "__main__":
    main()
