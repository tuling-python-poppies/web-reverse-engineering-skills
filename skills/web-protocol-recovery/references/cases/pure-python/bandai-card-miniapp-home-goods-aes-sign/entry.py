"""Offline Bandai miniapp homepage goods signing and parsing artifact."""

from __future__ import annotations

import base64
from typing import Any

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


APP_ID = "19"
BASE_URL = "https://bdmatchapi.windoent.com"
TIME_URL = "https://appsevice.windoent.com/ct"
GOODS_PATH = "/h5/goods/index"
AES_KEY = b"DYi2KOv9UwabixY4GZCSxX=="
AES_IV = b"FQAziVSKNT1Th5wi"
SECRET_ID = "FQAziVSKNT1Th5wi"


def aes_cbc_base64(text: str) -> str:
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    encrypted = cipher.encrypt(pad(text.encode("utf-8"), AES.block_size))
    return base64.b64encode(encrypted).decode("ascii")


def build_signature(server_time: int | str) -> str:
    return aes_cbc_base64(f"{server_time}{SECRET_ID}")


def build_goods_params(
    *, page: int = 1, limit: int = 10, category_id: int = 0, is_home: int = 1
) -> dict[str, int]:
    if page < 1:
        raise ValueError("page must be >= 1")
    if limit < 1:
        raise ValueError("limit must be >= 1")
    return {
        "page": page,
        "limit": limit,
        "categoryId": category_id,
        "isHome": is_home,
    }


def build_headers(server_time: int | str, mini_version: str = "1.0.0") -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Mini-User-Agent": f"windoentMini/{mini_version}",
        "signature": build_signature(server_time),
        "Token": "",
    }


def parse_goods_response(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a JSON object")
    data = payload.get("data", [])
    if not isinstance(data, list):
        raise ValueError("payload.data must be a list")
    return {
        "code": payload.get("code"),
        "message": payload.get("message"),
        "count": payload.get("count", len(data)),
        "goods": data,
    }


def run(*, live: bool = False) -> None:
    if live:
        raise RuntimeError(
            "case entry is offline-only; use the project main.py for live egress"
        )
