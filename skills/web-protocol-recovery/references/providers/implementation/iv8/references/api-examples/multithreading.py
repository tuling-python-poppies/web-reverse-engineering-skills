"""
iv8 多线程与 Isolate 隔离

演示内容：
  - 多线程并发执行（每个线程独立 JSContext + Isolate）
  - 同线程多上下文隔离
  - 线程间不互相干扰验证
  - Context 创建/销毁开销测量

---

iv8 Multithreading & Isolate Isolation

Demonstrates:
  - Concurrent execution across threads (independent JSContext + Isolate per thread)
  - Multiple context isolation within the same thread
  - Verification that threads do not interfere with each other
  - Context creation/destruction overhead measurement
"""

import threading
import time
import iv8


print("=" * 60)
print("1. 多线程并发执行")
print("=" * 60)

results = {}
lock = threading.Lock()


def run_js(thread_id):
    with iv8.JSContext(environment={
        "navigator": {"userAgent": f"ThreadBot/{thread_id}"}
    }) as ctx:
        ua = ctx.eval("navigator.userAgent")
        val = ctx.eval(f"{thread_id} * {thread_id}")
        with lock:
            results[thread_id] = {"ua": ua, "val": val}


threads = []
for i in range(8):
    t = threading.Thread(target=run_js, args=(i,))
    threads.append(t)

t0 = time.perf_counter()
for t in threads:
    t.start()
for t in threads:
    t.join()
elapsed = time.perf_counter() - t0

print(f"8 个线程并发完成，耗时: {elapsed:.3f}s")
for tid in sorted(results):
    r = results[tid]
    print(f"  Thread {tid}: UA={r['ua']}, {tid}²={r['val']}")


print("\n" + "=" * 60)
print("2. 同线程多上下文隔离")
print("=" * 60)

ctx1 = iv8.JSContext(environment={"navigator": {"userAgent": "UA-1"}})
ctx2 = iv8.JSContext(environment={"navigator": {"userAgent": "UA-2"}})

ctx1.eval("var secret = 'ctx1_only';")
ctx2.eval("var secret = 'ctx2_only';")

print("ctx1 UA:", ctx1.eval("navigator.userAgent"))
print("ctx2 UA:", ctx2.eval("navigator.userAgent"))
print("ctx1 secret:", ctx1.eval("secret"))
print("ctx2 secret:", ctx2.eval("secret"))

ua1 = ctx1.eval("navigator.userAgent")
ua2 = ctx2.eval("navigator.userAgent")
assert ua1 != ua2, "上下文应该隔离"
print("\n验证: 两个上下文完全隔离 ✓")

ctx2.close()
ctx1.close()


print("\n" + "=" * 60)
print("3. 多线程 + 复杂 JS 执行")
print("=" * 60)

errors = []


def heavy_js(thread_id):
    try:
        with iv8.JSContext() as ctx:
            ctx.eval(f"var tid = {thread_id};")
            ctx.eval("""
                // 计算密集型任务
                function compute(n) {
                    let sum = 0;
                    for (let i = 0; i < n; i++) {
                        sum += Math.sin(i) * Math.cos(i);
                    }
                    return sum;
                }

                var result = compute(10000);
                var arr = Array.from({length: 100}, (_, i) => i * tid);
            """)
            result = ctx.eval("result")
            arr_len = ctx.eval("arr.length")
            with lock:
                results[f"heavy_{thread_id}"] = {
                    "result": round(result, 4),
                    "arr_len": arr_len
                }
    except Exception as e:
        with lock:
            errors.append((thread_id, str(e)))


threads = []
for i in range(4):
    t = threading.Thread(target=heavy_js, args=(i,))
    threads.append(t)

t0 = time.perf_counter()
for t in threads:
    t.start()
for t in threads:
    t.join()
elapsed = time.perf_counter() - t0

print(f"4 线程计算密集任务完成，耗时: {elapsed:.3f}s")
for tid in range(4):
    key = f"heavy_{tid}"
    if key in results:
        r = results[key]
        print(f"  Thread {tid}: result={r['result']}, arr_len={r['arr_len']}")

if errors:
    print(f"\n错误: {errors}")
else:
    print("\n所有线程无错误 ✓")


print("\n" + "=" * 60)
print("4. Context 创建/销毁性能")
print("=" * 60)

N = 100
t0 = time.perf_counter()
for i in range(N):
    with iv8.JSContext() as ctx:
        ctx.eval("1 + 1")
elapsed = time.perf_counter() - t0

print(f"{N} 次 JSContext 创建/eval/销毁: {elapsed:.3f}s")
print(f"单次平均: {elapsed / N * 1000:.1f}ms")


print("\nDone.")
