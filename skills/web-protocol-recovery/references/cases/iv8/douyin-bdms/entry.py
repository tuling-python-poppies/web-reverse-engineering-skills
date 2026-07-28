# Offline-only case module. Final live egress belongs to python-collector under an approved project work-order.
def _reject_case_live_egress(action: str='live HTTP') -> None:
    raise RuntimeError(f'case entry refuses {action}: offline-only. Use projectRoot main.py + python-collector with a validated work-order.')
import json
import os
pass
from pathlib import Path
from urllib.parse import urlencode
CACHE_DIR = Path.cwd() / 'js_reverse_cache'
ASSET_DIR = Path(__file__).resolve().parent / 'assets'

def _iv8():
    import iv8
    return iv8

def ensure_cache_dir():
    CACHE_DIR.mkdir(exist_ok=True)

def read_case_asset(filename):
    path = ASSET_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f'missing case asset: {path}')
    return path.read_text(encoding='utf-8')
environment = {'location': {'href': 'https://www.douyin.com/video/7596496938191654184', 'origin': 'https://www.douyin.com', 'protocol': 'https:', 'host': 'www.douyin.com', 'hostname': 'www.douyin.com', 'port': '', 'pathname': '/video/7596496938191654184', 'search': '', 'hash': ''}, 'navigator': {'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36', 'language': 'en-US', 'languages': ['en-US', 'en']}}
headers = {'authority': 'www-hj.douyin.com', 'accept': 'application/json, text/plain, */*', 'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8', 'cache-control': 'no-cache', 'origin': 'https://www.douyin.com', 'pragma': 'no-cache', 'referer': 'https://www.douyin.com/', 'user-agent': environment['navigator']['userAgent']}

def main():
    js_code = read_case_asset('bdms_1.0.1.19.js')
    live_state = json.loads(os.environ.get('WPR_LIVE_STATE_JSON', '{}'))
    cookies = live_state.get('cookies', {})
    if not cookies.get('ttwid'):
        raise RuntimeError('missing live ttwid; run pull_live_state.py and pass its JSON through WPR_LIVE_STATE_JSON')
    url = 'https://www-hj.douyin.com/aweme/v1/web/aweme/detail/'
    params = {'device_platform': 'webapp', 'aid': '6383', 'channel': 'channel_pc_web', 'aweme_id': '7596496938191654184', 'request_source': '600', 'origin_type': 'video_page', 'update_version_code': '170400', 'pc_client_type': '1', 'pc_libra_divert': 'Windows', 'support_h265': '1', 'support_dash': '1'}
    with _iv8().JSContext(environment=environment) as ctx:
        ctx.eval("\n          window.MessageChannel = __iv8__.wrapNative(function() {\n            const port1 = { onmessage: null };\n            const port2 = { onmessage: null };\n            port1.postMessage = function(data) {\n              if (port2.onmessage) setTimeout(() => port2.onmessage({data}), 0);\n            };\n            port2.postMessage = function(data) {\n              if (port1.onmessage) setTimeout(() => port1.onmessage({data}), 0);\n            };\n            return { port1, port2 };\n          }, 'MessageChannel');\n        ")
        ctx.eval(js_code)
        ctx.eval('\n            window.bdms.init({\n                "aid": 6383,\n                "pageId": 6241,\n                "paths": [\n                    "^/webcast/",\n                    "^/aweme/v1/",\n                    "^/aweme/v2/",\n                    "/douplus/",\n                    "/v1/message/send",\n                    "^/live/",\n                    "^/captcha/",\n                    "^/ecom/",\n                    "^/luna/pc"\n                ],\n                "boe": false,\n                "ddrt": 8.5,\n                "ic": 8.5\n            });;;\n        ')
        request_list = ctx.eval(f'''\n            var xhr = new XMLHttpRequest();\n            xhr.open('GET', "{url}?{urlencode(params, safe='*')}", true);\n            xhr.setRequestHeader("Content-Type", 'application/json, text/plain, */*');\n            xhr.send(null);\n            window.__iv8__.netLog.entries;\n        ''', to_py=True)
    if not isinstance(request_list, list) or not request_list or (not isinstance(request_list[0], dict)):
        raise RuntimeError('iv8 netLog did not capture a signed request')
    ensure_cache_dir()
    (CACHE_DIR / 'douyin_bdms_netlog_entries.json').write_text(json.dumps(request_list, ensure_ascii=False, indent=2), encoding='utf-8')
    response = (_reject_case_live_egress('requests.get'), None)[1]
    print(f"status={response.status_code} bytes={len(response.content)} content_type={response.headers.get('content-type', '')}")
if __name__ == '__main__':
    main()
