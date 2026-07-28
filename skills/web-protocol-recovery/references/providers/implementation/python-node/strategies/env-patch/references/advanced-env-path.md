# Optional Advanced Env Path

Default path remains `scripts/vm-browser-gap-diagnose.js` plus the `env/` module tree. Enable `scripts/advanced-env-engine.js` only when the gate below is met. This is an optional branch inside env-patch, not a second default architecture and not a substitute for iv8 when browser-host semantics are required.

## Enable Gate

Use advanced only when all of the following hold:

1. Entry (or `script-load-only`) is known and the trust gate has passed.
2. The modular path has already been tried for at least one diagnose round, **or** evidence already shows the only remaining pressure is native/descriptor/`toString` shape.
3. At least one of:
   - need `Function.prototype.toString` / `Symbol.toStringTag` / constructor shape via `setFuncNative` / `setObjNative` / `getNativeProto`;
   - modules load but signer format still diverges from browser and a few objects need targeted `monitor`;
   - user wants cache-area verification before promoting root `mod.js` / `main.js`;
   - webpack modules are located and need `scripts/webpack-module-runtime.js` beside a hand-written host.
4. The task still wants Node/vm/jsdom env-patch, not an iv8 host.

If the first divergence is browser-like XHR/netLog, cross-realm, Worker, or real-engine semantics → escalate to iv8 (or return a blocker). Do not open advanced on the first turn by default.

## Layout

Write temporary runtime files under the approved `projectRoot` only:

```text
<project-root>/
  mod.js                    # promote only after fixed-vector proof
  main.js                   # promote only after fixed-vector proof
  js_reverse_cache/
    source/                 # original JS / entry slices
    env/
      package.json          # { "type": "module" }
      advanced-env-engine.js  # copy from provider scripts/
      verify-entry.mjs      # task-local verification entry
      ai-generated/         # site patches
```

Copy `advanced-env-engine.js` from the provider `scripts/` into `js_reverse_cache/env/`. Prefer ESM in the cache dir via `package.json` `{ "type": "module" }`. Do not force root `main.js` / `mod.js` to ESM unless the project already is ESM.

## Minimal verify-entry.mjs

```javascript
import env from './advanced-env-engine.js';
const _process = env._nativeRef.process;

function makeDocument() {
  return {
    cookie: '',
    readyState: 'complete',
    createElement(tag) {
      if (String(tag).toLowerCase() === 'canvas') {
        return {
          getContext() {
            return {
              measureText(text) {
                return { width: String(text).length * 8 };
              },
            };
          },
        };
      }
      return { style: {}, getContext: undefined };
    },
    getElementsByTagName() { return []; },
    addEventListener() {},
    removeEventListener() {},
  };
}

function makeNavigator() {
  return {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    webdriver: false,
    language: 'zh-CN',
    languages: ['zh-CN', 'zh', 'en-US', 'en'],
    platform: 'Win32',
  };
}

function makeLocation() {
  return {
    href: 'https://example.com/',
    origin: 'https://example.com',
    protocol: 'https:',
    host: 'example.com',
    hostname: 'example.com',
    pathname: '/',
    search: '',
    hash: '',
  };
}

const fakeDocument = makeDocument();
const fakeNavigator = makeNavigator();
const fakeLocation = makeLocation();

const fakeWindow = {
  document: fakeDocument,
  navigator: fakeNavigator,
  location: fakeLocation,
  addEventListener() {},
  removeEventListener() {},
  setTimeout,
  clearTimeout,
  setInterval,
  clearInterval,
  Math,
  Date,
  JSON,
};

fakeWindow.window = fakeWindow;
fakeWindow.self = fakeWindow;
fakeWindow.top = fakeWindow;
fakeWindow.parent = fakeWindow;
fakeWindow.globalThis = fakeWindow;

env.init({
  window: env.createProxy(fakeWindow, 'window'),
  document: env.createProxy(fakeDocument, 'document'),
  navigator: env.createProxy(fakeNavigator, 'navigator'),
  location: env.createProxy(fakeLocation, 'location'),
});

Object.defineProperty(global, 'chrome', {
  value: undefined,
  configurable: true,
  writable: true,
});

_process.on('uncaughtException', (err) => {
  console.error('[uncaughtException]', err && err.stack ? err.stack : err);
});
_process.on('unhandledRejection', (err) => {
  console.error('[unhandledRejection]', err && err.stack ? err.stack : err);
});

await import('./main.js');

console.log('entry type =', typeof window.sign);
```

Replace `window.sign` and host seeds with the real entry and approved profile values. For richer document/navigator/XHR shells, take only the stubs you need from `references/browser-stubs.md`.

## Usage Rules

1. Copy `advanced-env-engine.js` unchanged; put site patches in `verify-entry.mjs` or `ai-generated/*`, then promote to root `mod.js` only after proof.
2. Initialize the environment before loading target entry code. If the target copy must load as CommonJS, use `createRequire(import.meta.url)` instead of bare `require` inside an ESM verify file.
3. Each round patches one minimal causal unit: one value, one function shell, one return object, or one object contract.
4. `env.report()` with 0 error / 0 undefined only means the external access chain looks complete; it is not signer or replay proof.
5. When signature length, prefix, or encoding still diverges from the browser, locate `first divergence`; do not promote to root `main.py` integration yet.
6. If a Proxy/gap log exists, run `scripts/gap-log-module-advisor.js` first for module shortlisting; use advanced for native/monitor layers the module tree cannot express.
7. Real browser seeds: paste `scripts/browser-seed-collector.js` in DevTools and save redacted JSON under `js_reverse_cache/env/`.

## Engine API (summary)

| API | Role |
|---|---|
| `setFuncNative(fn, name?, len?)` | Native-looking `toString` / name / length |
| `setObjNative(obj, tag)` | `Symbol.toStringTag` |
| `getNativeProto(ctorName, attrs, opts)` | Illegal-constructor style prototype pair |
| `wrapFunc` / `monitor` / `createProxy` | Targeted observation without broad spray |
| `init` / `report` / `reset` | Wire host + dump access stats |
| `_nativeRef` | Preserved Node `process` / `Buffer` / timers |

## Relation To Modular Path

| Need | Prefer |
|---|---|
| Missing browser surfaces (`navigator`, storage, fetch, …) | `env/` modules via diagnose |
| Gap-log shortlist | `gap-log-module-advisor.js` → `env-modules.md` |
| Native shape / constructor / targeted monitor | advanced path (this file) |
| Browser-like host / XHR netLog / registry runtime case | iv8 |

Do not load the full modular tree and advanced as two competing defaults in the same ungoverned loop. Prefer modules first; switch to advanced when the gate is met; stop and escalate when the host boundary is wrong.

## Promote

After fixed-vector (or named checkpoint) acceptance:

1. Merge verified host construction into assigned root `mod.js` / `main.js`.
2. Keep the engine copy and probes under `js_reverse_cache/env/` or drop them if no longer needed.
3. Return hashes, first divergence (if any), residual assumptions, and hand final live egress to python-collector / hub.
