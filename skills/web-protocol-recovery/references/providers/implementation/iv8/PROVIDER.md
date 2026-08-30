# iv8 Provider

## Select When

- Browser-like local JS is the smallest faithful path: signing bundles, challenge state, browser tokens, XHR/fetch mutation, trusted input, verifier runtime proof, or a root-registry-selected runtime case.
- One explicit artifact must return to Python-owned live egress.

## Do Not Select When

- Only minimal Node/jsdom gaps for a known entry (prefer `python-node` with `strategy: env-patch`).
- Final live egress should stay in a browser (forbidden; Python owns egress).
- No artifact boundary is named yet.

## vs python-node env-patch

| If | Prefer |
|---|---|
| Known entry needs a few missing Node/jsdom surfaces | `python-node` with `strategy: env-patch` |
| Bundle expects browser-like host, timers, XHR/fetch semantics, or full page-like runtime | `iv8` |
| Both plausible | name the artifact boundary; pick the smaller host that still produces that artifact |

Use iv8 when web-protocol-recovery proves that browser-like local JavaScript execution is the smallest faithful implementation: signing bundles, server challenge state, browser tokens, XHR/fetch mutation, trusted input, verifier runtime proof, or a root-registry-selected case.

Architecture boundary: web-protocol-recovery owns route choice, `projectRoot`, layout, acceptance, and final delivery. This provider only writes assigned runtime probes/helpers under `web-protocol-recovery-simple`, then returns one explicit artifact or blocker for Python-owned live egress.

Python retains live-egress ownership. iv8 returns one explicit artifact such as a cookie, sign/header dict, final URL, wrapped body, telemetry object, or decoded payload.

## GT4 Narrow Artifact

For a Geetest GT4 verifier, the preferred iv8 artifact is the current bundle's
`w` output. The context may execute the bundle's isolated encryption export,
but it must not perform `/load`, image/GCT downloads, `/verify`, WebSocket
traffic, cookie persistence, or filesystem access through JavaScript. Python
fetches the same-round inputs and owns the final verifier request.

The work order must bind the exact bundle SHA-256, adapter SHA-256, an
ISO-8601 approval deadline, and a capability-denied adapter identity. The
adapter must fail closed when the bundle hash or required export feature
changes. A module number such as `require(32)` is current evidence only: also
check that the registry exists and that the approved module's export is
callable, then refresh the binding after a bundle change.

GT4 `td`, `td_sign`, coordinate mapping, OCR candidates, and `w` payload
assembly remain owned by the verifier workflow. iv8 should receive an already
validated same-round payload and return only the narrow encrypted artifact.

## Evidence First

web-protocol-recovery selects cases only through `../../../cases/registry.json`. Restored implementations and their process documents live under the registry-selected `../../../cases/iv8/<case-id>/` directory. Provider-local API examples and taxonomy are supporting runtime material, never alternate selectors.

## Mandatory API-First Sequence

Before authoring or modifying any iv8 code, issue a dedicated work order whose only Provider-local reference is `references/api-inventory.md`. Return the installed iv8 version, exact API members needed, and one offline member probe. Do not write code until web-protocol-recovery accepts that result.

After the API gate, use a new bounded work order for exactly one next reference: the root-selected case process/entry, one API example from `references/api-examples/README.md`, `references/script-writing-rules.md`, or `references/runtime-cheatsheet.md`. A second reference requires another accepted blocker and work order. Historical cases are hash-bound, credential-redacted source material and always require fresh current-target verification. The current work order still controls account state, target-code execution, dependency installation, verifier submission, artifacts, and every live request.

`references/example-taxonomy.md` explains the restored runtime families after root-registry selection; it does not replace the registry. `references/case-ingestion-rules.md` is maintenance-only and may be read only during an explicitly confirmed case-writeback work order.

## Project Shape

Use web-protocol-recovery's assigned `projectRoot`. Temporary scripts, downloaded assets, net logs, and environment snapshots stay under `js_reverse_cache/iv8/` or `js_reverse_cache/source/`. Never default those writes to OS temp. Stable compact code belongs in root `main.py` or assigned `utils/`; do not create another project, `collector/`, or alternate helper tree.

### Silent iv8 import and logger

Stable Python iv8 helpers and any final `main.py` that imports iv8 must not use top-level `import iv8` or `from iv8 import ...`. Create or reuse `utils/iv8_silent.py` **and** `utils/logger.py`, then load:

```python
from utils.iv8_silent import import_iv8_silent
from utils.logger import logger

iv8 = import_iv8_silent()
```

Template source of truth: `references/script-writing-rules.md` sections `utils/iv8_silent.py` and `utils/logger.py`. Do not invent a second helper body that can drift. `loguru` is optional and not installed by default; the logger helper provides PrintLogger fallback. Progress uses `logger.info`; do not paste loguru try/except into every main script; do not call `logger.remove()` / `logger.add()`.

Rules:

1. Silent import only suppresses the iv8 package import banner. Keep runtime diagnostic logs (for example EnvironmentAccessor errors) via `logger` or explicit diagnostics.
2. Do not wrap the whole collector, network calls, or event-loop work in a silent stdout/stderr redirect.
3. One-shot throwaway probes under `js_reverse_cache/iv8/` may use a bare import. Scripts a user will re-run should still prefer `import_iv8_silent()` and `logger`.
4. Bundled case `entry.py` files that still bare-import iv8 are historical examples, not new-delivery templates. New delivery code must not copy that import style.
5. Helpers stay import-safe: no target URL, cookie, token, network, or file side effects.

Generated helpers must be import-safe, use editable nonsecret inputs, have bounded runtime deadlines, and produce no network or file side effects on import. Use one coherent browser/session baseline; never mix cookies, UA, storage, TLS, and environment fields from different captures. Python owns all live egress, and verifier submission requires the work order to allow both live replay and the `verifier` action class.

Run `py_compile` and deterministic/fixed-vector checks before approved live replay. Require semantic response success, not only non-empty iv8 output or HTTP `200`.

## Failure Recovery

| Trigger | First fix | Still fails → stop |
|---|---|---|
| API inventory missing or member probe fails | One corrective API-gate work order only | Blocker: installed iv8 version + missing members; no code write |
| Registry case disagrees with current evidence | Stop case reuse immediately | Return to hub evidence routing; no sibling case |
| Import runs network or file I/O | Make import side-effect free; move I/O behind explicit call | Reject helper until import-safe |
| Mixed session baseline (cookie/UA/storage from different captures) | Rebuild from one coherent capture | Blocker naming mismatched fields |
| Non-empty sign but semantic fail | Diff fixed vectors / response shape / challenge markers | Do not scale; return precise mismatch |
| Needs browser recon for fresh baseline | Do not call browser MCP from iv8 | Return blocker for recon Provider work order |

## Exit

Return runtime/API versions, case id used (if any), artifact shape and path, fixed-vector acceptance state, side effects, remaining host dependencies, cleanup state, and the next hub action (python-collector, another implementation Provider, or stop). Do not claim delivery complete while Python live-egress ownership is still unproved when the shape requires it.
