"""Select current PZDS live prerequisites from an approved project root.

Importing this module performs no network traffic and writes no files. It only
validates project-local profile/session shapes and reports missing gates for the
next agent question. Credentials are never stored in the case library.
"""

from __future__ import annotations

import json
import os
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
PRIVATE_STATE_ROOT = Path("js_reverse_cache") / "private" / "pzds"
PROFILE_RELATIVE_PATH = PRIVATE_STATE_ROOT / "t001_profile.json"
SESSION_RELATIVE_PATH = PRIVATE_STATE_ROOT / "session.json"
SUPPORTED_DEVICE_FIELD_COUNTS = frozenset({111, 133, 142})
FILE_ATTRIBUTE_REPARSE_POINT = 0x400


def _is_reparse_point(path: Path) -> bool:
    try:
        attributes = getattr(os.stat(path, follow_symlinks=False), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    return bool(attributes & FILE_ATTRIBUTE_REPARSE_POINT)


def _plain_project_root(project_root: str | Path) -> Path:
    root = Path(os.path.abspath(os.fspath(project_root)))
    current = Path(root.anchor)
    for part in root.parts[1:]:
        current /= part
        if not os.path.lexists(current):
            continue
        if current.is_symlink() or _is_reparse_point(current):
            raise ValueError(f"project root contains a reparse path: {current}")
    if not root.is_dir():
        raise ValueError(f"project root is not a directory: {root}")
    return root


def _plain_project_file(root: Path, relative: Path) -> Path:
    path = root
    for part in relative.parts:
        path /= part
        if not os.path.lexists(path):
            continue
        if path.is_symlink() or _is_reparse_point(path):
            raise ValueError(f"project state path contains a reparse path: {path}")
    if not path.is_file() or os.stat(path, follow_symlinks=False).st_nlink != 1:
        raise ValueError(f"expected plain regular project state file: {path}")
    return path


def _require_raw_secret_handling(confirmed: bool) -> None:
    if confirmed is not True:
        raise PermissionError(
            "raw-secret-handling confirmation is required before loading persisted "
            "PZDS profile or session state"
        )


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


def _require_string_list(
    profile: dict[str, Any],
    field: str,
    supported_counts: frozenset[int],
) -> list[str]:
    value = profile.get(field)
    if not isinstance(value, list) or len(value) not in supported_counts or not all(
        isinstance(item, str) for item in value
    ):
        raise ValueError(
            f"{field} must be a list of {sorted(supported_counts)} strings"
        )
    return value


def load_profile(
    project_root: str | Path, *, raw_secret_handling_confirmed: bool = False
) -> dict[str, Any]:
    _require_raw_secret_handling(raw_secret_handling_confirmed)
    root = _plain_project_root(project_root)
    try:
        profile_path = _plain_project_file(root, PROFILE_RELATIVE_PATH)
    except ValueError as error:
        if not os.path.lexists(root / PROFILE_RELATIVE_PATH):
            raise FileNotFoundError(f"missing live profile: {root / PROFILE_RELATIVE_PATH}") from error
        raise
    profile = _load_json(profile_path)
    missing = REQUIRED_PROFILE_TOP_LEVEL.difference(profile)
    if missing:
        raise ValueError(f"profile missing keys: {', '.join(sorted(missing))}")
    full_device_fields = _require_string_list(
        profile,
        "fullDeviceFields",
        SUPPORTED_DEVICE_FIELD_COUNTS,
    )
    token_fields = _require_string_list(
        profile,
        "tokenFields",
        SUPPORTED_DEVICE_FIELD_COUNTS,
    )
    if len(token_fields) != len(full_device_fields):
        raise ValueError("tokenFields length must match fullDeviceFields length")
    version = profile.get("feilinVersion")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("feilinVersion must be a nonempty string")
    if "feilin" not in version.lower():
        raise ValueError(f"unexpected FeiLin version: {version!r}")
    user_agent = profile.get("userAgent")
    if not isinstance(user_agent, str) or not user_agent.strip():
        raise ValueError("userAgent must be a nonempty string")
    field21 = profile.get("field21")
    if not isinstance(field21, dict) or not all(
        isinstance(field21.get(key), str) and field21[key]
        for key in ("sourceKey", "xorMaskHex")
    ):
        raise ValueError("field21 must include nonempty sourceKey and xorMaskHex strings")
    for field in ("combat511", "combat504"):
        if not isinstance(profile.get(field), dict):
            raise ValueError(f"{field} must be an object")
    return {
        "profilePath": str(profile_path.relative_to(root)).replace("\\", "/"),
        "feilinVersion": version,
        "userAgent": user_agent,
        "hasField21": True,
        "fullDeviceFieldCount": len(full_device_fields),
        "tokenFieldCount": len(token_fields),
    }


def load_session(
    project_root: str | Path, *, raw_secret_handling_confirmed: bool = False
) -> dict[str, Any]:
    _require_raw_secret_handling(raw_secret_handling_confirmed)
    root = _plain_project_root(project_root)
    try:
        session_path = _plain_project_file(root, SESSION_RELATIVE_PATH)
    except ValueError as error:
        if not os.path.lexists(root / SESSION_RELATIVE_PATH):
            raise FileNotFoundError(f"missing login session: {root / SESSION_RELATIVE_PATH}") from error
        raise
    session_data = _load_json(session_path)
    missing = [
        key
        for key in REQUIRED_SESSION_KEYS
        if not isinstance(session_data.get(key), str) or not session_data[key].strip()
    ]
    if missing:
        raise ValueError(f"session missing keys: {', '.join(missing)}")
    present_optional = {
        key: isinstance(session_data.get(key), str) and bool(session_data[key].strip())
        for key in OPTIONAL_SESSION_KEYS
    }
    token = session_data["token"].strip()
    return {
        "sessionPath": str(session_path.relative_to(root)).replace("\\", "/"),
        "hasToken": True,
        "tokenLength": len(token),
        "optional": present_optional,
    }


def inspect_project(
    project_root: str | Path, *, raw_secret_handling_confirmed: bool = False
) -> dict[str, Any]:
    """Return readiness of project-local live prerequisites without secrets."""
    root = _plain_project_root(project_root)
    result: dict[str, Any] = {
        "projectRoot": str(root),
        "profile": None,
        "session": None,
        "missing": [],
        "nextAsk": [],
        "readyForPureProtocol": False,
    }

    if not raw_secret_handling_confirmed:
        result["missing"].append("rawSecretHandling")
        result["nextAsk"].append(
            "raw-secret-handling confirmation is required before loading persisted "
            "PZDS profile/session state under js_reverse_cache/private/pzds/**"
        )
        return result

    try:
        result["profile"] = load_profile(root, raw_secret_handling_confirmed=True)
    except Exception as exc:
        result["missing"].append("feilinProfile")
        result["nextAsk"].append(
            "project is missing a current js_reverse_cache/private/pzds/t001_profile.json that matches "
            f"the live DeviceConfig.version ({exc})"
        )

    try:
        result["session"] = load_session(root, raw_secret_handling_confirmed=True)
    except Exception as exc:
        result["missing"].append("loginSession")
        result["nextAsk"].append(
            "login session missing or incomplete. Ask the user for username and password "
            "for one project-local protocol login and keep them in memory unless a separate "
            f"raw-secret-handling decision permits persistence ({exc})"
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
    parser.add_argument(
        "--raw-secret-handling-confirmed",
        action="store_true",
        help="Required before this selector reads persisted profile/session state.",
    )
    args = parser.parse_args()
    if args.mode == "profile":
        payload = load_profile(
            args.project_root,
            raw_secret_handling_confirmed=args.raw_secret_handling_confirmed,
        )
    elif args.mode == "session":
        payload = load_session(
            args.project_root,
            raw_secret_handling_confirmed=args.raw_secret_handling_confirmed,
        )
    else:
        payload = inspect_project(
            args.project_root,
            raw_secret_handling_confirmed=args.raw_secret_handling_confirmed,
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
