# iv8 API Examples Index

Use `../api-inventory.md` as the full API guide. This file is only a quick map for choosing which runnable example to read.

## Quick Map

| File | Use When |
| --- | --- |
| `dom_pageload.py` | Need `__iv8__.page.load(snapshot)`, DOM seeding, script execution, lifecycle events, URL sync, external resources, or DOM querying/manipulation. |
| `event_loop.py` | Need timers, promises, `drainMicrotasks()`, `drain()`, `sleep()`, `advance()`, `tick()`, or logical vs system time behavior. |
| `environment_fingerprint.py` | Need to set JS-visible browser/device fields such as `navigator`, `screen`, `location`, or WebGL-like values through `environment={...}`. |
| `full_configuration.py` | Need a broad reference for supported `environment` and `config` paths, defaults, timezone, permissions, time mode, storage, network, or debug configuration. |
| `network_intercept.py` | Need offline resource injection with `ctx.add_resource(...)`, XHR/fetch hitting bundled responses, `netLog`, or `page.load(... resources=...)`. |
| `network_bridge.py` | Need JS to call a Python `requests` bridge through `ctx.expose(...)`; useful for demos or low-frequency synchronous real HTTP from JS. |
| `xhr_real_network.py` | Need to hook `XMLHttpRequest.open/send`, perform the real request in Python, inject the response with `add_resource`, and preserve XHR event lifecycle. |
| `hook_and_wrap.py` | Need `__iv8__.wrapNative(...)` for native-looking function patches or `Function.prototype.toString()` anti-detection checks. |
| `input_simulation.py` | Need trusted `isTrusted === true` mouse/pointer events through `__iv8__.input.dispatchMouseEvent` or `dispatchPointerEvent`. |
| `devtools.py` | Need interactive iv8 DevTools debugging, `mode="debug"`, `with_devtools(...)`, `vdebugger`, `watch_apis`, or `eval(devtools=False)`. |
| `multithreading.py` | Need one `JSContext` per thread, isolate separation, context isolation checks, or context creation/destruction cost examples. |

## Selection Notes

- Start from the closest real site case in `../cases/` first; open these API examples only when syntax or iv8 behavior is unclear.
- For protected-request replay, prefer real HTTP in Python and use iv8 for JS runtime state, signing, cookies, URL mutation, or telemetry.
- Use `network_intercept.py` for offline fixtures and `netLog`; use `xhr_real_network.py` only when the JS-side XHR lifecycle itself matters.
- Use `network_bridge.py` sparingly because bridge calls are synchronous and hold the Python GIL during the Python call.
- Copy only the minimal pattern needed by the current target script.
