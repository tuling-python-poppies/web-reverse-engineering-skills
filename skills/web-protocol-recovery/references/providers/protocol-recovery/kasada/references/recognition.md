# Recognition

## Marker set

Confirm the family from concrete surfaces, not a vendor guess:

| Surface | Kasada marker |
|---|---|
| Response cookies | `KP_UIDz`, `KP_UIDz-ssn` |
| Response headers | `x-kpsdk-ct`, `x-kpsdk-cr`, `x-kpsdk-st`, `x-kpsdk-r`, `x-kpsdk-h`, `x-kpsdk-fc` |
| Inline bootstrap | `window.KPSDK={}`, `KPSDK.now`, `KPSDK.start`, `KPSDK.configure(...)` |
| Script path | double-UUID prefix `/<uuid>/<uuid>/p.js` or `/.../ips.js` (the leading UUID is often shared across customers) |
| Submission | `POST /tl` with a binary sensor body; `/mfc` for `x-kpsdk-h` |
| Telemetry | beacon to `reporting.cdndex.io` (e.g. `/error`) |
| Interstitial | `429` carrier page (~sub-1KB) that regenerates a token per request |

Require at least two independent surfaces before selecting the Provider.

## p.js vs ips.js triage

- `p.js` is the top-level bootstrap and business-request wrapper: it sets `window.KPSDK`, exposes `KPSDK.now`/`KPSDK.start`, calls `KPSDK.configure(...)` to name the protected domains/paths, and creates the `/fp` context.
- `ips.js` is the environment collector and sensor generator that runs inside `/fp`. It reads the environment, builds the binary sensor, and submits `/tl`.
- The `x-kpsdk-ct` credential comes from `ips.js` at `/tl`. Do not attribute it to `p.js`.

## Environment surfaces the collector reads

The collector cross-checks many surfaces; a gap in any is a likely anomaly-beacon trigger:

- `window` topology and capabilities (`self`/`top`/`parent`/`frameElement`, sizes, `visualViewport`, `isSecureContext`, timers, `fetch`, `postMessage`).
- `document` state and DOM prototype descriptors (`cookie`, `readyState`, `visibilityState`, create/query/listener APIs).
- `navigator` (`userAgent`, `platform`, `hardwareConcurrency`, `deviceMemory`, `languages`, `webdriver`, `userAgentData`, `plugins`, `permissions`).
- `screen` / `location` / `history` consistency across prototypes.
- Canvas 2D, WebGL/WebGL2 (`WEBGL_debug_renderer_info`, `getParameter`, extensions), Audio, font widths.
- JavaScript native integrity (`toString` of natives, descriptor shapes, getter/setter behavior, correct Web IDL, realm identity).
- Async timing: promise/microtask order, timer delays, page lifecycle.

## Not-Kasada / do-not-select

- A generic `403`/`429`, an H2 reset, or one cookie name with no `x-kpsdk-*`/`KPSDK`/double-UUID/`/tl` corroboration.
- An exception in a sandbox run is not automatically a missing environment: Kasada also runs deliberate negative tests expecting native errors. Separate "collector took a normal path and failed on a real gap" from "collector forced an illegal call and the runtime correctly threw".
