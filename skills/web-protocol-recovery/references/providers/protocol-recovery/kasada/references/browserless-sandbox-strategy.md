# Browserless Sandbox Strategy

Run the `ips.js` collector without a full browser by hosting it in a minimal JS runtime and filling only the environment surfaces it reads. The goal is a sensor the server accepts, minted on a coherent egress.

## Runtime shape

- Host the collector in a lightweight DOM + a script VM context (a DOM-emulation library plus an isolated evaluation context is enough; a full browser is not required).
- Provide the inline bootstrap the interstitial normally sets before the collector: `window.KPSDK = {}`, `KPSDK.now = <monotonic-ms>`, `KPSDK.start = KPSDK.now()`.
- Intercept `fetch`, `XMLHttpRequest`, and `sendBeacon`. Record every call; forward the real collector calls (`/tl`, `/mfc`, the double-UUID paths) to one Python/HTTP session on a single coherent IP/UA/TLS egress, and mirror response headers/cookies back into the runtime before callbacks fire.
- Wrap the global object in a read proxy that logs every property access and every missing property. The missing-property log is the primary worklist for closing environment gaps.

## Environment surfaces to fill

Fill from a real captured profile, not invented values:

- `navigator`: `userAgent`, `platform`, `hardwareConcurrency`, `deviceMemory`, `languages`, and `userAgentData` consistent with the UA and the TLS/egress.
- Canvas 2D: stub drawing calls and return a stable, host-consistent `toDataURL`.
- WebGL/WebGL2: answer `getParameter` for vendor/renderer (`WEBGL_debug_renderer_info`) and extension queries consistently with the claimed GPU.
- Timers and lifecycle: bounded `setInterval`/`setTimeout` heartbeats, `postMessage`/`message` handshake between the parent and the `/fp` context.
- Native integrity: keep intercepted functions reporting native-like `toString`; do not leave obvious wrapper source visible.

## Reading the run

- **`reporting.cdndex.io` beacon fired** (often `POST /error` with a large body): the collector detected an environment or integrity anomaly. This is a fail signal. Diff the missing-property log and native-integrity surfaces against a real browser; fill the specific gap, do not guess broadly.
- **Threw inside a VM handler** (e.g. reading a property of a value your shim returned as null): a concrete environment gap. The thrown location and the access log name the surface to fill.
- **Reached `/tl` with a plausible sensor body and got a non-empty `ct`**: the sandbox is minting; move to same-session business replay.

## Hard constraints

- The runtime bytecode is assembled during bootstrap; you must let the collector build it, not inject a captured integer array.
- Any string cipher, opcode arity, or constant is version-locked to the captured `p.js`/`ips.js`; re-solve per build.
- `x-kpsdk-ct` is bound to IP + UA + TLS. Mint and replay on one coherent egress; a `ct` from a different exit will not carry the business request.
- Do not chase environment gaps indefinitely to force a pass. If the beacon persists after the known surfaces are filled, return a bounded "sandbox detected" blocker rather than a fabricated success.
