"""Select current PZDS live prerequisites from an approved project root.

Importing this module performs no network traffic and writes no files. It only
validates project-local profile/session shapes and reports missing gates for the
next agent question. Credentials are never stored in the case library.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_PROFILE_TOP_LEVEL = {
    "feilinVersion",
    "userAgent",
    "fullDeviceFields",
    "tokenFields",
    "field21",
    "combat511",
    "combat504",
}
REQUIRED_SESSION_KEYS = {"token"}
OPTIONAL_SESSION_KEYS = {"pzId", "deviceId", "globalId"}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


def load_profile(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    profile_path = root / "verifier" / "t001_profile.json"
    if not profile_path.is_file():
        raise FileNotFoundError(f"missing live profile: {profile_path}")
    profile = _load_json(profile_path)
    missing = REQUIRED_PROFILE_TOP_LEVEL.difference(profile)
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
        "profilePath": str(profile_path.relative_to(root)).replace("\\", "/"),
        "feilinVersion": version,
        "userAgent": profile.get("userAgent"),
        "field21": profile.get("field21"),
        "fullDeviceFieldCount": len(profile["fullDeviceFields"]),
        "tokenFieldCount": len(profile["tokenFields"]),
    }


def load_session(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    session_path = root / "js_reverse_cache" / "pzds_session.json"
    if not session_path.is_file():
        raise FileNotFoundError(f"missing login session: {session_path}")
    session = _load_json(session_path)
    missing = [key for key in REQUIRED_SESSION_KEYS if not str(session.get(key) or "").strip()]
    if missing:
        raise ValueError(f"session missing keys: {', '.join(missing)}")
    present_optional = {
        key: bool(str(session.get(key) or "").strip()) for key in OPTIONAL_SESSION_KEYS
    }
    token = str(session["token"]).strip()
    return {
        "sessionPath": str(session_path.relative_to(root)).replace("\\", "/"),
        "hasToken": True,
        "tokenLength": len(token),
        "optional": present_optional,
    }


def inspect_project(project_root: str | Path) -> dict[str, Any]:
    """Return readiness of project-local live prerequisites without secrets."""
    root = Path(project_root).resolve()
    result: dict[str, Any] = {
        "projectRoot": str(root),
        "profile": None,
        "session": None,
        "missing": [],
        "nextAsk": [],
        "readyForPureProtocol": False,
    }

    try:
        result["profile"] = load_profile(root)
    except Exception as exc:
        result["missing"].append("feilinProfile")
        result["nextAsk"].append(
            "project is missing a current verifier/t001_profile.json that matches "
            f"the live DeviceConfig.version ({exc})"
        )

    try:
        result["session"] = load_session(root)
    except Exception as exc:
        result["missing"].append("loginSession")
        result["nextAsk"].append(
            "login session missing or incomplete. Ask the user for username and password "
            "for one project-local protocol login. Store credentials only in project "
            f"config.local.json (gitignored); never write them into the case library ({exc})"
        )

    result["readyForPureProtocol"] = not result["missing"]
    if result["readyForPureProtocol"]:
        result["nextAsk"] = []
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate PZDS project-local profile/session prerequisites"
    )
    parser.add_argument("project_root")
    parser.add_argument(
        "--mode",
        choices=("inspect", "profile", "session"),
        default="inspect",
    )
    args = parser.parse_args()
    if args.mode == "profile":
        payload = load_profile(args.project_root)
    elif args.mode == "session":
        payload = load_session(args.project_root)
    else:
        payload = inspect_project(args.project_root)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
