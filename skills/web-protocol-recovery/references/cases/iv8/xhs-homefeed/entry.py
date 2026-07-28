# Offline-only case module. Final live egress belongs to python-collector under an approved project work-order.
def _reject_case_live_egress(action: str='live HTTP') -> None:
    raise RuntimeError(f'case entry refuses {action}: offline-only. Use projectRoot main.py + python-collector with a validated work-order.')
import json
import os
import random
import time
import urllib.parse
from pathlib import Path
pass
START_PAGE = 1
PAGE_COUNT = 1
PAGE_SIZE = 20
CATEGORY = 'homefeed.food_v3'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
PAGE_URL = 'https://www.xiaohongshu.com/explore?language=zh-CN&channel_id=homefeed.food_v3'
API_URL = 'https://edith.xiaohongshu.com/api/sns/web/v1/homefeed'
API_PATH = '/api/sns/web/v1/homefeed'
PLATFORM = 'Windows'
CACHE_DIR = Path.cwd() / 'js_reverse_cache'
ASSET_DIR = Path(__file__).resolve().parent / 'assets'
SEED_FILE = Path(__file__).resolve().parent / 'fixtures' / 'runtime_seed.sample.json'
SIGN_V2_INIT_FILE = ASSET_DIR / 'signV2Init_function.json'
HEADER_SIGN_FILE = ASSET_DIR / 'xhs_header_sign.js'

def _iv8():
    import iv8
    return iv8
LOGIN_COOKIES = {'id_token': '', 'web_session': '', 'acw_tc': '', 'unread': ''}

def read_text(path):
    if not path.exists():
        raise FileNotFoundError(f'missing case asset: {path}')
    return path.read_text(encoding='utf-8', errors='ignore')

def load_json(path):
    return json.loads(read_text(path))

def load_seed():
    seed = load_json(SEED_FILE)
    cookies = {key: value for key, value in seed.get('cookies', {}).items() if value and (not str(value).startswith('YOUR_'))}
    cookies.update({key: value for key, value in LOGIN_COOKIES.items() if value})
    local_seeds = seed.get('localSeeds', {})
    live_state = json.loads(os.environ.get('WPR_LIVE_STATE_JSON', '{}'))
    cookies.update(live_state.get('cookies', {}))
    local_seeds.update(live_state.get('storage', {}))
    if not cookies.get('a1'):
        raise RuntimeError('missing live a1; run pull_live_state.py and pass its JSON through WPR_LIVE_STATE_JSON')
    return (cookies, local_seeds)

def random_trace_id(length=16):
    return ''.join((random.choice('0123456789abcdef') for _ in range(length)))

def build_payload(cursor_score=''):
    return {'cursor_score': cursor_score, 'num': PAGE_SIZE, 'refresh_type': 1, 'note_index': 0, 'unread_begin_note_id': '', 'unread_end_note_id': '', 'unread_note_count': 0, 'category': CATEGORY, 'search_key': '', 'need_num': PAGE_SIZE, 'image_scenes': ['CRD_WM_WEBP']}

def build_environment(page_url=PAGE_URL):
    parsed = urllib.parse.urlparse(page_url)
    return {'location': {'href': page_url, 'origin': f'{parsed.scheme}://{parsed.netloc}', 'protocol': f'{parsed.scheme}:', 'host': parsed.netloc, 'hostname': parsed.hostname or '', 'port': str(parsed.port or ''), 'pathname': parsed.path or '/', 'search': f'?{parsed.query}' if parsed.query else '', 'hash': f'#{parsed.fragment}' if parsed.fragment else ''}, 'navigator': {'userAgent': UA, 'platform': 'Win32', 'language': 'zh-CN', 'languages': ['zh-CN', 'zh', 'en'], 'webdriver': False, 'hardwareConcurrency': 8, 'deviceMemory': 8, 'maxTouchPoints': 0}, 'screen': {'width': 1920, 'height': 1080, 'availWidth': 1920, 'availHeight': 1040, 'colorDepth': 24, 'pixelDepth': 24}, 'window': {'innerWidth': 1920, 'innerHeight': 969, 'outerWidth': 1920, 'outerHeight': 1040, 'devicePixelRatio': 1}}

def build_iv8_bootstrap():
    location_json = json.dumps(build_environment()['location'], ensure_ascii=False)
    navigator_json = json.dumps(build_environment()['navigator'], ensure_ascii=False)
    platform_json = json.dumps(PLATFORM, ensure_ascii=False)
    source = '\nvar window = globalThis;\nvar self = window;\nvar global = window;\nglobalThis.window = window;\nglobalThis.self = window;\nglobalThis.global = window;\ntry {{\n  if (typeof Node !== "undefined") {{\n    Node.prototype.removeChild = function(child){{ return child || null; }};\n    Node.prototype.appendChild = function(child){{ if (child && typeof child.onload === "function") {{ try {{ child.onload(); }} catch(e) {{}} }} return child || null; }};\n    Node.prototype.insertBefore = function(child){{ return child || null; }};\n  }}\n  if (typeof Element !== "undefined") {{\n    Element.prototype.removeChild = function(child){{ return child || null; }};\n    Element.prototype.appendChild = function(child){{ if (child && typeof child.onload === "function") {{ try {{ child.onload(); }} catch(e) {{}} }} return child || null; }};\n    Element.prototype.insertBefore = function(child){{ return child || null; }};\n  }}\n}} catch (e) {{}}\nvar location = __LOCATION__;\nvar navigator = __NAVIGATOR__;\nvar performance = {{now:function(){{return Date.now();}}, timeOrigin: Date.now(), getEntriesByType:function(){{return []}}, mark:function(){{}}, measure:function(){{}}}};\nfunction MutationObserver(cb){{ this.observe=function(){{}}; this.disconnect=function(){{}}; this.takeRecords=function(){{return []}}; }}\nfunction makeNode(tag) {{\n  var node = {{tagName:String(tag || "div").toUpperCase(), nodeName:String(tag || "div").toUpperCase(), style:{{}}, children:[], childNodes:[], parentNode:null}};\n  node.setAttribute = function(k,v){{ this[k]=v; }};\n  node.getAttribute = function(k){{ return this[k]; }};\n  node.appendChild = function(x){{ if (x) {{ x.parentNode=this; this.children.push(x); this.childNodes=this.children; }} if (x && typeof x.onload === "function") {{ try {{ x.onload(); }} catch(e) {{}} }} return x || null; }};\n  node.removeChild = function(x){{ if (!x) return null; var i=this.children.indexOf(x); if (i>=0) this.children.splice(i,1); if (x) x.parentNode=null; this.childNodes=this.children; return x || null; }};\n  node.insertBefore = function(x){{ return this.appendChild(x); }};\n  node.addEventListener = function(){{}};\n  node.removeEventListener = function(){{}};\n  return node;\n}}\nvar head = makeNode("head");\nvar body = makeNode("body");\nvar document = {{\n  "cookie": "",\n  referrer: "",\n  hidden: false,\n  visibilityState: "visible",\n  documentElement: makeNode("html"),\n  body: body,\n  head: head,\n  createElement: function(tag){{ return makeNode(tag); }},\n  createTextNode: function(text){{ var node=makeNode("#text"); node.textContent=text; return node; }},\n  getElementsByTagName: function(name){{ name=String(name).toLowerCase(); return name === "head" ? [head] : name === "body" ? [body] : []; }},\n  getElementById: function(){{ return null; }},\n  querySelector: function(){{ return null; }},\n  querySelectorAll: function(){{ return []; }},\n  addEventListener: function(){{}},\n  removeEventListener: function(){{}}\n}};\nwindow.location = location;\nwindow.navigator = navigator;\nwindow.document = document;\nwindow.performance = performance;\nwindow.MutationObserver = MutationObserver;\nwindow.addEventListener = function(){{}};\nwindow.removeEventListener = function(){{}};\nwindow.dispatchEvent = function(){{}};\nwindow.setTimeout = function(fn){{ if (typeof fn === "function") {{ try {{ fn(); }} catch(e) {{ window.__timeout_error = String(e && e.stack || e); }} }} return 1; }};\nwindow.clearTimeout = function(){{}};\nwindow.setInterval = function(){{ return 1; }};\nwindow.clearInterval = function(){{}};\nwindow.localStorage = {{ _:{}, getItem:function(k){{ return this._[k] || null; }}, setItem:function(k,v){{ this._[k]=String(v); }}, removeItem:function(k){{ delete this._[k]; }} }};\nwindow.sessionStorage = {{ _:{}, getItem:function(k){{ return this._[k] || null; }}, setItem:function(k,v){{ this._[k]=String(v); }}, removeItem:function(k){{ delete this._[k]; }} }};\nwindow.xsecplatform = __PLATFORM__;\nvar templateObject_1;\nvar __makeTemplateObject = function(e, a) {{ return Object.defineProperty ? Object.defineProperty(e, "raw", {{ value: a }}) : (e.raw = a), e; }};\n'
    source = source.replace('{{', '{').replace('}}', '}')
    return source.replace('__LOCATION__', location_json).replace('__NAVIGATOR__', navigator_json).replace('__PLATFORM__', platform_json)

def create_context():
    ctx = _iv8().JSContext(environment=build_environment(), config={'timezone': 'Asia/Shanghai'})
    try:
        ctx.eval(build_iv8_bootstrap(), name='xhs_bootstrap.js')
        ctx.eval(load_json(SIGN_V2_INIT_FILE)['src'], name=str(SIGN_V2_INIT_FILE))
        ctx.eval('signV2Init();')
        if ctx.eval('typeof window.mnsv2') != 'function':
            raise RuntimeError('window.mnsv2 initialization failed')
        ctx.eval(read_text(HEADER_SIGN_FILE), name=str(HEADER_SIGN_FILE))
        return ctx
    except Exception:
        ctx.close()
        raise

def generate_signed_headers(ctx, payload, cookies, local_seeds):
    seed = {'apiPath': API_PATH, 'platform': PLATFORM, 'a1': cookies.get('a1', ''), 'b1': local_seeds.get('b1', ''), 'b1b1': local_seeds.get('b1b1') or '1', 'dsllt': local_seeds.get('dsllt') or str(int(time.time() * 1000)), 'dsl': local_seeds.get('dsl') or '1700000000000', 'sc': local_seeds.get('sc') or 0}
    ctx.expose({'payload': payload, 'seed': seed}, 'signInput')
    signed = ctx.eval('generateHeaders(__iv8__.data.signInput.payload, __iv8__.data.signInput.seed)', to_py=True)
    if not isinstance(signed, dict):
        raise RuntimeError('iv8 generateHeaders did not return a header object')
    common_object = signed.pop('X-S-Common-Object')
    return (signed, common_object)

def build_headers(signed_headers):
    headers = {'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'zh-CN,zh;q=0.9', 'Cache-Control': 'no-cache', 'Content-Type': 'application/json;charset=UTF-8', 'Origin': 'https://www.xiaohongshu.com', 'Pragma': 'no-cache', 'Referer': 'https://www.xiaohongshu.com/', 'Sec-Ch-Ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"', 'Sec-Ch-Ua-Mobile': '?0', 'Sec-Ch-Ua-Platform': '"Windows"', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site', 'User-Agent': UA, 'x-b3-traceid': random_trace_id(), 'x-xray-traceid': 'cf' + random_trace_id(30)}
    headers.update(signed_headers)
    return headers

def print_response(page, resp):
    try:
        payload = resp.json()
        keys = sorted(payload) if isinstance(payload, dict) else []
    except ValueError:
        keys = []
    print(f'page={page} status={resp.status_code} bytes={len(resp.content)} json_keys={keys}')

def main():
    cookies, local_seeds = load_seed()
    session = _reject_case_live_egress('requests.Session')
    session.cookies.update(cookies)
    cursor_score = ''
    ctx = create_context()
    try:
        for page in range(START_PAGE, START_PAGE + PAGE_COUNT):
            payload = build_payload(cursor_score)
            signed_headers, common_object = generate_signed_headers(ctx, payload, cookies, local_seeds)
            print(f"page={page} X-s prefix={signed_headers['X-s'][:32]}")
            print(f"page={page} X-S-Common length={len(signed_headers['X-S-Common'])}")
            print(f'page={page} X-S-Common fields={sorted(common_object)}')
            resp = (_reject_case_live_egress('session.post'), None)[1]
            print_response(page, resp)
    finally:
        ctx.close()
if __name__ == '__main__':
    main()
