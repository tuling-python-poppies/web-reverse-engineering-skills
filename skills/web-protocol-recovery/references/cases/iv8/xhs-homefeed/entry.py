"""Offline-only Xiaohongshu mnsv2 artifact entry.

The case entry never downloads bundles, reads account state, or sends HTTP.
Project delivery supplies current cookies/state in memory and Python owns live
HTTP egress outside the case library.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


CASE_DIR = Path(__file__).resolve().parent
RUNTIME_PATH = CASE_DIR / "assets" / "mnsv2_runtime.js"
APP_ID = "xhs-pc-web"


def _reject_live(action: str) -> None:
    raise RuntimeError(
        f"case entry refuses {action}: offline-only; use project main.py for live egress"
    )


def load_runtime(*, live: bool = False) -> str:
    """Load the frozen runtime source without side effects."""
    if live:
        _reject_live("live runtime download")
    return RUNTIME_PATH.read_text(encoding="utf-8")


def canonical_md5(url: str, data: Any = None) -> tuple[str, str]:
    body = "" if data is None else json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return hashlib.md5((url + body).encode("utf-8")).hexdigest(), hashlib.md5(url.encode("utf-8")).hexdigest()


def vector_shape(url: str, data: Any = None) -> dict[str, Any]:
    """Return deterministic signer inputs and the accepted mnsv2 shape."""
    u, p = canonical_md5(url, data)
    return {
        "url": url,
        "data_type": "object" if isinstance(data, dict) else "" if data is None else type(data).__name__,
        "u": u,
        "p": p,
        "x3_prefix": "mns",
        "x3_min_length": 32,
        "header_names": ["x-s", "x-t", "x-s-common"],
    }


def run(*, live: bool = False) -> dict[str, Any]:
    if live:
        _reject_live("live HTTP")
    vectors = json.loads((CASE_DIR / "fixtures" / "vectors.json").read_text(encoding="utf-8"))
    return {
        "status": "offline",
        "caseId": "iv8-xhs-homefeed",
        "vector_count": len(vectors["vectors"]),
        "runtime_sha256": hashlib.sha256(load_runtime().encode("utf-8")).hexdigest(),
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False))
