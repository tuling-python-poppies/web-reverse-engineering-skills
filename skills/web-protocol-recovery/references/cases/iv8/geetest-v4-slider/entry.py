# pyright: reportMissingImports=false
"""Geetest v4 / 滑块：官方 JS 在 iv8 中生成 w，Python 提交验证。"""

import io
import json
import random
import time
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import cv2
import ddddocr
from curl_cffi import requests
from PIL import Image

CAPTCHA_PROVIDER = "Geetest"
CAPTCHA_VERSION = "v4"
CAPTCHA_TYPE = "滑块"
CAPTCHA_PROTOCOL_TYPE = "slide"
CAPTCHA_ID = "54088bb07d2df3c46b79f80300b0abbe"  # Geetest public demo ID
PAGE_URL = "https://gt4.geetest.com/"
LOAD_URL = "https://gcaptcha4.geetest.com/load"
STATIC_HOST = "https://static.geetest.com/"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
)
TIMEOUT = (10, 30)
MIN_VERIFY_DELAY = 1.5
WORK_DIR = Path.cwd()
CACHE_DIR = WORK_DIR / "js_reverse_cache"


def _iv8():
    import iv8  # type: ignore

    return iv8


def ensure_cache_dir():
    CACHE_DIR.mkdir(exist_ok=True)


BOOTSTRAP = r"""
document.documentElement.innerHTML = '<head></head><body><div id="captcha"></div></body>';
if (typeof document.createElementNS !== 'function') {
    document.createElementNS = window.__iv8__.wrapNative(function(_ns, tag) {
        return document.createElement(tag);
    }, 'createElementNS');
}
window.__verifyUrl = '';
(function() {
    var head = document.head;
    var append = head.appendChild;
    head.appendChild = window.__iv8__.wrapNative(function(node) {
        var result = append.call(head, node);
        var tag = String(node.tagName || '').toLowerCase();
        var src = String(node.src || node.href || '');
        if (tag === 'script') setTimeout(function() {
            try {
                if (src.indexOf('/load?') >= 0) {
                    var name = decodeURIComponent(/[?&]callback=([^&]+)/.exec(src)[1]);
                    window[name]({status: 'success', data: window.__iv8__.data.loadData});
                } else if (src.indexOf('/verify?') >= 0) {
                    window.__verifyUrl = src;
                    var verifyName = decodeURIComponent(/[?&]callback=([^&]+)/.exec(src)[1]);
                    if (typeof window[verifyName] === 'function') {
                        window[verifyName]({status: 'error', data: {result: 'fail'}});
                    }
                } else if (src.indexOf('/gct/') >= 0) {
                    (0, eval)(window.__iv8__.data.gct);
                } else if (src.indexOf('/js/gcaptcha4.js') >= 0) {
                    (0, eval)(window.__iv8__.data.gcaptcha);
                } else if (src.indexOf('/i18n/') >= 0) {
                    (0, eval)(window.__iv8__.data.lang);
                }
                node.readyState = 'complete';
                if (typeof node.onload === 'function') node.onload();
            } catch (error) {
                window.__resourceError = String(error && (error.stack || error));
            }
        }, 0);
        else if (tag === 'link') setTimeout(function() {
            if (typeof node.onload === 'function') node.onload();
        }, 0);
        return result;
    }, 'appendChild');
})();
"""

SIGN = r"""
window.__initDone = false;
window.initGeetest4({
    captchaId: window.__iv8__.data.captchaId,
    riskType: 'slide',
    product: 'float',
    language: 'zho'
}, function(obj) {
    window.captchaObj = obj;
    obj.appendTo('#captcha');
    obj.showCaptcha();
    window.__initDone = true;
});
window.__iv8__.eventLoop.drain();
window.__iv8__.eventLoop.sleep(1000);
window.__iv8__.eventLoop.drain();
var backend = window.__gtRequire(17).default.$_BEP(window.captchaObj.$_BAGF);
backend.$_BBFs(window.__iv8__.data.answer, function() {}, true);
window.__iv8__.eventLoop.drain();
window.__iv8__.eventLoop.sleep(100);
window.__iv8__.eventLoop.drain();
({
    initialized: window.__initDone,
    error: window.__resourceError || '',
    url: window.__verifyUrl
})
"""


def parse_jsonp(text):
    return json.loads(text[text.find("(") + 1:text.rfind(")")])


def get(session, url):
    response = session.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    return response


def match_slide_center(piece, background):
    """Normalize ddddocr 1.5.x and 1.6.x slide-match results."""
    matcher = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
    simple_target = False
    try:
        match = matcher.slide_match(piece, background, simple_target=False)
    except (ValueError, SystemError, cv2.error):
        # ddddocr 1.5.x may derive an empty RGBA crop on some slider images.
        simple_target = True
        match = matcher.slide_match(piece, background, simple_target=True)
    target = match.get("target") or []
    if len(target) >= 4:
        center_x = (float(target[0]) + float(target[2])) / 2
    elif target:
        center_x = float(target[0])
    else:
        raise RuntimeError(f"ddddocr returned an invalid slide target: {match!r}")
    match["simple_target"] = simple_target
    match["target_center_x"] = center_x
    return match, center_x


def cache_script(session, url, name):
    source = get(session, url).text
    ensure_cache_dir()
    (CACHE_DIR / name).write_text(source, encoding="utf-8")
    return source


def patch_gcaptcha(source):
    start = source.index("loadCss:function(){")
    end = source.index("},setDark:function(){", start)
    source = source[:start] + "loadCss:function(){return Promise.resolve()}" + source[end + 1:]
    return source.replace("}return i[", "}window.__gtRequire=i;return i[", 1)


def environment():
    # These values came from the verified browser baseline. Adapt from the
    # current evidence owner's same-session browser_env.json for a new target.
    return {
        "location": {
            "href": PAGE_URL, "origin": "https://gt4.geetest.com",
            "protocol": "https:", "host": "gt4.geetest.com",
            "hostname": "gt4.geetest.com", "port": "", "pathname": "/",
            "search": "", "hash": "",
        },
        "navigator": {
            "userAgent": UA, "platform": "Win32", "language": "zh-CN",
            "languages": ["zh-CN", "zh"], "hardwareConcurrency": 28,
            "deviceMemory": 16, "maxTouchPoints": 0, "webdriver": False,
        },
        "screen": {
            "width": 1707, "height": 1067, "availWidth": 1707,
            "availHeight": 1019, "colorDepth": 24, "pixelDepth": 24,
        },
        "window": {
            "innerWidth": 1078, "innerHeight": 630, "outerWidth": 1093,
            "outerHeight": 725, "devicePixelRatio": 1.5,
        },
    }


def build_verify_url(data, answer, scripts):
    with _iv8().JSContext(environment=environment(), config={"timezone": "Asia/Shanghai"}) as ctx:
        for name, value in {
            "captchaId": CAPTCHA_ID, "loadData": data, "answer": answer,
            "gcaptcha": patch_gcaptcha(scripts["gcaptcha"]),
            "gct": scripts["gct"], "lang": scripts["lang"],
        }.items():
            ctx.expose(value, name)
        ctx.eval(BOOTSTRAP)
        ctx.eval(scripts["gt4"])
        result = ctx.eval(SIGN, to_py=True)
    if not isinstance(result, dict):
        raise RuntimeError("iv8 Geetest signer did not return a result object")
    if not result["initialized"] or result["error"]:
        raise RuntimeError(result["error"] or "Geetest initialization failed")
    if not parse_qs(urlparse(result["url"]).query).get("w"):
        raise RuntimeError("Geetest did not generate w")
    return result["url"]


def main():
    session = requests.Session(impersonate="chrome")
    session.headers.update({
        "Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": PAGE_URL, "User-Agent": UA,
    })
    callback = f"geetest_{int(time.time() * 1000)}"
    load = session.get(LOAD_URL, params={
        "callback": callback, "captcha_id": CAPTCHA_ID,
        "challenge": str(uuid.uuid4()), "client_type": "web",
        "risk_type": CAPTCHA_PROTOCOL_TYPE, "lang": "zho",
    }, timeout=TIMEOUT)
    load.raise_for_status()
    loaded_at = time.monotonic()
    data = parse_jsonp(load.text)["data"]
    if data.get("captcha_type") != CAPTCHA_PROTOCOL_TYPE:
        raise RuntimeError(f"unexpected captcha type: {data.get('captcha_type')}")
    static = f"https://{(data.get('static_servers') or ['static.geetest.com'])[0]}/"

    bg = get(session, urljoin(static, data["bg"])).content
    piece = get(session, urljoin(static, data["slice"])).content
    match, gap_x = match_slide_center(piece, bg)
    bg_width = Image.open(io.BytesIO(bg)).width
    piece_width = Image.open(io.BytesIO(piece)).width
    scale = 0.8876 * 340 / bg_width
    set_left = round((gap_x - piece_width / 2) * scale)
    answer = {
        "setLeft": set_left,
        "passtime": random.randint(950, 1450),
        "userresponse": set_left / scale + 2,
    }

    scripts = {
        "gt4": cache_script(session, urljoin(STATIC_HOST, "v4/gt4.js"), "gt4.js"),
        "gcaptcha": cache_script(
            session, urljoin(static, data["static_path"].strip("/") + data["js"]), "gcaptcha4.js"
        ),
        "gct": cache_script(session, urljoin(static, data["gct_path"]), "gct4.js"),
        "lang": cache_script(
            session, urljoin(static, data["static_path"].strip("/") + "/i18n/zho.js"), "zho.js"
        ),
    }
    verify_url = build_verify_url(data, answer, scripts)
    time.sleep(max(0, MIN_VERIFY_DELAY - (time.monotonic() - loaded_at)))
    result = parse_jsonp(get(session, verify_url).text)
    response_data = result.get("data") if isinstance(result, dict) else None
    print(json.dumps({
        "provider": CAPTCHA_PROVIDER,
        "version": CAPTCHA_VERSION,
        "captcha_type": CAPTCHA_TYPE,
        "gap_x": gap_x,
        "move_distance": gap_x - piece_width / 2,
        "setLeft": set_left,
        "verify_has_w": bool(parse_qs(urlparse(verify_url).query).get("w")),
        "status": result.get("status"),
        "result": response_data.get("result") if isinstance(response_data, dict) else None,
        "fail_count": response_data.get("fail_count") if isinstance(response_data, dict) else None,
        "score": response_data.get("score") if isinstance(response_data, dict) else None,
    }, ensure_ascii=False, indent=2))
    if result.get("status") != "success" or not isinstance(response_data, dict) \
            or response_data.get("result") != "success":
        raise RuntimeError("Geetest verifier returned semantic failure")


if __name__ == "__main__":
    main()
