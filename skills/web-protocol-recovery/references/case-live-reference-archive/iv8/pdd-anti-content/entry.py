# ============================================================
# Disclaimer
# This example is for educational iv8 API usage reference only.
# Users must comply with all applicable laws and target site terms.
# The author assumes no responsibility for misuse.
# ============================================================

import json
import re
import urllib.parse
from pathlib import Path

import requests


START_PAGE = 1
PAGE_COUNT = 1
PAGE_SIZE = 39
TF_ID = "TFRQ0v00000Y_13396"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
PAGE_URL = "https://www.pinduoduo.com/home/girlclothes/"
STM_URL = "https://apiv2.pinduoduo.com/api/server/_stm"
API_URL = "https://apiv2.pinduoduo.com/api/gindex/tf/query_tf_goods_info"

CACHE_DIR = Path.cwd() / "js_reverse_cache"


def _iv8():
    import iv8  # type: ignore

    return iv8


def ensure_cache_dir():
    CACHE_DIR.mkdir(exist_ok=True)

BASE_HEADERS = {
    "accept": "application/json, text/javascript",
    "accept-language": "zh-CN,zh;q=0.9",
    "origin": "https://www.pinduoduo.com",
    "referer": "https://www.pinduoduo.com/",
    "user-agent": UA,
}


def build_environment():
    parsed = urllib.parse.urlparse(PAGE_URL)
    return {
        "location": {
            "href": PAGE_URL,
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
            "hardwareConcurrency": 8,
            "deviceMemory": 8,
            "webdriver": False,
            "maxTouchPoints": 0,
        },
        "screen": {
            "width": 1920,
            "height": 1080,
            "availWidth": 1920,
            "availHeight": 1040,
            "colorDepth": 24,
            "pixelDepth": 24,
        },
        "window": {
            "innerWidth": 1920,
            "innerHeight": 969,
            "outerWidth": 1920,
            "outerHeight": 1040,
            "devicePixelRatio": 1,
        },
    }


def fetch_text(session, url):
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def script_cache_name(url):
    path = urllib.parse.urlparse(url).path
    if path.endswith("/pages/subject.js"):
        return "pdd_subject.js"
    if path.endswith("/pages/_app.js"):
        return "pdd_app.js"
    if "/chunks/commons." in path:
        return "pdd_commons.js"
    if "/runtime/webpack-" in path:
        return "pdd_webpack.js"
    return "pdd_" + re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(path).name)


def load_current_webpack_assets(session):
    html = fetch_text(session, PAGE_URL)
    ensure_cache_dir()
    (CACHE_DIR / "pdd_page.html").write_text(html, encoding="utf-8", errors="ignore")
    src_list = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
    script_urls = [urllib.parse.urljoin(PAGE_URL, src) for src in src_list]
    wanted = [url for url in script_urls if any(part in url for part in (
        "/pages/subject.js",
        "/pages/_app.js",
        "/chunks/commons.",
        "/runtime/webpack-",
    ))]
    if not wanted:
        raise RuntimeError("current page did not expose the expected webpack bundles")

    assets = []
    for url in wanted:
        path = CACHE_DIR / script_cache_name(url)
        path.write_text(fetch_text(session, url), encoding="utf-8", errors="ignore")
        assets.append((url, path))
    return assets


def get_server_time(session):
    headers = {"content-type": "application/json;charset=UTF-8", **BASE_HEADERS}
    resp = session.get(STM_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    return int(resp.json()["server_time"])


def generate_anti_content(assets, server_time):
    with _iv8().JSContext(environment=build_environment(), config={"timezone": "Asia/Shanghai"}) as ctx:
        ctx.eval("""
            window.window = window;
            window.self = window;
            window.globalThis = window;
            window.__NEXT_P = window.__NEXT_P || [];
        """)
        for url, path in assets:
            ctx.eval(path.read_text(encoding="utf-8", errors="ignore"), name=url)

        # Capture webpack require, then call the obfuscated fbeZ module entry.
        anti = ctx.eval(f"""
            window.webpackJsonp.push([[Math.floor(Math.random() * 1e9)], {{
                __pdd_capture_req__: function(module, exports, __webpack_require__) {{
                    window.__pdd_require__ = __webpack_require__;
                }}
            }}, [["__pdd_capture_req__"]]]);

            var fbeZ = window.__pdd_require__('fbeZ');
            var done = false;
            var result = '';
            var error = '';
            Promise.resolve((new fbeZ({{serverTime: {server_time}}})).messagePackSync()).then(
                function(value) {{ result = String(value); done = true; }},
                function(reason) {{ error = String(reason && reason.stack || reason); done = true; }}
            );
            window.__iv8__.eventLoop.drainMicrotasks();
            window.__iv8__.eventLoop.drain();
            window.__iv8__.eventLoop.sleep(50);
            if (error) throw new Error(error);
            if (!done || !result) throw new Error('anti_content promise did not resolve');
            result;
        """)
    if not anti or len(anti) < 100:
        raise RuntimeError(f"invalid anti_content: {anti!r}")
    return anti


def print_response(page, resp):
    try:
        payload = resp.json()
        keys = sorted(payload) if isinstance(payload, dict) else []
    except ValueError:
        keys = []
    print(f"page={page} status={resp.status_code} bytes={len(resp.content)} json_keys={keys}")


def main():
    session = requests.Session()
    session.headers.update(BASE_HEADERS)
    assets = load_current_webpack_assets(session)
    for page in range(START_PAGE, START_PAGE + PAGE_COUNT):
        server_time = get_server_time(session)
        anti_content = generate_anti_content(assets, server_time)
        print(f"page={page} anti_content_len={len(anti_content)} prefix={anti_content[:48]}")
        params = {
            "tf_id": TF_ID,
            "page": page,
            "size": PAGE_SIZE,
            "anti_content": anti_content,
        }
        resp = session.get(API_URL, params=params, headers=BASE_HEADERS, timeout=30)
        print_response(page, resp)


if __name__ == "__main__":
    main()
