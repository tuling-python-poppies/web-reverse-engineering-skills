"""
iv8 浏览器环境配置与指纹伪装

演示内容：
  - environment 参数配置 navigator、screen、location、webgl（仅创建 JSContext 时可设置）
  - 指纹属性在 JS 侧的表现

---

iv8 Browser Environment & Fingerprint Spoofing

Demonstrates:
  - Configure navigator, screen, location, webgl via environment (set at JSContext creation only)
  - How fingerprint properties appear on the JS side
"""

import iv8


print("=" * 60)
print("1. 完整浏览器指纹配置")
print("=" * 60)

with iv8.JSContext(environment={
    "navigator": {
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "platform": "Win32",
        "language": "en-US",
        "languages": ["en-US", "en"],
        "hardwareConcurrency": 16,
        "deviceMemory": 8,
        "maxTouchPoints": 0,
    },
    "screen": {
        "width": 1920,
        "height": 1080,
        "availWidth": 1920,
        "availHeight": 1040,
        "colorDepth": 24,
        "pixelDepth": 24,
    },
    "location": {
        "href": "https://example.com/dashboard",
    },
    "webgl": {
        "vendor": "Google Inc. (NVIDIA)",
        "renderer": "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650)",
    },
}) as ctx:
    print("navigator.userAgent:", ctx.eval("navigator.userAgent"))
    print("navigator.platform:", ctx.eval("navigator.platform"))
    print("navigator.language:", ctx.eval("navigator.language"))
    print("navigator.languages:", ctx.eval("navigator.languages", to_py=True))
    print("navigator.hardwareConcurrency:", ctx.eval("navigator.hardwareConcurrency"))
    print("navigator.deviceMemory:", ctx.eval("navigator.deviceMemory"))
    print()
    print("screen.width:", ctx.eval("screen.width"))
    print("screen.height:", ctx.eval("screen.height"))
    print("screen.colorDepth:", ctx.eval("screen.colorDepth"))
    print()
    print("location.href:", ctx.eval("location.href"))
    print("location.hostname:", ctx.eval("location.hostname"))


print("\n" + "=" * 60)
print("2. 构造时配置：不同 language（环境在创建后不可变，需新建 Context）")
print("=" * 60)

with iv8.JSContext(environment={
    "navigator": {
        "userAgent": "Mozilla/5.0 Chrome/120.0.0.0",
        "language": "zh-CN",
        "hardwareConcurrency": 8,
    }
}) as ctx:
    print("zh-CN 配置:")
    print("  language:", ctx.eval("navigator.language"))
    print("  UA:", ctx.eval("navigator.userAgent"))
    print("  cores:", ctx.eval("navigator.hardwareConcurrency"))

with iv8.JSContext(environment={
    "navigator": {
        "userAgent": "Mozilla/5.0 Chrome/120.0.0.0",
        "language": "en-US",
        "hardwareConcurrency": 8,
    }
}) as ctx:
    print("\nen-US 配置（新 Context）:")
    print("  language:", ctx.eval("navigator.language"))
    print("  UA:", ctx.eval("navigator.userAgent"))
    print("  cores:", ctx.eval("navigator.hardwareConcurrency"))


print("\n" + "=" * 60)
print("3. navigator.webdriver 检测")
print("=" * 60)

with iv8.JSContext() as ctx:
    print("navigator.webdriver:", ctx.eval("navigator.webdriver"))  # false


print("\n" + "=" * 60)
print("4. 内置浏览器对象验证")
print("=" * 60)

with iv8.JSContext() as ctx:
    checks = ctx.eval("""
        [
            'typeof window: ' + typeof window,
            'typeof document: ' + typeof document,
            'typeof navigator: ' + typeof navigator,
            'typeof screen: ' + typeof screen,
            'typeof localStorage: ' + typeof localStorage,
            'typeof sessionStorage: ' + typeof sessionStorage,
            'typeof crypto: ' + typeof crypto,
            'typeof performance: ' + typeof performance,
            'typeof history: ' + typeof history,
            'typeof location: ' + typeof location,
        ]
    """, to_py=True)
    for check in checks:
        print(f"  {check}")


print("\nDone.")
