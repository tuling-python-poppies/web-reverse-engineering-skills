# 脚本写作规则

生成目标站脚本时使用本文件。默认输出一个可直接运行的紧凑主 `.py` 文件；可附带 `utils/iv8_silent.py` 和 `utils/logger.py` 这种最小公共 helper，不做框架、CLI 或通用工程。

## 默认骨架

顶部放可编辑常量和缓存目录。只有 web-protocol-recovery 工作单给出绝对 `projectRoot`、`layout=web-protocol-recovery-simple`、非 `no-write` 的 `writeMode` 和精确 `allowedPaths` 后才创建 `js_reverse_cache/`。`offline-skeleton` 是验证模式，不是写入模式；`no-write` 时只在回复中给代码，不运行文件模板。

skill 自带案例的最小 JS/HTML 素材放在对应 `references/cases/iv8/<case-id>/assets/`。新任务下载的素材仍必须写入当前项目的 `js_reverse_cache/`，不要写回 skill。只有明确确认案例回写时，才按 `references/case-ingestion-rules.md` 复制最小、公开、无凭证的 frozen 素材。

读取 bundled case 时只通过 root `references/cases/registry.json` 选择一个 manifest，先读其 `PROCESS.md`，再读 `entry.py` 和当前验收所需的声明资产。不得绕过 registry 浏览 sibling 案例。

创建新任务基础模板时，默认创建 `utils/iv8_silent.py` 和 `utils/logger.py`，主脚本只导入 `import_iv8_silent()` 和 `logger`；不要在每个主脚本里重复粘贴 iv8 banner 静默代码或 loguru fallback 代码，除非用户明确要求单文件交付。进度日志用 `logger.info`，不要用裸 `print` 替代共享 logger（用户明确要求 console-only 的最终结果表除外）。动态素材只写 `js_reverse_cache/**`，禁止默认写 OS temp / AppData temp / agent temp。

所有新任务都写入 web-protocol-recovery 分配的 `web-protocol-recovery-simple` 项目根。若用户提供了旧项目或旧目录结构，把它当输入证据读取；不要继续生成旧布局。iv8 只能写这些路径：

- 稳定 helper：`utils/iv8_silent.py`、`utils/logger.py`，或工作单明确分配的 `utils/*.py`。
- 临时 probe、netLog、运行快照：`js_reverse_cache/iv8/`。
- 下载的 HTML/JS/WASM/图片等原始素材：`js_reverse_cache/source/` 或 `js_reverse_cache/iv8/`。
- 固定输入输出样本：`js_reverse_cache/samples/` 或稳定 `tests/`。
- 最终只向 Python-owned `main.py` 返回一个明确 artifact，不接管最终 HTTP、分页、持久化或业务解析。

禁止生成 `collector/`、`analysis/`、`input/`、`logs/`、provider 专用项目根或第二 landing 目录。

统一项目形态：

```text
<project-root>/
  main.py
  utils/
    iv8_silent.py
    logger.py
  js_reverse_cache/
    iv8/
    source/
    samples/
  tests/
```

如果缺少 web-protocol-recovery 指定的 `projectRoot`、目标写入路径、输入 artifact、预期输出或验收标准，先要求补齐，不要自行选择输出目录。

```python
# pyright: reportMissingImports=false
import json
import sys
import time
import urllib.parse
from pathlib import Path

import requests

from utils.iv8_silent import import_iv8_silent
from utils.logger import logger

iv8 = import_iv8_silent()


START_PAGE = 1
PAGE_COUNT = 1
PAGE_SIZE = 10
KEYWORD = ""
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
PAGE_URL = "https://example.com/page"
API_URL = "https://example.com/api"
BROWSER_BASELINE = "browser"  # browser / devtools / manual / default
ACCOUNT_SESSION_USE = "none"  # none / approved-identifiers-only / approved-account-bound
APPROVED_COOKIE_NAMES = ()  # required when using approved-identifiers-only
APPROVED_STORAGE_NAMES = ()  # use local:<key> or session:<key>
# Refuse to create files until web-protocol-recovery assigns the project root.
PROJECT_ROOT = Path("")  # approved absolute projectRoot
WRITE_MODE = ""  # project-root / no-write
if WRITE_MODE not in {"project-root", "no-write"}:
    raise RuntimeError("write mode is missing or invalid")
if WRITE_MODE == "no-write" or not PROJECT_ROOT.is_absolute():
    raise RuntimeError("an approved absolute projectRoot is required before file creation")
WORK_DIR = PROJECT_ROOT.resolve()
CACHE_ROOT = WORK_DIR / "js_reverse_cache"
CACHE_DIR = CACHE_ROOT / "iv8"
SOURCE_DIR = CACHE_ROOT / "source"
SAMPLES_DIR = CACHE_ROOT / "samples"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
BROWSER_ENV_PATH = CACHE_DIR / "browser_env.json"
```

不要添加 `sys.stdout.reconfigure(...)`。PyCharm 输出不需要它，而且可能破坏嵌入控制台。

## `utils/iv8_silent.py`

基础模板默认创建该文件，用于去除 `import iv8` 时打印的 banner。该 helper 只放通用静默导入能力，不放目标站 URL、Cookie、签名逻辑或动态素材。

```python
import contextlib
import importlib
import io
import os
import sys


@contextlib.contextmanager
def silent_import():
    sys.stdout.flush()
    sys.stderr.flush()
    stdout = sys.__stdout__ or sys.stdout
    stderr = sys.__stderr__ or sys.stderr
    saved_stdout = os.dup(stdout.fileno())
    saved_stderr = os.dup(stderr.fileno())
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, stdout.fileno())
        os.dup2(devnull, stderr.fileno())
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            yield
    finally:
        os.dup2(saved_stdout, stdout.fileno())
        os.dup2(saved_stderr, stderr.fileno())
        os.close(saved_stdout)
        os.close(saved_stderr)
        os.close(devnull)


def import_iv8_silent():
    with silent_import():
        return importlib.import_module("iv8")
```

## `utils/logger.py`

基础模板默认创建该文件，用于统一 `loguru` 可选导入和 fallback 输出。不要在主脚本重复粘贴这段逻辑，不要添加 `logger.remove()` / `logger.add()`。

```python
import sys

try:
    from loguru import logger
except ImportError:
    class PrintLogger:
        @staticmethod
        def info(message, *args):
            if args:
                message = message.format(*args)
            out = getattr(sys.stdout, "buffer", None)
            if out:
                out.write((message + "\n").encode("utf-8", errors="replace"))
                out.flush()
            else:
                print(message)

    logger = PrintLogger()
```

## 缓存规则

经用户确认且经过脱敏的自动下载或生成的目标站动态素材才写入 `CACHE_DIR`：

- challenge HTML，例如 `CACHE_DIR / "challenge.html"`。
- 下载到的保护 JS，例如 `CACHE_DIR / "rs_source_code.js"`。
- 临时 runtime JS，例如 `CACHE_DIR / "runtime_sign.js"`。
- 浏览器环境快照，例如最终 baseline `CACHE_DIR / "browser_env.json"`；`browser_env_raw.json` 仅在用户明确确认后保存。
- 调试或手工样本，例如 `CACHE_DIR / "browser_network.json"`、`CACHE_DIR / "browser_scripts.json"`、`CACHE_DIR / "manual_sample.json"`，仅在目标确实需要或用户要求时保存。
- XHR/netLog 样本，例如 `CACHE_DIR / "netlog.json"`，仅在用户明确要保存样本时保存。
- 运行报告，例如 `CACHE_DIR / "run_report.txt"`，仅在确有必要时保存。

默认不保存业务响应 JSON，不创建 `artifacts/`。

默认只打印和保存状态、长度、字段名和脱敏摘要，不打印或持久化 cookie、Authorization、token、storage、header、sign、URL 查询、请求体、响应字段、telemetry 或最终 suffix 原文。只有用户明确确认字段和保存位置后，才输出或保存原文。

案例回写是显式例外：先在当前项目完成复现和验证，再只复制最小、已脱敏的可复用素材到对应 `references/cases/iv8/<case-id>/assets/` 或 `fixtures/`。不要把运行报告、完整响应、浏览器状态或一次性抓包写入 skill。

```python
import re


def redact_text(text):
    return re.sub(
        r"(?i)(cookie|authorization|token|secret|set-cookie)(\s*[:=]\s*)[^,;\s]+",
        r"\1\2[REDACTED]",
        str(text),
    )


def save_text(name, text, *, allow_raw=False):
    if not allow_raw:
        text = redact_text(text)
    path = CACHE_DIR / name
    path.write_text(text, encoding="utf-8", errors="ignore")
    return path
```

如果需要按站点或时间分目录：

```python
RUN_DIR = CACHE_DIR / time.strftime("%Y%m%d_%H%M%S")
RUN_DIR.mkdir(exist_ok=True)
```

## 常用小函数

只添加当前脚本用得上的 helper。

### 验证码视觉候选：ddddocr 优先，OpenCV 回退

遇到滑块、点选、文字验证码时，默认使用本地 Python 包 `ddddocr` 生成视觉候选；`ddddocr` 报错、无框、低置信度或几何不稳定时，再用 OpenCV 做模板匹配、差异比较、轮廓检测和预处理回退。OCR/CV 结果只是候选，最终仍以 verifier/业务接口返回成功为准。

不要引入额外常驻进程、端口、远程 OCR 依赖或服务生命周期管理。脚本内直接 import 本地包即可。

```python
from typing import Any

import cv2
import ddddocr


_OCR: Any = None
_DET: Any = None
_SLIDE: Any = None


def ocr_client(beta=False):
    global _OCR
    if _OCR is None:
        _OCR = ddddocr.DdddOcr(ocr=True, det=False, beta=beta, show_ad=False)
    return _OCR


def det_client():
    global _DET
    if _DET is None:
        _DET = ddddocr.DdddOcr(ocr=False, det=True, show_ad=False)
    return _DET


def slide_client():
    global _SLIDE
    if _SLIDE is None:
        _SLIDE = ddddocr.DdddOcr(ocr=False, det=False, show_ad=False)
    return _SLIDE


def ocr_text(image_bytes, *, png_fix=False, charset_range=None, probability=False):
    ocr = ocr_client()
    if charset_range is not None:
        ocr.set_ranges(charset_range)  # 0=digits, or custom charset like "0123456789+-x/="
    return ocr.classification(image_bytes, png_fix=png_fix, probability=probability)


def detect_boxes(image_bytes):
    return det_client().detection(image_bytes)  # [[x1, y1, x2, y2], ...]


def slide_x(target_bytes, background_bytes, *, simple_target=False, min_confidence=0.5):
    try:
        result = slide_client().slide_match(target_bytes, background_bytes, simple_target=simple_target)
    except (ValueError, SystemError, cv2.error):
        if simple_target:
            raise
        result = slide_client().slide_match(target_bytes, background_bytes, simple_target=True)
    confidence = float(result.get("confidence", 1.0))
    if confidence < min_confidence:
        return None, result
    target = result.get("target") or [result.get("target_x", 0), result.get("target_y", 0)]
    if len(target) >= 4:
        center_x = (float(target[0]) + float(target[2])) / 2
    elif target:
        center_x = float(target[0])
    else:
        raise RuntimeError(f"ddddocr returned an invalid slide target: {result!r}")
    return round(center_x), result


def comparison_xy(gapped_bytes, full_bytes):
    result = slide_client().slide_comparison(gapped_bytes, full_bytes)
    target = result.get("target") or [result.get("target_x", 0), result.get("target_y", 0)]
    return int(target[0]), int(target[1]), result
```

OpenCV 回退只放当前任务实际需要的函数，不要铺满通用库：

```python
import cv2
import numpy as np


def cv_decode(image_bytes, flags=cv2.IMREAD_COLOR):
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), flags)
    if image is None:
        raise RuntimeError("OpenCV could not decode captcha image")
    return image


def cv_template_x(target_bytes, background_bytes):
    target = cv_decode(target_bytes, cv2.IMREAD_GRAYSCALE)
    background = cv_decode(background_bytes, cv2.IMREAD_GRAYSCALE)
    target_edges = cv2.Canny(target, 50, 150)
    background_edges = cv2.Canny(background, 50, 150)
    result = cv2.matchTemplate(background_edges, target_edges, cv2.TM_CCOEFF_NORMED)
    _, _, _, max_loc = cv2.minMaxLoc(result)
    return int(max_loc[0])


def cv_contour_boxes(image_bytes):
    image = cv_decode(image_bytes)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = gray.shape[:2]
    min_area = max(16, int(w * h * 0.0002))
    boxes = []
    for contour in contours:
        x, y, bw, bh = cv2.boundingRect(contour)
        if bw * bh >= min_area and bw >= 3 and bh >= 3:
            boxes.append([int(x), int(y), int(x + bw), int(y + bh)])
    return sorted(boxes, key=lambda item: (item[1], item[0]))
```

点选流程必须拆开记录：提示 OCR、背景候选框、框内 crop OCR、匹配决策、原图坐标到提交坐标的变换、verify 响应。滑块流程必须拆开记录：厂商、产品版本、验证码类型、协议值、原图缺口坐标、显示坐标、提交坐标、轨迹/行为字段、verify 响应。

不要默认把 `ddddocr.slide_match()` 的 `target[0]` 当成提交所需的左边缘。不同版本可能返回中心点或 `[x1,y1,x2,y2]` bbox；透明切片还可能让旧版 `simple_target=False` 触发 Pillow 的 `Coordinate 'lower' is less than 'upper'`，或在 OpenCV 4.13 中因空裁剪触发 `cv2.error: ... !_src.empty()`。必须先归一化坐标，再结合切片宽度和浏览器证据确认坐标语义，并在 reverse-process 中保存公式。例如已验证的 Geetest v4 滑块透明切片使用：

```python
move_distance = target_x - target_width / 2
scale = 0.8876 * 340 / background_width
set_left = round(move_distance * scale)
```

该公式是 `Geetest / v4 / 滑块(slide)` 的案例证据，不得不经验证套到其它厂商、版本或验证码类型。

### 响应摘要

```python
def print_response_summary(page, resp):
    try:
        payload = resp.json()
        keys = sorted(payload) if isinstance(payload, dict) else []
    except ValueError:
        keys = []
    content_type = resp.headers.get("content-type", "")
    logger.info(
        "page={} status={} content_type={} bytes={} json_keys={}",
        page,
        resp.status_code,
        content_type,
        len(resp.content),
        keys,
    )
```

Only print a bounded, redacted body after the user explicitly confirms the target and
fields. A `200` response is not success by itself: check challenge markers, the
expected content type, business result code, and a small semantic success predicate.

### 从 URL 构造 iv8 environment

```python
def build_environment(page_url):
    parsed = urllib.parse.urlparse(page_url)
    return {
        "location": {
            "href": page_url,
            "origin": f"{parsed.scheme}://{parsed.netloc}",
            "protocol": f"{parsed.scheme}:",
            "host": parsed.netloc,
            "hostname": parsed.hostname or "",
            "port": str(parsed.port or ""),
            "pathname": parsed.path or "/",
            "search": f"?{parsed.query}" if parsed.query else "",
            "hash": f"#{parsed.fragment}" if parsed.fragment else "",
        },
        "navigator": {
            "userAgent": UA,
            "platform": "Win32",
            "language": "zh-CN",
            "languages": ["zh-CN", "zh", "en"],
            "webdriver": False,
        },
    }
```

### 从浏览器快照构造 iv8 environment

当任务启用浏览器环境桥接时，先读 `references/browser-iv8-bridge.md`，默认读取 `BROWSER_ENV_PATH`。不要把多个来源的字段混拼到一个请求链路；`browser_env.json` 应当来自单一 `BROWSER_BASELINE`。

```python
IV8_ENV_KEYS = {
    "location", "navigator", "window", "screen", "document", "media", "webgl",
    "webgl2", "webgpu", "chrome", "audioContext", "visualViewport",
    "geolocation", "performance", "batteryManager", "history", "credentials",
    "clipboard", "webrtc", "video", "html", "canvas", "managed",
}
IV8_CONFIG_KEYS = {
    "timezone", "time", "fingerprint", "security", "wasm", "webgl",
    "canvas", "webgpu", "streams", "media", "permissions", "iframe", "features",
    "modelExecution",
}


def load_browser_snapshot():
    if not BROWSER_ENV_PATH.exists():
        if BROWSER_BASELINE != "default":
            raise FileNotFoundError(f"missing browser baseline: {BROWSER_ENV_PATH}")
        return {"baseline": "default", "fallback_level": 1}
    snapshot = json.loads(BROWSER_ENV_PATH.read_text(encoding="utf-8"))
    if snapshot.get("baseline") != BROWSER_BASELINE:
        raise ValueError("browser_env.json baseline does not match BROWSER_BASELINE")
    if BROWSER_BASELINE == "default" and int(snapshot.get("fallback_level", 0)) < 1:
        raise ValueError("default baseline must declare fallback_level >= 1")
    return snapshot


def deep_update(base, extra):
    for key, value in (extra or {}).items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value
    return base


def normalize_browser_snapshot(snapshot, page_url):
    environment = build_environment(page_url)
    config = {}
    env_patch = dict(snapshot.get("environment") or {})
    for key in IV8_ENV_KEYS:
        if key in snapshot and key not in env_patch:
            env_patch[key] = snapshot[key]
    if snapshot.get("userAgent"):
        env_patch.setdefault("navigator", {})["userAgent"] = snapshot["userAgent"]
    if snapshot.get("timezone"):
        config["timezone"] = snapshot["timezone"]
    config_patch = dict(snapshot.get("config") or {})
    for key in IV8_CONFIG_KEYS:
        if key in snapshot and key not in config_patch:
            config_patch[key] = snapshot[key]
    deep_update(environment, env_patch)
    deep_update(config, config_patch)
    return environment, config


def build_iv8_profile(page_url):
    return normalize_browser_snapshot(load_browser_snapshot(), page_url)


def _check_account_scope(names, account_session_use, approved_names=(), *, allow_none=False):
    names = {str(name).lower() for name in names}
    approved = {str(name).lower() for name in approved_names}
    if not names:
        return
    if account_session_use == "none":
        if allow_none:
            return
        raise PermissionError("account/session identifiers are not allowed")
    if account_session_use in {"blocked", "unknown"}:
        raise PermissionError("account/session artifacts are not approved")
    if account_session_use == "approved-identifiers-only" and not names <= approved:
        raise PermissionError(f"unapproved account/session identifiers: {sorted(names - approved)}")
    if account_session_use not in {"approved-identifiers-only", "approved-account-bound"}:
        raise PermissionError(f"invalid account/session scope: {account_session_use}")


def browser_headers(default_headers=None, *, account_session_use, approved_names=()):
    snapshot = load_browser_snapshot()
    headers = dict(snapshot.get("headers", {}))
    for key, value in (default_headers or {}).items():
        existing = next((k for k in headers if k.lower() == str(key).lower()), None)
        if existing is not None and headers[existing] != value:
            raise ValueError(f"header conflicts with selected browser baseline: {key}")
        headers.setdefault(key, value)
    raw_headers = {str(k).lower(): v for k, v in headers.items()}
    sensitive = {
        name for name in raw_headers
        if name in {"authorization", "cookie", "proxy-authorization"}
        or any(marker in name for marker in ("token", "session", "api-key"))
    }
    _check_account_scope(sensitive, account_session_use, approved_names)
    env_nav = snapshot.get("environment", {}).get("navigator", {})
    ua = snapshot.get("userAgent") or raw_headers.get("user-agent") or env_nav.get("userAgent") or snapshot.get("navigator", {}).get("userAgent") or UA
    if "user-agent" not in raw_headers:
        headers["User-Agent"] = ua
    return headers


def apply_browser_cookies(session, *, account_session_use, approved_names=()):
    snapshot = load_browser_snapshot()
    cookies = snapshot.get("cookies", {})
    if isinstance(cookies, list):
        cookie_names = {item.get("name") for item in cookies if item.get("name")}
        if account_session_use == "none" and any(item.get("accountBound") is not False for item in cookies):
            raise PermissionError("cookie metadata must prove accountBound=false for accountSessionUse=none")
    else:
        cookie_names = set(cookies)
        if cookies and account_session_use == "none":
            raise PermissionError("legacy cookie dictionaries lack account-bound metadata")
    _check_account_scope(
        cookie_names, account_session_use, approved_names,
        allow_none=account_session_use == "none",
    )
    session.cookies.clear()
    host = urllib.parse.urlparse(snapshot.get("page_url") or PAGE_URL).hostname
    if not host:
        raise ValueError("browser baseline page_url must have a hostname")
    if isinstance(cookies, list):
        for item in cookies:
            name = item.get("name")
            value = item.get("value")
            if name is not None and value is not None:
                kwargs = {"path": item.get("path") or "/"}
                if item.get("domain"):
                    kwargs["domain"] = item["domain"]
                session.cookies.set(name, value, **kwargs)
    elif isinstance(cookies, dict):
        for name, value in cookies.items():
            session.cookies.set(str(name), str(value), domain=host, path="/")
    return cookies


def apply_browser_storage(ctx, *, account_session_use, approved_names=()):
    snapshot = load_browser_snapshot()
    storage = snapshot.get("storage", {})
    local_storage = storage.get("local") or snapshot.get("localStorage") or {}
    session_storage = storage.get("session") or snapshot.get("sessionStorage") or {}
    storage_names = {f"local:{name}" for name in local_storage}
    storage_names.update(f"session:{name}" for name in session_storage)
    if account_session_use == "none" and storage_names and storage.get("accountBound") is not False:
        raise PermissionError("storage metadata must prove accountBound=false")
    _check_account_scope(
        storage_names, account_session_use, approved_names,
        allow_none=account_session_use == "none",
    )
    ctx.expose({"local": local_storage, "session": session_storage}, "browserStorage")
    ctx.eval("""
        (function() {
            var data = window.__iv8__.data.browserStorage || {};
            Object.entries(data.local || {}).forEach(function(pair) { localStorage.setItem(pair[0], String(pair[1])); });
            Object.entries(data.session || {}).forEach(function(pair) { sessionStorage.setItem(pair[0], String(pair[1])); });
        })();
    """)
    return storage
```

生成 `browser_env.json` 时建议结构：

```json
{
  "baseline": "browser",
  "fallback_level": 0,
  "userAgent": "...",
  "timezone": "Asia/Shanghai",
  "headers": {"User-Agent": "..."},
  "cookies": [
    {"name": "name", "value": "...", "domain": ".example.com", "path": "/", "accountBound": false}
  ],
  "storage": {"accountBound": false, "local": {}, "session": {}},
  "environment": {
    "navigator": {},
    "screen": {},
    "location": {}
  },
  "config": {
    "timezone": "Asia/Shanghai",
    "permissions": {},
    "time": {"mode": "logical"}
  },
  "patches": {
    "webgl": {},
    "canvas": {}
  }
}
```

如果 `cookies` 出现在快照里，脚本启动时必须显式调用 `apply_browser_cookies(session, account_session_use=ACCOUNT_SESSION_USE, approved_names=APPROVED_COOKIE_NAMES)`；`none` 只接受 `accountBound=false` 的对象列表，`approved-identifiers-only` 只接受点名 cookie，`blocked|unknown` 拒绝。通过 Permission Gate 后才用同一个 `session` 下载获准动态 JS 和发真实 API 请求。创建 iv8 context 时默认先建立正确 URL/origin，再写 storage：

```python
environment, config = build_iv8_profile(PAGE_URL)
with iv8.JSContext(environment=environment, config=config or {"timezone": "Asia/Shanghai"}) as ctx:
    # 如果使用 page.load，先同步 baseURL / location，再写 localStorage/sessionStorage。
    # 如果目标内联脚本在加载阶段就读取 storage，需要把 storage prelude 插到目标脚本之前。
    # ctx.eval("window.__iv8__.page.load(window.__iv8__.data.snapshot)")
    apply_browser_storage(
        ctx,
        account_session_use=ACCOUNT_SESSION_USE,
        approved_names=APPROVED_STORAGE_NAMES,
    )
    # 继续执行目标 JS 或触发 XHR
    pass
```

### Cookie 合并

```python
def update_session_cookies(session, cookie_text, *, domain, path="/"):
    cookies = {}
    for part in (cookie_text or "").split(";"):
        if "=" not in part:
            continue
        key, value = part.strip().split("=", 1)
        cookies[key] = value
    if cookies:
        for name, value in cookies.items():
            session.cookies.set(name, value, domain=domain, path=path)
    return cookies
```

### MessageChannel patch

仅当目标案例或目标 JS 确实需要时添加。

```python
MESSAGE_CHANNEL_PATCH = """
window.MessageChannel = __iv8__.wrapNative(function() {
    const port1 = { onmessage: null };
    const port2 = { onmessage: null };
    port1.postMessage = function(data) {
        if (port2.onmessage) setTimeout(() => port2.onmessage({data}), 0);
    };
    port2.postMessage = function(data) {
        if (port1.onmessage) setTimeout(() => port1.onmessage({data}), 0);
    };
    return { port1, port2 };
}, 'MessageChannel');
"""
```

## 翻页规则

使用顶部常量控制翻页。

```python
for page in range(START_PAGE, START_PAGE + PAGE_COUNT):
    params = build_params(page)
    headers = build_headers(params)
    resp = session.get(API_URL, params=params, headers=headers, timeout=30)
    print_response(page, resp)
```

如果 params/body/timestamp 参与签名，每一页都必须在循环里重新构造 params/body/timestamp/sign。

## Challenge Cookie 模式

适用于保护页必须在 iv8 中执行的场景。

下载或用户提供的 JavaScript 属于不可信输入。iv8 worker 必须运行在独立进程中，设置 wall-clock timeout，超时后终止，并只返回有大小上限的结果；同时设置虚拟时间和 event-step 预算，不得在无界循环中调用 `eventLoop.drain()` 或重复 `sleep()`。如果当前 iv8 binding 无法安全中断，不要在 agent 进程执行目标 bundle，改为交付离线骨架并报告缺失的运行边界。

下面的 `JSContext` 片段只描述隔离 worker 内部的业务逻辑；生成脚本必须由父进程以 deadline 启动该 worker，不能把下载 bundle 直接 eval 到 agent 或主 HTTP 进程。

```python
def run_snapshot_cookie(page_url, html, resources, headers=None):
    environment = build_environment(page_url)
    snapshot = {
        "baseURL": page_url,
        "html": html,
        "headers": headers or [],
        "resources": resources,
    }
    with iv8.JSContext(environment=environment, config={"timezone": "Asia/Shanghai"}) as ctx:
        ctx.expose(snapshot, "snapshot")
        ctx.eval("window.__iv8__.page.load(window.__iv8__.data.snapshot)")
        ctx.eval("window.__iv8__.eventLoop.sleep(100)")
        cookie_text = ctx.eval("document.cookie")
        if not cookie_text:
            cookie_text = ctx.eval("""
                var entries = window.__iv8__.netLog.entries;
                entries.length ? (entries[entries.length - 1].cookieHeader || '') : '';
            """)
        return cookie_text
```

保护源码保存到缓存目录：

```python
rs_path = save_text("rs_source_code.js", js_code)
logger.info("rs source saved = {}", rs_path)
```

## XHR Hook / 动态 URL 模式

适用于 JS SDK 改写 XHR URL 或 headers 的场景。

```python
def capture_xhr_entry(environment, js_code, init_code, api_url, params, method="GET", body=None):
    query = urllib.parse.urlencode(params, safe="*")
    request_url = f"{api_url}?{query}" if query else api_url
    with iv8.JSContext(environment=environment, config={"timezone": "Asia/Shanghai"}) as ctx:
        ctx.eval(MESSAGE_CHANNEL_PATCH)
        ctx.eval(js_code)
        if init_code:
            ctx.eval(init_code)
        entry = ctx.eval(f"""
            var xhr = new XMLHttpRequest();
            xhr.open({json.dumps(method)}, {json.dumps(request_url)}, true);
            xhr.setRequestHeader('Content-Type', 'application/json, text/plain, */*');
            xhr.send({json.dumps(body) if body is not None else 'null'});
            window.__iv8__.eventLoop.sleep(100);
            var entries = window.__iv8__.netLog.entries;
            entries[entries.length - 1];
        """, to_py=True)
    if not entry:
        raise RuntimeError("iv8 netLog did not capture the protected XHR")
    return entry
```

Python 重放时使用捕获到的 `url`、可选 `headers`、准确 body 序列化和 cookie。

## Runtime Sign 模式

适用于已知对象/函数直接返回 sign/header/token 的场景。

```python
def run_sign(js_code, call_code, page_url=PAGE_URL, page_html=""):
    with iv8.JSContext(environment=build_environment(page_url), config={"timezone": "Asia/Shanghai"}) as ctx:
        ctx.eval(MESSAGE_CHANNEL_PATCH)
        if page_html:
            ctx.eval(f"document.documentElement.innerHTML = {json.dumps(page_html)}")
        ctx.eval(js_code)
        return ctx.eval(call_code, to_py=True)
```

`call_code` 应返回字符串或 dict，便于 Python 合并进 params、headers、cookies 或 body。

## 可信输入模式

适用于 TDC 或行为采集。

```javascript
const st = window.__iv8__;
const input = st.input;
const handle = document.body || document.documentElement;

input.dispatchPointerEvent({
    type: "pointerdown",
    target: handle,
    pointerId: 1,
    pointerType: "mouse",
    isPrimary: true,
    clientX: 50,
    clientY: 400,
    button: 0,
    buttons: 1
});

st.eventLoop.sleep(16);

input.dispatchPointerEvent({
    type: "pointerup",
    target: document,
    pointerId: 1,
    pointerType: "mouse",
    isPrimary: true,
    clientX: 300,
    clientY: 400,
    button: 0,
    buttons: 0
});
```

完整轨迹循环见 registry-selected `iv8-tencent-tdc-slider` 案例的 `entry.py`。

## 依赖

默认最小导入：

```python
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests

from utils.iv8_silent import import_iv8_silent
from utils.logger import logger
```

按需添加：

- `hashlib`：MD5/SHA 签名。
- 验证码滑块缺口识别：优先 `ddddocr` + `Pillow`，回退 `cv2` + `numpy`（见下方"图像识别回退"章节）。
- `curl_cffi.requests`：目标确实需要浏览器 TLS 指纹时使用。

核心依赖缺失且用户允许安装时，只安装缺失核心包：

```bash
python -m pip install iv8 requests
```

`loguru` 是可选依赖，不默认安装。

## 图像识别回退

验证码滑块缺口识别优先使用 `ddddocr`，未安装时自动回退 `opencv`。按以下模式组织导入和函数：

```python
import io

try:
    import ddddocr
    from PIL import Image
    _HAS_DDDDOCR = True
except ImportError:
    import cv2
    import numpy as np
    _HAS_DDDDOCR = False


if _HAS_DDDDOCR:

    def find_gap(bg_bytes, sprite_bytes, crop_xy, crop_wh):
        """ddddocr 滑块识别"""
        sprite_img = Image.open(io.BytesIO(sprite_bytes))
        sx, sy = crop_xy
        sw, sh = crop_wh
        cropped = sprite_img.crop((sx, sy, sx + sw, sy + sh))

        cropped_buf = io.BytesIO()
        cropped.save(cropped_buf, format="PNG")
        cropped_bytes = cropped_buf.getvalue()

        det = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
        result = det.slide_match(cropped_bytes, bg_bytes, simple_target=True)
        x = result["target"][0]
        y = result["target"][1]
        return (x, y)

else:

    def find_gap(bg_bytes, sprite_bytes, crop_xy, crop_wh):
        """opencv 边缘检测 + 模板匹配"""
        bg_img = cv2.imdecode(np.frombuffer(bg_bytes, np.uint8), cv2.IMREAD_COLOR)
        sprite_img = cv2.imdecode(np.frombuffer(sprite_bytes, np.uint8), cv2.IMREAD_COLOR)

        sx, sy = crop_xy
        sw, sh = crop_wh
        tp_gray = cv2.cvtColor(sprite_img, cv2.COLOR_BGR2GRAY)[sy:sy + sh, sx:sx + sw]

        bg_shift = cv2.pyrMeanShiftFiltering(bg_img, 5.0, 50.0)
        tp_edges = cv2.Canny(tp_gray, 255, 255)
        bg_edges = cv2.Canny(bg_shift, 255, 255)

        match_map = cv2.matchTemplate(bg_edges, tp_edges, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc = cv2.minMaxLoc(match_map)
        return max_loc
```

完整用例见 registry-selected `iv8-tencent-tdc-slider` 案例的 `entry.py`。

## 验证

至少做语法校验：

```bash
python -m py_compile your_script.py
python -m py_compile utils/iv8_silent.py
python -m py_compile utils/logger.py
```

如果网络、Cookie、账号和目标环境允许，并且用户已确认目标、频率、session 范围和停止条件，再运行脚本。报告 HTTP 状态码、Content-Type/挑战标记、业务成功字段、预期数据断言，以及 iv8 是否返回了非空 cookie/sign/header/token/URL；不能把 `200` 或非空签名单独当成跑通证据。
