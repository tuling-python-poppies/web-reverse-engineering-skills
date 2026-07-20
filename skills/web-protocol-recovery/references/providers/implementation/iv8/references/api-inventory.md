# iv8 API Inventory

## web-protocol-recovery Mandatory API Gate

Read this file in a dedicated iv8 work order before authoring or modifying any iv8 code, including restored cases. Record the installed iv8 version, the exact members the intended case uses, and one offline member probe. The installed runtime remains authoritative when a historical example differs.

This inventory is one Provider-local reference. Opening one linked API example, `script-writing-rules.md`, the case taxonomy, a process document, or a case script requires a later accepted work order under the normal read budget. Historical examples and cases are restored byte-for-byte; their presence is not authorization to run live HTTP, submit a verifier, install dependencies, or retain account state. Python and the web-protocol-recovery work order still own live HTTP and side-effect gates.

The historical API inventory below is preserved verbatim. Where its original case-first order conflicts with the web-protocol-recovery gate above, the web-protocol-recovery gate controls execution order.

This reference is the entry point for iv8 API usage inside this skill. The runnable API examples are bundled in `references/api-examples/`; use `references/api-examples/README.md` as the quick file-selection map.

## How To Use This Reference

1. Start from the closest site case in `references/cases/`.
2. When API syntax is unclear, use the index below or `references/api-examples/README.md` to open the matching file under `references/api-examples/`.
3. Copy only the minimal pattern needed by the current target script.
4. Keep generated target materials in the current workspace `js_reverse_cache/`, not in this skill directory.

## Embedded API Example Files

The following `.py` files are part of this skill:

| File | Use When You Need |
| --- | --- |
| `references/api-examples/dom_pageload.py` | `__iv8__.page.load`, DOM seeding, external resources, lifecycle events |
| `references/api-examples/event_loop.py` | timers, promises, `drain`, `sleep`, `advance`, logical vs system time |
| `references/api-examples/environment_fingerprint.py` | `environment={...}` for navigator, screen, location, WebGL |
| `references/api-examples/full_configuration.py` | complete `environment` and `config` path examples plus defaults |
| `references/api-examples/network_intercept.py` | `ctx.add_resource`, offline XHR/fetch resources, `netLog` |
| `references/api-examples/network_bridge.py` | `ctx.expose` Python HTTP bridge callable from JS |
| `references/api-examples/xhr_real_network.py` | hook XHR, perform real Python requests, inject response with `add_resource` |
| `references/api-examples/hook_and_wrap.py` | `__iv8__.wrapNative` and native-looking function patches |
| `references/api-examples/input_simulation.py` | trusted mouse/pointer events via `__iv8__.input.*` |
| `references/api-examples/devtools.py` | `mode="debug"`, `with_devtools`, `vdebugger`, `watch_apis` |
| `references/api-examples/multithreading.py` | one `JSContext` per thread, isolate separation |

## Core Context APIs

Use `iv8.JSContext(...)` as the execution boundary. Create a fresh context for clean state, and use one context per thread.

```python
import iv8

with iv8.JSContext() as ctx:
    print(ctx.eval("1 + 2"))
```

Common constructor parameters:

```python
iv8.JSContext(
    mode="prod",              # "prod" or "debug"
    environment=None,         # browser/device fingerprint overrides
    config=None,              # engine/runtime behavior config
    ignore_apis=None,         # APIs excluded from debug monitoring
    time_mode="logical",      # "logical" or "system"
    js_api="__iv8__",         # JS-side helper object name
)
```

Close explicitly only when not using a context manager:

```python
ctx = iv8.JSContext()
try:
    ctx.eval("1 + 1")
finally:
    ctx.close()
```

For full examples, read `references/api-examples/multithreading.py` and `references/api-examples/full_configuration.py`.

## JavaScript Evaluation

`ctx.eval(source, name="", line=-1, col=-1, to_py=False, devtools=True)` runs JavaScript.

Use `to_py=True` for nested objects, arrays, `netLog` entries, or telemetry.

```python
data = ctx.eval("({name: 'test', items: [1, 2, 3]})", to_py=True)
print(data["items"])
```

Use `name=` when evaluating a large bundle so stack traces and DevTools source names are meaningful.

```python
ctx.eval(js_code, name="https://example.com/app.js")
```

Use `devtools=False` for bookkeeping expressions that should not stop on DevTools breakpoints.

```python
value = ctx.eval("window.result", devtools=False)
```

## Environment And Config

`environment={...}` sets browser/device values visible to JS. It is configured when the context is created; create a new context for a different profile.

```python
environment = {
    "location": {
        "href": PAGE_URL,
        "origin": "https://example.com",
        "protocol": "https:",
        "host": "example.com",
        "hostname": "example.com",
        "pathname": "/page",
        "search": "",
        "hash": "",
    },
    "navigator": {
        "userAgent": UA,
        "platform": "Win32",
        "language": "zh-CN",
        "languages": ["zh-CN", "zh", "en"],
        "hardwareConcurrency": 8,
        "deviceMemory": 8,
        "webdriver": False,
    },
    "screen": {
        "width": 1920,
        "height": 1080,
        "availWidth": 1920,
        "availHeight": 1040,
        "colorDepth": 24,
    },
}
```

`config={...}` controls engine behavior rather than browser-visible profile.

```python
with iv8.JSContext(
    environment=environment,
    config={
        "timezone": "Asia/Shanghai",
        "permissions": {"geolocation": "granted"},
        "time": {"mode": "logical"},
    },
) as ctx:
    pass
```

List supported defaults when needed:

```python
for path, value in sorted(iv8.JSContext.get_defaults().items()):
    print(f"{path} = {value!r}")
```

Detailed examples:

- `references/api-examples/environment_fingerprint.py`
- `references/api-examples/full_configuration.py`

## Page Loading And DOM

Prefer `__iv8__.page.load(snapshot)` when lifecycle events, script order, `document.URL`, `location`, external scripts, XHR resources, or cookies matter.

```python
ctx.eval("""
    window.__iv8__.page.load({
        baseURL: 'https://example.com/page',
        html: '<html><head><script src="/app.js"></script></head><body></body></html>',
        resources: {
            'https://example.com/app.js': {
                body: 'window.APP_LOADED = true;',
                status: 200,
                headers: {'content-type': 'application/javascript'}
            }
        },
        headers: {'content-type': 'text/html; charset=utf-8'}
    });
""")
```

`document.documentElement.innerHTML = ...` is lighter DOM-only seeding. It does not execute scripts, dispatch lifecycle events, or synchronize URL.

```python
ctx.eval("document.documentElement.innerHTML = " + json.dumps(html))
```

Detailed example: `references/api-examples/dom_pageload.py`.

## Event Loop

`__iv8__.eventLoop.*` controls timers, promises, XHR/fetch callbacks, and animation frames.

```python
ctx.eval("window.__iv8__.eventLoop.drainMicrotasks()")
ctx.eval("window.__iv8__.eventLoop.drain()")
ctx.eval("window.__iv8__.eventLoop.sleep(100)")
ctx.eval("window.__iv8__.eventLoop.advance(250)")
```

Use `time_mode="logical"` for fast virtual time. Use `time_mode="system"` when target code checks real elapsed time or PoW timing.

Detailed example: `references/api-examples/event_loop.py`.

## Network Model

For skill scripts, do real network in Python and use iv8 for page/runtime execution. Inject offline responses with `ctx.add_resource(...)`, or let a JS-side XHR/fetch expose SDK-mutated request data through `netLog`.

```python
ctx.add_resource(
    url="https://api.example.com/config",
    body=json.dumps({"version": "2.0"}),
    status=200,
    headers={"content-type": "application/json"},
)
```

Read JS-side network attempts:

```python
entries = ctx.eval("window.__iv8__.netLog.entries", to_py=True)
for entry in entries:
    print(entry.get("method"), entry.get("url"), entry.get("headers"))
```

Detailed examples:

- `references/api-examples/network_intercept.py`
- `references/api-examples/network_bridge.py`
- `references/api-examples/xhr_real_network.py`

## Python Bridge

Expose Python functions to JS under `__iv8__.data` with `ctx.expose(...)`.

```python
def py_http(method, url, body, headers_json):
    ...

ctx.expose(py_http, "pyHttp")
```

JS side:

```javascript
var raw = __iv8__.data.pyHttp('GET', 'https://example.com', null, '{}');
```

Bridge calls are synchronous and hold the Python GIL during the Python call. Avoid long-running bridge calls inside high-frequency JS hooks.

Detailed examples:

- `references/api-examples/network_bridge.py`
- `references/api-examples/xhr_real_network.py`

## Native Function Disguise

Use `__iv8__.wrapNative(fn, name)` when a patch might be checked through `Function.prototype.toString()`.

```javascript
window.MessageChannel = __iv8__.wrapNative(function() {
    const port1 = { onmessage: null };
    const port2 = { onmessage: null };
    return { port1, port2 };
}, 'MessageChannel');
```

Detailed example: `references/api-examples/hook_and_wrap.py`.

## Trusted Input

Use `__iv8__.input.dispatchMouseEvent` and `dispatchPointerEvent` when target telemetry requires `isTrusted === true` events.

```javascript
__iv8__.input.dispatchPointerEvent({
    type: 'pointerdown',
    target: document.body,
    clientX: 10,
    clientY: 10,
    button: 0,
    buttons: 1,
    pointerId: 1,
    pointerType: 'mouse'
});
```

Detailed example: `references/api-examples/input_simulation.py`.

## DevTools Debugging

Use debug mode only when you need interactive inspection. `vdebugger` is the explicit breakpoint statement; native `debugger` is disabled by iv8.

```python
with iv8.JSContext(mode="debug").with_devtools(
    port=9229,
    watch_apis=["navigator.userAgent", "document.cookie"],
    enable_console=False,
) as ctx:
    ctx.eval("vdebugger;")
```

Detailed example: `references/api-examples/devtools.py`.

## Multithreading

Use one independent context per thread. Do not share a live `JSContext` across worker threads.

Detailed example: `references/api-examples/multithreading.py`.

## Quick Selection Rules

- Need lifecycle, external scripts, cookies, or URL sync: use `page.load` and read `dom_pageload.py`.
- Need async completion: call `drainMicrotasks`, `drain`, `sleep`, or `advance`, and read `event_loop.py`.
- Need environment values: build `environment={...}` and read `environment_fingerprint.py` / `full_configuration.py`.
- Need final rewritten URL/header/cookie from SDK hook: trigger XHR/fetch in iv8, then read `__iv8__.netLog.entries` and `network_intercept.py`.
- Need real HTTP inside XHR lifecycle: use Python bridge + `ctx.add_resource`, and read `xhr_real_network.py`.
- Need anti-detection patch: wrap replacement functions with `__iv8__.wrapNative`, and read `hook_and_wrap.py`.
- Need trusted behavior data: use `__iv8__.input.dispatchMouseEvent` / `dispatchPointerEvent`, and read `input_simulation.py`.
