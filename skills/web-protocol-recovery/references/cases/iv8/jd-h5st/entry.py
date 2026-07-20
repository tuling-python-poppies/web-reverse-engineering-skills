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
# 如果本示例涉及的网站方认为存在侵权，请提交 Issue，将及时删除。
# If any website owner believes this example infringes their rights,
# please open an Issue and it will be promptly removed.
# ============================================================

import hashlib
import json
from pathlib import Path

from curl_cffi import requests

import iv8

CACHE_DIR = Path.cwd() / "js_reverse_cache"
CACHE_DIR.mkdir(exist_ok=True)
ASSET_DIR = Path(__file__).resolve().parent / "assets"


def read_case_asset(filename):
    path = ASSET_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"missing case asset: {path}")
    return path.read_text(encoding="utf-8")


js_code = read_case_asset("js_security_v3_main.js")
index_html = read_case_asset("jd_index.html")


url = "https://api.m.jd.com/api"
params = {
    "appid": "jd-cphdeveloper-m",
    "functionId": "recommend_like_m",
    "body": "{\"func\":\"item_rec\",\"recpos\":6163,\"param\":\"{\\\"pagenum\\\":1,\\\"pagecount\\\":20,\\\"startpos\\\":20,\\\"ptag\\\":\\\"\\\",\\\"sku\\\":\\\"\\\",\\\"cid1\\\":\\\"\\\",\\\"cid2\\\":\\\"\\\",\\\"cid3\\\":\\\"\\\"}\",\"clientPageId\":\"\",\"clientVersion\":\"2.0\"}",
    "x-api-eid-token": "",
    "loginType": "2"
}

with iv8.JSContext(environment={
    "location": {
        "href": "https://m.jd.com/",
        "origin": "https://m.jd.com",
        "protocol": "https:",
        "host": "m.jd.com",
        "hostname": "m.jd.com",
        "port": "",
        "pathname": "/",
        "search": "",
        "hash": ""
    }
}, config={"timezone": "Asia/Shanghai"}) as ctx:
    ctx.eval("""
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
    """)

    ctx.eval(f"document.documentElement.innerHTML = {json.dumps(index_html)}")
    ctx.eval(js_code, name="https://storage.360buyimg.com/webcontainer/main/js_security_v3_main.js")
    h5st = ctx.eval("""
    _ParamsSign = new window.ParamsSignMain({appId: "2088b"})
    _ParamsSign._$sdnmd({
        "appid": "jd-cphdeveloper-m",
        "functionId": "recommend_like_m",
        "body": "%s"
    }).h5st

    """ % hashlib.sha256(params['body'].encode('utf-8')).hexdigest())
    if not isinstance(h5st, str) or not h5st:
        raise RuntimeError("iv8 ParamsSignMain did not return h5st")
    params['h5st'] = h5st

(CACHE_DIR / "jd_h5st.txt").write_text(str(params['h5st']), encoding="utf-8")

headers = {
    "authority": "api.m.jd.com",
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "access-control-request-headers": "x-referer-page,x-rp-client",
    "access-control-request-method": "GET",
    "cache-control": "no-cache",
    "origin": "https://m.jd.com",
    "pragma": "no-cache",
    "referer": "https://m.jd.com/",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

response = requests.get(url, headers=headers, params=params, timeout=30)

print(f"status={response.status_code} bytes={len(response.content)} content_type={response.headers.get('content-type', '')}")
