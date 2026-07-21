# iv8 Provider

## Select When

- Browser-like local JS is the smallest faithful path: signing bundles, challenge state, browser tokens, XHR/fetch mutation, trusted input, verifier runtime proof, or a root-registry-selected runtime case.
- One explicit artifact must return to Python-owned live egress.

## Do Not Select When

- Only minimal Node/jsdom gaps for a known entry (prefer env-patch).
- Final live egress should stay in a browser (forbidden; Python owns egress).
- No artifact boundary is named yet.

## vs env-patch

| If | Prefer |
|---|---|
| Known entry needs a few missing Node/jsdom surfaces | `env-patch` |
| Bundle expects browser-like host, timers, XHR/fetch semantics, or full page-like runtime | `iv8` |
| Both plausible | name the artifact boundary; pick the smaller host that still produces that artifact |

Use iv8 when web-protocol-recovery proves that browser-like local JavaScript execution is the smallest faithful implementation: signing bundles, server challenge state, browser tokens, XHR/fetch mutation, trusted input, verifier runtime proof, or a root-registry-selected case.

Architecture boundary: web-protocol-recovery owns route choice, `projectRoot`, layout, acceptance, and final delivery. This provider only writes assigned runtime probes/helpers under `web-protocol-recovery-simple/v1`, then returns one explicit artifact or blocker for Python-owned live egress.

Python retains live-egress ownership. iv8 returns one explicit artifact such as a cookie, sign/header dict, final URL, wrapped body, telemetry object, or decoded payload.

## Evidence First

web-protocol-recovery selects cases only through `../../../cases/registry.json`. Restored implementations and their process documents live under the registry-selected `../../../cases/iv8/<case-id>/` directory. Provider-local API examples and taxonomy are supporting runtime material, never alternate selectors.

## Mandatory API-First Sequence

Before authoring or modifying any iv8 code, issue a dedicated work order whose only Provider-local reference is `references/api-inventory.md`. Return the installed iv8 version, exact API members needed, and one offline member probe. Do not write code until web-protocol-recovery accepts that result.

After the API gate, use a new bounded work order for exactly one next reference: the root-selected case process/entry, one API example from `references/api-examples/README.md`, `references/script-writing-rules.md`, or `references/runtime-cheatsheet.md`. A second reference requires another accepted blocker and work order. Historical cases are hash-bound, credential-redacted source material and always require fresh current-target verification. The current work order still controls account state, target-code execution, dependency installation, verifier submission, artifacts, and every live request.

`references/example-taxonomy.md` explains the restored runtime families after root-registry selection; it does not replace the registry. `references/case-ingestion-rules.md` is maintenance-only and may be read only during an explicitly confirmed case-writeback work order.

## Project Shape

Use web-protocol-recovery's assigned `projectRoot`. Temporary scripts, downloaded assets, net logs, and environment snapshots stay under `js_reverse_cache/iv8/` or `js_reverse_cache/source/`. Stable compact code belongs in root `main.py` or assigned `utils/`; do not create another project, `collector/`, or alternate helper tree.

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
