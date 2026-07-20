#!/usr/bin/env python3
"""Select this case's live state from browser-exported JSON without persistence."""

from __future__ import annotations

import importlib.util
from pathlib import Path


HELPER = Path(__file__).resolve().parents[4] / "scripts" / "providers" / "cases" / "live_state.py"
SPEC = importlib.util.spec_from_file_location("web_protocol_recovery_live_state", HELPER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"could not load live-state helper: {HELPER}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
CONFIG = {"storageKeys":["b1","b1b1","dsllt","dsl","sc"],"optionalCookies":["id_token","web_session","acw_tc","unread"],"cookieNamePatterns":[],"requiredCookies":["a1"]}


if __name__ == "__main__":
    raise SystemExit(MODULE.run_case(CONFIG))