# Challenge State Envelope Playbook

Canonical first path for executable/stateful bootstrap, harvest boundaries, server-JS cookie double-call, and tiny side assets. Thin stubs (`challenge-artifact-harvest`, `server-js-cookie-bootstrap`, `side-asset-bootstrap`) only redirect here — do not load a stub and this file in the same dispatch window.

Use `public-bootstrap-envelope-playbook.md` when bootstrap is passive public data (key/config/nonce) with no challenge execution or derived client state.

## Variant index

| Symptom | Section |
|---|---|
| Getter / XHR-fetch egress / alternate route already has artifact | Harvest-first |
| Same endpoint `202`/JS then cookie then data; refresh function | Server-JS cookie bootstrap |
| Tiny `.wasm`/side script/font/config owns next state | Side asset |
| Full session chain, envelope family, executionPolicy | Fast Execution Path |

## Boundary

This file owns executable and stateful bootstrap:

- entry HTML plus challenge JavaScript must run before business requests stabilize
- a first response such as `202` or `412` contains executable JavaScript or linked challenge assets
- `.wasm`, a small side script, font, config asset, or returned code changes the next request
- challenge output appears in cookies, storage, URL, body, headers, or a preflight token
- one encoded envelope family spans request and response fields
- an approved local runtime exposes a getter or outgoing request containing the final artifact

## Core Model

Challenge output is protocol state, not decoration. Keep three concerns separate:

1. **State chain:** entry response, seed cookies, executable assets, derived state, replay.
2. **Envelope family:** framing, checksum, alphabet, state prefix, inner cipher, payload anchor.
3. **Harvest boundary:** getter, transport egress, lower serializer/packer, or alternate route.

Recover the artifact at the nearest stable boundary. Full deobfuscation or perfect DOM parity is optional when a smaller faithful boundary already proves and returns the replayable artifact.

## Harvest-first

Use when the decisive artifact is already visible before full challenge modeling.

Typical stable boundaries (prefer in order supported by evidence):

- exposed getter after synchronous init
- outgoing XHR or fetch call (body, decisive headers, derived cookie)
- lower serializer, signer, packer, or export below a failing facade
- cleaner alternate route that avoids the challenge

Path:

1. Classify path: getter / egress / bypass.
2. Preserve scheduler when timers, microtasks, lifecycle, or self-issued requests matter (script insertion over blocking `vm` when needed).
3. Patch the smallest faithful boundary (one missing env read, code-gen edge, local request hook, or narrow success stub).
4. Harvest one explicit artifact and hand real HTTP back to Python.
5. Reacquire version-randomized bootstrap assets rather than assuming one patch stays valid.

Do not finish every timer callback when one getter already returns the artifact. Do not let the local runtime issue unapproved live business HTTP when only local mutation evidence was needed.

## Server-JS cookie bootstrap

Use when the same endpoint (or a page refresh function) drives cookie/token state:

Typical flow:

1. call without the derived cookie/token
2. receive challenge response (often `202`) with executable JS (sometimes in `JSON.data`)
3. execute payload in a minimal sandbox → cookie, storage, or token
4. replay same endpoint with new state → real data array

Refresh-function variant: obfuscated bootstrap script + exposed renew function + optional in-memory timestamp slot (both must refresh).

Hook variant: global `beforeSend`/ajax wrapper rewrites body/headers while response encrypts only a `data` field — port both request mutation and response-field decryption.

Capture: first request, status, body shape, exact cookie/token written, second-request deltas, page-specific headers, parallel in-memory values.

Minimal sandbox start: `window`, `document.cookie`, `navigator.userAgent`, `location`, `Date`/`Math`, timers, base64/URI helpers. Add only when errors prove need. Parse the specific cookie value, not the whole raw string blindly.

Delivery shape: small extract helper + Python collector that challenge → helper → replay → aggregate. Done only after helper is consistent, replay returns real data twice+, and page-specific rules are documented.

Cookie writer still unknown after this path → `cookie-provenance-playbook.md` as a later expansion only.

## Side asset

Small assets often carry the whole secret. Inspect early:

- `.wasm` signers
- side scripts (e.g. `/offset`)
- server-returned JS bootstrap payloads
- dynamic fonts or glyph maps
- responses that set cookies and return executable code together

Method: identify which asset changes next-request state → execute/emulate locally → carry cookies/globals/keys/mappings into the next request → keep as local helper, not browser dependency. Do not over-reverse the main bundle while ignoring a tiny asset. Prefer local glyph maps over browser font rendering when decode is the goal. Response-only decode without challenge state → `response-decode-playbook.md`.

## Fast Execution Path

1. Freeze one fresh session chain.
   Capture entry HTML, challenge responses, inline code, linked scripts/WASM/fonts/config, seed cookies, post-challenge cookie/storage, one preflight exchange when present, and one business exchange. Do not splice neighboring sessions even when shapes match.

2. Classify the challenge variant.
   Common forms are:
   - same endpoint: first response carries JS, second request carries derived state
   - challenged document: non-final HTML seeds state and linked assets, then the same URL is replayed
   - page refresh function: an exposed function renews cookies/params plus an in-memory timestamp
   - side asset: small JS/WASM/font/config controls the signer, decoder, mapping, or next-request state
   - runtime harvest: a getter, hooked XHR/fetch, serializer, or packer already emits the decisive artifact

3. Review target code before execution.
   Hash the exact code and require `executionPolicy.targetCodeExecution=approved-reviewed-hash` for that hash. Use a capability-denied local sandbox: no network, filesystem, process, or dependency installation unless separately approved.

4. Preserve scheduler and script-order semantics only as needed.
   Use script insertion or an event-capable runtime when timers, microtasks, lifecycle, or self-issued requests matter. Do not force blocking evaluation when it deadlocks the real path. Add environment fields only after a concrete missing read.

5. Choose the smallest faithful harvest boundary (see Harvest-first).

6. Map shared envelopes once.
   For each related field record wire name, version/fixed prefix, checksum scope, alphabet/remap, state-derived prefix, encrypted segment, and payload anchor. Prove whether each field needs business plaintext alone or also current state bytes.

7. Return one explicit artifact to Python.
   Examples: one cookie, the authoritative outbound `Cookie` header, final URL, decisive headers, wrapped body, token, glyph map, or decoded payload. Python owns real HTTP, retries, replay, parsing, and persistence.

8. Verify semantic success on the same fresh chain.
   Check status plus business anchors, schema keys, pagination markers, checksum, segment counts, or token format. Reacquire version-randomized bootstrap assets rather than assuming one patch remains valid.

## Minimal Sandbox Surface

Start with only what errors prove necessary, typically `window`, `document.cookie`, location, navigator, Date/Math, timers, base64/URI helpers, parser support, and correct inline/linked script order. A local request capture must not be allowed to become an unapproved live business request.

## High-Value Checks

- Does the runtime emit the decisive artifact before later timer or DOM failures?
- Is the observed outbound `Cookie` header more authoritative than `document.cookie` or a jar snapshot?
- Can one synthetic request prove what a global hook injects automatically?
- Does the outer SDK fail only in adapter/telemetry glue while a lower primitive remains callable?
- Do URL, body, response, and cookie share one packet prefix, alphabet, or checksum family?
- Does a linked config hide keys, IVs, salts, cookie names, mappings, or compatibility constants?
- Is an apparent key/IV sliced, concatenated, masked, wrapped, or length-normalized before use?
- Is a bundle hash/version an embedded compatibility constant rather than a digest of current bytes?
- Is a side font better decoded locally as a glyph map than rendered in a browser?

## Common Traps

- copying a historical browser cookie instead of reproducing or pulling current authorized state
- mixing entry HTML, cookies, challenge assets, generated state, or tokens across sessions
- patching every DOM hole after a getter or egress record already contains the answer
- reversing the main bundle while ignoring a small state-bearing asset
- treating a first `202`/`412` response as an ordinary error
- proving inner crypto but missing outer framing, checksum, alphabet, or state prefix
- trusting stored state over observed wire egress when they diverge
- swallowing every exception and hiding recursion, stack overflow, or state corruption
- retaining the local runtime as a hidden browser replacement after the artifact boundary is understood

## Delivery And Handoff

Preferred shape:

1. Python obtains the fresh bootstrap/session chain.
2. One approved local runtime step executes or emulates the minimum asset.
3. One explicit artifact crosses back to Python.
4. Python performs replay and validates semantic output.

Report the winning boundary, scheduler assumptions, reviewed code hashes, required state fields, envelope order, narrow patches, extracted artifact, session-reuse evidence, and checkpoints that prove current reconstruction.
