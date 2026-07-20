# ============================================================
# Disclaimer
# This example is for educational iv8 API usage reference only.
# Users must comply with all applicable laws and target site terms.
# The author assumes no responsibility for misuse.
# ============================================================

import json
import os
import random
import time
import urllib.parse
from pathlib import Path

import iv8
import requests


START_PAGE = 1
PAGE_COUNT = 1
PAGE_SIZE = 20
CATEGORY = "homefeed.food_v3"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
PAGE_URL = "https://www.xiaohongshu.com/explore?language=zh-CN&channel_id=homefeed.food_v3"
API_URL = "https://edith.xiaohongshu.com/api/sns/web/v1/homefeed"
API_PATH = "/api/sns/web/v1/homefeed"
PLATFORM = "Windows"

CACHE_DIR = Path.cwd() / "js_reverse_cache"
CACHE_DIR.mkdir(exist_ok=True)
ASSET_DIR = Path(__file__).resolve().parent / "assets"
SEED_FILE = Path(__file__).resolve().parent / "fixtures" / "runtime_seed.sample.json"
SIGN_V2_INIT_FILE = ASSET_DIR / "signV2Init_function.json"
HEADER_SIGN_FILE = ASSET_DIR / "xhs_header_sign.js"

# Fill these only when the target endpoint requires an authenticated session.
LOGIN_COOKIES = {
    "id_token": "",
    "web_session": "",
    "acw_tc": "",
    "unread": "",
}


def read_text(path):
    if not path.exists():
        raise FileNotFoundError(f"missing case asset: {path}")
    return path.read_text(encoding="utf-8", errors="ignore")


def load_json(path):
    return json.loads(read_text(path))


def load_seed():
    seed = load_json(SEED_FILE)
    cookies = {
        key: value
        for key, value in seed.get("cookies", {}).items()
        if value and not str(value).startswith("YOUR_")
    }
    cookies.update({key: value for key, value in LOGIN_COOKIES.items() if value})
    local_seeds = seed.get("localSeeds", {})
    live_state = json.loads(os.environ.get("WPR_LIVE_STATE_JSON", "{}"))
    cookies.update(live_state.get("cookies", {}))
    local_seeds.update(live_state.get("storage", {}))
    if not cookies.get("a1"):
        raise RuntimeError("missing live a1; run pull_live_state.py and pass its JSON through WPR_LIVE_STATE_JSON")
    return cookies, local_seeds


def random_trace_id(length=16):
    return "".join(random.choice("0123456789abcdef") for _ in range(length))


def build_payload(cursor_score=""):
    # Body serialization participates in X-s, so keep field order stable.
    return {
        "cursor_score": cursor_score,
        "num": PAGE_SIZE,
        "refresh_type": 1,
        "note_index": 0,
        "unread_begin_note_id": "",
        "unread_end_note_id": "",
        "unread_note_count": 0,
        "category": CATEGORY,
        "search_key": "",
        "need_num": PAGE_SIZE,
        "image_scenes": ["CRD_WM_WEBP"],
    }


def build_environment(page_url=PAGE_URL):
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
            "hardwareConcurrency": 8,
            "deviceMemory": 8,
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


def build_iv8_bootstrap():
    location_json = json.dumps(build_environment()["location"], ensure_ascii=False)
    navigator_json = json.dumps(build_environment()["navigator"], ensure_ascii=False)
    platform_json = json.dumps(PLATFORM, ensure_ascii=False)
    source = r'''
var window = globalThis;
var self = window;
var global = window;
globalThis.window = window;
globalThis.self = window;
globalThis.global = window;
try {{
  if (typeof Node !== "undefined") {{
    Node.prototype.removeChild = function(child){{ return child || null; }};
    Node.prototype.appendChild = function(child){{ if (child && typeof child.onload === "function") {{ try {{ child.onload(); }} catch(e) {{}} }} return child || null; }};
    Node.prototype.insertBefore = function(child){{ return child || null; }};
  }}
  if (typeof Element !== "undefined") {{
    Element.prototype.removeChild = function(child){{ return child || null; }};
    Element.prototype.appendChild = function(child){{ if (child && typeof child.onload === "function") {{ try {{ child.onload(); }} catch(e) {{}} }} return child || null; }};
    Element.prototype.insertBefore = function(child){{ return child || null; }};
  }}
}} catch (e) {{}}
var location = __LOCATION__;
var navigator = __NAVIGATOR__;
var performance = {{now:function(){{return Date.now();}}, timeOrigin: Date.now(), getEntriesByType:function(){{return []}}, mark:function(){{}}, measure:function(){{}}}};
function MutationObserver(cb){{ this.observe=function(){{}}; this.disconnect=function(){{}}; this.takeRecords=function(){{return []}}; }}
function makeNode(tag) {{
  var node = {{tagName:String(tag || "div").toUpperCase(), nodeName:String(tag || "div").toUpperCase(), style:{{}}, children:[], childNodes:[], parentNode:null}};
  node.setAttribute = function(k,v){{ this[k]=v; }};
  node.getAttribute = function(k){{ return this[k]; }};
  node.appendChild = function(x){{ if (x) {{ x.parentNode=this; this.children.push(x); this.childNodes=this.children; }} if (x && typeof x.onload === "function") {{ try {{ x.onload(); }} catch(e) {{}} }} return x || null; }};
  node.removeChild = function(x){{ if (!x) return null; var i=this.children.indexOf(x); if (i>=0) this.children.splice(i,1); if (x) x.parentNode=null; this.childNodes=this.children; return x || null; }};
  node.insertBefore = function(x){{ return this.appendChild(x); }};
  node.addEventListener = function(){{}};
  node.removeEventListener = function(){{}};
  return node;
}}
var head = makeNode("head");
var body = makeNode("body");
var document = {{
  "cookie": "",
  referrer: "",
  hidden: false,
  visibilityState: "visible",
  documentElement: makeNode("html"),
  body: body,
  head: head,
  createElement: function(tag){{ return makeNode(tag); }},
  createTextNode: function(text){{ var node=makeNode("#text"); node.textContent=text; return node; }},
  getElementsByTagName: function(name){{ name=String(name).toLowerCase(); return name === "head" ? [head] : name === "body" ? [body] : []; }},
  getElementById: function(){{ return null; }},
  querySelector: function(){{ return null; }},
  querySelectorAll: function(){{ return []; }},
  addEventListener: function(){{}},
  removeEventListener: function(){{}}
}};
window.location = location;
window.navigator = navigator;
window.document = document;
window.performance = performance;
window.MutationObserver = MutationObserver;
window.addEventListener = function(){{}};
window.removeEventListener = function(){{}};
window.dispatchEvent = function(){{}};
window.setTimeout = function(fn){{ if (typeof fn === "function") {{ try {{ fn(); }} catch(e) {{ window.__timeout_error = String(e && e.stack || e); }} }} return 1; }};
window.clearTimeout = function(){{}};
window.setInterval = function(){{ return 1; }};
window.clearInterval = function(){{}};
window.localStorage = {{ _:{}, getItem:function(k){{ return this._[k] || null; }}, setItem:function(k,v){{ this._[k]=String(v); }}, removeItem:function(k){{ delete this._[k]; }} }};
window.sessionStorage = {{ _:{}, getItem:function(k){{ return this._[k] || null; }}, setItem:function(k,v){{ this._[k]=String(v); }}, removeItem:function(k){{ delete this._[k]; }} }};
window.xsecplatform = __PLATFORM__;
var templateObject_1;
var __makeTemplateObject = function(e, a) {{ return Object.defineProperty ? Object.defineProperty(e, "raw", {{ value: a }}) : (e.raw = a), e; }};
'''
    source = source.replace("{{", "{").replace("}}", "}")
    return source.replace("__LOCATION__", location_json).replace("__NAVIGATOR__", navigator_json).replace("__PLATFORM__", platform_json)


def create_context():
    ctx = iv8.JSContext(environment=build_environment(), config={"timezone": "Asia/Shanghai"})
    try:
        ctx.eval(build_iv8_bootstrap(), name="xhs_bootstrap.js")
        ctx.eval(load_json(SIGN_V2_INIT_FILE)["src"], name=str(SIGN_V2_INIT_FILE))
        ctx.eval("signV2Init();")
        if ctx.eval("typeof window.mnsv2") != "function":
            raise RuntimeError("window.mnsv2 initialization failed")
        ctx.eval(read_text(HEADER_SIGN_FILE), name=str(HEADER_SIGN_FILE))
        return ctx
    except Exception:
        ctx.close()
        raise


def generate_signed_headers(ctx, payload, cookies, local_seeds):
    seed = {
        "apiPath": API_PATH,
        "platform": PLATFORM,
        "a1": cookies.get("a1", ""),
        "b1": local_seeds.get("b1", ""),
        "b1b1": local_seeds.get("b1b1") or "1",
        "dsllt": local_seeds.get("dsllt") or str(int(time.time() * 1000)),
        "dsl": local_seeds.get("dsl") or "1700000000000",
        "sc": local_seeds.get("sc") or 0,
    }
    ctx.expose({"payload": payload, "seed": seed}, "signInput")
    signed = ctx.eval("generateHeaders(__iv8__.data.signInput.payload, __iv8__.data.signInput.seed)", to_py=True)
    if not isinstance(signed, dict):
        raise RuntimeError("iv8 generateHeaders did not return a header object")
    common_object = signed.pop("X-S-Common-Object")
    return signed, common_object


def build_headers(signed_headers):
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://www.xiaohongshu.com",
        "Pragma": "no-cache",
        "Referer": "https://www.xiaohongshu.com/",
        "Sec-Ch-Ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": UA,
        "x-b3-traceid": random_trace_id(),
        "x-xray-traceid": "cf" + random_trace_id(30),
    }
    headers.update(signed_headers)
    return headers


def print_response(page, resp):
    try:
        payload = resp.json()
        keys = sorted(payload) if isinstance(payload, dict) else []
    except ValueError:
        keys = []
    print(f"page={page} status={resp.status_code} bytes={len(resp.content)} json_keys={keys}")


def main():
    cookies, local_seeds = load_seed()
    session = requests.Session()
    session.cookies.update(cookies)

    cursor_score = ""
    ctx = create_context()
    try:
        for page in range(START_PAGE, START_PAGE + PAGE_COUNT):
            payload = build_payload(cursor_score)
            signed_headers, common_object = generate_signed_headers(ctx, payload, cookies, local_seeds)
            print(f"page={page} X-s prefix={signed_headers['X-s'][:32]}")
            print(f"page={page} X-S-Common length={len(signed_headers['X-S-Common'])}")
            print(f"page={page} X-S-Common fields={sorted(common_object)}")
            resp = session.post(
                API_URL,
                headers=build_headers(signed_headers),
                data=json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
                timeout=30,
            )
            print_response(page, resp)
    finally:
        ctx.close()


if __name__ == "__main__":
    main()
