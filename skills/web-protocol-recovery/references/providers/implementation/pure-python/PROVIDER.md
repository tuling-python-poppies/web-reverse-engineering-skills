# Pure-Python Implementation Provider

## Select When

- The protocol artifact can be generated in Python with no Node, jsdom, iv8, browser automation, or page runtime.
- Inputs, randomness, time, UA, environment values, and serialization rules are explicit.
- Fixed vectors or named checkpoints can validate the artifact before delivery.
- A target-specific profile such as `douyin-abogus-native` is explicitly selected and its prerequisites are already supplied.

## Do Not Select When

- The implementation still needs JS host semantics, browser-like runtime behavior, WASM through Node, or target page execution.
- The algorithm, entry point, state layout, or fixed vectors are unknown.
- The requested work is final HTTP delivery without a separate protocol artifact boundary.
- A non-empty signature, cookie, token, or HTTP `200` is the only evidence.

`pure-python` is an implementation Provider. It produces deterministic Python artifacts and hands final live egress to `python-collector`.

## Profiles

| Profile | Use |
|---|---|
| `douyin-abogus-native` | Existing complete Douyin Web BDMS 1.0.1.19 pure-Python `a_bogus` maintenance. Entry: `profiles/douyin-abogus-native.md`. |

## Contract

1. Stable helpers must not import browser automation, Node, jsdom, iv8, or page runtime code.
2. Helpers must be import-safe: no network, file writes, live cookie access, or target state binding at import time.
3. Fixed vectors compare exact bytes or named intermediate checkpoints, not only length or format.
4. Live HTTP belongs to `python-collector`; pure-Python may provide a signer/helper module for that delivery path.
5. Dynamic samples and first divergences stay under assigned `js_reverse_cache/samples/` or promoted `tests/` only after approval.

## Exit

Return the profile if any, artifact boundary, fixed-vector acceptance state, first divergence if any, dependency scan result, artifact path/hash, side effects, cleanup state, and next action. Do not claim delivery complete.
