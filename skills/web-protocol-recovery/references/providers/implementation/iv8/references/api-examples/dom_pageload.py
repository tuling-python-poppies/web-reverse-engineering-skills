"""
iv8 DOM 操作与页面加载

演示内容：
  - page.load(snapshot) 流式加载（含脚本执行、事件派发、URL 同步）
  - innerHTML 直接赋值方式
  - 带 resources / headers 的完整加载
  - DOM 查询与操作（getElementById、querySelector、createElement 等）
  - page.load 返回值

---

iv8 DOM Operations & Page Loading

Demonstrates:
  - page.load(snapshot) streaming load (script execution, event dispatch, URL sync)
  - Direct innerHTML assignment
  - Full page load with resources / headers
  - DOM queries & manipulation (getElementById, querySelector, createElement, etc.)
  - page.load return value
"""

import iv8


print("=" * 60)
print("1. page.load — 基础用法")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        window.__iv8__.page.load({
            baseURL: 'https://example.com/page',
            html: `<!DOCTYPE html>
                <html>
                <head><title>Hello iv8</title></head>
                <body>
                    <div id="app">Initial Content</div>
                    <ul id="nav">
                        <li class="item">Home</li>
                        <li class="item">About</li>
                        <li class="item">Contact</li>
                    </ul>
                </body>
                </html>`
        });
    """)

    print("document.title:", ctx.eval("document.title"))
    print("document.URL:", ctx.eval("document.URL"))
    print("location.href:", ctx.eval("location.href"))
    print("location.hostname:", ctx.eval("location.hostname"))
    print("#app text:", ctx.eval("document.getElementById('app').textContent"))
    print(".item count:", ctx.eval("document.querySelectorAll('.item').length"))


print("\n" + "=" * 60)
print("2. DOM 操作")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        window.__iv8__.page.load({
            baseURL: 'https://example.com',
            html: '<html><body><div id="root"></div></body></html>'
        });
    """)

    ctx.eval("""
        const root = document.getElementById('root');

        // 创建元素
        const header = document.createElement('h1');
        header.textContent = 'Hello World';
        header.id = 'title';
        root.appendChild(header);

        // 创建列表
        const ul = document.createElement('ul');
        ['Apple', 'Banana', 'Cherry'].forEach(fruit => {
            const li = document.createElement('li');
            li.textContent = fruit;
            li.className = 'fruit';
            ul.appendChild(li);
        });
        root.appendChild(ul);

        // 设置属性
        root.setAttribute('data-loaded', 'true');
        root.style.cssText = 'color: red; font-size: 16px;';
    """)

    print("#title text:", ctx.eval("document.getElementById('title').textContent"))
    print("fruit count:", ctx.eval("document.querySelectorAll('.fruit').length"))
    print("data-loaded:", ctx.eval("document.getElementById('root').getAttribute('data-loaded')"))
    print("children:", ctx.eval("document.getElementById('root').children.length"))


print("\n" + "=" * 60)
print("3. innerHTML 直接赋值（轻量方式）")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        document.documentElement.innerHTML = `
            <head><title>Simple</title></head>
            <body>
                <div id="content">
                    <p>Paragraph 1</p>
                    <p>Paragraph 2</p>
                </div>
            </body>`;
    """)

    print("title:", ctx.eval("document.title"))
    print("p count:", ctx.eval("document.querySelectorAll('p').length"))
    print("注意: innerHTML 不会同步 document.URL:", ctx.eval("document.URL"))


print("\n" + "=" * 60)
print("4. 带 resources 加载（外联脚本自动执行）")
print("=" * 60)

with iv8.JSContext() as ctx:
    result = ctx.eval("""
        window.__iv8__.page.load({
            baseURL: 'https://mysite.com',
            html: `<!DOCTYPE html>
                <html><head>
                    <script src="/lib.js"></script>
                    <script src="/app.js"></script>
                </head><body></body></html>`,
            resources: {
                'https://mysite.com/lib.js': {
                    body: 'window.LIB_VERSION = "1.0";'
                },
                'https://mysite.com/app.js': {
                    body: 'window.APP_INIT = true; window.APP_LIB = window.LIB_VERSION;'
                }
            }
        });
    """, to_py=True)

    print("page 返回值:", result)
    print("LIB_VERSION:", ctx.eval("window.LIB_VERSION"))
    print("APP_INIT:", ctx.eval("window.APP_INIT"))
    print("APP_LIB:", ctx.eval("window.APP_LIB"))


print("\n" + "=" * 60)
print("5. 带 headers 加载")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        window.__iv8__.page.load({
            baseURL: 'https://example.com',
            html: '<html><body>Hello</body></html>',
            headers: {
                'content-type': 'text/html; charset=utf-8',
                'x-custom': 'test-value'
            }
        });
    """)
    print("document.URL:", ctx.eval("document.URL"))


print("\n" + "=" * 60)
print("6. 页面脚本执行 & 生命周期事件")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        window.__iv8__.page.load({
            baseURL: 'https://example.com',
            html: `<!DOCTYPE html>
                <html><head>
                    <script>
                        window.LOG = [];
                        document.addEventListener('DOMContentLoaded', () => {
                            window.LOG.push('DOMContentLoaded');
                        });
                        window.addEventListener('load', () => {
                            window.LOG.push('load');
                        });
                        window.LOG.push('script-executed');
                    </script>
                </head><body>
                    <div id="app">Content</div>
                </body></html>`
        });
    """)

    log = ctx.eval("window.LOG", to_py=True)
    print("生命周期事件顺序:", log)


print("\nDone.")
