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

import json
import os
import requests
from pathlib import Path
from urllib.parse import urlencode

CACHE_DIR = Path.cwd() / "js_reverse_cache"
ASSET_DIR = Path(__file__).resolve().parent / "assets"


def _iv8():
    import iv8  # type: ignore

    return iv8


def ensure_cache_dir():
    CACHE_DIR.mkdir(exist_ok=True)


def read_case_asset(filename):
    path = ASSET_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"missing case asset: {path}")
    return path.read_text(encoding="utf-8")


js_code = read_case_asset("bdms_1.0.1.19.js")



environment = {
    "location": {
        "href": "https://www.douyin.com/video/7596496938191654184",
        "origin": "https://www.douyin.com",
        "protocol": "https:",
        "host": "www.douyin.com",
        "hostname": "www.douyin.com",
        "port": "",
        "pathname": "/video/7596496938191654184",
        "search": "",
        "hash": ""
    },
    "navigator": {
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "language": "en-US",
        "languages": ["en-US", "en"],
    },
}

headers = {
    "authority": "www-hj.douyin.com",
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "cache-control": "no-cache",
    "origin": "https://www.douyin.com",
    "pragma": "no-cache",
    "referer": "https://www.douyin.com/",
    "user-agent": environment["navigator"]["userAgent"],
}


def main():
    live_state = json.loads(os.environ.get("WPR_LIVE_STATE_JSON", "{}"))
    cookies = live_state.get("cookies", {})
    if not cookies.get("ttwid"):
        raise RuntimeError("missing live ttwid; run pull_live_state.py and pass its JSON through WPR_LIVE_STATE_JSON")

    url = "https://www-hj.douyin.com/aweme/v1/web/aweme/detail/"
    params = {
        "device_platform": "webapp",
        "aid": "6383",
        "channel": "channel_pc_web",
        "aweme_id": "7596496938191654184",
        "request_source": "600",
        "origin_type": "video_page",
        "update_version_code": "170400",
        "pc_client_type": "1",
        "pc_libra_divert": "Windows",
        "support_h265": "1",
        "support_dash": "1",
    }




    with _iv8().JSContext(environment=environment) as ctx:
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
        ctx.eval(js_code)
        ctx.eval("""
            window.bdms.init({
                "aid": 6383,
                "pageId": 6241,
                "paths": [
                    "^/webcast/",
                    "^/aweme/v1/",
                    "^/aweme/v2/",
                    "/douplus/",
                    "/v1/message/send",
                    "^/live/",
                    "^/captcha/",
                    "^/ecom/",
                    "^/luna/pc"
                ],
                "boe": false,
                "ddrt": 8.5,
                "ic": 8.5
            });;;
        """)
        request_list = ctx.eval(f"""
            var xhr = new XMLHttpRequest();
            xhr.open('GET', "{url}?{urlencode(params, safe='*')}", true);
            xhr.setRequestHeader("Content-Type", 'application/json, text/plain, */*');
            xhr.send(null);
            window.__iv8__.netLog.entries;
        """, to_py=True)

    if not isinstance(request_list, list) or not request_list or not isinstance(request_list[0], dict):
        raise RuntimeError("iv8 netLog did not capture a signed request")

    ensure_cache_dir()
    (CACHE_DIR / "douyin_bdms_netlog_entries.json").write_text(
        json.dumps(request_list, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )



    response = requests.get(request_list[0]["url"], headers=headers, cookies=cookies, timeout=30)


    print(f"status={response.status_code} bytes={len(response.content)} content_type={response.headers.get('content-type', '')}")


if __name__ == "__main__":
    main()
