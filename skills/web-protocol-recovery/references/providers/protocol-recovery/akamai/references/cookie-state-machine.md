# Cookie State Machine

## Typical roles

| Cookie | Typical role | Provenance rule |
|---|---|---|
| `_abck` | Classic main Bot Manager state | Seeded by server, advanced by collector responses, sometimes updated by route responses |
| `bm_sz` | Classic sensor/challenge seed and key material | Server-issued; preserve exact value and trailing fields |
| `ak_bmsc` | Akamai Pixel/session state | Often HttpOnly and updated by Pixel or early document responses |
| `bm_s` | Modern main sensor/session state on some sites | Server-issued and rotated by collector POSTs; treat like the primary trust cookie when `_abck` is absent |
| `bm_sc` | Second-verification result on some deployments | Server-issued; capture the writer and transition, do not infer acceptance from shape |
| `bm_sv` | Short-lived validation/session value | Server-issued on auxiliary or business responses |
| `bm_so` / `bm_ss` / `bm_mi` | Auxiliary sensor/session markers | Capture transitions; do not invent values |
| `bm_lso` | Often JS-visible companion to sensor state | May be written from `document.cookie`; do not treat as HttpOnly server authority |
| `sbsd_o` | Seed-state alias on some second-verification deployments | Capture the response writer and the next request consumer |
| `sbsd_c` | Compatibility result Cookie on some deployments | Server-issued; require business validation |

Names indicate likely roles, not proof. Always capture the writer. Some modern targets never expose `_abck`/`bm_sz` and still are Akamai via random-path collectors + `bm_*` rotation.

## Minimum transition table

Record one row per network boundary:

```text
step | request URL | outbound cookie lengths/hashes | response status | Set-Cookie names | next state
```

Do not store only final values. The transition order is the protocol.

## Common sequence

1. Document response seeds `_abck`, `bm_sz`, and possibly `ak_bmsc`.
2. Collector script is downloaded in the same session.
3. Sensor POST 1 receives a new `_abck`.
4. Sensor POST 2 must send exactly that new `_abck` and receives another update.
5. Pixel POST may update `ak_bmsc` without changing `_abck`.
6. Route document may expand or replace `_abck`.
7. Route-local sensor POSTs may advance it again.
8. Business API uses the final same-session jar plus route-local server context.

## State-aware gates

The response branch is part of the cookie state machine. A repeated document URL can return a degraded challenge page or a trusted/full page depending on the current session, landing sensor result, and route context.

- Classify the response before running the next sensor or requiring a cookie: use semantic page markers and the expected business structure, not only the presence of a collector script or HTTP 200.
- Require `bm_sc`, `sbsd_c`, or another second-verification cookie only when the observed challenge/degraded branch emits it and the next request consumes it.
- If the same request already returns the trusted/full business page, skip challenge-only assertions and validate the page plus its next business request. A full page may still contain a collector script and rotate `bm_s` without producing `bm_sc`.
- Record the branch in the transition table so a missing stage-specific cookie is distinguishable from a failed cookie refresh.

## Rules

- Do not seed the Python session from reconnaissance-browser cookies.
- Do not expose HttpOnly cookies to local JavaScript unless live evidence proves page visibility.
- Mirror response-visible `_abck` and `bm_sz` into the local runtime before the emulated XHR callback executes.
- Preserve domain, path, Secure, and duplicate-name behavior when the wire header differs from a simple dict.
- Validate state with business replay, not `_abck` length or a substring heuristic.

## Failure signatures

- Collector 201 but route reset: transport mismatch, low-confidence sensor, route-local state, or exit reputation.
- Sensor POST 2 uses the seed cookie: response cookie was not mirrored before callback.
- Pixel succeeds but `_abck` stays seed-shaped: Pixel and main collector were confused.
- Business refresh 403 with valid sensor chain: missing route context, application-session initialization, Referer, or XHR header.
- Homepage/main/sensor 200 but business document POST Access Denied: incomplete multi-stage sensor settle or low-confidence `bm_s` trust, not necessarily missing CSRF.
- Full page returned where a degraded page was expected: do not force the degraded branch or infer failure from an absent challenge-only cookie; classify the full-page branch and continue with its business contract.
- Business form 400 after Akamai admission: compare submit-time serialization, including runtime-added fields, date normalization, and branch-specific hidden inputs before changing sensor logic.
- Local run reuses foreign canvas/WebGL cache: sensor may still 200 while business gate rejects; recapture host fingerprints.
- `429` with `cpr_chlge`: classify as a second-verification challenge and preserve the CPR, collector, and response-Cookie chain.
- A `~`-segmented Cookie shape is a triage clue only; acceptance still requires the business replay and response contract.
