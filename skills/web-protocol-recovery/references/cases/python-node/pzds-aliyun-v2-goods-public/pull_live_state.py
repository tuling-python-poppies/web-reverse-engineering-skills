"""Select current PZDS Aliyun V2 live state from an approved project root.

This helper does not access browser state and does not persist cookies/tokens.
It only validates the shape of a caller-supplied project profile path so a
reproduction runner can load current FeiLin profile data at runtime.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL = {"feilinVersion", "userAgent", "fullDeviceFields", "tokenFields", "field21", "combat511", "combat504"}


def load_profile(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    profile_path = root / "verifier" / "t001_profile.json"
    if not profile_path.is_file():
        raise FileNotFoundError(f"missing live profile: {profile_path}")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    missing = REQUIRED_TOP_LEVEL.difference(profile)
    if missing:
        raise ValueError(f"profile missing keys: {', '.join(sorted(missing))}")
    if len(profile.get("fullDeviceFields") or []) != 133:
        raise ValueError("fullDeviceFields must contain 133 entries")
    if len(profile.get("tokenFields") or []) != 133:
        raise ValueError("tokenFields must contain 133 entries")
    version = str(profile.get("feilinVersion") or "")
    if "feilin" not in version.lower():
        raise ValueError(f"unexpected FeiLin version: {version!r}")
    return {
        "profilePath": str(profile_path),
        "feilinVersion": version,
        "userAgent": profile.get("userAgent"),
        "field21": profile.get("field21"),
        "fullDeviceFieldCount": len(profile["fullDeviceFields"]),
        "tokenFieldCount": len(profile["tokenFields"]),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate an approved PZDS Aliyun V2 project profile")
    parser.add_argument("project_root")
    args = parser.parse_args()
    print(json.dumps(load_profile(args.project_root), ensure_ascii=False, indent=2))
