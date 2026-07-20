"""
iv8 网络桥接：将 Python requests 传入 V8

演示内容：
  - 将 Python 的 requests 模块作为可调用 JS 函数传入 V8
  - JavaScript 通过 Python 桥接发起真实 HTTP 请求
  - 完整的请求/响应往返（headers, status, body）

⚠ GIL 警告：
  桥接函数（ctx.locals.xxx = python_callable）在执行期间持有 Python GIL。
  当 JS 调用桥接的 Python 函数时：
    1. V8 执行暂停（单线程）
    2. Python GIL 被获取并在整个 Python 调用期间持有
    3. 其他 Python 线程在调用返回前被阻塞
  这意味着通过桥接的 HTTP 请求是完全同步阻塞的。
  高并发场景建议使用 iv8 内置的 add_resource()/netLog，或在 Python 层使用异步模式。

---

iv8 Network Bridge: Pass Python requests to V8

Demonstrates:
  - Pass Python's `requests` module to V8 as callable JS functions
  - JavaScript making real HTTP requests through the Python bridge
  - Complete request/response round-trip (headers, status, body)

⚠ GIL WARNING:
  Bridge functions (ctx.locals.xxx = python_callable) hold the Python GIL
  during execution. When JS calls a bridged Python function:
    1. V8 execution is paused (single-threaded)
    2. Python GIL is acquired and held for the entire Python call
    3. Other Python threads are blocked until the call returns
  This means HTTP requests through the bridge are fully synchronous and
  blocking. For high-concurrency scenarios, prefer iv8's built-in
  add_resource() / netLog approach, or use async patterns at the Python layer.
"""

import json
import requests
import iv8


# ================================================================
print("=" * 60)
print("1. Simple GET - JS calls Python requests.get()")
print("=" * 60)

with iv8.JSContext() as ctx:
    def py_get(url):
        resp = requests.get(str(url), timeout=10)
        return json.dumps({
            "status": resp.status_code,
            "statusText": resp.reason,
            "headers": dict(resp.headers),
            "body": resp.text[:2000],
        })

    ctx.expose(py_get, "pyGet")

    result = ctx.eval("""
        (function() {
            var raw = __iv8__.data.pyGet('https://httpbin.org/get?foo=bar');
            var resp = JSON.parse(raw);
            return {
                ok: resp.status === 200,
                status: resp.status,
                fooParam: JSON.parse(resp.body).args.foo
            };
        })()
    """, to_py=True)

    print(f"  Status: {result['status']}")
    print(f"  OK: {result['ok']}")
    print(f"  foo param echoed: {result['fooParam']}")


# ================================================================
print("\n" + "=" * 60)
print("2. POST with JSON body")
print("=" * 60)

with iv8.JSContext() as ctx:
    def py_post(url, body, content_type):
        headers = {"Content-Type": str(content_type)} if content_type else {}
        resp = requests.post(str(url), data=str(body), headers=headers, timeout=10)
        return json.dumps({
            "status": resp.status_code,
            "body": resp.text[:2000],
        })

    ctx.expose(py_post, "pyPost")

    result = ctx.eval("""
        (function() {
            var payload = JSON.stringify({key: 'hello', ts: Date.now()});
            var raw = __iv8__.data.pyPost('https://httpbin.org/post', payload, 'application/json');
            var resp = JSON.parse(raw);
            var serverSide = JSON.parse(resp.body);
            return {
                status: resp.status,
                echoedData: serverSide.json
            };
        })()
    """, to_py=True)

    print(f"  Status: {result['status']}")
    print(f"  Server echoed: {result['echoedData']}")


# ================================================================
print("\n" + "=" * 60)
print("3. Full HTTP client - reusable from JS")
print("=" * 60)

with iv8.JSContext() as ctx:
    def py_http(method, url, body, headers_json):
        method = str(method).upper()
        url = str(url)
        req_headers = json.loads(str(headers_json)) if headers_json else {}
        req_body = str(body) if body else None

        resp = requests.request(method, url, data=req_body,
                                headers=req_headers, timeout=10)
        return json.dumps({
            "status": resp.status_code,
            "statusText": resp.reason,
            "headers": dict(resp.headers),
            "body": resp.text[:2000],
        })

    ctx.expose(py_http, "pyHttp")

    result = ctx.eval("""
        (function() {
            // GET
            var r1 = JSON.parse(__iv8__.data.pyHttp('GET', 'https://httpbin.org/get', null, '{}'));

            // PUT
            var r2 = JSON.parse(__iv8__.data.pyHttp(
                'PUT',
                'https://httpbin.org/put',
                JSON.stringify({updated: true}),
                JSON.stringify({'Content-Type': 'application/json'})
            ));

            return {
                getStatus: r1.status,
                putStatus: r2.status,
                putEchoed: JSON.parse(r2.body).json
            };
        })()
    """, to_py=True)

    print(f"  GET status: {result['getStatus']}")
    print(f"  PUT status: {result['putStatus']}")
    print(f"  PUT echoed: {result['putEchoed']}")


print("\nDone.")
