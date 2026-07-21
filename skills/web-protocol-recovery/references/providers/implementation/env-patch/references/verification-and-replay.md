# Verification And Replay

Use this reference after `vm-browser-gap-diagnose.js` can load the target script. Loading success is only a runtime milestone; it does not prove the target sign, token, cookie, header, or encrypted field is accepted.

## Function Verification

`success: true` means requested env modules loaded and the observable target path completed under the diagnosis timeout. It does not prove DOM events, XHR hooks, Worker messages, swallowed internal branches, repeated intervals, or business callbacks produced the right artifact.

Verification flow:

1. Keep original target material under `js_reverse_cache/target/`.
2. Trigger the known behavior: SDK init call, XHR send, direct signer call, cookie writer, or header builder.
3. Compare output shape against browser evidence: length, prefix, segment count, encoding, cookie name, header name, and stable fields.
4. Move verified env state into root `mod.js` and the callable JS entry into root `main.js` only after fixed-vector parity passes.
5. Let root `main.py` own live HTTP only after web-protocol-recovery's live replay gate is approved.

For hook-style SDKs, keep this order:

```text
env modules -> fake XMLHttpRequest/fetch boundary -> target JS -> capture hook -> init(config) -> trigger request
```

Details:

1. Fake XHR/fetch must exist before loading target JS if the target patches prototypes at load time.
2. Capture hooks such as `URLSearchParams.append` should be injected after target JS if the target may replace native APIs with polyfills.
3. SDK `init` or `setup` parameters must come from browser evidence when they control route matching, feature switches, or path whitelists.

## Common Failures After Load Success

| Symptom | Likely cause | Check |
|---|---|---|
| Sign is `undefined` | Missing crypto/performance/storage dependency | Review selected env modules and load order |
| Hook runs but does not sign | Missing SDK init params or path whitelist | Capture init params in browser evidence |
| Capture hook never fires | Hook injected before target polyfill overwrote it | Move capture hook after target JS |
| JSVMP silently fails | Internal try/catch swallowed errors | Instrument known exits cautiously |
| Sign length differs from browser | Environment fingerprint mismatch | Collect coherent browser seeds and patch minimally |

## HTTP Replay Checks

Validate in this order:

1. Format check: run `node main.js '{"url":"..."}'` and compare artifact shape with browser evidence.
2. Python JS execution check: run `python main.py` and confirm it uses `execjs` or subprocess fallback successfully.
3. Request replay: send one approved API request with the returned artifact and the same browser-side request contract.

Python request rules:

1. Use a cookies dict or cookie jar. Do not place raw cookie strings in `headers["cookie"]` unless browser evidence proves manual header replay is required.
2. Do not pre-quote generated sign/header/token values unless the captured browser request proves the exact encoded form.
3. Rebuild time-sensitive values inside pagination, retry, or concurrency loops.
4. One successful HTTP status is not enough; verify content type, challenge markers, business result, and data shape.
