# Verifier Replay Playbook

Platform-specific captcha workflows now live next to this file and are selected by `../PROVIDER.md`. Use this file only for unknown captcha families or generic round binding, visual solver, coordinate normalization, and artifact discipline. When a migrated workflow matches the platform, that workflow is authoritative for request order, fields, dynamic helpers, and success markers.

Use this Provider reference when:

- data requests are gated behind captcha, one-shot verification, or click-order challenges
- there is no meaningful business signer, but requests still fail until a verifier passes
- browser clicks appear to unlock the next request

## Core rule

The verifier output is the real dynamic parameter.

## Working method

1. classify the verifier family before lifting fields:
   - slider, point-click, ordered-click, rotate, or another verifier branch
   - old and new generations of one vendor can still have incompatible fields and proof builders
2. freeze one verifier round end to end:
   - prehandle or load response
   - callback ids or random keys
   - asset URLs and downloaded images
   - verifier token, work factor, or round id
   - final verify request and response
3. determine what output authorizes the next business request
4. split the answer path by verifier type:
   - point-click or ordered-click: prompt extraction, hit localization, proof packaging
   - slider or image-derived: restored-image coordinate, display coordinate, submitted coordinate, behavior trace
5. solve or reconstruct that output locally
6. replay the verifier in protocol form
7. send the business request with the resulting token, cookie, coordinates, or grant

## Bootstrap framing

When prehandle or load returns JSONP, freeze the requested callback value and the raw response together. Validate the exact `callback(<json>)` envelope, parse the inner JSON once, and retain both forms; do not use broad parenthesis stripping or treat the callback as cosmetic when later fields bind to it. Malformed callback framing, a mismatched callback id, or trailing executable text fails closed before solver work.

## Local visual solver pattern

For visual captcha candidate generation, use local `ddddocr` first and fall back to local OpenCV/Pillow logic when the model errors, returns no boxes, or produces weak slider confidence. OCR and CV outputs are candidates only; the verifier response is the proof.

Backend order:

1. `ddddocr` Python package for text OCR, point-click target detection, slider matching, and two-image comparison
2. OpenCV/Pillow for preprocessing, template matching, image difference, contour detection, bbox cleanup, and coordinate sanity checks
3. fail clearly when the captcha requires text OCR and `ddddocr` is unavailable or cannot read the prompt

Keep the solver in-process. Do not add a long-running OCR process, port, daemon, or remote dependency to the collector.

### ddddocr modes

Use one cached instance per mode. Do not instantiate `DdddOcr` for every image.

```python
from __future__ import annotations

from typing import Any

import ddddocr


_OCR: Any = None
_DET: Any = None
_SLIDE: Any = None


def ocr_client(*, beta: bool = False, use_gpu: bool = False, device_id: int = 0) -> Any:
    global _OCR
    if _OCR is None:
        _OCR = ddddocr.DdddOcr(
            ocr=True,
            det=False,
            beta=beta,
            use_gpu=use_gpu,
            device_id=device_id,
            show_ad=False,
        )
    return _OCR


def det_client(*, use_gpu: bool = False, device_id: int = 0) -> Any:
    global _DET
    if _DET is None:
        _DET = ddddocr.DdddOcr(
            ocr=False,
            det=True,
            use_gpu=use_gpu,
            device_id=device_id,
            show_ad=False,
        )
    return _DET


def slide_client() -> Any:
    global _SLIDE
    if _SLIDE is None:
        _SLIDE = ddddocr.DdddOcr(ocr=False, det=False, show_ad=False)
    return _SLIDE
```

Use the mode that matches the action:

- prompt text or cropped character OCR: `DdddOcr(ocr=True, det=False)` then `classification(...)`
- point-click candidate boxes: `DdddOcr(ocr=False, det=True)` then `detection(...)`
- slider image matching: `DdddOcr(ocr=False, det=False)` then `slide_match(...)`
- full image difference: `DdddOcr(ocr=False, det=False)` then `slide_comparison(...)`

Calling `classification` on a detection instance raises a mode error. Calling `detection` on an OCR instance raises a mode error. Keep separate cached clients.

### Text OCR helper

Prefer bytes from the captured verifier round. `ddddocr` also accepts file paths, `pathlib.Path`, and `PIL.Image`, but bytes make artifacts easier to freeze and replay.

```python
def ocr_text(
    image_bytes: bytes,
    *,
    png_fix: bool = False,
    charset_range: int | str | list[str] | None = None,
    probability: bool = False,
    color_filter_colors: list[str] | None = None,
    color_filter_custom_ranges: list[tuple[tuple[int, int, int], tuple[int, int, int]]] | None = None,
) -> str | dict[str, Any]:
    ocr = ocr_client()
    if charset_range is not None:
        ocr.set_ranges(charset_range)

    kwargs: dict[str, Any] = {"png_fix": png_fix, "probability": probability}
    if color_filter_colors:
        kwargs["color_filter_colors"] = color_filter_colors
    if color_filter_custom_ranges:
        kwargs["color_filter_custom_ranges"] = color_filter_custom_ranges

    return ocr.classification(image_bytes, **kwargs)
```

Useful `ddddocr` OCR knobs:

- `png_fix=True` for transparent PNG prompts that render black/transparent in the raw asset
- `probability=True` when you need per-character confidence and want to reject weak prompt OCR
- `set_ranges(0)` for numeric-only prompts
- `set_ranges("0123456789+-x/=")` for math captchas or restricted alphabets
- `beta=True` when the default OCR model is weak for the prompt family
- `color_filter_colors=["red", "blue"]` or custom HSV ranges when the prompt uses strong color separation

When color filter argument names differ across installed versions, inspect the local `classification` signature and adapt the project helper. Keep this adaptation local to the helper, not scattered across collector code.

### Point-click target detection helper

```python
def ddddocr_detect_boxes(background_bytes: bytes) -> list[list[int]]:
    boxes = det_client().detection(background_bytes)
    return [[int(x1), int(y1), int(x2), int(y2)] for x1, y1, x2, y2 in boxes]


def box_center(box: list[int]) -> tuple[float, float]:
    x1, y1, x2, y2 = box
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0
```

Point-click or ordered-click flow:

1. OCR the prompt image into ordered symbols/classes
2. detect candidate boxes on the background image
3. crop each candidate box and OCR the crop when the challenge requires character matching
4. match prompt order to candidate boxes
5. convert raw image centers to rendered display coordinates, then to submitted proof coordinates
6. verify with the server and require a successful verifier response

Do not submit raw detection boxes directly. Detection output is in image pixel space, not necessarily display or verifier proof space.

### Slider helper

```python
from math import isfinite
from typing import Any


def normalize_slide_result(
    result: Any,
    *,
    min_confidence: float,
    image_width: int,
    image_height: int,
) -> tuple[int, int, float] | None:
    if isinstance(min_confidence, bool) or not isinstance(min_confidence, (int, float)):
        return None
    min_confidence = float(min_confidence)
    if not isfinite(min_confidence) or not 0.0 < min_confidence <= 1.0:
        return None
    if isinstance(image_width, bool) or isinstance(image_height, bool):
        return None
    if not isinstance(image_width, int) or not isinstance(image_height, int):
        return None
    if image_width <= 0 or image_height <= 0:
        return None
    if not isinstance(result, dict):
        return None

    confidence = result.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return None
    confidence = float(confidence)
    if not isfinite(confidence) or not 0.0 <= confidence <= 1.0 or confidence < min_confidence:
        return None

    target = result.get("target")
    if isinstance(target, (list, tuple)) and len(target) >= 2:
        raw_x, raw_y = target[0], target[1]
    elif "target_x" in result and "target_y" in result:
        raw_x, raw_y = result["target_x"], result["target_y"]
    else:
        return None

    if isinstance(raw_x, bool) or isinstance(raw_y, bool):
        return None
    if not isinstance(raw_x, (int, float)) or not isinstance(raw_y, (int, float)):
        return None
    raw_x = float(raw_x)
    raw_y = float(raw_y)
    if not isfinite(raw_x) or not isfinite(raw_y):
        return None
    if not 0.0 <= raw_x < image_width or not 0.0 <= raw_y < image_height:
        return None
    return int(raw_x), int(raw_y), confidence


def ddddocr_slide_x(
    target_bytes: bytes,
    background_bytes: bytes,
    *,
    background_width: int,
    background_height: int,
    simple_target: bool = False,
    min_confidence: float = 0.50,
) -> tuple[int, dict[str, Any]] | None:
    result = slide_client().slide_match(
        target_bytes,
        background_bytes,
        simple_target=simple_target,
    )
    normalized = normalize_slide_result(
        result,
        min_confidence=min_confidence,
        image_width=background_width,
        image_height=background_height,
    )
    if normalized is None:
        return None
    target_x, _target_y, _confidence = normalized
    return target_x, result


def ddddocr_comparison_xy(
    target_bytes: bytes,
    background_bytes: bytes,
    *,
    background_width: int,
    background_height: int,
    min_confidence: float = 0.50,
) -> tuple[int, int, dict[str, Any]] | None:
    result = slide_client().slide_comparison(target_bytes, background_bytes)
    normalized = normalize_slide_result(
        result,
        min_confidence=min_confidence,
        image_width=background_width,
        image_height=background_height,
    )
    if normalized is None:
        return None
    target_x, target_y, _confidence = normalized
    return target_x, target_y, result
```

Pass the captured background's decoded pixel width and height, not rendered CSS dimensions. Use `simple_target=True` for slider pieces without a useful transparent edge. Use `slide_comparison` when the verifier gives a gapped image and a full image rather than a separate slider piece. Some installed versions omit confidence; treat that shape as unverified and corroborate it with an independent OpenCV result before any live verify instead of inventing confidence.

### OpenCV fallback snippets

Use OpenCV after `ddddocr` errors, returns no boxes, or returns weak confidence. Keep the fallback deterministic and save the raw CV result next to the verifier round artifacts.

```python
import cv2
import numpy as np


def cv_decode(image_bytes: bytes, flags: int = cv2.IMREAD_COLOR):
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), flags)
    if image is None:
        raise RuntimeError("OpenCV could not decode captcha image")
    return image


def cv_template_x(target_bytes: bytes, background_bytes: bytes) -> int:
    target = cv_decode(target_bytes, cv2.IMREAD_GRAYSCALE)
    background = cv_decode(background_bytes, cv2.IMREAD_GRAYSCALE)
    target_edges = cv2.Canny(target, 50, 150)
    background_edges = cv2.Canny(background, 50, 150)
    result = cv2.matchTemplate(background_edges, target_edges, cv2.TM_CCOEFF_NORMED)
    _min_val, _max_val, _min_loc, max_loc = cv2.minMaxLoc(result)
    return int(max_loc[0])


def cv_diff_target(gapped_bytes: bytes, full_bytes: bytes) -> tuple[int, int]:
    gapped = cv_decode(gapped_bytes)
    full = cv_decode(full_bytes)
    diff = cv2.absdiff(gapped, full)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    _threshold, binary = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    contours, _hierarchy = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise RuntimeError("OpenCV found no difference contour")
    x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))
    return int(x + w / 2), int(y + h / 2)


def cv_contour_boxes(image_bytes: bytes) -> list[list[int]]:
    image = cv_decode(image_bytes)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _threshold, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _hierarchy = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    height, width = gray.shape[:2]
    min_area = max(16, int(width * height * 0.0002))
    boxes: list[list[int]] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w * h < min_area or w < 3 or h < 3:
            continue
        boxes.append([int(x), int(y), int(x + w), int(y + h)])
    return sorted(boxes, key=lambda item: (item[1], item[0]))
```

Use OpenCV preprocessing before OCR when the prompt is noisy:

```python
def cv_threshold_bytes(image_bytes: bytes) -> bytes:
    image = cv_decode(image_bytes)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _threshold, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    ok, encoded = cv2.imencode(".png", binary)
    if not ok:
        raise RuntimeError("OpenCV could not encode preprocessed image")
    return encoded.tobytes()
```

### Artifact discipline for visual solver rounds

Save enough evidence to debug whether the failure is OCR, CV, coordinate transform, behavior trace, or protocol state:

- prompt image, background image, target image, and any reconstructed/restored image
- `ddddocr` raw result for OCR, detection, slider match, or comparison
- OpenCV raw result when fallback was used
- crop images and crop OCR labels for point-click challenges
- raw image coordinate, display coordinate, submitted coordinate, and transform math
- verifier request and verifier response from the same round
- business request proof after verifier success

## Common traps

- hunting for a fake business-layer signer while ignoring the verifier
- automating clicks instead of understanding the verifier payload
- treating the verifier as UI-only behavior
- mixing token, images, callbacks, or proof fields across adjacent verifier rounds
- treating prompt OCR or image matching alone as proof of verifier success
- mixing restored-image pixels, rendered UI coordinates, and submitted proof coordinates
- carrying fields from one verifier family or generation into another because the page role looks similar
- using a detection-mode `DdddOcr` instance for text OCR, or an OCR-mode instance for target detection
- reinitializing `DdddOcr` for every crop or slider round instead of caching per mode
- accepting low-confidence slider coordinates without OpenCV or live verifier negative controls
- defaulting a missing confidence or coordinate field to a successful value
- treating OpenCV contour order as prompt order on ordered-click challenges

## Delivery rule

Do not simulate UI interaction in the final solution. Reproduce the verifier as protocol data.
