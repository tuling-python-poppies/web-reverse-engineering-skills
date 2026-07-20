"""
iv8 函数伪装

演示内容：
  - wrapNative(fn, name) — 将 JS 函数伪装为原生函数
  - Function.prototype.toString 检测绕过

---

iv8 Function Native Disguise

Demonstrates:
  - wrapNative(fn, name) — Disguise a JS function as a native function
  - Function.prototype.toString detection bypass
"""

import iv8


print("=" * 60)
print("1. wrapNative — 将函数伪装为原生函数")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        function myFunc() { return 42; }
    """)
    print("伪装前:")
    print("  toString:", ctx.eval("myFunc.toString()"))

    ctx.eval("""
        myFunc = window.__iv8__.wrapNative(myFunc, 'myFunc');
    """)
    print("\n伪装后:")
    print("  toString:", ctx.eval("myFunc.toString()"))
    print("  调用结果:", ctx.eval("myFunc()"))


print("\n" + "=" * 60)
print("2. wrapNative — toString 检测绕过")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        var customFetch = function(url) { return 'intercepted: ' + url; };
        customFetch = window.__iv8__.wrapNative(customFetch, 'fetch');
    """)

    print("toString:", ctx.eval("customFetch.toString()"))
    native_check = ctx.eval("customFetch.toString().includes('[native code]')")
    print(f"包含 [native code]: {native_check}")
    print("调用结果:", ctx.eval("customFetch('https://example.com')"))


print("\n" + "=" * 60)
print("3. wrapNative — 替换内置函数")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        var origStringify = JSON.stringify;
        var callCount = 0;
        JSON.stringify = window.__iv8__.wrapNative(function() {
            callCount++;
            return origStringify.apply(JSON, arguments);
        }, 'stringify');
    """)

    print("JSON.stringify.toString():", ctx.eval("JSON.stringify.toString()"))
    result = ctx.eval("JSON.stringify({a: 1})")
    print(f"JSON.stringify({{a:1}}): {result}")
    print(f"调用计数: {ctx.eval('callCount')}")


print("\n" + "=" * 60)
print("4. 综合: 反检测验证")
print("=" * 60)

with iv8.JSContext() as ctx:
    checks = ctx.eval("""
        (function() {
            var results = [];

            // 1. navigator.webdriver
            results.push('webdriver: ' + navigator.webdriver);

            // 2. eval 原生检测
            results.push('eval is native: ' + (eval.toString().indexOf('[native code]') !== -1));

            // 3. 自定义函数伪装后的检测
            var fake = window.__iv8__.wrapNative(function(){}, 'alert');
            results.push('wrapped alert is native: ' + (fake.toString().indexOf('[native code]') !== -1));

            // 4. __iv8__ 不可检测
            results.push('typeof __iv8__: ' + typeof window.__iv8__);

            return results;
        })()
    """, to_py=True)

    print("反检测验证结果:")
    for check in checks:
        print(f"  {check}")


print("\nDone.")
