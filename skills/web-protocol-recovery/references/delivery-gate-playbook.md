# Delivery Gate Playbook

Use this reference only after the current proof path is selected and working, to decide whether it is a real handoff or a dressed-up shortcut. It does not choose a heavier layer; unresolved gates return one precise blocker to `escalation-ladder-playbook.md`.

## Core rule

If the final handoff still depends on live page context, it is not done.

Explicit config inputs are acceptable.
Live page reads are not.

If browser-shaped values such as UA, platform, viewport, or screen metrics only survive as signer inputs, they may remain as declared config or sample-derived parameters in the final collector.
That does not justify keeping a browser, embedded runtime, or page-context call alive just to reread them on every run.

## Acceptable delivery shapes

- pure Python HTTP collector
- Python plus isolated local JS helper
- Python plus local WASM helper
- Python plus local bootstrap executor
- Python plus local decoder for fonts, protobuf, msgpack, or compressed payloads

## Unacceptable delivery shapes

- browser automation as the collector
- CDP or page-context `fetch` as the steady-state path
- manual cookie export as an operating requirement
- "works only with my browser profile" handoff
- hidden verifier clicks instead of protocol replay
- importing runtime-backed predecessor modules whose import side effects still patch globals, read cookies, or depend on browser or host state
- live browser or host-runtime reads whose only purpose is to refill payload fields already understood as explicit inputs

## Gate checklist

1. real endpoint confirmed
2. moving parts named explicitly
3. signer or decoder has fixed-sample proof
4. request succeeds repeatedly
5. decode or parser path is local when applicable
6. required session state is explicit
7. no browser dependency remains in the final run path
8. host-like signer inputs are explicit config when they are only consumed as values
9. deterministic proof mode and live-generation mode are separated when randomness, timestamp jitter, or filler noise matter
10. final helper code is self-contained and free of runtime-backed import side effects

## Failed Gate Result

If one gate fails, do not package the current path as "good enough". Report the exact failed gate and current evidence. Resolution or rung selection happens outside this file.
