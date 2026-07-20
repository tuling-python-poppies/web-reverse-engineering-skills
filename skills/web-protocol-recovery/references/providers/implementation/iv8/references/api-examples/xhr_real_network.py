"""
iv8 XHR 真实网络桥接

演示内容：
  - hook XMLHttpRequest.open/send，让 XHR 请求走 Python requests 真实发包
  - 通过 add_resource 注入真实响应，保证 XHR 事件链完整触发
  - 异步 XHR + 事件循环推进，readyState 状态机时序完全对齐 Chromium
  - readystatechange / onload / onloadend 全部按正确顺序触发
  - 适用于需要真实网络交互的反爬/验证码场景

原理：
  JS hook xhr.send() → 调用 Python requests 真实发包 → add_resource 注入响应
  → 原始 send() 将 readyState 状态推进拆分为宏任务排入事件循环
  → eventLoop.drain() 逐步推进 → C++ 层按 Chromium 时序驱动所有事件

异步 XHR 事件时序（对齐 Chromium）：
  send() → loadstart → [宏任务] readyState=2 (HEADERS_RECEIVED)
         → [宏任务] readyState=3 (LOADING)
         → [宏任务] readyState=4 (DONE) → load → loadend

⚠ GIL 注意：
  每次 XHR 请求都会同步调用 Python requests，阻塞 V8 执行。
  适合调试和逆向分析，不适合高并发生产场景。

---

iv8 XHR Real Network Bridge

Demonstrates:
  - Hook XMLHttpRequest.open/send to route XHR through Python requests
  - Inject real responses via add_resource, preserving full XHR event lifecycle
  - Async XHR + event loop advancement, readyState timing aligned with Chromium
  - readystatechange / onload / onloadend all fire in correct order
  - Suitable for anti-bot / captcha scenarios requiring real network interaction

How it works:
  JS hooks xhr.send() → calls Python requests (real HTTP) → add_resource injects response
  → original send() posts readyState transitions as macrotasks into event loop
  → eventLoop.drain() advances step by step → C++ drives all events per Chromium timing

Async XHR event timing (Chromium-aligned):
  send() → loadstart → [macrotask] readyState=2 (HEADERS_RECEIVED)
         → [macrotask] readyState=3 (LOADING)
         → [macrotask] readyState=4 (DONE) → load → loadend

⚠ GIL Note:
  Each XHR request synchronously calls Python requests, blocking V8 execution.
  Suitable for debugging and reverse engineering, not for high-concurrency production.
"""

import json
import requests
import iv8


def setup_real_network(ctx):
    """
    安装 XHR 真实网络桥接 hook。
    Install XHR real network bridge hooks.

    调用后，当前 ctx 中所有 XHR 请求都会走 Python requests 真实发包，
    响应自动注入 resource bundle，XHR 事件链完整保留。
    """

    def real_fetch(method, url, body, headers_json):
        method = str(method).upper()
        url = str(url)
        req_headers = json.loads(str(headers_json)) if headers_json else {}
        req_body = str(body) if body and str(body) != "null" else None

        print(f"  [Python] {method} {url}")
        resp = requests.request(method, url, data=req_body,
                                headers=req_headers, timeout=30)
        print(f"  [Python] -> {resp.status_code} ({len(resp.text)} bytes)")

        ctx.add_resource(
            url=url,
            body=resp.text,
            status=resp.status_code,
            headers=dict(resp.headers),
        )

    ctx.expose(real_fetch, "realFetch")

    ctx.eval("""
        window.__iv8__.page.load({
            html: '<html><body></body></html>',
            baseURL: 'https://localhost'
        });
    """)

    ctx.eval("""
        (function() {
            var _origOpen = XMLHttpRequest.prototype.open;
            var _origSend = XMLHttpRequest.prototype.send;
            var _origSetHeader = XMLHttpRequest.prototype.setRequestHeader;

            XMLHttpRequest.prototype.open = function(method, url) {
                this.__method = method;
                this.__url = url;
                this.__headers = {};
                return _origOpen.apply(this, arguments);
            };

            XMLHttpRequest.prototype.setRequestHeader = function(name, value) {
                this.__headers[name] = value;
                return _origSetHeader.apply(this, arguments);
            };

            XMLHttpRequest.prototype.send = function(body) {
                __iv8__.data.realFetch(
                    this.__method,
                    this.__url,
                    body,
                    JSON.stringify(this.__headers || {})
                );
                return _origSend.apply(this, arguments);
            };
        })()
    """)


# ================================================================
print("=" * 60)
print("1. Async XHR GET + event loop - full event lifecycle")
print("=" * 60)

with iv8.JSContext() as ctx:
    setup_real_network(ctx)

    ctx.eval("""
        var eventLog = [];
        var xhr = new XMLHttpRequest();

        xhr.onreadystatechange = function() {
            eventLog.push('readystatechange: readyState=' + xhr.readyState);
        };
        xhr.addEventListener('loadstart', function() {
            eventLog.push('loadstart');
        });
        xhr.addEventListener('load', function() {
            eventLog.push('load: status=' + xhr.status);
        });
        xhr.addEventListener('loadend', function() {
            eventLog.push('loadend');
        });

        xhr.open('GET', 'https://httpbin.org/get?demo=iv8', true);
        xhr.send(null);
    """)

    ctx.eval("window.__iv8__.eventLoop.drain();")

    log = ctx.eval("eventLog", to_py=True)
    status = ctx.eval("xhr.status")
    body_preview = ctx.eval("xhr.responseText.substring(0, 150)")

    print(f"  Event sequence ({len(log)} events):")
    for entry in log:
        print(f"    {entry}")
    print(f"  Final status: {status}")
    print(f"  Body preview: {body_preview[:80]}...")


# ================================================================
print("\n" + "=" * 60)
print("2. Async XHR POST + event loop - JSON body & headers")
print("=" * 60)

with iv8.JSContext() as ctx:
    setup_real_network(ctx)

    ctx.eval("""
        var postLog = [];
        var postXhr = new XMLHttpRequest();

        postXhr.onreadystatechange = function() {
            postLog.push('readyState=' + postXhr.readyState);
        };
        postXhr.onload = function() {
            postLog.push('onload: status=' + postXhr.status);
        };

        postXhr.open('POST', 'https://httpbin.org/post', true);
        postXhr.setRequestHeader('Content-Type', 'application/json');
        postXhr.send(JSON.stringify({key: 'iv8_bridge_test', ts: Date.now()}));
    """)

    ctx.eval("window.__iv8__.eventLoop.drain();")

    log = ctx.eval("postLog", to_py=True)
    resp_text = ctx.eval("postXhr.responseText")
    result = json.loads(resp_text)

    print(f"  Event sequence: {log}")
    print(f"  Server echoed JSON: {result.get('json')}")
    print(f"  Content-Type header sent: {result.get('headers', {}).get('Content-Type')}")


# ================================================================
print("\n" + "=" * 60)
print("3. Sync XHR GET - classic synchronous request")
print("=" * 60)

with iv8.JSContext() as ctx:
    setup_real_network(ctx)

    result = ctx.eval("""
        (function() {
            var syncLog = [];
            var xhr = new XMLHttpRequest();

            xhr.onreadystatechange = function() {
                syncLog.push('readyState=' + xhr.readyState);
            };
            xhr.onload = function() {
                syncLog.push('onload');
            };

            xhr.open('GET', 'https://httpbin.org/get?mode=sync', false);
            xhr.send(null);

            return {
                events: syncLog,
                status: xhr.status,
                hasResponse: xhr.responseText.length > 0
            };
        })()
    """, to_py=True)

    print(f"  Events: {result['events']}")
    print(f"  Status: {result['status']}")
    print(f"  Has response: {result['hasResponse']}")


print("\nDone.")
