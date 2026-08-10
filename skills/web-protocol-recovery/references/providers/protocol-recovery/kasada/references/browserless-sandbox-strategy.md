# Browserless Sandbox Strategy

Run the `ips.js` collector without a full browser using EdgeSandbox — a Node 24 Edge 150 compatibility sandbox with full DOM/Canvas/WebGL/Audio state machines and 1232 Window properties.

## EdgeSandbox Runtime

EdgeSandbox provides an exact Edge 150 browser environment surface in an isolated Node.js process:

- **1232 Window properties, 11449 browser functions**: exact Edge 150 match with correct descriptor order.
- **Canvas 2D state machine**: `getComputedStyle`, `measureText`, `getImageData`, `toDataURL` driven by configurable fingerprint.
- **WebGL/WebGL2**: `getParameter` for vendor/renderer (`WEBGL_debug_renderer_info`), extensions, and readback consistency.
- **AudioContext**: oscillator→analyzer→FFT state machine producing fingerprint-consistent output.
- **All Chrome constructors**: `ImageData`, `Worker`, `RTCPeerConnection`, `IntersectionObserver`, `ResizeObserver`, `MutationObserver`, `PerformanceObserver`, `BroadcastChannel`, `MessageChannel`, `WebAssembly` — all present with correct `.prototype` chains and Web IDL brands.
- **Offline network replay**: configure `/tl`, `/mfc`, double-UUID responses via `replay` array.
- **Network capture**: `sandbox.networkRequests()` intercepts all fetch/XHR automatically — captures the `/tl` POST body.
- **Independent iframe Realms**: the `/fp` context runs in a real child Realm with isolated `Array`, `JSON`, and DOM constructors.
- **`document.currentScript`**: correctly set during script execution.
- **`performance.timing` / `performance.navigation`**: present (Chrome exposes these deprecated APIs).
- **Native toString integrity**: intercepted functions report native-like `toString()`.

Python automatically locates Node 24 via `NVM_HOME` environment variable — no manual `nvm use` needed.

## Architecture

```javascript
import { EdgeSandbox } from 'edge-sandbox';
import { readFileSync } from 'node:fs';

// Load real fingerprint from Camoufox export
const fp = JSON.parse(readFileSync('./fingerprint.json', 'utf-8'));

const sandbox = await EdgeSandbox.create({
  page: {
    url: 'https://target.example/',
    html: interstitialHtml, // or minimal HTML
  },
  fingerprint: {
    locale: fp.locale || 'en-US',
    timezone: fp.timezone || 'America/New_York',
    screen: fp.screen || { width: 1920, height: 1080, availWidth: 1920, availHeight: 1040, colorDepth: 24, pixelDepth: 24 },
  },
  replay: [{
    method: 'GET',
    url: 'https://target.example/<uuid>/<uuid>/ips.js',
    status: 200,
    headers: { 'Content-Type': 'application/javascript' },
    body: ipsJsSource,
  }],
  networkCapture: { enabled: true, maxEntries: 100, maxBodyBytes: 64 * 1024 },
  limits: { timeoutMs: 20_000, maxHeapBytes: 512 * 1024 * 1024, maxSourceBytes: 2 * 1024 * 1024 },
});

try {
  // Set KPSDK bootstrap (what the interstitial normally provides)
  await sandbox.evaluate(`
    window.KPSDK = {};
    KPSDK.now = () => performance.now();
    KPSDK.start = KPSDK.now();
  `);

  // Execute ips.js
  await sandbox.evaluate(ipsJsSource);

  // Keep event loop alive for /tl POST (async via setTimeout)
  await sandbox.evaluate('new Promise(r => setTimeout(r, 10000))');

  // Capture /tl POST
  const requests = await sandbox.networkRequests();
  const tlPost = requests.find(r => r.url.includes('/tl') && r.method === 'POST');

  if (tlPost) {
    console.log(JSON.stringify({
      url: tlPost.url,
      body: tlPost.bodyBase64,
      bodySize: tlPost.bodyByteLength,
      headers: Object.fromEntries(tlPost.headers),
    }));
  }
} finally {
  await sandbox.close();
}
```

## Environment Surfaces

EdgeSandbox provides all surfaces `ips.js` reads natively:

| Surface | EdgeSandbox Coverage |
|---------|---------------------|
| `navigator` (userAgent, platform, hardwareConcurrency, deviceMemory, languages, userAgentData, vendor, connection, mediaDevices, storage, serviceWorker, getBattery) | Full — driven by `fingerprint.navigator` config |
| Standard Chrome constructors (ImageData, Worker, RTCPeerConnection, IntersectionObserver, etc.) | All 1232 Window properties present |
| Canvas 2D (bindable methods, measureText, getImageData, toDataURL) | Full state machine — real fingerprint values |
| WebGL/WebGL2 (getParameter, extensions, vendor/renderer) | Full — driven by `fingerprint.rendering` config |
| AudioContext (oscillator→analyzer→FFT) | State machine with configurable output |
| Timers (setInterval, setTimeout, requestAnimationFrame) | Full — configurable timing profile |
| postMessage/message handshake | Full — independent iframe/Worker Realms |
| document.currentScript with .src | Correct during script execution |
| performance.timing / performance.navigation | Present (deprecated but Chrome-visible) |
| Native function toString integrity | Maintained — no wrapper source leaks |

## `has()` and Introspection

EdgeSandbox handles all introspection paths correctly:

- `has` / `in` operator returns `true` only for genuinely existing properties (1232 Window names).
- `ownKeys` / `Object.keys` returns the correct Edge 150 property set in correct order.
- `getOwnPropertyDescriptor` returns accurate descriptors.
- Kasada's `randomName in window` consistency probes pass because EdgeSandbox does not lie about non-existent properties.
- No internal `_`-prefixed keys, random-hex session fields, or emulation library internals leak through.

## Fingerprint Plausibility

EdgeSandbox state machines produce rendering values driven by the `fingerprint` config:

- **Canvas pixel data**: state machine produces consistent patterns per fingerprint seed.
- **WebGL readback**: GPU vendor/renderer/extensions and parameter queries return coherent values.
- **AudioContext FFT**: oscillator→analyzer output matches fingerprint config.
- **Font metrics**: measureText returns plausible bounding box values.

### Recommended: Export from Real Browser

For maximum server-side acceptance:

1. Launch Camoufox with a clean target-region residential exit.
2. Navigate to the target page (let the browser render).
3. Export fingerprint profile:
   ```python
   await camoufox.launch_browser(headless=True, os_type='windows', locale='en-US')
   await camoufox.navigate('https://target.example/')
   fp = await camoufox.export_fingerprint_profile(include_heavy=True)
   # Save to fingerprint.json
   ```
4. Inject into EdgeSandbox via `fingerprint` config.
5. Same-version `ips.js` uses fixed drawing instructions → one export covers all sessions until `ips.js` updates.
6. When `ips.js` updates (new drawing commands), re-run the export.

This makes the sandbox fingerprint indistinguishable from a real browser on the same device/exit. The cdndex report carries authentic rendering hashes, and the `ct` should pass server-side scoring.

### Fallback: real headless browser with clean egress

If fingerprint injection is impractical (`ips.js` varies challenge per session, or the rendering pipeline is too complex):
- Use Camoufox directly with clean residential egress.
- This sacrifices speed/scalability but guarantees fingerprint authenticity.

## Reading the Run

- **`reporting.cdndex.io` beacon fired** (`POST /error`, ~34KB): This is a **fingerprint report**, NOT an error. It fires on every init, carrying canvas hash/WebGL/audio/timing. Its presence is expected. The real acceptance signal is whether the minted `ct` passes business replay on clean egress.
- **Threw inside VM handler**: A concrete environment gap. Check `sandbox.evaluate` error message for the accessed property. With EdgeSandbox, most gaps are already filled by the 1232-property surface. Kasada also runs **random-property probes** (`undefined[randomName]`); these are deliberate anti-instrumentation checks — do not chase them.
- **Reached `/tl` with plausible sensor + non-empty `ct`**: Sandbox is minting. Move to same-session business replay. A minted `ct` does NOT guarantee acceptance — the `ct` may be flagged server-side based on fingerprint plausibility.

## Hard Constraints

- The runtime bytecode is assembled during bootstrap; let `ips.js` build it, do not inject a captured integer array.
- String cipher/opcode/constants are version-locked to the captured `p.js`/`ips.js`; re-solve per build.
- `x-kpsdk-ct` is bound to IP + UA + TLS. Mint and replay on one coherent egress.
- Do not chase environment gaps indefinitely. If the beacon persists after EdgeSandbox fills the known surfaces, the remaining signal is fingerprint plausibility — re-export from real browser or report "fingerprint plausibility ceiling reached."
- Datacenter proxies may receive empty `ips.js` (len=0) — Kasada rate-limits known DC IP ranges at script-delivery layer (egress-reputation gate).
- Browser-free reaches `/tl` and mints `ct` more reliably than a real browser on flagged egress. The EdgeSandbox path is the preferred diagnostic and production path for this provider.
