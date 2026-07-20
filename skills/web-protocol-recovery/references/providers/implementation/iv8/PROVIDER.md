# iv8 Provider

## Select When

- Browser-like local JS is the smallest faithful path: signing bundles, challenge state, browser tokens, XHR/fetch mutation, trusted input, verifier runtime proof, or a root-registry-selected runtime case.
- One explicit artifact must return to Python-owned live HTTP.

## Do Not Select When

- Only minimal Node/jsdom gaps for a known entry (prefer env-patch).
- Final live HTTP should stay in a browser (forbidden; Python owns HTTP).
- No artifact boundary is named yet.

**vs env-patch:** iv8 = browser-like host; env-patch = smallest Node module gaps.

Use iv8 when web-protocol-recovery proves that browser-like local JavaScript execution is the smallest faithful implementation: signing bundles, server challenge state, browser tokens, XHR/fetch mutation, trusted input, verifier runtime proof, or a root-registry-selected case.

Python retains live HTTP ownership. iv8 returns one explicit artifact such as a cookie, sign/header dict, final URL, wrapped body, telemetry object, or decoded payload.

## Evidence First

web-protocol-recovery selects cases only through `../../../cases/registry.json`. The 14 restored implementations and their process documents live under the registry-selected `../../../cases/iv8/<case-id>/` directory. Provider-local API examples and taxonomy are supporting runtime material, never alternate selectors.

## Mandatory API-First Sequence

Before authoring or modifying any iv8 code, issue a dedicated work order whose only Provider-local reference is `references/api-inventory.md`. Return the installed iv8 version, exact API members needed, and one offline member probe. Do not write code until web-protocol-recovery accepts that result.

After the API gate, use a new bounded work order for exactly one next reference: the root-selected case process/entry, one API example from `references/api-examples/README.md`, `references/script-writing-rules.md`, or `references/runtime-cheatsheet.md`. A second reference requires another accepted blocker and work order. Historical cases are hash-bound, credential-redacted source material and always require fresh current-target verification. The current work order still controls account state, target-code execution, dependency installation, verifier submission, artifacts, and every live request.

`references/example-taxonomy.md` explains the restored runtime families after root-registry selection; it does not replace the registry. `references/case-ingestion-rules.md` is maintenance-only and may be read only during an explicitly confirmed case-writeback work order.

## Project Shape

Use web-protocol-recovery's assigned `projectRoot`. Temporary scripts, downloaded assets, net logs, and environment snapshots stay under `js_reverse_cache/iv8/` or `js_reverse_cache/source/`. Stable compact code belongs in root `main.py` or assigned `utils/`; do not create another project, `collector/`, or standalone helper tree.

Generated helpers must be import-safe, use editable nonsecret inputs, have bounded runtime deadlines, and produce no network or file side effects on import. Use one coherent browser/session baseline; never mix cookies, UA, storage, TLS, and environment fields from different captures. Python owns all live HTTP, and verifier submission requires the work order to allow both live replay and the `verifier` action class.

Run `py_compile` and deterministic/fixed-vector checks before approved live replay. Require semantic response success, not only non-empty iv8 output or HTTP `200`. Return runtime/API versions, case used, artifact shape, verification, side effects, and remaining host dependencies.
