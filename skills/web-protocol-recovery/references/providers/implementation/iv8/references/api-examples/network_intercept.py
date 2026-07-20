"""
iv8 网络请求拦截与监控

演示内容：
  - add_resource() 注入离线 HTTP 响应
  - XMLHttpRequest / fetch 从 resource bundle 获取响应
  - netLog 网络日志监控
  - page.load + resources 预置外联资源

---

iv8 Network Interception & Monitoring

Demonstrates:
  - Inject offline HTTP responses via add_resource()
  - XMLHttpRequest / fetch reads from the resource bundle
  - Network log monitoring via netLog
  - Preload external resources with page.load + resources
"""

import json
import iv8


print("=" * 60)
print("1. add_resource + XHR — 注入资源后 XHR 可命中")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        window.__iv8__.page.load({
            html: '<html><body></body></html>',
            baseURL: 'https://example.com'
        });
    """)

    ctx.add_resource(
        url="https://api.example.com/config",
        body=json.dumps({"version": "2.0", "features": ["a", "b"]}),
        status=200,
        headers={"content-type": "application/json"},
    )

    ctx.eval("""
        var xhr = new XMLHttpRequest();
        xhr.open('GET', 'https://api.example.com/config', false);
        xhr.send();
    """)

    print("status:", ctx.eval("xhr.status"))
    resp = ctx.eval("xhr.responseText")
    print("responseText:", resp)
    parsed = json.loads(resp)
    assert parsed["version"] == "2.0", "XHR should return injected body"
    print("PASS: XHR hit resource bundle")


print("\n" + "=" * 60)
print("2. add_resource + fetch — 注入资源后 fetch 可命中")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        window.__iv8__.page.load({
            html: '<html><body></body></html>',
            baseURL: 'https://example.com'
        });
    """)

    ctx.add_resource(
        url="https://api.example.com/data",
        body=json.dumps({"key": "value123"}),
        status=200,
        headers={"content-type": "application/json"},
    )

    ctx.eval("""
        var fetchResult = null;
        var fetchError = null;
        fetch('https://api.example.com/data')
            .then(r => r.text())
            .then(t => { fetchResult = t; })
            .catch(e => { fetchError = e.message; });
    """)
    ctx.eval("window.__iv8__.eventLoop.drain();")

    err = ctx.eval("fetchError")
    result = ctx.eval("fetchResult")
    print("fetchError:", err)
    print("fetchResult:", result)
    if result:
        parsed = json.loads(result)
        assert parsed["key"] == "value123", "fetch should return injected body"
        print("PASS: fetch hit resource bundle")
    else:
        print("WARN: fetch did not resolve (may need recompile)")


print("\n" + "=" * 60)
print("3. netLog — 网络日志监控")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        window.__iv8__.page.load({
            html: '<html><body></body></html>',
            baseURL: 'https://example.com'
        });
    """)

    initial_count = ctx.eval("window.__iv8__.netLog.entries.length")
    print(f"初始 netLog 条目数: {initial_count}")

    ctx.eval("""
        var xhr = new XMLHttpRequest();
        xhr.open('GET', 'https://example.com/api/data', false);
        xhr.send();
    """)

    new_count = ctx.eval("window.__iv8__.netLog.entries.length")
    print(f"XHR 请求后 netLog 条目数: {new_count}")

    entries = ctx.eval("window.__iv8__.netLog.entries", to_py=True)
    for i, entry in enumerate(entries):
        print(f"\n  Entry {i}:")
        if isinstance(entry, dict):
            for k, v in entry.items():
                val = str(v)[:80]
                print(f"    {k}: {val}")


print("\n" + "=" * 60)
print("4. page.load + resources（外联脚本自动加载）")
print("=" * 60)

with iv8.JSContext() as ctx:
    result = ctx.eval("""
        window.__iv8__.page.load({
            baseURL: 'https://app.example.com',
            html: `<!DOCTYPE html>
                <html><head>
                    <script src="/vendor.js"><\/script>
                    <script src="/main.js"><\/script>
                    <script src="/missing.js"><\/script>
                </head><body></body></html>`,
            resources: {
                'https://app.example.com/vendor.js': {
                    body: 'window.VENDOR = "loaded";'
                },
                'https://app.example.com/main.js': {
                    body: 'window.MAIN = "loaded"; window.HAS_VENDOR = !!window.VENDOR;'
                }
            }
        });
    """, to_py=True)

    print("page 返回值:")
    if isinstance(result, dict):
        for k, v in result.items():
            print(f"  {k}: {v}")

    print(f"\nVENDOR: {ctx.eval('window.VENDOR')}")
    print(f"MAIN: {ctx.eval('window.MAIN')}")
    print(f"HAS_VENDOR: {ctx.eval('window.HAS_VENDOR')}")


print("\n" + "=" * 60)
print("5. 多次 add_resource + XHR 请求")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        window.__iv8__.page.load({
            html: '<html><body></body></html>',
            baseURL: 'https://example.com'
        });
    """)

    ctx.add_resource(
        url="https://example.com/api/users",
        body=json.dumps([{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]),
        status=200,
        headers={"content-type": "application/json"},
    )

    ctx.add_resource(
        url="https://example.com/api/settings",
        body=json.dumps({"theme": "dark", "lang": "zh"}),
        status=200,
        headers={"content-type": "application/json"},
    )

    ctx.eval("""
        var xhr1 = new XMLHttpRequest();
        xhr1.open('GET', 'https://example.com/api/users', false);
        xhr1.send();

        var xhr2 = new XMLHttpRequest();
        xhr2.open('GET', 'https://example.com/api/settings', false);
        xhr2.send();
    """)

    print("users status:", ctx.eval("xhr1.status"))
    users = ctx.eval("xhr1.responseText")
    print("users response:", users)
    parsed_users = json.loads(users)
    assert parsed_users[0]["name"] == "Alice"

    print("settings status:", ctx.eval("xhr2.status"))
    settings = ctx.eval("xhr2.responseText")
    print("settings response:", settings)
    parsed_settings = json.loads(settings)
    assert parsed_settings["theme"] == "dark"

    print("PASS: multiple XHR requests hit correct resources")


print("\nDone.")
