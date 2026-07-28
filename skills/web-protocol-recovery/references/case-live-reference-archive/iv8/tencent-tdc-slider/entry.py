# pyright: reportMissingImports=false
import hashlib
import importlib.util
import json
import os
import time
from pathlib import Path
import io

import requests

_HAS_DDDDOCR = importlib.util.find_spec("ddddocr") is not None and importlib.util.find_spec("PIL") is not None

class PrintLogger:
    @staticmethod
    def info(message, *args):
        print(message.format(*args))


logger = PrintLogger()

# ============================================================================
# 可编辑常量
# ============================================================================

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
BASE_URL = "https://turing.captcha.qcloud.com"
PAGE_URL = "https://login-user.kugou.com/login/?appid=1014&ref=https://www.kugou.com/reg/web/&redirect_uri=https://staticssl.kugou.com/common/html/login/regok.html&callback=UsLoginCallback"
AID = "197787253"

WORK_DIR = Path.cwd()
CACHE_DIR = WORK_DIR / "js_reverse_cache"
SAVE_RAW_CACHE = os.environ.get("IV8_ALLOW_CACHE_WRITE") == "1"


def _iv8():
    import iv8  # type: ignore

    return iv8


def ensure_cache_dir():
    CACHE_DIR.mkdir(exist_ok=True)

proxies = {}
REQUEST_TIMEOUT = (10, 30)


def cache_json(name, value):
    if SAVE_RAW_CACHE:
        ensure_cache_dir()
        (CACHE_DIR / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

headers = {
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Pragma": "no-cache",
    "Referer": "https://login-user.kugou.com/",
    "Sec-Fetch-Dest": "script",
    "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Site": "cross-site",
    "User-Agent": UA,
}

environment = {
    "location": {
        "href": PAGE_URL,
        "origin": "https://login-user.kugou.com",
        "protocol": "https:",
        "host": "login-user.kugou.com",
        "hostname": "login-user.kugou.com",
        "port": "",
        "pathname": "/login/",
        "search": "?appid=1014&ref=https://www.kugou.com/reg/web/&redirect_uri=https://staticssl.kugou.com/common/html/login/regok.html&callback=UsLoginCallback",
        "hash": "",
    },
    "navigator": {
        "userAgent": UA,
        "platform": "Win32",
        "language": "zh-CN",
        "languages": ["zh-CN", "zh", "en"],
        "webdriver": False,
    },
    "screen": {
        "width": 1920,
        "height": 1080,
        "availWidth": 1920,
        "availHeight": 1040,
        "colorDepth": 24,
    },
}


# ============================================================================
# 辅助函数
# ============================================================================

def find_gap(bg_bytes, sprite_bytes, crop_xy, crop_wh):
    if _HAS_DDDDOCR:
        import ddddocr
        from PIL import Image

        """ddddocr 滑块识别：PIL 裁剪 sprite 拼图块后做滑块匹配"""
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

    import cv2
    import numpy as np

    bg_img = cv2.imdecode(np.frombuffer(bg_bytes, np.uint8), cv2.IMREAD_COLOR)
    sprite_img = cv2.imdecode(np.frombuffer(sprite_bytes, np.uint8), cv2.IMREAD_COLOR)
    if bg_img is None or sprite_img is None:
        raise RuntimeError("OpenCV could not decode captcha images")

    sx, sy = crop_xy
    sw, sh = crop_wh
    tp_gray = cv2.cvtColor(sprite_img, cv2.COLOR_BGR2GRAY)[sy:sy + sh, sx:sx + sw]

    bg_shift = cv2.pyrMeanShiftFiltering(bg_img, 5.0, 50.0)
    tp_edges = cv2.Canny(tp_gray, 255, 255)
    bg_edges = cv2.Canny(bg_shift, 255, 255)

    match_map = cv2.matchTemplate(bg_edges, tp_edges, cv2.TM_CCOEFF_NORMED)
    _, _, _, max_loc = cv2.minMaxLoc(match_map)
    return max_loc


def solve_pow(challenge_prefix, target_md5, timeout=30):
    """暴力搜索 MD5  nonce  求解 POW"""
    start = time.time()
    nonce = 0
    while time.time() - start < timeout:
        if hashlib.md5(f"{challenge_prefix}{nonce}".encode()).hexdigest() == target_md5:
            return nonce, int((time.time() - start) * 1000)
        nonce += 1
    return nonce, int((time.time() - start) * 1000)


# ============================================================================
# Step 1: cap_union_prehandle —— 获取验证码会话数据
# ============================================================================


def main():
    url = BASE_URL + "/cap_union_prehandle"
    params = {
        "aid": AID,
        "protocol": "https",
        "accver": "1",
        "showtype": "popup",
        "ua": "TW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEwNC4wLjAuMCBTYWZhcmkvNTM3LjM2",
        "noheader": "1",
        "fb": "1",
        "aged": "0",
        "enableAged": "0",
        "enableDarkMode": "0",
        "grayscale": "1",
        "clientype": "2",
        "cap_cd": "",
        "uid": "",
        "lang": "zh-cn",
        "entry_url": "https://login-user.kugou.com/login/",
        "elder_captcha": "0",
        "js": "/tcaptcha-frame.5bae14dd.js",
        "login_appid": "",
        "wb": "1",
        "subsid": "1",
        "callback": "",
        "sess": "",
    }
    response = requests.get(url, headers=headers, params=params, proxies=proxies, timeout=REQUEST_TIMEOUT)
    response_json = json.loads(response.text[1:-1])
    cache_json("tdc_prehandle.json", response_json)

    sess = response_json["sess"]
    sid = response_json["sid"]
    tdc_path = response_json["data"]["comm_captcha_cfg"]["tdc_path"]
    pow_prefix = response_json["data"]["comm_captcha_cfg"]["pow_cfg"]["prefix"]
    pow_md5 = response_json["data"]["comm_captcha_cfg"]["pow_cfg"]["md5"]

    dyn_info = response_json["data"]["dyn_show_info"]
    bg_url = dyn_info["bg_elem_cfg"]["img_url"]
    sprite_url = dyn_info["sprite_url"]

    puzzle_cfg = next(
        fg for fg in dyn_info["fg_elem_list"]
        if fg.get("move_cfg", {}).get("data_type")
    )
    sprite_pos = puzzle_cfg["sprite_pos"]
    size_2d = puzzle_cfg["size_2d"]
    init_pos_y = puzzle_cfg["init_pos"][1]

    logger.info("captcha session received; sess_len={}", len(sess))
    logger.info("拼图块: sprite_pos={}, size={}, init_pos_y={}", sprite_pos, size_2d, init_pos_y)

    # ============================================================================
    # Step 2: 下载图片 + 识别缺口位置
    # ============================================================================

    bg_data = requests.get(BASE_URL + bg_url, headers=headers, proxies=proxies, timeout=REQUEST_TIMEOUT).content
    sprite_data = requests.get(BASE_URL + sprite_url, headers=headers, proxies=proxies, timeout=REQUEST_TIMEOUT).content
    if SAVE_RAW_CACHE:
        ensure_cache_dir()
        (CACHE_DIR / "tdc_bg_image.bin").write_bytes(bg_data)
        (CACHE_DIR / "tdc_sprite_image.bin").write_bytes(sprite_data)

    gap_pos = find_gap(bg_data, sprite_data, sprite_pos, size_2d)
    gap_x = gap_pos[0]
    init_pos_x = puzzle_cfg["init_pos"][0]
    move_distance = gap_x - init_pos_x
    logger.info("缺口位置: x={}, y={}", gap_pos[0], gap_pos[1])
    logger.info("拼图初始位置: x={}, 需要移动距离: {}px", init_pos_x, move_distance)

    # ============================================================================
    # Step 3: 求解 POW
    # ============================================================================

    pow_ans, pow_time = solve_pow(pow_prefix, pow_md5)
    logger.info("POW: ans={}, time={}ms", pow_ans, pow_time)

    # ============================================================================
    # Step 4: 生成滑块拖拽轨迹
    # ============================================================================

    traj = [[0.0034882217273119877, 0.3640062113271487, 0], [0.16116017976391322, 1.3434697736274832, 5], [0.8082328016777587, 1.6773426133215674, 10], [2.589265126295226, 0.9530825477545615, 15], [8.55652025326086, 1.1984456881526069, 20], [17.07542660604542, 0.1982774020748035, 26], [32.2419314172331, -2.1677630547678, 32], [45.95648323142274, -1.4971381802309534, 39], [64.59384359706242, -0.028904276244747784, 45], [79.05661829111422, -0.4231823437196679, 51], [106.34217705294992, -2.1756571267898837, 55], [134.4355456481945, -2.2949652977629875, 62], [157.3688656867247, -1.4246767641301834, 69], [187.26764315761068, -0.27630191375345947, 74], [220.40938626528248, -1.6471492437010922, 81], [245.48208117889266, -2.2976787633546647, 88], [266.5201576629163, -2.388773273843453, 94], [293.49457651907005, -3.1530489504538104, 98], [321.33715929308016, -3.478504600137932, 105], [350.23870937501505, -0.00505056232160328, 111], [370.1673109281234, 1.841392238892762, 118], [395.79070579144076, 4.122152800631017, 123], [415.311530833768, 5.487770885251011, 131], [431.9909807634337, 4.843442183314909, 137], [444.4214584422933, 3.448826876830256, 143], [455.66751026965954, 2.701446579007204, 148], [465.71163568209073, 1.9708211765475538, 153], [473.6254717665588, 2.5200661230569485, 159], [479.6755947074312, 1.628972184406798, 165], [482.5020581479708, 0.5946008659218551, 172], [483.52058229595326, -0.5749900423804799, 178], [482.2222118096939, -1.1607497264330568, 184], [480.26956643183877, -1.9428061304821074, 190], [475.9011638657713, -1.9463742861657936, 195], [468.6607014059131, -2.6979862962955523, 201], [462.67268944271086, -2.669957105311624, 208], [453.8498042992967, -2.196369781834755, 212], [443.43033484672014, -1.3104474312500072, 218], [434.0840854316353, -1.3389556664804052, 224], [423.4419450795285, -0.45775591189470066, 230], [413.1615517186761, 0.15847096625233592, 235], [404.6411975603229, -0.04776714726167042, 240], [395.8695095449859, -0.4810613210584501, 244]]

    # iv8：可信拖拽与 TDC 采集拆成两段 eval，便于阅读与计时
    JS_TRUSTED_DRAG = """
    const st = window.__iv8__;
    const input = st.input;
    const traj = st.data.traj;

    const startX = 50 + Math.floor(Math.random() * 10);
    const startY = 410 + Math.floor(Math.random() * 15);
    const handle = document.body || document.documentElement;

    function dispatchTrustedDragByTrajectory(input, st, trajectory, start, handle) {
        const pointerBase = {
            target: handle,
            pointerId: 1,
            pointerType: "mouse",
            isPrimary: true,
            button: 0,
        };

        const down = {
            clientX: start.clientX,
            clientY: start.clientY,
            button: 0,
            buttons: 1,
        };

        input.dispatchPointerEvent({ ...pointerBase, ...down, type: "pointerdown" });
        input.dispatchMouseEvent({ target: handle, ...down, type: "mousedown" });

        let lastT = 0;
        let lastX = start.clientX;
        let lastY = start.clientY;

        for (const rawPt of trajectory) {
            const dx = Number(rawPt[0]) || 0;
            const dy = Number(rawPt[1]) || 0;
            const t = Number(rawPt[2]) || 0;
            const dt = Math.max(0, t - lastT);
            if (dt > 0) {
                st.eventLoop.sleep(dt);
            }

            lastX = start.clientX + dx;
            lastY = start.clientY + dy;
            lastT = t;

            const move = {
                target: document,
                clientX: lastX,
                clientY: lastY,
                button: 0,
                buttons: 1,
            };
            input.dispatchPointerEvent({ ...pointerBase, target: document, ...move, type: "pointermove" });
            input.dispatchMouseEvent({ ...move, type: "mousemove" });
        }

        const up = {
            target: document,
            clientX: lastX,
            clientY: lastY,
            button: 0,
            buttons: 0,
        };
        input.dispatchPointerEvent({ ...pointerBase, target: document, ...up, type: "pointerup" });
        input.dispatchMouseEvent({ ...up, type: "mouseup" });
    }

    dispatchTrustedDragByTrajectory(input, st, traj, { clientX: startX, clientY: startY }, handle);
    st.eventLoop.sleep(50);
    """

    JS_TDC_COLLECT = """
    const collect = decodeURIComponent(window.TDC.getData(true));
    const eksRaw = window.TDC.getInfo();

    ({ collect, eks: eksRaw.info || eksRaw })
    """

    # ============================================================================
    # Step 5: iv8 执行 TDC JS + 可信输入模拟 + 收集 collect/eks
    # ============================================================================

    tdc_js = requests.get(BASE_URL + tdc_path, headers=headers, proxies=proxies, timeout=REQUEST_TIMEOUT).text
    if SAVE_RAW_CACHE:
        ensure_cache_dir()
        (CACHE_DIR / "tdc_runtime.js").write_text(tdc_js, encoding="utf-8", errors="ignore")

    with _iv8().JSContext(environment=environment) as ctx:
        ctx.expose(traj, "traj")

        ctx.eval(tdc_js)
        ctx.eval(JS_TRUSTED_DRAG)
        tdc_result = ctx.eval(JS_TDC_COLLECT, to_py=True)
        if not isinstance(tdc_result, dict):
            raise RuntimeError("iv8 TDC collector did not return a result object")

        collect = tdc_result["collect"]
        eks = tdc_result["eks"]
        if SAVE_RAW_CACHE:
            ensure_cache_dir()
            (CACHE_DIR / "tdc_collect.txt").write_text(collect, encoding="utf-8", errors="ignore")
            (CACHE_DIR / "tdc_eks.txt").write_text(str(eks), encoding="utf-8", errors="ignore")
        logger.info("collect 长度: {}", len(collect))

    logger.info("eks type={} keys={}", type(eks).__name__, sorted(eks) if isinstance(eks, dict) else "n/a")

    # ============================================================================
    # Step 6: 提交验证
    # ============================================================================

    ans_data = json.dumps([{
        "elem_id": 1,
        "type": "DynAnswerType_POS",
        "data": f"{gap_x + 10},{init_pos_y}",
    }])

    verify_data = {
        "collect": collect,
        "tlg": str(len(collect)),
        "eks": eks,
        "sess": sess,
        "ans": ans_data,
        "pow_answer": f"{pow_prefix}{pow_ans}",
        "pow_calc_time": str(pow_time),
    }

    verify_resp = requests.post(
        BASE_URL + "/cap_union_new_verify",
        headers=headers,
        data=verify_data,
        proxies=proxies,
        timeout=REQUEST_TIMEOUT,
    )

    logger.info("验证 HTTP {}，响应字节数={}", verify_resp.status_code, len(verify_resp.content))


if __name__ == "__main__":
    main()
