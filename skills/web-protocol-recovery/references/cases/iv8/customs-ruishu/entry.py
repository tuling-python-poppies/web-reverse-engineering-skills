# Offline-only case module. Final live egress belongs to python-collector under an approved project work-order.
def _reject_case_live_egress(action: str='live HTTP') -> None:
    raise RuntimeError(f'case entry refuses {action}: offline-only. Use projectRoot main.py + python-collector with a validated work-order.')
import json
import re
import urllib.parse
from pathlib import Path
pass
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
environment = {'location': {'ancestorOrigins': {}, 'href': 'http://credit.customs.gov.cn/ccppwebserver/pages/ccpp/html/directory.html', 'origin': 'http://credit.customs.gov.cn', 'protocol': 'http:', 'host': 'credit.customs.gov.cn', 'hostname': 'credit.customs.gov.cn', 'port': '', 'pathname': '/ccppwebserver/pages/ccpp/html/directory.html', 'search': '', 'hash': ''}, 'navigator': {'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}}
url = 'http://credit.customs.gov.cn/ccppserver/ccpp/queryList'
data = {'manaType': '0', 'apanage': '', 'depCodeChg': '', 'curPage': '1', 'pageSize': 20}
headers = {'Accept': 'application/json, text/javascript, */*; q=0.01', 'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'Content-Type': 'application/json; charset=UTF-8', 'Origin': 'http://credit.customs.gov.cn', 'Pragma': 'no-cache', 'Referer': 'http://credit.customs.gov.cn/ccppwebserver/pages/ccpp/html/directory.html', 'User-Agent': environment['navigator']['userAgent'], 'X-Requested-With': 'XMLHttpRequest'}
page_url = environment['location']['href']

def main():
    with _iv8().JSContext(environment=environment, config={'timezone': 'Asia/Shanghai'}) as ctx:
        resp1 = (_reject_case_live_egress('requests.get'), None)[1]
        print(f'首次请求状态码: {resp1.status_code}')
        save_text('customs_first_page.html', resp1.text)
        js_match = re.search('src="([^"]+\\.js)"[^>]*r=\\\'m\\\'', resp1.text)
        js_url = urllib.parse.urljoin(page_url, js_match.group(1))
        js_code = (_reject_case_live_egress('requests.get'), None)[1].text
        save_text('customs_first_rs_source_code.js', js_code)
        ctx.expose({'baseURL': page_url, 'html': resp1.text, 'headers': [[k, v] for k, v in resp1.raw.headers.items()], 'resources': {js_url: js_code}}, 's1')
        ctx.eval('window.__iv8__.page.load(window.__iv8__.data.s1)')
        ctx.eval('window.__iv8__.eventLoop.sleep(100)')
        cookies_str = ctx.eval('window.__iv8__.netLog.entries[window.__iv8__.netLog.entries.length - 1].cookieHeader')
        print(f'首次 cookie fields: {sorted(cookie_header_to_dict(cookies_str))}')
        resp2 = (_reject_case_live_egress('requests.get'), None)[1]
        print(f'第二次请求状态码: {resp2.status_code}')
        save_text('customs_second_page.html', resp2.text)
        js_match2 = re.search('src="([^"]+\\.js)"[^>]*r=\\\'m\\\'', resp2.text)
        js_url2 = urllib.parse.urljoin(page_url, js_match2.group(1))
        js_code2 = (_reject_case_live_egress('requests.get'), None)[1].text
        save_text('customs_second_rs_source_code.js', js_code2)
        ctx.expose({'baseURL': page_url, 'html': resp2.text, 'headers': [[k, v] for k, v in resp2.raw.headers.items()], 'resources': {js_url2: js_code2}}, 's2')
        ctx.eval('window.__iv8__.page.load(window.__iv8__.data.s2)')
        body_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        ctx.expose({'url': url, 'body': body_str}, 'xhrInput')
        ctx.eval("\n            var xhr = new XMLHttpRequest();\n            xhr.open('POST', window.__iv8__.data.xhrInput.url);\n            xhr.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');\n            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');\n            xhr.send(window.__iv8__.data.xhrInput.body);\n        ")
        entry = ctx.eval('window.__iv8__.netLog.entries[window.__iv8__.netLog.entries.length - 1]', to_py=True)
        if not entry:
            print('未找到 queryList 请求')
            exit(1)
        print(f"API URL: {entry['url']}")
        save_text('customs_xhr_entry.json', json.dumps(entry, ensure_ascii=False, indent=2))
        final_cookie = entry.get('cookieHeader') or cookies_str
        api_url = f"{environment['location']['origin']}{entry['url']}" if entry['url'].startswith('/') else entry['url']
        response = (_reject_case_live_egress('requests.post'), None)[1]
        print(f'状态码: {response.status_code}')
        print(f'响应字节数: {len(response.content)}')
if __name__ == '__main__':
    main()
