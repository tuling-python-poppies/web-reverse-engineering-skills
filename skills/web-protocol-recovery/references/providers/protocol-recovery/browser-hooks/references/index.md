# Browser Hooks Reference Index

Use these references only after the work order already names a concrete boundary or artifact. They preserve local, reversible patterns for cases that are too specific or risky to live in the canonical executable templates.

## Topic Files

1. `network.md`: XHR, fetch, WebSocket, jQuery transport, `postMessage`, `MessagePort`, and page-main-world injection.
2. `storage.md`: `document.cookie`, `localStorage`, `sessionStorage`, direct Storage assignment caveats, and form value descriptors.
3. `crypto.md`: `atob`/`btoa`, WebCrypto, `getRandomValues`, and `TextEncoder`/`TextDecoder` boundaries.
4. `dom.md`: element creation/insertion, targeted attributes/lookups, same-origin iframe load, `MutationObserver`, and canvas boundaries.
5. `events.md`: filtered `addEventListener` registration and one legacy `on*` property assignment.
6. `properties.md`: one known configurable object property or method.
7. `runtime.md`: JSON, dynamic code, safe logging, Blob/object URL, Worker, webpack chunk registration, bounded string assembly, and targeted timers.
8. `hook-output-samples.md`: expected log shapes and noise controls.

## Example Finder

| Known boundary | Read |
|---|---|
| URL, request header/body shape, WebSocket, bridge, or port message | `network.md` |
| Cookie, storage key, or input value | `storage.md` |
| Base64, digest, cipher, nonce, or text/byte conversion | `crypto.md` |
| Script/iframe/canvas creation, attribute mutation, element lookup, or export | `dom.md` |
| Keyboard, mouse, resize, context-menu, or another named event registration | `events.md` |
| One named global/object property or helper method | `properties.md` |
| JSON, generated code, Blob, Worker, webpack chunk, string assembly, console tamper, or timer | `runtime.md` |

## Selection Rules

1. Read exactly one topic file after the current work order names its boundary.
2. Prefer an existing canonical script for routine XHR/fetch, cookie/header, crypto, or storage observation.
3. Configure every URL/key/event/property/module/value filter before installation; high-frequency primitive hooks also require a finite capture cap.
4. Keep payloads redacted unless the work order explicitly permits the exact raw field.
5. Restore task-owned wrappers before completion and treat integrity-check detection as a blocker, not a reason to add stealth patches.

## Patterns To Avoid By Default

1. Broad debugger-removal scripts or source rewriting inside global `eval`.
2. Replacing every `console` method instead of preserving one early bound logger.
3. Clearing every `setInterval` or timer instead of cancelling one captured matching ID.
4. Rewriting global `RegExp`, `Date`, `Function.prototype.constructor`, or `Array.prototype` without a known target and hard capture bounds.
5. Rewriting `Function.prototype.toString` globally to hide installed hooks.

When targeted observation is insufficient, return a blocker for debugger controls, source-level instrumentation, engine-level tracing, or offline extraction. Do not widen into behavior-changing bypass code inside this Provider.
