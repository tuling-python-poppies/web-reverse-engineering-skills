# Akamai Provider

## Select When

- Evidence includes at least one Akamai-native marker: `_abck`, `bm_sz`, `ak_bmsc`, `bm_s`, `bm_sv`, `bm_so`, `bm_ss`, `bm_mi`, `bm_lso`, `sensor_data`, `/akam/13/pixel_*`, or a confirmed random-path collector.
- A second independent surface corroborates the family: network collector POST, script marker, cookie transition, Pixel branch, `Server-Timing: ak_p`, or transport behavior tied to an Akamai edge.
- The desired result is browser-free Python protocol replay, with a narrow local JS/iv8 collector executor only when pure Python is not the smallest faithful path.

## Do Not Select When

- The only evidence is a generic `403`, `412`, H2 reset, or one cookie name with no network/script/cookie-transition corroboration.
- The user only wants a browser hook, generic signer entry trace, AST deobfuscation, CAPTCHA solving, or final browser automation.
- The task is maintaining a legacy Akamai 1.7/1.75 generator without current live replay proof.
- Live business replay is requested without exact authorization, scope, and request budget.

web-protocol-recovery owns intake, route choice, authorization, `projectRoot`, allowed paths, acceptance, runtime lifecycle, live-egress budget, case selection, and final delivery status. This Provider owns Akamai family proof, cookie transition modeling, collector/Pixel separation, transport coherence, host-local fingerprint policy, local collector execution constraints, and Akamai-specific report shape.

## References

Read only the selected reference after a work order names the current blocker.

| Need | Reference |
|---|---|
| Short end-to-end Akamai execution map | `references/workflow.md` |
| `_abck` / `bm_*` / `ak_bmsc` writer and transition order | `references/cookie-state-machine.md` |
| TLS/UA/Client-Hints/proxy/egress coherence | `references/transport-coherence.md` |
| Host-bound current collector in local iv8 with Python XHR bridge | `references/iv8-live-collector.md` |
| T'way modern `bm_s` / `ak_bmsc` field case | `references/case-twayair-iv8.md` |
| Public Akamai repo or old generator evaluation | `references/public-project-triage.md` |
| Final report format | `references/report-template.md` |

## Core Rules

1. Confirm at least two Akamai evidence surfaces before selecting this Provider. Cookie name alone is not enough.
2. Capture the complete state machine: first document, collector GET, every sensor POST, Pixel branch, route document, and one business success/failure boundary.
3. Treat stored jar, `document.cookie`, response `Set-Cookie`, and outbound `Cookie` header as different evidence surfaces.
4. Separate main collector, `/akam/13/*` Pixel, application CSRF/session/queue state, and route-local business context.
5. Multi-stage sensor matters. Do not stop after the first collector POST when browser captures show later POSTs with different body sizes.
6. Do not copy reconnaissance browser cookies or another host's canvas/systemColors/WebGL cache into final replay. Fingerprints must be recaptured on the execution host.
7. TLS impersonation, UA major, Client Hints, sensor navigator values, language/timezone, and proxy exit must be coherent.
8. Browser and MCP tools are evidence only. Final live egress is Python HTTP; local JS/iv8 only generates/settles collector artifacts through an allowlisted bridge.
9. If a real browser on the same exit also gets Access Denied, classify the blocker as egress reputation before rewriting sensor or form code.
10. Business replay, response shape, cookie transition, and sensor stage parity are success criteria; `_abck`/`bm_s` length or collector 200 alone is not success.

## Optional Script

`scripts/check_akamai_env.py` reports Python, `curl_cffi`, `iv8`, `bs4`, curl_cffi default Chrome profile, and proxy environment variables. Run from the task project or Provider path as a read-only startup check; do not write task evidence into the Provider directory.

## Internal Handoffs

- Unknown family or weak evidence returns to web-protocol-recovery evidence/recon instead of guessing Akamai.
- Hook-only observation uses `browser-hooks`.
- Whole-source recovery uses `ast`.
- Generic environment patching uses `python-node` with `strategy: env-patch`.
- Local browser-like collector execution uses `iv8`, with Akamai acceptance still owned by this Provider.
- CAPTCHA or interactive verification uses `verifier`.
- Stable final HTTP delivery uses `python-collector` after Akamai proof is accepted.

## Acceptance

All applicable checks must pass:

1. Family proof includes an Akamai-native marker plus an independent corroborating surface.
2. Cookie transition table proves writer/order for `_abck`, `bm_sz`, `ak_bmsc`, `bm_s`, `bm_sv`, or active companion cookies.
3. Local collector reproduces the observed sensor POST count or a documented lower bound that still unlocks the route, with plausible body-size sequence and correct response cookie continuity.
4. Pixel and collector responsibilities are separated; neither is substituted for the other without evidence.
5. Transport tuple is coherent and proxy/egress behavior is recorded.
6. Business endpoint returns the expected application envelope/data under a fresh session.
7. Final delivery has no browser/profile dependency and writes task artifacts only under assigned project paths.

## Failure Recovery

| Trigger | First fix | Still fails -> stop |
|---|---|---|
| Only generic 403/reset/cookie name | Return to evidence/recon and collect a second surface | Do not select Akamai |
| Sensor POST 2 sends seed cookie | Mirror response cookies before runtime callback | Blocker: cookie transition continuity |
| Collector 200 but route/business 403 | Compare multi-stage count, Pixel, transport, route context, and egress | Do not claim sensor success |
| Browser on same exit also Access Denied | Change node/exit and rerun full chain | Report egress-gated residual risk |
| Foreign fingerprint cache in use | Recapture host-local fingerprint surfaces | Reject cache reuse |
| Business body is SBSD/privacy shell | Treat as soft challenge, not business success | Route blocker to challenge/verifier as needed |
| Current workflow needs host JS semantics | Return internal `iv8` work-order blocker | Do not deliver browser automation |

## Exit

Return: Akamai evidence surfaces, cookie family, selected references/case, collector and Pixel roles, sensor POST count/body-size sequence, cookie transition result, transport tuple, host fingerprint source, business endpoint contract/result, artifact paths/hashes, budget consumed/remaining, cleanup state, and residual egress/transport risk.
