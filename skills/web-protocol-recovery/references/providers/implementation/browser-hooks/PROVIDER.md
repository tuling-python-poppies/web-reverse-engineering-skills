# Browser Hooks Provider

## Select When

- One concrete observation boundary is already known (method, property, constructor, field, or URL-filtered request).
- User asks only for a reversible Console/hook snippet (fast path; no automatic full recon).

## Do Not Select When

- Entry point is still unknown (start with recon).
- Whole-file structural recovery is needed (AST).
- Final collector delivery is requested without a boundary (prove protocol first).

Use this provider only after web-protocol-recovery identifies one concrete observation boundary: a method, property, constructor, field, or URL-filtered request. It produces reversible observation code and never discovers a broad unknown entry by spraying global hooks.

Architecture boundary: web-protocol-recovery owns route choice, `projectRoot`, layout, acceptance, and final delivery. This provider only produces bounded hook code or assigned cache/helper artifacts under `web-protocol-recovery-simple`, then returns observed evidence or a blocker.

Canonical executable templates:

- `scripts/xhr_fetch.js`
- `scripts/cookie_header.js`
- `scripts/crypto_api.js`
- `scripts/storage.js`

If the observation boundary is concrete but the safest hook surface, log fields, restore strategy, or adjacent hook family is unclear, read `references/observation-boundary.md` first, then only the relevant topic file from `references/index.md`. Do not read topic files for routine template use.

Additional boundaries stay target-driven rather than becoming a second snippet library:

- hook jQuery transport only when initiator evidence proves `$.ajax`, `ajaxPrefilter`, or `beforeSend` owns the mutation
- observe WebSocket, Worker, `MessagePort`, or `postMessage` at the narrow message type and direction that carries the target artifact
- inject in the page's main world when isolated-world globals differ from the target's world
- treat cookie and storage observations as provenance evidence; direct property assignment and sibling writers can bypass one setter hook
- intercept direct `eval` through a local wrapper at its call site when code identity matters; replacing global `eval` changes direct-eval scope semantics

Every hook must preserve original `this`, arguments, return value, exceptions, and Promise behavior; install idempotently; bind logs to target/event/method/URL/field; default to types, lengths, hashes, and redaction; and expose a named restore function. Canonical templates fail closed until their target URL/key/API/cookie/header filter is configured. Do not consume Request/Response bodies by default.

The work order specifies engine/session/target, injection timing, filter, allowed log fields, and acceptance event. If the target caches native references before injection or hook integrity checks change behavior, return a blocker or narrower boundary instead of adding broader proxies.

Save a script only at the assigned cache/helper path. A standalone hook request may return code without writing files. Restore task-owned hooks before completion.
