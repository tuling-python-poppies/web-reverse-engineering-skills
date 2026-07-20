"""
iv8 DevTools 调试

演示内容：
  - with_devtools(port, watch_apis, enable_console) — 启动 DevTools Inspector
  - vdebugger 语句 — 显式打断点（iv8 禁用了原生 debugger，用 vdebugger 替代）
  - watch_apis — 访问指定 API 时自动触发断点，无需在 JS 里手写 vdebugger
  - eval(devtools=False) — 对指定 eval 跳过调试器直接执行
  - enable_console 参数说明

使用方式：
  1. 运行本脚本，打印 DevTools URL 后程序阻塞等待
  2. 复制 URL 粘贴到 Chrome 地址栏（devtools://devtools/...）
  3. 连接成功后自动继续，执行到断点时 DevTools 会暂停
  4. 在 DevTools 中单步/查看变量，点击 Resume（▶）继续下一个断点
     （本 demo 共触发 5 次暂停：1 次 vdebugger + 4 次 watch_apis）

---

iv8 DevTools Debugging

Demonstrates:
  - with_devtools(port, watch_apis, enable_console) — Start DevTools Inspector
  - vdebugger statement — Explicit JS breakpoints (iv8 disables native debugger; use vdebugger instead)
  - watch_apis — Auto-breakpoint when specified APIs are accessed
  - eval(devtools=False) — Skip debugger for specific eval calls
  - enable_console parameter

Usage:
  1. Run this script; it prints a DevTools URL and waits
  2. Paste the URL into Chrome (devtools://devtools/...)
  3. Once connected, execution resumes; DevTools pauses at each breakpoint
  4. Step/inspect, then click Resume (▶) to continue
     (This demo triggers 5 pauses: 1 vdebugger + 4 watch_apis)

enable_console 说明：
  默认 True — 正常 Inspector console，适合开发调试。
  设为 False — 禁用 Inspector console，V8 注入 vconsole 替代。
  用于防止反爬脚本通过 console.groupEnd.toString() 等探针检测调试环境。
  示例：with_devtools(port=9229, enable_console=False)
"""

import iv8


with iv8.JSContext(mode="debug").with_devtools(
    port=9229,

    # watch_apis: 访问这些 API 时自动触发断点，无需在 JS 里写 vdebugger
    # 在 DevTools 调用栈面板可看到是哪行代码触发了本次访问
    watch_apis=[
        "navigator.userAgent",
        "navigator.webdriver",
        "document.cookie",
        "screen.width",
    ],
) as ctx:

    # ── 初始化代码传 devtools=False，直接执行不等待 DevTools 连接 ──
    ctx.eval("""
        window.__iv8__.page.load({
            baseURL: 'https://example.com',
            html: '<html><body></body></html>'
        });
    """)

    # ── 断点 1：vdebugger 语句（第一次走调试器的 eval，会先等待 DevTools 前端连接）──
    # 注意：iv8 禁用了原生 debugger;（防止反爬 JS 的无限 debugger 循环），用 vdebugger; 替代
    ctx.eval("""
        var x = 10, y = 20;
        debugger;               // ← iv8 中不会暂停（已被禁用）
        vdebugger;              // ← 在 Sources 面板查看 x、y，然后 Resume
        var z = x + y;
    """)

    # ── 断点 2-5：watch_apis 自动触发（每次属性访问都会暂停，共 4 次 Resume）──
    # 暂停时 Sources 面板显示的是动态生成的 "vdebugger; // navigator.userAgent" 等代码，
    # 在 Call Stack 面板中向上查找即可定位到触发访问的用户 JS 代码行。
    ctx.eval("""
        var ua     = navigator.userAgent;    // ← 自动断点
        var wd     = navigator.webdriver;    // ← 自动断点
        var cookie = document.cookie;        // ← 自动断点
        var sw     = screen.width;           // ← 自动断点
    """)

    # ── 结果验证（devtools=False，不触发断点）──
    z  = ctx.eval("z",  devtools=False)
    ua = ctx.eval("ua", devtools=False)
    print(f"z  = {z}")
    print(f"ua = {ua}")

print("\nDone.")
