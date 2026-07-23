# ============================================================
# Disclaimer
# This example is for educational iv8 API usage reference only.
# Users must comply with the target site's terms and applicable laws.
# ============================================================

import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests

try:
    from loguru import logger  # pyright: ignore[reportMissingImports]
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


START_OFFSET = 0
PAGE_COUNT = 1
PAGE_SIZE = 10
KEYWORD = ""
ANNOUNCEMENT_TYPE = "103"
IFEND = ""
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
PAGE_URL = f"https://ec.chng.com.cn/channel/home/?SlJfApAfmEBp={int(time.time() * 1000)}#/purchase?top=0"
API_URL = "https://ec.chng.com.cn/scm-uiaoauth-web/s/business/uiaouth/queryAnnouncementByTitle"

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


def build_environment(page_url):
    parsed = urllib.parse.urlparse(page_url)
    return {
        "location": {
            "ancestorOrigins": {},
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
        "screen": {"width": 1920, "height": 1080, "availWidth": 1920, "availHeight": 1040},
    }


def cookie_header_to_dict(cookie_header):
    cookies = {}
    for part in (cookie_header or "").split(";"):
        if "=" not in part:
            continue
        key, value = part.strip().split("=", 1)
        if key:
            cookies[key] = value
    return cookies


def update_session_cookies(session, cookie_text):
    cookies = cookie_header_to_dict(cookie_text)
    if cookies:
        session.cookies.update(cookies)
    return cookies


def extract_rs_script_url(html, base_url):
    patterns = [
        r"<script[^>]+src=[\"']([^\"']+\.js[^\"']*)[\"'][^>]*\br=[\"']m[\"']",
        r"<script[^>]+\br=[\"']m[\"'][^>]+src=[\"']([^\"']+\.js[^\"']*)[\"']",
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.I)
        if match:
            return urllib.parse.urljoin(base_url, match.group(1))
    srcs = re.findall(r"<script[^>]+src=[\"']([^\"']+\.js[^\"']*)[\"']", html, re.I)
    if srcs:
        return urllib.parse.urljoin(base_url, srcs[-1])
    raise RuntimeError("challenge page did not contain a Ruishu JS URL")


def base_headers(referer=PAGE_URL):
    return {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "keep-alive",
        "Referer": referer,
        "Upgrade-Insecure-Requests": "1",
    }


def api_headers(referer=PAGE_URL):
    return {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Origin": "https://ec.chng.com.cn",
        "Referer": referer,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "X-Requested-With": "XMLHttpRequest",
    }


def load_rs_page(ctx, name, page_url, html, js_url, js_code, response):
    snapshot = {
        "baseURL": page_url,
        "html": html,
        "headers": [[k, v] for k, v in response.headers.items()],
        "resources": {js_url: js_code},
    }
    ctx.expose(snapshot, name)
    ctx.eval(f"window.__iv8__.page.load(window.__iv8__.data.{name})")
    ctx.eval("window.__iv8__.eventLoop.sleep(300)")
    return ctx.eval(
        """
        (function() {
            var entries = window.__iv8__.netLog.entries;
            var last = entries.length ? entries[entries.length - 1] : null;
            return {
                "cookie": document.cookie || (last && last.cookieHeader) || '',
                href: location.href,
                entries: entries.map(function(e) {
                    return {url: e.url, method: e.method, status: e.status, cookieHeader: e.cookieHeader || ''};
                })
            };
        })();
        """,
        to_py=True,
    )


def fetch_rs_stage(session, page_url, index, cookie_text=""):
    headers = base_headers(page_url)
    if cookie_text:
        headers["Cookie"] = cookie_text
    response = session.get(page_url, headers=headers, timeout=30, allow_redirects=False)
    html_path = save_text(f"chng_stage{index}_page.html", response.text)
    logger.info("stage{} page status={} saved={}", index, response.status_code, html_path)

    js_url = extract_rs_script_url(response.text, page_url)
    js_response = session.get(js_url, headers={**base_headers(page_url), "Accept": "*/*"}, timeout=30)
    js_path = save_text(f"chng_stage{index}_rs.js", js_response.text)
    logger.info("stage{} rs js status={} url={} saved={}", index, js_response.status_code, js_url, js_path)
    return response, js_url, js_response.text


def build_body(start):
    return {
        "start": start,
        "limit": PAGE_SIZE,
        "type": ANNOUNCEMENT_TYPE,
        "search": KEYWORD,
        "ifend": IFEND,
    }


def capture_api_entry(ctx, start, body):
    body_text = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    ctx.expose({"url": API_URL, "body": body_text}, "xhrInput")
    ctx.eval(
        """
        (function() {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', window.__iv8__.data.xhrInput.url, true);
            xhr.setRequestHeader('Accept', 'application/json, text/plain, */*');
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            xhr.send(window.__iv8__.data.xhrInput.body);
            window.__iv8__.eventLoop.sleep(300);
        })();
        """
    )
    entry = ctx.eval(
        """
        (function() {
            var entries = window.__iv8__.netLog.entries;
            for (var i = entries.length - 1; i >= 0; i--) {
                if (String(entries[i].url).indexOf('queryAnnouncementByTitle') !== -1) return entries[i];
            }
            return entries.length ? entries[entries.length - 1] : null;
        })();
        """,
        to_py=True,
    )
    if not entry:
        raise RuntimeError("iv8 netLog did not capture the announcement XHR")
    save_text(f"chng_start{start}_xhr_entry.json", json.dumps(entry, ensure_ascii=False, indent=2))
    return entry, body_text


def print_response(start, response):
    try:
        payload = response.json()
        keys = sorted(payload) if isinstance(payload, dict) else []
    except ValueError:
        keys = []
    logger.info("start={} status={} bytes={} json_keys={}", start, response.status_code, len(response.content), keys)


def main():
    session = requests.Session()
    stage2 = {}
    with _iv8().JSContext(environment=build_environment(PAGE_URL), config={"timezone": "Asia/Shanghai"}) as ctx:
        response1, js_url1, js_code1 = fetch_rs_stage(session, PAGE_URL, 1)
        stage1 = load_rs_page(ctx, "stage1", PAGE_URL, response1.text, js_url1, js_code1, response1)
        save_text("chng_stage1_iv8_result.json", json.dumps(stage1, ensure_ascii=False, indent=2))
        cookie1 = stage1.get("cookie") or "; ".join(f"{k}={v}" for k, v in session.cookies.get_dict().items())
        update_session_cookies(session, cookie1)
        logger.info("stage1 cookie fields={}", sorted(cookie_header_to_dict(cookie1)))
        logger.info("stage1 href={}", stage1.get("href"))

        second_url = stage1.get("href") or PAGE_URL
        if not second_url.startswith("http"):
            second_url = urllib.parse.urljoin(PAGE_URL, second_url)

        response2, js_url2, js_code2 = fetch_rs_stage(session, second_url, 2, cookie1)
        stage2 = load_rs_page(ctx, "stage2", second_url, response2.text, js_url2, js_code2, response2)
        save_text("chng_stage2_iv8_result.json", json.dumps(stage2, ensure_ascii=False, indent=2))
        cookie2 = stage2.get("cookie") or cookie1
        update_session_cookies(session, cookie2)
        logger.info("stage2 cookie fields={}", sorted(cookie_header_to_dict(cookie2)))
        logger.info("stage2 href={}", stage2.get("href"))

        for index in range(PAGE_COUNT):
            start = START_OFFSET + index * PAGE_SIZE
            body = build_body(start)
            entry, body_text = capture_api_entry(ctx, start, body)
            final_url = urllib.parse.urljoin(API_URL, entry.get("url") or API_URL)
            final_cookie = entry.get("cookieHeader") or cookie2
            update_session_cookies(session, final_cookie)
            final_headers = api_headers(stage2.get("href") or PAGE_URL)
            if entry.get("headers"):
                final_headers.update(dict(entry["headers"]))
            if final_cookie:
                final_headers["Cookie"] = final_cookie
            logger.info("start={} captured url={}", start, final_url)
            logger.info("start={} captured cookie fields={}", start, sorted(cookie_header_to_dict(final_cookie)))
            response = session.post(
                final_url,
                data=body_text.encode("utf-8"),
                headers=final_headers,
                cookies=cookie_header_to_dict(final_cookie),
                timeout=30,
            )
            print_response(start, response)


if __name__ == "__main__":
    main()
