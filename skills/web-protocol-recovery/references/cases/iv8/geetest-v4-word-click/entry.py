# Offline-only case module. Final live egress belongs to python-collector under an approved project work-order.
"""Geetest v4 / 文字点选：Python 识图，官方 JS 在 iv8 中生成 w。"""

def _reject_case_live_egress(action: str='live HTTP') -> None:
    raise RuntimeError(f'case entry refuses {action}: offline-only. Use projectRoot main.py + python-collector with a validated work-order.')
import io
import json
import os
import random
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse
import cv2
import ddddocr
import numpy as np
pass
from PIL import Image, ImageDraw, ImageFont, ImageOps
CAPTCHA_PROVIDER = 'Geetest'
CAPTCHA_VERSION = 'v4'
CAPTCHA_TYPE = '文字点选'
CAPTCHA_PROTOCOL_TYPE = 'word'
CAPTCHA_ID = '54088bb07d2df3c46b79f80300b0abbe'
PAGE_URL = 'https://gt4.geetest.com/'
LOAD_URL = 'https://gcaptcha4.geetest.com/load'
STATIC_HOST = 'https://static.geetest.com/'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36'
TIMEOUT = (10, 30)
MIN_VERIFY_DELAY = 1.5
REQUEST_LIMIT = 20
WORK_DIR = Path.cwd()
CACHE_DIR = WORK_DIR / 'js_reverse_cache'
REQUESTS_USED = 0
FONT_PATH = Path(os.environ.get('GEETEST_CJK_FONT', 'C:\\Windows\\Fonts\\msyh.ttc'))

def _iv8():
    import iv8
    return iv8

def ensure_cache_dir():
    CACHE_DIR.mkdir(exist_ok=True)
BOOTSTRAP = '\ndocument.documentElement.innerHTML = \'<head></head><body><div id="captcha"></div></body>\';\nif (typeof document.createElementNS !== \'function\') {\n    document.createElementNS = window.__iv8__.wrapNative(function(_ns, tag) {\n        return document.createElement(tag);\n    }, \'createElementNS\');\n}\nwindow.__verifyUrl = \'\';\n(function() {\n    var head = document.head;\n    var append = head.appendChild;\n    head.appendChild = window.__iv8__.wrapNative(function(node) {\n        var result = append.call(head, node);\n        var tag = String(node.tagName || \'\').toLowerCase();\n        var src = String(node.src || node.href || \'\');\n        if (tag === \'script\') setTimeout(function() {\n            try {\n                if (src.indexOf(\'/load?\') >= 0) {\n                    var name = decodeURIComponent(/[?&]callback=([^&]+)/.exec(src)[1]);\n                    window[name]({status: \'success\', data: window.__iv8__.data.loadData});\n                } else if (src.indexOf(\'/verify?\') >= 0) {\n                    window.__verifyUrl = src;\n                    var verifyName = decodeURIComponent(/[?&]callback=([^&]+)/.exec(src)[1]);\n                    if (typeof window[verifyName] === \'function\') {\n                        window[verifyName]({status: \'error\', data: {result: \'fail\'}});\n                    }\n                } else if (src.indexOf(\'/gct/\') >= 0) {\n                    (0, eval)(window.__iv8__.data.gct);\n                } else if (src.indexOf(\'/js/gcaptcha4.js\') >= 0) {\n                    (0, eval)(window.__iv8__.data.gcaptcha);\n                } else if (src.indexOf(\'/i18n/\') >= 0) {\n                    (0, eval)(window.__iv8__.data.lang);\n                }\n                node.readyState = \'complete\';\n                if (typeof node.onload === \'function\') node.onload();\n            } catch (error) {\n                window.__resourceError = String(error && (error.stack || error));\n            }\n        }, 0);\n        else if (tag === \'link\') setTimeout(function() {\n            if (typeof node.onload === \'function\') node.onload();\n        }, 0);\n        return result;\n    }, \'appendChild\');\n})();\n'
SIGN = "\nwindow.__initDone = false;\nwindow.initGeetest4({\n    captchaId: window.__iv8__.data.captchaId,\n    riskType: window.__iv8__.data.protocolType,\n    product: 'float',\n    language: 'zho'\n}, function(obj) {\n    window.captchaObj = obj;\n    obj.appendTo('#captcha');\n    obj.showCaptcha();\n    window.__initDone = true;\n});\nwindow.__iv8__.eventLoop.drain();\nwindow.__iv8__.eventLoop.sleep(1000);\nwindow.__iv8__.eventLoop.drain();\nvar backend = window.__gtRequire(17).default.$_BEP(window.captchaObj.$_BAGF);\nbackend.$_BBFs(window.__iv8__.data.answer, function() {}, true);\nwindow.__iv8__.eventLoop.drain();\nwindow.__iv8__.eventLoop.sleep(100);\nwindow.__iv8__.eventLoop.drain();\n({initialized: window.__initDone, error: window.__resourceError || '', url: window.__verifyUrl})\n"

def parse_jsonp(text):
    return json.loads(text[text.find('(') + 1:text.rfind(')')])

def get(session, url, **kwargs):
    global REQUESTS_USED
    if REQUESTS_USED >= REQUEST_LIMIT:
        raise RuntimeError('request budget exhausted')
    if urlparse(url).hostname not in {'gcaptcha4.geetest.com', 'static.geetest.com'}:
        raise RuntimeError(f'host outside allowed scope: {url}')
    REQUESTS_USED += 1
    response = (_reject_case_live_egress('session.get'), None)[1]
    response.raise_for_status()
    if len(response.content) > 8 * 1024 * 1024:
        raise RuntimeError('response exceeded 8 MiB')
    return response

def cache_script(session, url, name):
    source = get(session, url).text
    ensure_cache_dir()
    (CACHE_DIR / name).write_text(source, encoding='utf-8')
    return source

def first_cjk(value):
    return next((char for char in str(value) if '㐀' <= char <= '鿿'), '')

def prompt_image(data):
    return Image.open(io.BytesIO(data)).convert('RGBA')

def candidate_labels(crop, beta_ocr, classic_ocr):
    labels = set()
    rgb = np.array(crop.convert('RGB'))
    color_mask = Image.fromarray(np.where(rgb.max(axis=2) - rgb.min(axis=2) > 80, 0, 255).astype(np.uint8))
    for image in (crop, color_mask):
        for angle in range(-40, 41, 10):
            rotated = image.rotate(angle, expand=True, fillcolor='white').resize((96, 96))
            buffer = io.BytesIO()
            rotated.save(buffer, format='PNG')
            for ocr in (beta_ocr, classic_ocr):
                label = first_cjk(ocr.classification(buffer.getvalue()))
                if label:
                    labels.add(label)
    return labels

def feature_score(prompt, candidate):
    create_sift = getattr(cv2, 'SIFT_create', None)
    if create_sift is None:
        return 0
    prompt_gray = np.array(ImageOps.invert(prompt.getchannel('A')).resize((128, 128)))
    candidate_gray = cv2.cvtColor(np.array(candidate.convert('RGB').resize((128, 128))), cv2.COLOR_RGB2GRAY)
    sift = create_sift()
    _, prompt_descriptors = sift.detectAndCompute(prompt_gray, None)
    _, candidate_descriptors = sift.detectAndCompute(candidate_gray, None)
    if prompt_descriptors is None or candidate_descriptors is None:
        return 0
    pairs = cv2.BFMatcher().knnMatch(prompt_descriptors, candidate_descriptors, k=2)
    return sum((1 for pair in pairs if len(pair) == 2 and pair[0].distance < 0.8 * pair[1].distance))

def glyph_left_score(prompt, labels):
    if not FONT_PATH.exists():
        return 0
    left = np.array(ImageOps.invert(prompt.getchannel('A')).resize((128, 128)))[:, :58]
    font = ImageFont.truetype(str(FONT_PATH), 86)
    sift_factory = getattr(cv2, 'SIFT_create', None)
    if not callable(sift_factory):
        raise RuntimeError('OpenCV build does not provide SIFT_create')
    sift: Any = sift_factory()
    best = 0
    for label in labels:
        canvas = Image.new('L', (128, 128), 'white')
        draw = ImageDraw.Draw(canvas)
        box = draw.textbbox((0, 0), label, font=font)
        draw.text(((128 - (box[2] - box[0])) / 2, (128 - (box[3] - box[1])) / 2 - box[1]), label, font=font, fill='black')
        right = np.array(ImageOps.invert(canvas))[:, :58]
        _, a = sift.detectAndCompute(left, None)
        _, b = sift.detectAndCompute(right, None)
        if a is None or b is None:
            continue
        pairs = cv2.BFMatcher().knnMatch(a, b, k=2)
        best = max(best, sum((1 for pair in pairs if len(pair) == 2 and pair[0].distance < 0.8 * pair[1].distance)))
    return best

def solve_word(background, prompts):
    beta_ocr = ddddocr.DdddOcr(ocr=True, det=False, beta=True, show_ad=False)
    classic_ocr = ddddocr.DdddOcr(ocr=True, det=False, beta=False, show_ad=False)
    detector = ddddocr.DdddOcr(ocr=False, det=True, show_ad=False)
    prompt_images = [prompt_image(data) for data in prompts]
    prompt_text = []
    for image in prompt_images:
        white = Image.new('RGBA', image.size, 'white')
        white.alpha_composite(image)
        normalized = ImageOps.autocontrast(white.convert('L')).resize((128, 128))
        buffer = io.BytesIO()
        normalized.save(buffer, format='PNG')
        label = first_cjk(beta_ocr.classification(buffer.getvalue()))
        if not label:
            raise RuntimeError('prompt OCR failed')
        prompt_text.append(label)
    boxes = [list(map(int, box)) for box in detector.detection(background)]
    if len(boxes) < len(prompts):
        raise RuntimeError(f'only detected {len(boxes)} candidate boxes')
    image = Image.open(io.BytesIO(background)).convert('RGB')
    crops = [image.crop((max(0, x1 - 4), max(0, y1 - 4), min(image.width, x2 + 4), min(image.height, y2 + 4))) for x1, y1, x2, y2 in boxes]
    labels = [candidate_labels(crop, beta_ocr, classic_ocr) for crop in crops]
    selected = {}
    used = set()
    methods = []
    for prompt_index, label in enumerate(prompt_text):
        exact = [i for i, values in enumerate(labels) if i not in used and label in values]
        if len(exact) == 1:
            selected[prompt_index] = exact[0]
            used.add(exact[0])
    for prompt_index, prompt in enumerate(prompt_images):
        if prompt_index in selected:
            methods.append('ocr-exact')
            continue
        scores = {i: feature_score(prompt, crop) for i, crop in enumerate(crops) if i not in used}
        if max(scores.values()) <= 1:
            radical_scores = {i: glyph_left_score(prompt, labels[i]) for i in scores}
            ranked = sorted(radical_scores, key=lambda i: (radical_scores[i], scores[i], -i), reverse=True)
            candidate = ranked[0]
            if radical_scores[candidate] <= 0 or (len(ranked) > 1 and radical_scores[ranked[0]] == radical_scores[ranked[1]]):
                raise RuntimeError('low-confidence point selection')
            method = f'radical-{radical_scores[candidate]}'
        else:
            candidate = max(scores, key=lambda i: (scores[i], -i))
            method = f'sift-{scores[candidate]}'
        selected[prompt_index] = candidate
        used.add(candidate)
        methods.append(method)
    points = []
    for prompt_index in range(len(prompts)):
        x1, y1, x2, y2 = boxes[selected[prompt_index]]
        points.append([round((x1 + x2) / 2 / image.width * 10000), round((y1 + y2) / 2 / image.height * 10000)])
    return (points, prompt_text, methods)

def patch_gcaptcha(source):
    start = source.index('loadCss:function(){')
    end = source.index('},setDark:function(){', start)
    source = source[:start] + 'loadCss:function(){return Promise.resolve()}' + source[end + 1:]
    return source.replace('}return i[', '}window.__gtRequire=i;return i[', 1)

def environment():
    return {'location': {'href': PAGE_URL, 'origin': 'https://gt4.geetest.com', 'protocol': 'https:', 'host': 'gt4.geetest.com', 'hostname': 'gt4.geetest.com', 'port': '', 'pathname': '/', 'search': '', 'hash': ''}, 'navigator': {'userAgent': UA, 'platform': 'Win32', 'language': 'zh-CN', 'languages': ['zh-CN', 'zh'], 'hardwareConcurrency': 28, 'deviceMemory': 16, 'maxTouchPoints': 0, 'webdriver': False}, 'screen': {'width': 1707, 'height': 1067, 'availWidth': 1707, 'availHeight': 1019, 'colorDepth': 24, 'pixelDepth': 24}, 'window': {'innerWidth': 1078, 'innerHeight': 630, 'outerWidth': 1093, 'outerHeight': 725, 'devicePixelRatio': 1.5}}

def build_verify_url(data, answer, scripts):
    with _iv8().JSContext(environment=environment(), config={'timezone': 'Asia/Shanghai'}) as ctx:
        for name, value in {'captchaId': CAPTCHA_ID, 'protocolType': CAPTCHA_PROTOCOL_TYPE, 'loadData': data, 'answer': answer, 'gcaptcha': patch_gcaptcha(scripts['gcaptcha']), 'gct': scripts['gct'], 'lang': scripts['lang']}.items():
            ctx.expose(value, name)
        ctx.eval(BOOTSTRAP)
        ctx.eval(scripts['gt4'])
        result = ctx.eval(SIGN, to_py=True)
    if not isinstance(result, dict):
        raise RuntimeError('iv8 Geetest signer did not return a result object')
    if not result['initialized'] or result['error']:
        raise RuntimeError(result['error'] or 'Geetest initialization failed')
    if not parse_qs(urlparse(result['url']).query).get('w'):
        raise RuntimeError('Geetest did not generate w')
    return result['url']

def main():
    global REQUESTS_USED
    REQUESTS_USED = 0
    session = _reject_case_live_egress('requests.Session')
    session.headers.update({'Accept': '*/*', 'Accept-Language': 'zh-CN,zh;q=0.9', 'Referer': PAGE_URL, 'User-Agent': UA})
    callback = f'geetest_{int(time.time() * 1000)}'
    load = get(session, LOAD_URL, params={'callback': callback, 'captcha_id': CAPTCHA_ID, 'challenge': str(uuid.uuid4()), 'client_type': 'web', 'risk_type': CAPTCHA_PROTOCOL_TYPE, 'lang': 'zh'})
    loaded_at = time.monotonic()
    data = parse_jsonp(load.text)['data']
    if data.get('captcha_type') != CAPTCHA_PROTOCOL_TYPE:
        raise RuntimeError(f"unexpected captcha type: {data.get('captcha_type')}")
    static = f"https://{(data.get('static_servers') or ['static.geetest.com'])[0]}/"
    background = get(session, urljoin(static, data['imgs'])).content
    prompts = [get(session, urljoin(static, path)).content for path in data['ques']]
    ensure_cache_dir()
    (CACHE_DIR / 'latest_bg.jpg').write_bytes(background)
    for index, prompt in enumerate(prompts, 1):
        (CACHE_DIR / f'latest_q{index}.png').write_bytes(prompt)
    points, prompt_text, methods = solve_word(background, prompts)
    scripts = {'gt4': cache_script(session, urljoin(STATIC_HOST, 'v4/gt4.js'), 'gt4.js'), 'gcaptcha': cache_script(session, urljoin(static, data['static_path'].strip('/') + data['js']), 'gcaptcha4.js'), 'gct': cache_script(session, urljoin(static, data['gct_path']), 'gct4.js'), 'lang': cache_script(session, urljoin(static, data['static_path'].strip('/') + '/i18n/zho.js'), 'zho.js')}
    answer = {'passtime': random.randint(1050, 1450), 'userresponse': points}
    verify_url = build_verify_url(data, answer, scripts)
    time.sleep(max(0, MIN_VERIFY_DELAY - (time.monotonic() - loaded_at)))
    result = parse_jsonp(get(session, verify_url).text)
    response_data = result.get('data') if isinstance(result.get('data'), dict) else {}
    summary = {'provider': CAPTCHA_PROVIDER, 'version': CAPTCHA_VERSION, 'captcha_type': CAPTCHA_TYPE, 'protocol_type': CAPTCHA_PROTOCOL_TYPE, 'prompt_text': prompt_text, 'match_methods': methods, 'verify_has_w': bool(parse_qs(urlparse(verify_url).query).get('w')), 'status': result.get('status'), 'result': response_data.get('result'), 'fail_count': response_data.get('fail_count'), 'score': response_data.get('score'), 'requests_used': REQUESTS_USED}
    print(json.dumps({**summary, 'verify_response': result}, ensure_ascii=False, indent=2))
    if summary['status'] != 'success' or summary['result'] != 'success':
        raise RuntimeError('Geetest verifier returned semantic failure')
if __name__ == '__main__':
    main()
