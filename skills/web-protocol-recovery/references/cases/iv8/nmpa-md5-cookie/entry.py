# Offline-only case module. Final live egress belongs to python-collector under an approved project work-order.
def _reject_case_live_egress(action: str='live HTTP') -> None:
    raise RuntimeError(f'case entry refuses {action}: offline-only. Use projectRoot main.py + python-collector with a validated work-order.')
import re
import time
from pathlib import Path
pass
import urllib.parse
import hashlib
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

def json_md5_to_str(input_str, app_secret='nmpasecret2020'):
    """严格 URL 编码（含 ~）+ MD5 签名"""
    input_str += '&' + app_secret
    encoded = urllib.parse.quote(input_str, safe='').replace('~', '%7E')
    return hashlib.md5(encoded.encode('utf-8')).hexdigest()
environment = {'location': {'ancestorOrigins': {}, 'href': 'https://www.nmpa.gov.cn/datasearch/search-result.html', 'origin': 'https://www.nmpa.gov.cn', 'protocol': 'https:', 'host': 'www.nmpa.gov.cn', 'hostname': 'www.nmpa.gov.cn', 'port': '', 'pathname': '/datasearch/search-result.html', 'search': '', 'hash': ''}, 'navigator': {'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}}
url = 'https://www.nmpa.gov.cn/datasearch/data/nmpadata/search'
params = {'itemId': 'ff80808183cad75001840881f848179f', 'isSenior': 'N', 'searchValue': '阿莫西林', 'pageNum': 1, 'pageSize': 10, 'timestamp': int(time.time()) * 1000}
headers = {'Accept': 'application/json, text/plain, */*', 'User-Agent': environment['navigator']['userAgent'], 'sign': json_md5_to_str('&'.join([f'{k}={v}' for k, v in sorted(params.items())])), 'timestamp': str(params['timestamp'])}
cookies = {}

def main():
    response = (_reject_case_live_egress('requests.get'), None)[1]
    if response.status_code != 200:
        cookies.update(response.cookies.get_dict())
        save_text('nmpa_challenge.html', response.text)
        js_match = re.search('src="([^"]+\\.js)"[^>]*r=\\\'m\\\'', response.text)
        js_path = js_match.group(1)
        js_full_url = environment['location']['origin'] + js_path
        js_response = (_reject_case_live_egress('requests.get'), None)[1]
        save_text('nmpa_rs_source_code.js', js_response.text)
        start_time = time.time()
        with _iv8().JSContext(environment=environment, config={'timezone': 'Asia/Shanghai'}) as ctx:
            snapshot = {'baseURL': environment['location']['href'], 'html': response.text, 'headers': [[k, v] for k, v in response.headers.items()], 'resources': {js_full_url: js_response.text}}
            ctx.expose(snapshot, 'snapshot')
            ctx.eval('__iv8__.page.load(__iv8__.data.snapshot);')
            document_cookie_str = ctx.eval('document.cookie')
            cookies.update(cookie_header_to_dict(document_cookie_str))
            print(f'计算耗时：{time.time() - start_time:.2f} 秒')
            response = (_reject_case_live_egress('requests.get'), None)[1]
            print(f'status={response.status_code} bytes={len(response.content)}')
    else:
        print('正常请求')
        print(f'status={response.status_code} bytes={len(response.content)}')
if __name__ == '__main__':
    main()
