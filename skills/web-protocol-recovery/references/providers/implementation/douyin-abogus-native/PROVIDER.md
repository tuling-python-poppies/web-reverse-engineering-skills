# Douyin A-Bogus Native Provider

## Select When

- Target is `douyin.com/aweme/v1/web/*` and the moving field is `a_bogus`.
- The project already has a complete `pure_abogus.py` proved against a fixed BDMS 1.0.1.19 trace.
- The requested work is pure Python maintenance, fixed-vector verification, or adapting that implementation into a bounded `requests` script/helper.

## Do Not Select When

- Version, entry point, field layout, trace, or `pure_abogus.py` completeness is unknown.
- The task is from-zero algorithm recovery, hook/AST/env/iv8 runtime work, or browser-based generation.
- The only evidence is an `a_bogus` parameter name, a non-empty signer output, URL roundtrip, or one HTTP `200`.
- The target is not Douyin Web BDMS 1.0.1.19 under `aweme/v1/web/*`.

This Provider route is `douyin-abogus-native`. It owns already-proved Douyin Web BDMS pure-Python `a_bogus` maintenance and request adaptation. web-protocol-recovery still owns route choice, authorization, `projectRoot`, allowed paths, acceptance tests, live-egress budget, and final delivery status.

## Work Order Inputs

Require all of the following before writing or live replay:

1. Absolute assigned paths for the existing `pure_abogus.py`, fixed trace/vector, and any output helper/script.
2. Evidence that the target URL family is `douyin.com/aweme/v1/web/*` and the BDMS version/field layout matches the fixed trace.
3. Explicit UA, query, timing/random controls, and browser-fingerprint inputs such as `WINDOW_INFO` when they are signer inputs.
4. A fixed-vector acceptance test that compares the final `a_bogus` value byte-for-byte, not only length or character set.
5. Live replay authorization and request budget only when the requested shape requires an actual HTTP request.

If any required file or vector is missing, return `nextAsk` for only that missing item: `pure_abogus.py` path, fixed trace/vector path, BDMS version proof, target URL family, explicit signer inputs, output helper path, or live replay budget. Do not infer missing fields from a non-empty `a_bogus`.

## Path And Dependency Rules

1. Fixed traces, redacted vectors, and first-divergence samples belong under `js_reverse_cache/samples/` or stable `tests/` when the user approves promotion.
2. Accepted pure Python helper code belongs under `utils/` or the compact `main.py`; do not create a provider-named project root.
3. Dependency scan must confirm final artifacts do not import browser automation, Node, jsdom, iv8, or page runtime helpers.
4. Allowed final dependencies are standard-library modules and explicit Python HTTP/utility packages already approved for the task project.

## Provider Rules

1. Do not create a complete generator from the bundled primitive template alone.
2. Do not import iv8, jsdom, Node, browser MCPs, or page runtime helpers into final Python code.
3. Keep dynamic evidence and failing samples under assigned `js_reverse_cache/**`; never write into the installed skill directory.
4. For `local-proof`, return fixed-vector parity, first divergence if any, URL roundtrip, dependency scan, and exact artifact paths/hashes.
5. For `compact-replay` or `collector`, return a pure Python helper/request adapter for the Python-owned live-egress chain; web-protocol-recovery must still accept semantic business response shape before scale.

## Acceptance

All required:

1. Fixed trace final value matches byte-for-byte.
2. Query serialization excludes `a_bogus` during signing and roundtrips after insertion.
3. UA, cursor/mode key, `WINDOW_INFO`, time, and random inputs are explicit and coherent with the trace.
4. Final Python artifacts do not import iv8, jsdom, Node, browser automation, or legacy feed-and-catch helpers.
5. Approved live replay, when requested, passes semantic response checks; HTTP `200` or a non-empty `a_bogus` alone is failure.

## Failure Recovery

| Trigger | First fix | Still fails -> stop |
|---|---|---|
| Missing complete generator or fixed trace | Return blocker naming missing file/evidence | Route back to recon/AST/iv8 instead of inventing fields |
| Fixed-vector mismatch | Diff digest, packing slots, alphabet, UA, and explicit fingerprint inputs | Save first divergence; no live replay |
| Shape correct but business response fails | Check cookie/session, UA coherence, first page visit, time window, and request boundary | Return semantic mismatch; do not add browser dependency |
| User asks for from-zero recovery | Preserve samples and current blocker | Route to normal web-protocol-recovery implementation chain |

## Exit

Return provider result fields plus: source implementation path, fixed trace path, vector result, output helper/script path and SHA-256, dependency scan result, live replay budget/result if approved, cleanup state, and residual assumptions.
