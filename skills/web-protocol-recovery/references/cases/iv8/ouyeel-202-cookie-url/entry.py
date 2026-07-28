# Offline-only case module. Final live egress belongs to python-collector under an approved project work-order.
def _reject_case_live_egress(action: str='live HTTP') -> None:
    raise RuntimeError(f'case entry refuses {action}: offline-only. Use projectRoot main.py + python-collector with a validated work-order.')
import re
import time
import json
from pathlib import Path
pass
import urllib.parse
CACHE_DIR = Path.cwd() / 'js_reverse_cache'

def _iv8():
    import iv8
    return iv8

def ensure_cache_dir():
    CACHE_DIR.mkdir(exist_ok=True)

def save_text(name, text):
    ensure_cache_dir()
    path = CACHE_DIR / name
    path.write_text(text, encoding='utf-8', errors='ignore')
    return path

def cookie_header_to_dict(cookie_header):
    cookies = {}
    for part in (cookie_header or '').split(';'):
        if '=' not in part:
            continue
        key, value = part.strip().split('=', 1)
        if key:
            cookies[key] = value
    return cookies
environment = {'location': {'href': 'https://www.ouyeel.com/steel/search?shopCode=SCDPT37420601&pageIndex=2&pageSize=50&productType=', 'origin': 'https://www.ouyeel.com', 'protocol': 'https:', 'host': 'www.ouyeel.com', 'hostname': 'www.ouyeel.com', 'port': '', 'pathname': '/steel/search', 'search': '?shopCode=SCDPT37420601&pageIndex=2&pageSize=50&productType=', 'hash': ''}}
headers = {'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'Content-Type': 'application/x-www-form-urlencoded', 'Origin': 'https://www.ouyeel.com', 'Pragma': 'no-cache', 'Referer': 'https://www.ouyeel.com/steel/search?shopCode=SCDPT37420601&pageIndex=2&pageSize=50&productType=', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-origin', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36'}
url = 'https://www.ouyeel.com/search-ng/commoditySearch/queryCommodityResult'
data = {'criteriaJson': '{"pageSize":50,"industryComponent":null,"channel":null,"productType":null,"sort":null,"warehouseCode":null,"key_search":null,"is_central":null,"searchField":null,"companyCode":null,"inquiryCategory":null,"inquirySpec":null,"provider":null,"shopCode":"SCDPT37420601","packCodes":null,"steelFactory":null,"resourceIds":null,"providerCode":null,"jsonParam":{"productType":"","keywordAnalyseResult":null},"excludeShowSoldOut":null,"pageIndex":0,"maxPage":50}'}

def main():
    response = (_reject_case_live_egress('requests.post'), None)[1]
    if response.status_code == 202:
        cookies = response.cookies.get_dict()
        html = response.text
        save_text('ouyeel_challenge.html', html)
        inline_scripts = re.findall("<script[^>]*r='m'[^>]*>([^<]+)</script>", html)
        js_match = re.search('src="([^"]+\\.js)"[^>]*r=\\\'m\\\'', html)
        js_path = js_match.group(1)
        js_response = (_reject_case_live_egress('requests.get'), None)[1]
        save_text('ouyeel_rs_source_code.js', js_response.text)
        start_time = time.time()
        with _iv8().JSContext(environment=environment) as ctx:
            ctx.eval('document.documentElement.innerHTML = ' + json.dumps(html))
            ctx.eval(inline_scripts[1])
            ctx.eval(js_response.text, name=environment['location']['origin'] + js_path)
            ctx.eval(inline_scripts[-1])
            ctx.eval("window.dispatchEvent(new Event('load'))")
            print(f'第一阶段耗时：{time.time() - start_time}')
            signed_xhr_entry = ctx.eval(f"\n                    var xhr = new XMLHttpRequest();\n                    xhr.open('POST', 'https://www.ouyeel.com/search-ng/commoditySearch/queryCommodityResult');\n                    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');\n                    xhr.send({json.dumps(urllib.parse.urlencode(data))});\n                    window.__iv8__.netLog.entries[0];\n                ", to_py=True)
            save_text('ouyeel_xhr_entry.json', json.dumps(signed_xhr_entry, ensure_ascii=False, indent=2))
            document_cookie_str = ctx.eval('document.cookie')
        print(f'总耗时：{time.time() - start_time}')
        cookies.update(cookie_header_to_dict(document_cookie_str))
        response = (_reject_case_live_egress('requests.post'), None)[1]
        print(f"status={response.status_code} bytes={len(response.content)} content_type={response.headers.get('content-type', '')}")
if __name__ == '__main__':
    main()
