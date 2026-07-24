# Workflow

## Short path

1. Confirm two Akamai evidence surfaces.
2. Capture a clean homepage with recon browsers: prefer web-protocol-recovery's Chromium recon route with `js-reverse` Edge when Chrome is gated; use `chrome-devtools` or Camoufox only as needed.
3. Export the collector GET, **every** sensor POST (count + body size + Content-Type), response `Set-Cookie`, and initiator.
4. Record the initial cookie jar and exact outbound cookie headers.
5. Probe raw HTTP admission with a small `curl_cffi` matrix.
6. Keep one transport profile and one session.
7. Fetch live HTML and dynamically extract collector and Pixel URLs.
8. Run the collector locally only if a pure algorithm port is not already proven.
9. Bridge collector XHR to the same Python session and mirror response cookies back into the local runtime before callbacks.
10. Request the route, rerun route-local collector when the page does so, extract server context, and replay one business endpoint.
11. Validate response shape and repeat with fresh sessions.

## Evidence checkpoints

### Checkpoint A: family

Required:

- at least one Akamai-native cookie, collector, Pixel, or `sensor_data` marker
- at least one independent network, script, cookie-transition, or transport corroboration

An H2 reset, 403, or cookie name by itself is not enough.

### Checkpoint B: cookie writer

Required:

- initial server seed
- sensor request cookie
- sensor response `Set-Cookie`
- next sensor request cookie

### Checkpoint C: local runtime

Required:

- multi-stage request count matching capture (not just first POST)
- non-empty sensor bodies with plausible size sequence
- expected 2xx collector response (often 200/202)
- response cookies applied in the correct order
- host-local fingerprint cache (no foreign GPU/canvas reuse)

### Checkpoint D: business API

Required:

- server context source identified
- exact method/query/body/header contract
- repeated application response, not just a plausible `_abck`

## Stop conditions

Stop and report a blocker when:

- only a real browser can issue every business request
- collector POST works but no business replay succeeds after transport, multi-stage sensor, form serialization, and context checks
- the target requires an interactive CAPTCHA outside the Akamai sensor flow
- required authorization or account state is unavailable

While blocked on pure protocol, it is valid to capture a headed Edge/Camoufox success packet and parse business HTML/JSON for immediate data, but label that output as recon-assisted, not pure-protocol completion.
