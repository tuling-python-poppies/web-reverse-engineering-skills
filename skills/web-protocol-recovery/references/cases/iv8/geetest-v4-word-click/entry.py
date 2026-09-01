"""Offline Geetest GT4 word-click wire helpers.

This entry has no network, browser, runtime, or file side effects on import.
The task project may use iv8 to produce the encrypted ``w`` artifact; this
case entry proves only the stable word-click input and coordinate boundary.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence


WIRE_SCALE = 10000


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).strip().lower()


def validate_word_load(data: Dict[str, Any]) -> Dict[str, Any]:
    if data.get("risk_type") != "word":
        raise ValueError("GT4 word-click requires risk_type=word")
    if data.get("captcha_type") != "word":
        raise ValueError("GT4 word-click requires captcha_type=word")
    if not isinstance(data.get("imgs"), str) or not data["imgs"]:
        raise ValueError("GT4 word-click requires imgs")
    questions = data.get("ques")
    if not isinstance(questions, list) or not questions or not all(isinstance(item, str) and item for item in questions):
        raise ValueError("GT4 word-click requires non-empty ques[]")
    required = ("lot_number", "payload", "process_token", "payload_protocol", "pt", "pow_detail")
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError("same-round load data missing: " + ", ".join(missing))
    return data


def validate_pixel_points(points: Sequence[Sequence[Any]], width: int, height: int) -> List[List[int]]:
    if width <= 0 or height <= 0:
        raise ValueError("image dimensions must be positive")
    if not points:
        raise ValueError("word-click requires at least one point")
    result: List[List[int]] = []
    for point in points:
        if len(point) != 2:
            raise ValueError("each point must be [x, y]")
        x, y = int(point[0]), int(point[1])
        if not (0 <= x < width and 0 <= y < height):
            raise ValueError(f"point outside image: {[x, y]}")
        result.append([x, y])
    return result


def pixel_points_to_wire(points: Sequence[Sequence[Any]], width: int, height: int) -> List[List[int]]:
    pixels = validate_pixel_points(points, width, height)
    return [[round(x / width * WIRE_SCALE), round(y / height * WIRE_SCALE)] for x, y in pixels]


def build_answer(passtime: int, pixel_points: Sequence[Sequence[Any]], width: int, height: int) -> Dict[str, Any]:
    if not isinstance(passtime, int) or passtime < 0:
        raise ValueError("passtime must be a non-negative integer")
    pixels = validate_pixel_points(pixel_points, width, height)
    return {"passtime": passtime, "userresponse": pixel_points_to_wire(pixels, width, height)}


def verify_success(response: Dict[str, Any]) -> bool:
    data = response.get("data") if isinstance(response.get("data"), dict) else {}
    return response.get("status") == "success" and data.get("result") == "success" and data.get("fail_count") == 0
