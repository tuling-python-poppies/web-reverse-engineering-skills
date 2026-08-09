# Browserless Sandbox Strategy

Run the `ips.js` collector without a full browser by hosting it in a minimal JS runtime and filling only the environment surfaces it reads. The goal is a sensor the server accepts, minted on a coherent egress.

## Runtime shape

- Host the collector in a lightweight DOM + a script VM context (a DOM-emulation library plus an isolated evaluation context is enough; a full browser is not required).
- Provide the inline bootstrap the interstitial normally sets before the collector: `window.KPSDK = {}`, `KPSDK.now = <monotonic-ms>`, `KPSDK.start = KPSDK.now()`.
- Intercept `fetch`, `XMLHttpRequest`, and `sendBeacon`. Record every call; forward the real collector calls (`/tl`, `/mfc`, the double-UUID paths) to one Python/HTTP session on a single coherent IP/UA/TLS egress, and mirror response headers/cookies back into the runtime before callbacks fire.
- Wrap the global object in a read proxy that logs every property access and every missing property. The missing-property log is the primary worklist for closing environment gaps.
- The proxy must trap **all introspection paths** (`has`, `ownKeys`, `getOwnPropertyDescriptor`), not only `get`. Emulation-library internals (e.g. happy-dom `_`-prefixed keys, internal constructor names, random-hex session fields) leak through `in` and `Object.keys` if only `get` is masked.
- **`has()` must not lie**: returning `true` for non-existent properties is itself a detection vector. Kasada runs `randomName in window` consistency probes; an overly permissive `has` (e.g. `() => true`) is detectable. Return `true` only for properties that genuinely exist in the target, overrides, or window-identity aliases (`window`/`self`/`globalThis`/`top`/`parent`/`frames`).

## Environment surfaces to fill

Fill from a real captured profile, not invented values:

- `navigator`: `userAgent`, `platform`, `hardwareConcurrency`, `deviceMemory`, `languages`, `userAgentData`, `vendor`, `connection`, `mediaDevices`, `storage`, `serviceWorker`, `getBattery` — all consistent with the UA and TLS/egress.
- Standard Chrome constructors the collector expects but lightweight DOM-libs omit: `ImageData`, `Worker`, `RTCPeerConnection`, `IntersectionObserver`, `ResizeObserver`, `MutationObserver`, `PerformanceObserver`, `BroadcastChannel`, `MessageChannel`, `IdleDetector`, `WebAssembly`. Provide named constructor stubs with `.prototype`.
- Canvas 2D: stub ALL string-keyed method reads as **callable no-ops** (not zero), so the VM can safely `.bind()` any canvas method. Return plausible shapes for `measureText`, `getImageData`, `createLinearGradient`.
- WebGL/WebGL2: answer `getParameter` for vendor/renderer (`WEBGL_debug_renderer_info`) and extension queries consistently with the claimed GPU.
- Timers and lifecycle: bounded `setInterval`/`setTimeout` heartbeats, `postMessage`/`message` handshake between the parent and the `/fp` context.
- `document.currentScript`: happy-dom leaves it null; set it to an actual script element with `.src` pointing at the page URL. The collector reads `.src` for referrer/origin derivation.
- `performance.timing` / `performance.navigation`: Chrome exposes these deprecated APIs; happy-dom omits them. Stub with plausible numeric timestamps.
- Native integrity: keep intercepted functions reporting native-like `toString`; do not leave obvious wrapper source visible.

## Reading the run

- **`reporting.cdndex.io` beacon fired** (`POST /error` with ~33-34KB body): this is a **fixed-size environment-fingerprint report**, NOT a JS-error report. Its body size is approximately constant (~34KB) regardless of whether the VM threw 0, 1, or 2 JS errors. It fires on every init, carrying the full collected fingerprint (canvas hash, webgl params, audio, timing, font metrics). Eliminating JS exceptions does NOT suppress the beacon — suppression requires the fingerprint itself to be plausible (real canvas rendering, webgl readback, audio context output). This is the ceiling of DOM-shell emulation: a happy-dom/jsdom shell returns stub canvas/webgl values that will always be flagged against a known-device database.
- **Threw inside a VM handler** (e.g. reading a property of a value your shim returned as null): a concrete environment gap. The thrown location and the access log name the surface to fill. BUT: Kasada also runs **random-property probes** (`undefined[randomName]`) that generate fresh key names each run — these are deliberate anti-instrumentation checks, not fillable env gaps. If the thrown property name looks random (20+ lowercase chars), it's likely a probe; do not chase it.
- **Reached `/tl` with a plausible sensor body and got a non-empty `ct`**: the sandbox is minting; move to same-session business replay. **However: a minted `ct` does NOT guarantee acceptance.** The ct may be flagged server-side based on fingerprint plausibility signals in the sensor. Business 429 with a valid ct = the fingerprint was flagged, not the ct format.

## Fingerprint plausibility ceiling

A browser-free DOM-shell (happy-dom, jsdom, linkedom) can fill API surfaces and eliminate JS exceptions, but CANNOT produce:
- Real canvas pixel data (actual glyph rendering, sub-pixel AA patterns).
- Real WebGL readback (actual GPU shader output, `readPixels` consistency).
- Real AudioContext output (oscillator→analyzer→FFT fingerprint).
- Real font-metric measurements (glyph bounding boxes from actual font rasterization).

These are the signals Kasada's server-side scoring uses to accept or reject a ct. If the business still returns 429 after minting a ct on clean egress, the fingerprint-plausibility ceiling has been hit.

### Recommended solution: browser fingerprint export + injection

Use Camoufox or CloakBrowser to harvest real rendering values, then inject them as static returns in the VM sandbox:

1. Launch Camoufox/Cloak with a clean target-region residential exit.
2. Navigate to the target page (let the browser actually render).
3. Export fingerprint profile:
   - Camoufox: `export_fingerprint_profile(include_heavy=True)` — returns canvas dataURL, WebGL params/readPixels, AudioContext FFT, screen/navigator values.
   - CloakBrowser: `compare_env()` + evaluate canvas/webgl/audio manually.
4. Inject the exported values into the VM sandbox stubs:
   - `canvas.toDataURL()` → return the real dataURL string.
   - `gl.getParameter(...)` → return the real GPU values.
   - `AudioContext.createOscillator→analyser→getFloatFrequencyData` → return the real FFT array.
   - Font metrics (`measureText`) → return the real bounding box values.
5. Same-version `ips.js` uses fixed drawing instructions → one export covers all sessions until ips.js updates.
6. When ips.js updates (new drawing commands), re-run the export.

This makes the sandbox fingerprint indistinguishable from a real browser on the same device/exit. The cdndex report carries authentic rendering hashes, and the ct should pass server-side scoring.

### Fallback: real headless browser with clean egress

If fingerprint injection is impractical (ips.js varies challenge per session, or the rendering pipeline is too complex to stub):
- Use a real headless browser (Camoufox/Cloak) directly with clean residential egress.
- This sacrifices the speed/scalability of browser-free but guarantees fingerprint authenticity.

## Hard constraints

- The runtime bytecode is assembled during bootstrap; you must let the collector build it, not inject a captured integer array.
- Any string cipher, opcode arity, or constant is version-locked to the captured `p.js`/`ips.js`; re-solve per build.
- `x-kpsdk-ct` is bound to IP + UA + TLS. Mint and replay on one coherent egress; a `ct` from a different exit will not carry the business request.
- Do not chase environment gaps indefinitely to force a pass. If the beacon persists after the known surfaces are filled, the remaining signal is fingerprint plausibility (canvas/webgl/audio/font), not a fillable JS-API gap. Return an honest "fingerprint plausibility ceiling reached" rather than a fabricated success.
- A datacenter proxy that serves the target region may still receive an **empty ips.js** (len=0) — Kasada rate-limits or blocks known datacenter IP ranges at the script-delivery layer. This is an egress-reputation gate independent of fingerprint quality.
- Browser-free reaches `/tl` and mints ct more reliably than a real browser on flagged egress (real browsers often stall at interstitial without even POSTing). The browser-free path is therefore the preferred diagnostic and production path for this provider.
