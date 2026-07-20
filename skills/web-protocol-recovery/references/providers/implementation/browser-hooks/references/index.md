# Browser Hooks Reference Index

Use these references only after the work order already names a concrete boundary or artifact. They preserve the local hook patterns for cases that are too specific or risky to live in the canonical executable templates.

## Topic Files

1. `network.md`: XHR, fetch, WebSocket, jQuery transport, `postMessage`, and page-main-world injection.
2. `storage.md`: `document.cookie`, `localStorage`, `sessionStorage`, direct Storage assignment caveats, and form value descriptors.
3. `crypto.md`: `atob`/`btoa`, WebCrypto, `getRandomValues`, and `TextEncoder`/`TextDecoder` boundaries.
4. `dom.md`: element creation, node insertion, `MutationObserver`, canvas context/drawing/export boundaries.
5. `runtime.md`: JSON parse/stringify, dynamic code, Blob/object URL, Worker, and timer boundaries.
6. `hook-output-samples.md`: expected log shapes and noise controls.

## Selection Rules

1. For request provenance, headers, body shape, or realtime messages, read `network.md`.
2. For token, cookie, browser cache, challenge state, or input value provenance, read `storage.md`.
3. For encoding, digest, signing, random nonce, or byte conversion boundaries, read `crypto.md`.
4. For dynamic node insertion, script injection, canvas fingerprinting, captcha drawing, or image export, read `dom.md`.
5. For dynamic execution, worker-side code, Blob resources, object URLs, JSON transformations, or timer-driven refresh/anti-debug behavior, read `runtime.md`.
6. For output formatting or deduplication, read `hook-output-samples.md`.

## Patterns To Avoid By Default

1. Broad debugger-removal scripts.
2. Replacing every `console` method.
3. Clearing every `setInterval` or timer globally.
4. Rewriting `RegExp`, `Date`, or `Function.prototype.constructor` broadly.

These are not forbidden forever; they are high-side-effect moves and require a target-specific reason plus an explicit acceptance test.
