# ============================================================
# 免责声明 / Disclaimer
# 本示例仅供学习 iv8 API 用法参考，不构成对任何网站的攻击或未授权访问。
# 使用者应自行遵守目标网站的服务条款及所在地区法律法规。
# 作者不对任何滥用行为承担责任。
#
# This example is for educational purposes only.
# Users must comply with all applicable laws and terms of service.
# The author assumes no responsibility for any misuse.
#
# If any website owner believes this example infringes their rights,
# please open an Issue and it will be promptly removed.
# ============================================================

import json
import os
import time
import urllib.parse
from pathlib import Path

import requests


START_PAGE = 1
PAGE_COUNT = 1
PAGE_SIZE = 15
KEYWORD = "python"
CITY_CODE = "101250100"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
PAGE_URL = f"https://www.zhipin.com/web/geek/jobs?query={urllib.parse.quote(KEYWORD)}&city={CITY_CODE}"
API_URL = "https://www.zhipin.com/wapi/zpgeek/search/joblist.json"

COOKIES = {
    "lastCity": "101250100",
}
COOKIE_HEADER_ENV = "ZHIPIN_COOKIE"

CACHE_DIR = Path.cwd() / "js_reverse_cache"


def _iv8():
    import iv8  # type: ignore

    return iv8


def ensure_cache_dir():
    CACHE_DIR.mkdir(exist_ok=True)


def save_text(name, text):
    ensure_cache_dir()
    path = CACHE_DIR / name
    path.write_text(text, encoding="utf-8", errors="ignore")
    return path


def build_headers(page_url=PAGE_URL):
    return {
        "user-agent": UA,
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://www.zhipin.com",
        "referer": page_url,
        "x-requested-with": "XMLHttpRequest",
    }


def build_data(page):
    return {
        "scene": "1",
        "query": KEYWORD,
        "city": CITY_CODE,
        "experience": "",
        "degree": "",
        "industry": "",
        "scale": "",
        "salary": "",
        "jobType": "",
        "page": str(page),
        "pageSize": str(PAGE_SIZE),
    }


def replace_session_cookie(session, name, value):
    for cookie in list(session.cookies):
        if cookie.name == name:
            session.cookies.clear(domain=cookie.domain, path=cookie.path, name=cookie.name)
    session.cookies.set(name, value)


def apply_cookie_header(session):
    """Load a user-provided cookie header only at runtime; never bundle it."""
    raw = os.environ.get(COOKIE_HEADER_ENV, "")
    for item in raw.split(";"):
        name, separator, value = item.strip().partition("=")
        if separator and name:
            session.cookies.set(name.strip(), value.strip(), domain=".zhipin.com", path="/")


def build_security_environment(security_url):
    parsed = urllib.parse.urlparse(security_url)
    return {
        "location": {
            "href": security_url,
            "origin": "https://www.zhipin.com",
            "protocol": "https:",
            "host": "www.zhipin.com",
            "hostname": "www.zhipin.com",
            "port": "",
            "pathname": parsed.path or "/web/common/security-check.html",
            "search": f"?{parsed.query}" if parsed.query else "",
            "hash": "",
        },
        "navigator": {
            "userAgent": UA,
            "platform": "Win32",
            "language": "zh-CN",
            "languages": ["zh-CN", "zh", "en"],
            "webdriver": False,
        },
        "screen": {"width": 1920, "height": 1080, "availWidth": 1920, "availHeight": 1040, "colorDepth": 24, "pixelDepth": 24},
        "window": {"origin": "https://www.zhipin.com", "devicePixelRatio": 1},
        "canvas": {
            "fingerprint": {
                "toDataURL": {
                    "png": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAFgwJ/lQn8YQAAAABJRU5ErkJggg=="
                }
            }
        },
    }


def print_response(page, resp):
    try:
        payload = resp.json()
        keys = sorted(payload) if isinstance(payload, dict) else []
    except ValueError:
        keys = []
    print(f"[page={page}] status={resp.status_code}")
    print(f"bytes={len(resp.content)} json_keys={keys}")


def parse_json(resp):
    try:
        return resp.json()
    except ValueError:
        return None


def compute_stoken(session, headers, challenge_payload):
    zp = challenge_payload.get("zpData") or {}
    seed = zp["seed"]
    name = zp["name"]
    ts = int(zp["ts"])

    js_url = f"https://www.zhipin.com/web/common/security-js/{name}.js"
    js_resp = session.get(js_url, headers={"user-agent": UA, "referer": PAGE_URL}, timeout=20)
    js_resp.raise_for_status()
    js_code = js_resp.text

    save_text(f"zhipin_security_{name}.js", js_code)

    security_url = "https://www.zhipin.com/web/common/security-check.html?" + urllib.parse.urlencode(
        {"seed": seed, "name": name, "ts": str(ts), "callbackUrl": "", "srcReferer": PAGE_URL}
    )
    html_page = f"""<!DOCTYPE html>
<html><head><meta charset=\"utf-8\"></head><body>
<script src=\"{js_url}\"></script>
</body></html>"""
    save_text("zhipin_security_check.html", html_page)

    snapshot = {
        "baseURL": security_url,
        "html": html_page,
        "headers": [[key, value] for key, value in headers.items()],
        "resources": {js_url: js_code},
    }

    # iv8 执行 Boss 安全 JS，生成本次挑战对应的 __zp_stoken__。
    with _iv8().JSContext(environment=build_security_environment(security_url), config={"timezone": "Asia/Shanghai"}) as ctx:
        ctx.expose(snapshot, "snapshot")
        ctx.eval("window.__iv8__.page.load(window.__iv8__.data.snapshot)")
        ctx.eval("window.__iv8__.eventLoop.sleep(100)")
        token = ctx.eval(
            f"encodeURIComponent((new window.ABC).z({json.dumps(seed, ensure_ascii=False)}, {ts}));"
        )

    save_text("zhipin_stoken.txt", str(token))
    return str(token), seed, name, ts


def request_page(session, page):
    headers = build_headers()
    data = build_data(page)
    resp = session.post(API_URL, headers=headers, data=data, timeout=30)
    payload = parse_json(resp)

    # code=37 表示当前 Cookie 需要刷新 __zp_stoken__。
    if payload and payload.get("code") == 37 and payload.get("zpData"):
        print(f"[page={page}] hit code=37, regenerate __zp_stoken__")
        token, seed, name, ts = compute_stoken(session, headers, payload)
        replace_session_cookie(session, "__zp_stoken__", token)
        replace_session_cookie(session, "__zp_sseed__", seed)
        replace_session_cookie(session, "__zp_sname__", name)
        replace_session_cookie(session, "__zp_sts__", str(ts))
        resp = session.post(API_URL, headers=headers, data=data, timeout=30)

    return resp


def main():
    session = requests.Session()
    for name, value in COOKIES.items():
        session.cookies.set(name, value, domain=".zhipin.com", path="/")
    apply_cookie_header(session)

    print(f"cache_dir={CACHE_DIR}")
    print(f"keyword={KEYWORD} city={CITY_CODE} start_page={START_PAGE} page_count={PAGE_COUNT} page_size={PAGE_SIZE}")

    for page in range(START_PAGE, START_PAGE + PAGE_COUNT):
        resp = request_page(session, page)
        print_response(page, resp)
        time.sleep(0.5)


if __name__ == "__main__":
    main()
