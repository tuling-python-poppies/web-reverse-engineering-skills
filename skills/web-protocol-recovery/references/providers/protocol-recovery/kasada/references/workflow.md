# Workflow

## Short path

1. Confirm two Kasada evidence surfaces (see `recognition.md`).
2. Capture a clean session with recon browsers: the `429` interstitial or business page, the `p.js` and/or `ips.js` fetch, the `/fp` context, `/mfc`, and the `/tl` POST with its response `x-kpsdk-*` headers and cookies.
3. Record the exact deployment shape (page-embedded `p.js`, `429` interstitial/carrier, or direct `ips.js`).
4. Record the initial cookie jar, the double-UUID script path, and the exact outbound headers on `/tl`.
5. Probe raw HTTP admission with a small `curl_cffi` matrix on one coherent egress; confirm the interstitial and script fetch succeed.
6. Recover the collector: reproduce the bootstrap so the runtime-assembled bytecode exists, then locate the sensor build and `/tl` submission (use `ast` + the JSVMP interpreter-shape technique when the VM is opaque).
7. Run the collector browser-free (see `browserless-sandbox-strategy.md`): assemble the VM, fill the environment surfaces it reads, and let it attempt `/tl` without firing a `reporting.cdndex.io` anomaly beacon.
8. Bridge collector network calls to the same Python session on one coherent IP/UA/TLS egress; mint `x-kpsdk-ct` on that session.
9. Carry the minted `ct`, cookies, and headers into the protected business request on the same session; parse the business response.
10. Validate response shape and repeat with a fresh session. State `x-kpsdk-cd` status honestly if it is in scope.

## Evidence checkpoints

### Checkpoint A: family

Required:

- at least one Kasada-native marker (`x-kpsdk-*`, `KPSDK` bootstrap, double-UUID collector path, `/tl`, or `reporting.cdndex.io`)
- at least one independent surface: interstitial/carrier page, collector script fetch, `/tl` POST, or `x-kpsdk-*` transition

A `429` or one cookie name by itself is not enough.

### Checkpoint B: script roles

Required:

- `p.js` bootstrap/wrapper identified (or shown absent for the direct-`ips.js` shape)
- `ips.js` collector identified as the `/tl` sensor producer
- the double-UUID script path and `/fp` context recorded

### Checkpoint C: browser-free run

Required:

- runtime bytecode assembled from the reproduced bootstrap (not a raw captured array)
- environment surfaces filled enough that no `reporting.cdndex.io` anomaly beacon fires
- a plausible sensor body POSTed to `/tl`
- `x-kpsdk-ct` returned non-empty with expected `cr`/`st`/cookie continuity

### Checkpoint D: business API

Required:

- `ct` minted and replayed on one coherent IP/UA/TLS session
- exact method/query/body/header contract for the business endpoint
- repeated application response, not just a non-empty `ct` or a `/tl` `200`

## Stop conditions

Stop and report a blocker when:

- only a real browser can mint a usable `ct` after bootstrap reproduction and environment work
- the sandbox keeps firing `reporting.cdndex.io` anomaly beacons after the known environment surfaces are filled
- the business path requires `x-kpsdk-cd` and the proof-of-work seed gap is unresolved (see `cd-open-problem.md`)
- a real browser on the same exit is also blocked (egress reputation)
- required authorization or account state is unavailable

While blocked on pure protocol, it is valid to capture a headed recon success packet and parse business data for immediate needs, but label that output as recon-assisted, not pure-protocol completion.
