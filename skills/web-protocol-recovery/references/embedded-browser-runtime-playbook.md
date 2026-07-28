# Embedded Browser Runtime Playbook

Use a local embedded runtime only when evidence proves it is the smallest faithful implementation boundary. This is browser-free but not runtime-free: Python owns live egress while iv8, Node, or WASM returns one narrow deterministic artifact.

## Entry Conditions

- The real request and canonical mutation point are known.
- Target JS/WASM, initialization state, and one fixed vector are available.
- A pure-Python implementation would duplicate a large unstable runtime or trusted-input path.
- The work order assigns exact `js_reverse_cache/` and stable output paths.

## Provider Selection

- iv8: browser-like local runtime, official XHR/fetch mutation, h5st, BDMS, challenge pages, verifier proof builders.
- `python-node` with `strategy: env-patch`: known JS entry that can run in Node/vm/jsdom after minimal environment completion.
- AST: source structure must first be restored before either runtime can execute a bounded entry.

Issue `web-protocol-recovery-provider-work-order`; do not create a cross-skill handoff. The provider returns `web-protocol-recovery-provider-result` with artifact path/hash, runtime versions, side effects, cleanup, and acceptance result.

## Stable Boundary

Prefer the nearest egress artifact: signed URL, headers, cookie, wrapped body, telemetry object, encoded frame, or decoded payload. Stop adding DOM APIs once that artifact is reproducible. Keep temporary scripts, assets, and net logs under `js_reverse_cache/iv8/` or `js_reverse_cache/env/`; promote only verified callable files to `main.js`, `mod.js`, or `utils/`.

## Verification

1. Compare fixed inputs and intermediate checkpoints against captured truth.
2. Confirm runtime load and helper errors separately from protocol output.
3. With explicit live permission, let Python send one fresh generated artifact.
4. Require semantic response success; HTTP `200` or non-empty output is insufficient.
5. Keep a browser-captured complete request clearly labeled as transport/session proof, not fresh local signer proof.

The final `main.py` launches only the required local runtime helper and performs all network, retry, pagination, decode, and persistence behavior itself.
