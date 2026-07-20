# ============================================================
# 免责声明 / Disclaimer
# 本示例仅供学习 iv8 API 用法参考，不构成对任何网站的攻击或未授权访问。
# 使用者应自行遵守目标网站的服务条款及所在地区法律法规。
# 作者不对任何滥用行为承担责任。
# ============================================================

import html
import json
import re
import sys
import urllib.parse
from pathlib import Path

import iv8
import requests

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


START_PAGE = 1
PAGE_COUNT = 1
PAGE_SIZE = 20
KEYWORD = "教育"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
PAGE_URL = "https://qikan.cqvip.com/Qikan/Search/Index?from=index"
API_URL = "https://qikan.cqvip.com/Search/SearchList"

CACHE_DIR = Path.cwd() / "js_reverse_cache"
CACHE_DIR.mkdir(exist_ok=True)


def save_text(name, text):
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
    }


def base_headers():
    return {
        "User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }


def update_session_cookies(session, cookie_text):
    cookies = {}
    for part in (cookie_text or "").split(";"):
        if "=" not in part:
            continue
        key, value = part.strip().split("=", 1)
        if key:
            cookies[key] = value
            session.cookies.set(key, value, domain="qikan.cqvip.com", path="/")
    return cookies


def extract_rs_script_url(page_url, html_text):
    match = re.search(r"src=[\"']([^\"']+\.js)[\"'][^>]*r=[\"']m[\"']", html_text)
    if not match:
        match = re.search(r"src=[\"']([^\"']+\.js)[\"']", html_text)
    if not match:
        raise RuntimeError("challenge page did not contain a protection JS URL")
    return urllib.parse.urljoin(page_url, match.group(1))


def refresh_ruishu_cookie(session, page_tag):
    page_headers = {
        **base_headers(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Referer": PAGE_URL,
    }
    response = session.get(PAGE_URL, headers=page_headers, timeout=30)
    response.encoding = "utf-8"
    save_text(f"cqvip_challenge_page_{page_tag}.html", response.text)

    if response.status_code != 412:
        logger.info("page={} first page status={} len={}, no challenge refresh needed", page_tag, response.status_code, len(response.text))
        return session.cookies.get_dict()

    js_url = extract_rs_script_url(PAGE_URL, response.text)
    js_code = session.get(js_url, headers={**page_headers, "Referer": PAGE_URL}, timeout=30).text
    save_text(f"cqvip_rs_source_code_{page_tag}.js", js_code)

    snapshot = {
        "baseURL": PAGE_URL,
        "html": response.text,
        "headers": [[k, v] for k, v in response.headers.items()],
        "resources": {js_url: js_code},
    }
    # 保护页脚本会写入 6HZbKHDjIEcgT，SearchList 必须携带同一组 S/T Cookie。
    with iv8.JSContext(environment=build_environment(PAGE_URL), config={"timezone": "Asia/Shanghai"}) as ctx:
        ctx.expose(snapshot, "snapshot")
        ctx.eval("window.__iv8__.page.load(window.__iv8__.data.snapshot)")
        ctx.eval("window.__iv8__.eventLoop.sleep(500)")
        cookie_text = ctx.eval("document.cookie")
        if not cookie_text:
            cookie_text = ctx.eval("""
                var entries = window.__iv8__.netLog.entries;
                entries.length ? (entries[entries.length - 1].cookieHeader || '') : '';
            """)

    cookies = update_session_cookies(session, cookie_text)
    if "6HZbKHDjIEcgT" not in cookies:
        raise RuntimeError("iv8 did not generate 6HZbKHDjIEcgT")
    logger.info("page={} iv8 cookie ok: {}", page_tag, "; ".join(cookies.keys()))
    return cookies


def build_search_model(page):
    return {
        "ObjectType": 1,
        "SearchKeyList": [
            {
                "FieldIdentifier": "U",
                "SearchKey": KEYWORD,
                "PreLogicalOperator": None,
                "AfterLogicalOperator": None,
                "LeftBracket": None,
                "RighgtBracket": None,
                "IsExact": None,
                "ClusterShowName": None,
            }
        ],
        "SearchExpression": None,
        "BeginYear": None,
        "EndYear": None,
        "UpdateTimeType": None,
        "JournalRange": None,
        "DomainRange": None,
        "ClusterFilter": "",
        "ClusterLimit": 0,
        "ClusterUseType": "Article",
        "UrlParam": "",
        "Sort": "0",
        "SortField": None,
        "UserID": None,
        "PageNum": page,
        "PageSize": PAGE_SIZE,
        "SType": None,
        "StrIds": None,
        "IsRefOrBy": 0,
        "ShowRules": f"  任意字段={KEYWORD}  ",
        "IsNoteHistory": 0,
        "AdvShowTitle": None,
        "ObjectId": None,
        "ObjectSearchType": 0,
        "ChineseEnglishExtend": 0,
        "SynonymExtend": 0,
        "ShowTotalCount": 0,
        "AdvTabGuid": "",
    }


def build_payload(page):
    model = build_search_model(page)
    return {
        "searchParamModel": json.dumps(model, ensure_ascii=False, separators=(",", ":")),
        "pageNum": str(page),
        "pageSize": str(PAGE_SIZE),
    }


def post_search_list(session, page):
    headers = {
        **base_headers(),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://qikan.cqvip.com",
        "Referer": PAGE_URL,
        "X-Requested-With": "XMLHttpRequest",
    }
    response = session.post(API_URL, headers=headers, data=build_payload(page), timeout=30)
    response.encoding = "utf-8"
    return response


def print_response(page, resp):
    try:
        payload = resp.json()
        keys = sorted(payload) if isinstance(payload, dict) else []
    except ValueError:
        keys = []
    logger.info("page={} status={} bytes={} json_keys={}", page, resp.status_code, len(resp.content), keys)


def print_brief_result(page, text):
    total_match = re.search(r'id="hidShowTotalCount" value="(\d+)"', text)
    titles = re.findall(
        r'<a[^>]+href="([^"]*/Qikan/Article/Detail\?id=[^"]+)"[^>]*>(.*?)</a>',
        text,
        flags=re.S,
    )[:5]
    total = total_match.group(1) if total_match else "unknown"
    logger.info("page={} total={} first_titles=", page, total)
    for index, (href, title_html) in enumerate(titles, 1):
        title = re.sub(r"<[^>]+>", "", title_html)
        logger.info("{}. {} {}", index, html.unescape(title).strip(), urllib.parse.urljoin(PAGE_URL, href))


def main():
    for page in range(START_PAGE, START_PAGE + PAGE_COUNT):
        session = requests.Session()
        refresh_ruishu_cookie(session, str(page))
        response = post_search_list(session, page)

        if response.status_code == 412 or "$_ts" in response.text[:500]:
            logger.info("page={} SearchList hit challenge, refreshing cookie once", page)
            session = requests.Session()
            refresh_ruishu_cookie(session, f"{page}_retry")
            response = post_search_list(session, page)

        print_brief_result(page, response.text)
        print_response(page, response)


if __name__ == "__main__":
    main()
