# NV8 Provider

## Select When

- The protocol task requires browser-free sensor/collector execution with full DOM/Web API surface (Canvas, WebGL, Audio, Workers, navigation timing).
- The target collector expects a precise browser environment: Edge-compatible Window globals and prototype members, native Web IDL brands, or configurable fingerprint surfaces.
- Pure Python or basic env-patch cannot faithfully reproduce the JS semantics (e.g., Akamai sensor, Kasada ips.js).
- A real browser is unacceptable due to overhead, profile persistence risk, or detection surface.

## Do Not Select When

- The target only needs basic DOM access (querySelector/innerHTML) — use `python-node` with `strategy: env-patch`.
- The collector is a simple Node.js script without browser-specific APIs.
- The task is hook-only observation, AST deobfuscation, or pure source recovery.
- Live browser automation is required (use Camoufox/CloakBrowser directly).

web-protocol-recovery owns intake, route choice, authorization, `projectRoot`, allowed paths, acceptance, runtime lifecycle, live-egress budget, case selection, and final delivery status. This Provider owns the NV8 lifecycle, Node environment validation, fingerprint profile construction, network replay configuration, and NV8-specific execution constraints.

## Core Capabilities

NV8 provides:

- **Edge-compatible surface**: Window globals and prototype members aligned with real Edge across the 150 / 151 / 152 profiles; exact counts and diffs are locked by the NV8 repository baselines.
- **Real rendering state machines**: Canvas 2D (getComputedStyle/measureText work), WebGL (vendor/renderer/extensions), AudioContext.
- **Offline network replay**: configure exact HTTP responses via `replay`; no socket access.
- **DOM/Worker/iframe Realms**: same-origin iframes, DedicatedWorker, SharedWorker, ServiceWorker with independent Realm isolation.
- **Configurable fingerprint**: navigator, screen, DPR, WebGL vendor/renderer, timing resolution, locale/timezone, sensors, media devices.
- **Network capture**: `sandbox.networkRequests()` returns all fetch/XHR requests with method/URL/headers/body.

## Environment Setup (Local npm install)

NV8 is installed as a **project-local npm dependency** or referenced by absolute path from the canonical install root. Each project maintains its own `node_modules/nv8/` when the dependency form is used.

Canonical install root on this machine: `D:\develop_software\Nv8` (the completed NV8 repository; `NV8_ROOT=D:/develop_software/Nv8`).

### Installation

In the project's `package.json`, declare nv8 as a local file dependency:

```json
{
  "dependencies": {
    "nv8": "file:D:/develop_software/Nv8"
  },
  "type": "module",
  "engines": { "node": ">=18.18.0" }
}
```

Then run:

```bash
npm install
```

This creates a symlink at `node_modules/nv8/` pointing to the NV8 installation.

### Importing the API

The completed package does **not** re-export the sandbox classes from the bare package
name. Import what the `exports` map actually provides, and load `EdgeSandbox` /
`createSandbox` from the package files:

```js
// Bare package imports (presets/plugins, in-process entry, fingerprints, protocol/collector):
import { createNv8, nv8Eval, domPreset } from 'nv8';
import { edge152Fingerprint } from 'nv8/fingerprint/edge-152';

// EdgeSandbox / createSandbox are NOT in the package exports map.
// Use an absolute file URL (NV8_ROOT is supplied by the Python host):
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
const NV8_ROOT = process.env.NV8_ROOT ?? 'D:/develop_software/Nv8';
const { EdgeSandbox } = await import(
  pathToFileURL(resolve(NV8_ROOT, 'src/public/edge-sandbox.js')).href
);
// Alternative when the project has node_modules/nv8 installed:
// import { EdgeSandbox } from './node_modules/nv8/src/public/edge-sandbox.js';
```

Do not write `import { EdgeSandbox } from 'nv8'` or a bare `nv8/src/public/...`
subpath — both are rejected by the package `exports` map.

### Node Version Policy

- NV8 runtime supports Node `>=18.18.0`; **fingerprint-sensitive runs need Node 22+**
  (Node 18/20 cannot order Window globals exactly like Edge).
- This Provider's Python helpers locate **Node 24** first (`NVM_HOME` → `v24.*`, FNM,
  then PATH with a version check). Node 24 stays the recommended execution baseline.
- Version mismatches must fail closed with a clear message; never silently fall back to
  an unsupported runtime.

### Node Auto-Detection

Python scripts automatically locate Node 24 via:

1. `NVM_HOME` environment variable + `v24.*` directory (Windows nvm-windows)
2. FNM-activated `node` (checks `node --version`)
3. System `node` in PATH (checks `node --version`)

Users do not need to manually run `nvm use 24` before execution — Python handles this.

### If Node 24 is not installed

- NVM: `nvm install 24`
- FNM: `fnm install 24`
- Manual: Download from https://nodejs.org/ (LTS 24.x)

### Environment Validation

Python `ensure_node_modules()` checks `node_modules/nv8/package.json` when the project
uses the dependency form, and the runner must resolve `NV8_ROOT` (or the project-local
`node_modules/nv8`) before execution. If neither is present, stop with a clear
`npm install` / `NV8_ROOT` instruction instead of degrading.

### Diagnostic tool (optional)

```bash
node references/providers/implementation/nv8/node-version-check.js
```

Use this only for troubleshooting Node version issues.

## References

| Need | Reference |
|------|-----------|
| Complete usage documentation | `sandbox_manual.md` |
| Sensor generator template | `examples/sensor-generator-template.mjs` |
| Node diagnostic tool | `node-version-check.js` |

## Core Rules

1. Validate the Node runtime before any NV8 work (Node 24 recommended; 22+ for
   fingerprint-sensitive runs); exit with a clear error when the policy is not met.
2. NV8 is installed as a **local npm dependency** or referenced by absolute path
   (`NV8_ROOT`). Run `npm install` to set up `node_modules/nv8/` when the dependency
   form is used.
3. Import NV8's API exactly as the `exports` map allows (see "Importing the API");
   `EdgeSandbox` / `createSandbox` load from `src/public/*` via file URL or
   `node_modules/nv8/src/public/*`.
4. Fingerprint profiles should be exported from real browsers (Camoufox/CloakBrowser
   `export_fingerprint_profile`) when plausibility matters (Kasada cdndex beacon,
   Akamai canvas/WebGL checks).
5. Network capture is enabled by default; use `sandbox.requests()` (createSandbox) or
   `sandbox.networkRequests()` (EdgeSandbox) to retrieve outbound requests after
   execution.
6. Use `replay: [...]` to provide offline HTTP responses (Worker scripts, fetch data,
   XHR endpoints).
7. Final live egress is Python HTTP; NV8 only generates sensor/collector bodies through
   network capture.
8. Close the sandbox after each use: `await sandbox.close()` or
   `await using sandbox = ...` (Node 24 explicit resource management).

## Execution Pattern

Typical NV8 workflow (use `createSandbox` quick API for most cases):

```javascript
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

const NV8_ROOT = process.env.NV8_ROOT ?? 'D:/develop_software/Nv8';
const { createSandbox } = await import(
  pathToFileURL(resolve(NV8_ROOT, 'src/public/create-sandbox.js')).href
);

const sb = await createSandbox('https://target.example/', {
  fingerprint: {
    locale: 'zh-HK',
    timezone: 'Asia/Shanghai',
    screen: { width: 1680, height: 1050, availWidth: 1680, availHeight: 1002, colorDepth: 24, pixelDepth: 24 },
  },
  timeout: 20_000,
});

try {
  // Execute sensor/collector
  await sb.run(sensorScript);

  // Keep event loop alive for async POST (if sensor uses setTimeout)
  await sb.run('new Promise(resolve => setTimeout(resolve, 10000))');

  // Capture outbound requests
  const requests = await sb.requests();
  const sensorPost = requests.find(r => r.method === 'POST');

  console.log(JSON.stringify({
    body: sensorPost.bodyText,
    headers: Object.fromEntries(sensorPost.headers),
  }));
} finally {
  await sb.close();
}
```

For advanced use cases requiring full control, use `EdgeSandbox`:

```javascript
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

const NV8_ROOT = process.env.NV8_ROOT ?? 'D:/develop_software/Nv8';
const { EdgeSandbox } = await import(
  pathToFileURL(resolve(NV8_ROOT, 'src/public/edge-sandbox.js')).href
);

const sandbox = await EdgeSandbox.create({
  page: {
    url: 'https://target.example/',
    html: challengeHtml,
  },
  fingerprint: { /* ... */ },
  networkCapture: { enabled: true, maxEntries: 100 },
  limits: { timeoutMs: 20_000 },
});

try {
  await sandbox.evaluate(sensorScript);
  const requests = await sandbox.networkRequests();
  // ...
} finally {
  await sandbox.close();
}
```

Output is JSON for Python to consume; Python forwards the body via `curl_cffi` or similar.

## Internal Handoffs

- Fingerprint export from real browser uses `camoufox` or `chromium-recon`.
- Final HTTP delivery uses `python-collector`.
- If NV8 execution fails due to Node version mismatch, stop immediately with a clear
  Node requirement message.

## Acceptance

All applicable checks must pass:

1. The Node runtime satisfies the provider policy (Node 24 baseline, 22+ for
   fingerprint-sensitive work) before importing NV8.
2. NV8 successfully creates a sandbox and evaluates the target script without
   unrecoverable VM exceptions.
3. `networkRequests()` captures the expected outbound POST/GET with plausible body size
   and structure.
4. Python forwards the captured request body to the real endpoint and receives the
   expected response (cookies, tokens, business data).
5. Final delivery has no browser/profile dependency and writes artifacts only under
   assigned project paths.

## Failure Recovery

| Trigger | First fix | Still fails -> stop |
|---------|-----------|---------------------|
| Unsupported Node runtime | Switch Node version via nvm/fnm/system (24 baseline) | Stop; report the required runtime |
| `node_modules/nv8` missing | Run `npm install` in the project directory | Check `package.json` has the correct `file:` path |
| NV8 import fails | Use the `exports`-valid import forms (`nv8` bare specifiers, `NV8_ROOT` file URL for `src/public/*`) | Verify the install root and `NV8_ROOT` |
| Sensor throws in sandbox | Fill missing environment surfaces (navigator, canvas, timing) | If fingerprint plausibility ceiling reached, use a real browser export |
| No POST captured | Extend the event-loop pump timeout (sensor POST is async) | Verify the sensor actually triggers a POST in a real browser first |
| POST captured but server rejects | Check transport coherence (UA, TLS, IP binding) and fingerprint plausibility | Report egress/fingerprint residual risk |

## Exit

Return: NV8 version/path, Node version, fingerprint source (default/exported), sandbox
execution outcome, captured request count/methods, sensor/collector body size/structure,
Python forwarding result, business endpoint response, artifact paths/hashes, and residual
risk.
