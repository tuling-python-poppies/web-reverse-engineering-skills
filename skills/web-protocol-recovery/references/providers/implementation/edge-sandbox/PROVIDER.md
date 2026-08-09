# EdgeSandbox Provider

## Select When

- The protocol task requires browser-free sensor/collector execution with full DOM/Web API surface (Canvas, WebGL, Audio, Workers, navigation timing).
- The target collector expects precise browser environment values: Edge 150 Window properties (1232), browser functions (11449), native Web IDL brands, or specific fingerprint surfaces.
- Pure Python or basic env-patch cannot faithfully reproduce the JS semantics (e.g., Akamai sensor, Kasada ips.js).
- A real browser is unacceptable due to overhead, profile persistence risk, or detection surface.

## Do Not Select When

- The target only needs basic DOM access (querySelector/innerHTML) — use `python-node` with `strategy: env-patch`.
- The collector is a simple Node.js script without browser-specific APIs.
- The task is hook-only observation, AST deobfuscation, or pure source recovery.
- Live browser automation is required (use Camoufox/CloakBrowser directly).

web-protocol-recovery owns intake, route choice, authorization, `projectRoot`, allowed paths, acceptance, runtime lifecycle, live-egress budget, case selection, and final delivery status. This Provider owns EdgeSandbox lifecycle, Node 24 environment validation, fingerprint profile construction, network replay configuration, and EdgeSandbox-specific execution constraints.

## Core Capabilities

EdgeSandbox provides:
- **Full Edge 150 compatibility surface**: 1232 Window properties, 11449 browser functions, exact descriptor/order match.
- **Real rendering state machines**: Canvas 2D (getComputedStyle/measureText work), WebGL (vendor/renderer/extensions), AudioContext.
- **Offline network replay**: configure exact HTTP responses via `replay` array; no socket access.
- **DOM/Worker/iframe Realms**: same-origin iframes, DedicatedWorker, SharedWorker, ServiceWorker with independent Realm isolation.
- **Configurable fingerprint**: navigator, screen, DPR, WebGL vendor/renderer, timing resolution, locale/timezone, sensors, media devices.
- **Network capture**: `sandbox.networkRequests()` returns all fetch/XHR requests with method/URL/headers/body.

## Node 24 Auto-Detection

EdgeSandbox requires Node.js 24.11.0. Python scripts automatically locate Node 24 via:
1. `NVM_HOME` environment variable + `v24.*` directory
2. FNM-activated `node` (checks `node --version`)
3. System `node` in PATH (checks `node --version`)

Users do not need to manually run `nvm use 24` before execution — Python handles this.

**If Node 24 is not installed:**
- NVM: `nvm install 24`
- FNM: `fnm install 24`
- Manual: Download from https://nodejs.org/ (LTS 24.x)

**Diagnostic tool (optional):**
```bash
node references/providers/implementation/edge-sandbox/node-version-check.js
```
Use this only for troubleshooting Node version issues.

## References

| Need | Reference |
|------|-----------|
| Complete usage documentation | `sandbox_manual.md` |
| Sensor generator template | `examples/sensor-generator-template.mjs` |
| Node 24 diagnostic tool | `node-version-check.js` |

## Core Rules

1. Check Node 24 before any EdgeSandbox work; exit with clear error if version mismatch.
2. EdgeSandbox binary lives outside the skill tree (user-installed, typically `D:\develop_software\edge_node_sandbox` or similar). Skill code uses absolute import paths or env vars pointing to the installation.
3. All EdgeSandbox scripts must use `import { EdgeSandbox } from 'file:///<edge-sandbox-root>/src/index.js'` (absolute file:// URL).
4. Fingerprint profiles should be exported from real browsers (Camoufox/CloakBrowser `export_fingerprint_profile`) when plausibility matters (Kasada cdndex beacon, Akamai canvas/WebGL checks).
5. Network capture is enabled by default; use `sandbox.networkRequests()` to retrieve outbound requests after execution.
6. Use `replay: [...]` to provide offline HTTP responses (Worker scripts, fetch data, XHR endpoints).
7. Final live egress is Python HTTP; EdgeSandbox only generates sensor/collector bodies through `networkRequests()` capture.
8. Close the sandbox after each use: `await sandbox.close()` or `await using sandbox = ...` (Node 24 explicit resource management).

## Execution Pattern

Typical EdgeSandbox workflow:

```javascript
import { EdgeSandbox } from 'file:///D:/develop_software/edge_node_sandbox/src/index.js';

const sandbox = await EdgeSandbox.create({
  page: {
    url: 'https://target.example/',
    html: challengeHtml, // or minimal HTML
  },
  fingerprint: {
    locale: 'zh-HK',
    timezone: 'Asia/Shanghai',
    screen: { width: 1680, height: 1050, availWidth: 1680, availHeight: 1002, colorDepth: 24, pixelDepth: 24 },
  },
  networkCapture: { enabled: true, maxEntries: 100 },
  limits: { timeoutMs: 20_000 },
});

try {
  // Execute sensor/collector
  await sandbox.evaluate(sensorScript);
  
  // Keep event loop alive for async POST (if sensor uses setTimeout)
  await sandbox.evaluate('new Promise(resolve => setTimeout(resolve, 10000))');
  
  // Capture outbound requests
  const requests = await sandbox.networkRequests();
  const sensorPost = requests.find(r => r.method === 'POST');
  
  console.log(JSON.stringify({
    body: sensorPost.bodyText,
    headers: Object.fromEntries(sensorPost.headers),
  }));
} finally {
  await sandbox.close();
}
```

Output is JSON for Python to consume; Python forwards the body via `curl_cffi` or similar.

## Internal Handoffs

- Fingerprint export from real browser uses `camoufox` or `chromium-recon`.
- Final HTTP delivery uses `python-collector`.
- If EdgeSandbox execution fails due to Node version mismatch, stop immediately with clear Node 24 requirement message.

## Acceptance

All applicable checks must pass:

1. Node 24.11.0 is active before EdgeSandbox import.
2. EdgeSandbox successfully creates a sandbox and evaluates the target script without unrecoverable VM exceptions.
3. `networkRequests()` captures the expected outbound POST/GET with plausible body size and structure.
4. Python forwards the captured request body to the real endpoint and receives the expected response (cookies, tokens, business data).
5. Final delivery has no browser/profile dependency and writes artifacts only under assigned project paths.

## Failure Recovery

| Trigger | First fix | Still fails -> stop |
|---------|-----------|---------------------|
| Node version is not 24.11.0 | User must switch Node version via nvm/fnm/system | Stop; cannot proceed without Node 24 |
| EdgeSandbox import fails with module error | Verify `file:///` absolute path is correct | Check EdgeSandbox installation integrity |
| Sensor throws in sandbox | Fill missing environment surfaces (navigator, canvas, timing) | If fingerprint plausibility ceiling reached, use real browser export |
| No POST captured | Extend event loop pump timeout (sensor POST is async) | Verify sensor actually triggers POST in real browser first |
| POST captured but server rejects | Check transport coherence (UA, TLS, IP binding) and fingerprint plausibility | Report egress/fingerprint residual risk |

## Exit

Return: EdgeSandbox version/path, Node version, fingerprint source (default/exported), sandbox execution outcome, captured request count/methods, sensor/collector body size/structure, Python forwarding result, business endpoint response, artifact paths/hashes, and residual risk.
