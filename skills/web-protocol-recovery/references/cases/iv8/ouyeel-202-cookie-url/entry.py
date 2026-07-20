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

import re
import time
import json
from pathlib import Path

import requests
import urllib.parse

import iv8


CACHE_DIR = Path.cwd() / "js_reverse_cache"
CACHE_DIR.mkdir(exist_ok=True)


def save_text(name, text):
    path = CACHE_DIR / name
    path.write_text(text, encoding="utf-8", errors="ignore")
    return path


def cookie_header_to_dict(cookie_header):
    cookies = {}
    for part in (cookie_header or "").split(";"):
        if "=" not in part:
            continue
        key, value = part.strip().split("=", 1)
        if key:
            cookies[key] = value
    return cookies


environment = {
    "location": {
        "href": "https://www.ouyeel.com/steel/search?shopCode=SCDPT37420601&pageIndex=2&pageSize=50&productType=",
        "origin": "https://www.ouyeel.com",
        "protocol": "https:",
        "host": "www.ouyeel.com",
        "hostname": "www.ouyeel.com",
        "port": "",
        "pathname": "/steel/search",
        "search": "?shopCode=SCDPT37420601&pageIndex=2&pageSize=50&productType=",
        "hash": ""
    }
}


headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://www.ouyeel.com",
    "Pragma": "no-cache",
    "Referer": "https://www.ouyeel.com/steel/search?shopCode=SCDPT37420601&pageIndex=2&pageSize=50&productType=",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
}

url = "https://www.ouyeel.com/search-ng/commoditySearch/queryCommodityResult"

data = {
    "criteriaJson": "{\"pageSize\":50,\"industryComponent\":null,\"channel\":null,\"productType\":null,\"sort\":null,\"warehouseCode\":null,\"key_search\":null,\"is_central\":null,\"searchField\":null,\"companyCode\":null,\"inquiryCategory\":null,\"inquirySpec\":null,\"provider\":null,\"shopCode\":\"SCDPT37420601\",\"packCodes\":null,\"steelFactory\":null,\"resourceIds\":null,\"providerCode\":null,\"jsonParam\":{\"productType\":\"\",\"keywordAnalyseResult\":null},\"excludeShowSoldOut\":null,\"pageIndex\":0,\"maxPage\":50}"
}


response = requests.post(url, headers=headers, data=data, timeout=30)


if response.status_code == 202:
    cookies = response.cookies.get_dict()
    html = response.text
    save_text("ouyeel_challenge.html", html)

    # 提取所有内联脚本
    inline_scripts = re.findall(r"<script[^>]*r='m'[^>]*>([^<]+)</script>", html)

    # 获取外部 JS 内容
    js_match = re.search(r'src="([^"]+\.js)"[^>]*r=\'m\'', html)
    js_path = js_match.group(1)
    js_response = requests.get(environment['location']['origin'] + js_path, headers=headers, cookies=cookies, timeout=30)
    save_text("ouyeel_rs_source_code.js", js_response.text)

    start_time = time.time()
    with iv8.JSContext(environment=environment) as ctx:
        ctx.eval("document.documentElement.innerHTML = " + json.dumps(html))  # 简化，未走流式加载DOM

        # 1. 执行第一段js
        ctx.eval(inline_scripts[1])

        # 2. 执行外部 JS
        ctx.eval(js_response.text, name=environment['location']['origin']+ js_path)

        # 3. 执行最后一个脚本（动态函数名：_$gO() 等）
        ctx.eval(inline_scripts[-1])
        ctx.eval("window.dispatchEvent(new Event('load'))")
        print(f"第一阶段耗时：{time.time() - start_time}")

        # 后缀
        signed_xhr_entry = ctx.eval(f"""
                var xhr = new XMLHttpRequest();
                xhr.open('POST', 'https://www.ouyeel.com/search-ng/commoditySearch/queryCommodityResult');
                xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
                xhr.send({json.dumps(urllib.parse.urlencode(data))});
                window.__iv8__.netLog.entries[0];
            """, to_py=True)
        save_text("ouyeel_xhr_entry.json", json.dumps(signed_xhr_entry, ensure_ascii=False, indent=2))

        document_cookie_str = ctx.eval('document.cookie')

    print(f"总耗时：{time.time() - start_time}")


    cookies.update(cookie_header_to_dict(document_cookie_str))

    response = requests.post(signed_xhr_entry["url"], headers=headers, data=data, cookies=cookies, timeout=30)

    print(f"status={response.status_code} bytes={len(response.content)} content_type={response.headers.get('content-type', '')}")
