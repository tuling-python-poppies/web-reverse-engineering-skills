# Python-Node Implementation Provider

## Select When

- A proved protocol artifact needs a local JavaScript, Node.js, `node:vm`, jsdom, or WASM sidecar.
- Python remains the orchestration and live-egress owner.
- The artifact boundary is named: signature, cookie value, header dict, URL/body wrapper, telemetry object, verifier proof body, or decoded payload.
- `strategy: env-patch` is selected when the known JS entry needs minimal Node/vm/jsdom browser-surface completion.

## Do Not Select When

- Browser-like host semantics are required beyond a bounded Node/jsdom sidecar; use `iv8`.
- The artifact is already fully portable to Python; use `pure-python`.
- The request endpoint, moving state, or artifact boundary is still unknown; return to reconnaissance or protocol recovery.
- The sidecar would directly send target HTTP, WebSocket handshakes, or sent frames.

`python-node` is an implementation Provider, not a protocol owner and not a delivery Provider. It only produces one explicit artifact for Hub or protocol-owner acceptance. Python owns target-network egress through `python-collector`.

## Strategies

| Strategy | Use |
|---|---|
| `direct-node` | Known entry runs in plain Node or `node:vm` with explicit inputs. |
| `env-patch` | Known entry needs minimal Node/vm/jsdom browser-surface completion. Entry: `strategies/env-patch/STRATEGY.md`. |
| `wasm-sidecar` | Python invokes a bounded Node/WASM helper to compute one artifact. |

## Runtime Contract

1. Helpers receive bounded JSON, text, or bytes and return bounded JSON, text, or bytes.
2. Helpers do not call `fetch`, `XMLHttpRequest`, WebSocket, `http`, `https`, or target network APIs directly.
3. Python owns process launch, deadlines, request scope, request budget, cookies, retries, and live response persistence.
4. Target-supplied JS/WASM execution requires reviewed bytes, SHA-256 approval, and a sandbox with network/file/process capabilities denied unless separately authorized.
5. Runtime load success is not protocol proof. Compare fixed vectors or named browser intermediates before delivery.
6. Keep generated probes and transient outputs under assigned `js_reverse_cache/env/`, `js_reverse_cache/source/`, or `js_reverse_cache/samples/` paths.

## Optional Scripts

| Script | Use |
|---|---|
| `scripts/gt4_bundle_helper.js` | GT4 current bundle metadata, PoW, GCT, and `w` artifact helper. Python delivery must pass `gctSource` or `biht`; the helper performs no target network I/O. |

## Exit

Return the strategy, artifact boundary, artifact value shape, artifact path/hash when saved, fixed-vector result, target-code hashes executed, installed commands, side effects, cleanup state, and next action. Do not claim complete delivery.
