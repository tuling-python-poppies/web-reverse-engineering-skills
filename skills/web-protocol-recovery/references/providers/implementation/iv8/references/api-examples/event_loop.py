"""
iv8 事件循环与定时器控制

演示内容：
  - 宏任务（setTimeout、setInterval）与微任务（Promise、queueMicrotask）调度模型
  - advance(total, step?) — 按帧推进虚拟时间
  - sleep(ms) — 按时间线推进
  - tick(ms?) — 单轮事件循环
  - drain(max?) — 排空已到期任务
  - drainMicrotasks() — 仅排空微任务
  - drainTimers() — 仅处理到期定时器
  - 逻辑时间模式（logical）vs 系统时间模式（system）

---

iv8 Event Loop & Timer Control

Demonstrates:
  - Macrotask (setTimeout, setInterval) and microtask (Promise, queueMicrotask) scheduling
  - advance(total, step?) — Advance virtual time frame by frame
  - sleep(ms) — Advance along timeline
  - tick(ms?) — Single event loop tick
  - drain(max?) — Drain all due tasks
  - drainMicrotasks() — Drain microtasks only
  - drainTimers() — Process due timers only
  - Logical time mode vs system time mode
"""

import iv8


print("=" * 60)
print("1. 宏任务 vs 微任务执行顺序")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        var log = [];
        setTimeout(() => log.push('timeout-0'), 0);
        Promise.resolve().then(() => log.push('promise-1'));
        queueMicrotask(() => log.push('microtask-1'));
        log.push('sync');
    """)

    print("执行同步代码后:", ctx.eval("log", to_py=True))

    ctx.eval("window.__iv8__.eventLoop.drainMicrotasks()")
    print("drainMicrotasks后:", ctx.eval("log", to_py=True))

    ctx.eval("window.__iv8__.eventLoop.drain()")
    print("drain后:", ctx.eval("log", to_py=True))
    # 顺序: sync → promise-1 → microtask-1 → timeout-0


print("\n" + "=" * 60)
print("2. advance — 按帧推进虚拟时间")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        var log = [];
        setTimeout(() => log.push('100ms'), 100);
        setTimeout(() => log.push('200ms'), 200);
        setTimeout(() => log.push('500ms'), 500);
        Promise.resolve().then(() => log.push('micro'));
    """)

    ctx.eval("window.__iv8__.eventLoop.advance(250)")
    print("advance(250)后:", ctx.eval("log", to_py=True))
    # micro 先执行，然后 100ms 和 200ms 的定时器触发，500ms 未到期

    ctx.eval("window.__iv8__.eventLoop.advance(300)")
    print("再 advance(300)后:", ctx.eval("log", to_py=True))
    # 500ms 定时器触发


print("\n" + "=" * 60)
print("3. sleep — 按时间线推进")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        var log = [];
        setTimeout(() => log.push('50ms'), 50);
        setTimeout(() => log.push('150ms'), 150);
    """)

    ctx.eval("window.__iv8__.eventLoop.sleep(100)")
    print("sleep(100)后:", ctx.eval("log", to_py=True))

    ctx.eval("window.__iv8__.eventLoop.sleep(100)")
    print("再sleep(100)后:", ctx.eval("log", to_py=True))


print("\n" + "=" * 60)
print("4. tick — 逐步调试（单轮事件循环）")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        var log = [];
        setTimeout(() => log.push('A'), 0);
        setTimeout(() => {
            log.push('B');
            Promise.resolve().then(() => log.push('B-micro'));
        }, 0);
        setTimeout(() => log.push('C'), 0);
    """)

    ctx.eval("window.__iv8__.eventLoop.tick()")
    print("tick 1:", ctx.eval("log", to_py=True))

    ctx.eval("window.__iv8__.eventLoop.tick()")
    print("tick 2:", ctx.eval("log", to_py=True))

    ctx.eval("window.__iv8__.eventLoop.tick()")
    print("tick 3:", ctx.eval("log", to_py=True))


print("\n" + "=" * 60)
print("5. drain — 排空所有已到期任务")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        var log = [];
        setTimeout(() => log.push('a'), 0);
        setTimeout(() => log.push('b'), 0);
        setTimeout(() => log.push('c'), 0);
        Promise.resolve().then(() => log.push('micro'));
    """)

    ctx.eval("window.__iv8__.eventLoop.drain()")
    print("drain后:", ctx.eval("log", to_py=True))


print("\n" + "=" * 60)
print("6. drainTimers — 仅处理已到期定时器")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        var log = [];
        setTimeout(() => log.push('timer-0'), 0);
        setTimeout(() => log.push('timer-100'), 100);
        Promise.resolve().then(() => log.push('micro'));
    """)

    ctx.eval("window.__iv8__.eventLoop.drainTimers()")
    print("drainTimers后:", ctx.eval("log", to_py=True))
    # timer-0（已到期）被执行，执行过程中产生的微任务（micro）也被处理，timer-100 未到期


print("\n" + "=" * 60)
print("7. setInterval 示例")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        var counter = 0;
        var id = setInterval(() => { counter++; }, 100);
    """)

    ctx.eval("window.__iv8__.eventLoop.advance(350)")
    print("advance(350)后 counter:", ctx.eval("counter"))

    ctx.eval("clearInterval(id)")
    ctx.eval("window.__iv8__.eventLoop.advance(200)")
    print("clearInterval后再 advance(200) counter:", ctx.eval("counter"))


print("\n" + "=" * 60)
print("8. requestAnimationFrame")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        var frames = 0;
        function animate() {
            frames++;
            if (frames < 5) requestAnimationFrame(animate);
        }
        requestAnimationFrame(animate);
    """)

    ctx.eval("window.__iv8__.eventLoop.advance(200)")
    print("5帧动画后 frames:", ctx.eval("frames"))


print("\n" + "=" * 60)
print("9. async/await 与事件循环配合")
print("=" * 60)

with iv8.JSContext() as ctx:
    ctx.eval("""
        var result = null;

        async function process() {
            const step1 = await Promise.resolve('step1');
            const step2 = await new Promise(resolve => {
                setTimeout(() => resolve('step2'), 100);
            });
            result = step1 + '+' + step2;
        }

        process();
    """)

    ctx.eval("window.__iv8__.eventLoop.drainMicrotasks()")
    print("drainMicrotasks后:", ctx.eval("result"))

    ctx.eval("window.__iv8__.eventLoop.advance(150)")
    print("advance(150)后:", ctx.eval("result"))


print("\n" + "=" * 60)
print("10. 逻辑时间模式 vs 系统时间模式")
print("=" * 60)

# logical 模式：虚拟时间，sleep(5000) 瞬间完成
with iv8.JSContext(time_mode="logical") as ctx:
    ctx.eval("var t0 = Date.now();")
    ctx.eval("window.__iv8__.eventLoop.sleep(5000)")
    elapsed = ctx.eval("Date.now() - t0")
    print(f"logical 模式: sleep(5000) 后 Date.now() 增量 = {elapsed}ms")

# system 模式：系统时间锚定
with iv8.JSContext(time_mode="system") as ctx:
    ctx.eval("var t0 = Date.now();")
    elapsed = ctx.eval("Date.now() - t0")
    print(f"system 模式: Date.now() 增量反映真实耗时 = {elapsed}ms")


print("\nDone.")
