"""
iv8 输入事件模拟

演示内容：
  - dispatchMouseEvent — 派发可信鼠标事件（isTrusted=true）
  - dispatchPointerEvent — 派发可信指针事件
  - 事件监听器捕获验证

注意：dragMouse / dragPointer 仅 Pro 版支持，Free 版不包含拖拽 API。

---

iv8 Input Event Simulation

Demonstrates:
  - dispatchMouseEvent — Dispatch trusted mouse events (isTrusted=true)
  - dispatchPointerEvent — Dispatch trusted pointer events
  - Event listener capture verification

Note: dragMouse / dragPointer are Pro-only; Free edition does not include drag APIs.
"""

import iv8


print("=" * 60)
print("1. dispatchMouseEvent — 可信鼠标事件")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        window.__iv8__.page.load({
            baseURL: 'https://example.com',
            html: '<html><body><button id="btn">Click me</button></body></html>'
        });
    """)

    ctx.eval("""
        var events = [];
        var btn = document.getElementById('btn');
        btn.addEventListener('click', function(e) {
            events.push({
                type: e.type,
                isTrusted: e.isTrusted,
                clientX: e.clientX,
                clientY: e.clientY,
                button: e.button
            });
        });
        btn.addEventListener('mousedown', function(e) {
            events.push({ type: e.type, isTrusted: e.isTrusted });
        });
        btn.addEventListener('mouseup', function(e) {
            events.push({ type: e.type, isTrusted: e.isTrusted });
        });
    """)

    ctx.eval("""
        window.__iv8__.input.dispatchMouseEvent({
            type: 'mousedown',
            target: document.getElementById('btn'),
            clientX: 50,
            clientY: 25,
            button: 0,
            buttons: 1
        });
        window.__iv8__.input.dispatchMouseEvent({
            type: 'mouseup',
            target: document.getElementById('btn'),
            clientX: 50,
            clientY: 25,
            button: 0,
            buttons: 0
        });
        window.__iv8__.input.dispatchMouseEvent({
            type: 'click',
            target: document.getElementById('btn'),
            clientX: 50,
            clientY: 25,
            button: 0,
            buttons: 0
        });
    """)

    events = ctx.eval("events", to_py=True)
    for e in events:
        print(f"  {e}")


print("\n" + "=" * 60)
print("2. dispatchPointerEvent — 可信指针事件")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        window.__iv8__.page.load({
            baseURL: 'https://example.com',
            html: '<html><body><div id="area" style="width:200px;height:200px;"></div></body></html>'
        });
    """)

    ctx.eval("""
        var pointerEvents = [];
        var area = document.getElementById('area');
        ['pointerdown', 'pointermove', 'pointerup'].forEach(type => {
            area.addEventListener(type, function(e) {
                pointerEvents.push({
                    type: e.type,
                    isTrusted: e.isTrusted,
                    clientX: e.clientX,
                    clientY: e.clientY,
                    pointerId: e.pointerId,
                    pointerType: e.pointerType
                });
            });
        });
    """)

    ctx.eval("""
        var target = document.getElementById('area');
        window.__iv8__.input.dispatchPointerEvent({
            type: 'pointerdown', target: target,
            clientX: 10, clientY: 10, button: 0, buttons: 1,
            pointerId: 1, pointerType: 'mouse'
        });
        window.__iv8__.input.dispatchPointerEvent({
            type: 'pointermove', target: target,
            clientX: 50, clientY: 50, button: 0, buttons: 1,
            pointerId: 1, pointerType: 'mouse'
        });
        window.__iv8__.input.dispatchPointerEvent({
            type: 'pointerup', target: target,
            clientX: 50, clientY: 50, button: 0, buttons: 0,
            pointerId: 1, pointerType: 'mouse'
        });
    """)

    events = ctx.eval("pointerEvents", to_py=True)
    for e in events:
        print(f"  {e}")


print("\n" + "=" * 60)
print("3. isTrusted 验证 / isTrusted verification")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        window.__iv8__.page.load({
            baseURL: 'https://example.com',
            html: '<html><body><div id="test"></div></body></html>'
        });
    """)

    ctx.eval("""
        var trustedCheck = {};
        var el = document.getElementById('test');

        el.addEventListener('click', function(e) {
            trustedCheck.iv8Click = e.isTrusted;
        });

        // iv8 派发的事件
        window.__iv8__.input.dispatchMouseEvent({
            type: 'click', target: el, clientX: 0, clientY: 0,
            button: 0, buttons: 0
        });

        // JS 手动创建的事件
        el.addEventListener('mousedown', function(e) {
            trustedCheck.jsEvent = e.isTrusted;
        });
        el.dispatchEvent(new MouseEvent('mousedown'));
    """)

    check = ctx.eval("trustedCheck", to_py=True)
    print(f"iv8 派发的 click.isTrusted: {check.get('iv8Click')}")
    print(f"JS dispatchEvent 的 mousedown.isTrusted: {check.get('jsEvent')}")


print("\nDone.")
