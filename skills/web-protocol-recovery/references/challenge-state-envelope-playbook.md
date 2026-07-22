# Challenge State Envelope Playbook

Use this playbook when executable bootstrap code or a side asset derives state before replay works, or when the approved local runtime already emits the decisive cookie, header, URL, body, token, or decoded payload.

When a getter, XHR/fetch egress, or alternate route already exposes the decisive artifact, start with `challenge-artifact-harvest-playbook.md` and only escalate here for session-chain, envelope-family, or executionPolicy work. Same-endpoint server-JS cookie patterns: `server-js-cookie-bootstrap-playbook.md`. Tiny controlling assets first: `side-asset-bootstrap-playbook.md`.

## Boundary

This file owns executable and stateful bootstrap:

- entry HTML plus challenge JavaScript must run before business requests stabilize
- a first response such as `202` or `412` contains executable JavaScript or linked challenge assets
- `.wasm`, a small side script, font, config asset, or returned code changes the next request
- challenge output appears in cookies, storage, URL, body, headers, or a preflight token
- one encoded envelope family spans request and response fields
- an approved local runtime exposes a getter or outgoing request containing the final artifact

Use `public-bootstrap-envelope-playbook.md` instead when the bootstrap artifact is passive public data such as a key, config blob, or nonce and no challenge execution or derived client state is involved.

## Core Model

Challenge output is protocol state, not decoration. Keep three concerns separate:

1. **State chain:** entry response, seed cookies, executable assets, derived state, replay.
2. **Envelope family:** framing, checksum, alphabet, state prefix, inner cipher, payload anchor.
3. **Harvest boundary:** getter, transport egress, lower serializer/packer, or alternate route.

Recover the artifact at the nearest stable boundary. Full deobfuscation or perfect DOM parity is optional when a smaller faithful boundary already proves and returns the replayable artifact.

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

5. Choose the smallest faithful harvest boundary.
   Prefer, in order supported by evidence:
   - exposed getter after initialization
   - intercepted local XHR/fetch egress
   - one synthetic request through an already-hooked transport primitive
   - lower serializer, signer, packer, or export below a failing facade
   - cleaner route that avoids the challenge

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
