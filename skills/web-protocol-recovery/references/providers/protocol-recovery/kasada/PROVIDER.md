# Kasada Provider

## Select When

- Evidence includes at least one Kasada-native marker: a `KP_UIDz` / `KP_UIDz-ssn` cookie, an `x-kpsdk-ct` / `x-kpsdk-cr` / `x-kpsdk-st` / `x-kpsdk-r` response header, an inline `window.KPSDK={}` bootstrap with `KPSDK.now` / `KPSDK.start`, a double-UUID script path such as `/<uuid>/<uuid>/p.js` or `/<uuid>/<uuid>/ips.js`, a `/tl` sensor submission, a `/mfc` request, or a `reporting.cdndex.io` telemetry beacon.
- A second independent surface corroborates the family: the `429` interstitial or carrier page, the collector script fetch, the `/tl` POST with a binary sensor body, or `x-kpsdk-*` cookie/header transitions across requests.
- The desired result is browser-free Python protocol replay, with a narrow local JS executor (VM sandbox) only when a pure Python port is not the smallest faithful path.

## Do Not Select When

- The only evidence is a generic `403`, `429`, or one cookie name with no `x-kpsdk-*` / `KPSDK` / double-UUID / `/tl` corroboration.
- The user only wants a browser hook, generic signer entry trace, AST deobfuscation, CAPTCHA solving, or final browser automation.
- Live business replay is requested without exact authorization, scope, and request budget.
- The only requirement is `x-kpsdk-cd` (per-request proof-of-work) with no path to the parent-side seed; see `references/cd-open-problem.md` before committing.

web-protocol-recovery owns intake, route choice, authorization, `projectRoot`, allowed paths, acceptance, runtime lifecycle, live-egress budget, case selection, and final delivery status. This Provider owns Kasada family proof, `p.js` vs `ips.js` role separation, the `/fp` execution-context model, sensor-to-`/tl` submission modeling, `x-kpsdk-*` token/cookie transition, browserless VM sandbox execution constraints, the `cd` proof-of-work boundary, and Kasada-specific report shape.

## Two-Script Model

Kasada splits work across two scripts. Keeping them separate is the core of correct analysis:

- `p.js`: top-level bootstrap, lifecycle triggers, and the business-request wrapper. Sets `window.KPSDK`, `KPSDK.now`, `KPSDK.start`, calls `KPSDK.configure(...)`, and creates the `/fp` context.
- `ips.js`: the environment collector and sensor generator that runs inside the `/fp` context (hidden iframe or separate realm). This is what mints the sensor and submits `/tl`.

The value that becomes `x-kpsdk-ct` is produced by the `ips.js` collector at `/tl`, not by `p.js`.

## Deployment Shapes

One protocol chain, different entry shapes (identify which one the target uses before building):

- **Page-embedded `p.js`**: business page auto-loads `p.js`, which wraps business requests.
- **`429` interstitial / carrier**: first response is a Kasada challenge page; the collector and `ips.js` and double-UUID paths are extracted from that page, then executed.
- **Direct `ips.js` execution**: skip page business logic, prepare the `/fp` context, load the real `ips.js`, submit `/tl`. Good for locating environment gaps and verifying sensor generation, but does not replace the full `p.js` wrapper chain; final proof is always a protected business response.

## References

Read only the selected reference after a work order names the current blocker.

| Need | Reference |
|---|---|
| Short end-to-end Kasada execution map | `references/workflow.md` |
| Family confirmation, marker set, `p.js` vs `ips.js` triage | `references/recognition.md` |
| Browser-free VM sandbox strategy and the environment surfaces to fill | `references/browserless-sandbox-strategy.md` |
| `x-kpsdk-cd` proof-of-work: what is known and what is unsolved | `references/cd-open-problem.md` |
| Final report format | `references/report-template.md` |

## Core Rules

1. Confirm at least two Kasada evidence surfaces before selecting this Provider. A `429` alone is not enough.
2. Separate `p.js` (bootstrap/wrapper) from `ips.js` (collector/sensor). Attribute the `/tl` submission to `ips.js`.
3. The Kasada script bytecode is assembled at runtime, not stored as a static literal. Reproducing the bootstrap is a prerequisite before any bytecode is meaningful; do not assume a captured integer array is the program.
4. Any embedded string cipher, opcode arity, or constant recovered from one `p.js`/`ips.js` build is version-locked. Re-solve per build; never freeze it into stable code.
5. `x-kpsdk-ct` is bound to the IP, User-Agent, and TLS it was minted on. Replay it only through the same session/egress; a `ct` minted on a different exit is not a valid credential.
6. Treat `reload=true`, `cr=true`, and a non-empty `ct` as distinct signals. No single one proves success.
7. A telemetry beacon to `reporting.cdndex.io` (often `/error`) means the collector detected an environment or integrity anomaly. Treat it as a fail signal for the sandbox, not as neutral traffic.
8. Browser and MCP tools are evidence only. Final live egress is Python HTTP; a local JS/VM sandbox only generates or settles the sensor through an allowlisted bridge.
9. If a real browser on the same exit is also blocked, classify the blocker as egress reputation before rewriting sensor or environment code.
10. Business replay and parsed response are the success criteria; a non-empty `ct` or a `200` on `/tl` alone is not success.

## Internal Handoffs

- Unknown family or weak evidence returns to web-protocol-recovery evidence/recon instead of guessing Kasada.
- Clean baseline capture of the interstitial, `p.js`/`ips.js`, and `/tl` uses `chromium-recon` (or `camoufox` when anti-detect capture is needed).
- Hook-only observation of `KPSDK`/`/tl` uses `browser-hooks`.
- Whole-source recovery of `p.js`/`ips.js` (string cipher, dispatch loop, export location) uses `ast`, with the JSVMP interpreter-shape technique from `references/jsvmp-analysis-playbook.md`.
- Browser-free VM execution of `ips.js` uses `python-node` with `strategy: env-patch` (or the WASM/VM sidecar strategy), with Kasada acceptance still owned by this Provider.
- Local browser-like collector execution uses `iv8` when host JS semantics are required.
- Stable final HTTP delivery uses `python-collector` after Kasada proof is accepted.

## Acceptance

All applicable checks must pass:

1. Family proof includes a Kasada-native marker (`x-kpsdk-*`, `KPSDK` bootstrap, or double-UUID collector path) plus an independent corroborating surface.
2. `p.js` and `ips.js` responsibilities are separated; the `/tl` sensor submission is attributed to the collector.
3. The browser-free run assembles the runtime bytecode and submits a plausible sensor body to `/tl` without firing a `reporting.cdndex.io` anomaly beacon.
4. The server returns a non-empty `x-kpsdk-ct` (and the expected `cr`/`st`/cookie transition) under the same IP/UA/TLS session that will carry the business request.
5. The protected business endpoint returns the expected application envelope/data under that session, repeated on a fresh session.
6. If `x-kpsdk-cd` is in scope, its status is stated honestly per `references/cd-open-problem.md`; an unsolved `cd` is reported as a bounded blocker, not hidden.
7. Final delivery has no browser/profile dependency and writes task artifacts only under assigned project paths.

## Failure Recovery

| Trigger | First fix | Still fails -> stop |
|---|---|---|
| Only a generic `429`/cookie name | Return to evidence/recon and collect a second surface | Do not select Kasada |
| Captured integer array does not disassemble | Reproduce the bootstrap so the runtime-assembled bytecode exists first | Blocker: bytecode not yet assembled |
| Sandbox fires `reporting.cdndex.io/error` | Fill the environment surface the collector read as anomalous (see browserless-sandbox-strategy) | Blocker: sandbox detected |
| `/tl` returns `ct` but business still blocked | Re-check IP/UA/TLS coherence and same-session replay; compare `reload`/`cr` signals | Do not claim success from `ct` alone |
| Business needs `x-kpsdk-cd` | Consult `references/cd-open-problem.md`; scope the PoW seed gap | Report `cd` as an open blocker |
| `ct` minted on a different exit than replay | Mint and replay on one coherent egress | Report egress-binding residual risk |

## Exit

Return: Kasada evidence surfaces, deployment shape (embedded / interstitial / direct), `p.js`/`ips.js` roles, collector path and `/tl` submission, sandbox run outcome (bytecode assembled? beacon fired?), `x-kpsdk-ct` mint result and session binding, `cd` status per the open-problem reference, business endpoint contract/result, artifact paths/hashes, budget consumed/remaining, cleanup state, and residual egress/version risk.
