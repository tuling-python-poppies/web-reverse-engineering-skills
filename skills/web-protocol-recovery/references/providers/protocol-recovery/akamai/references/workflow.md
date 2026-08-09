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

## Sensor field recovery (methodology, not fixed values)

When recovering the sensor body fields (device/window/screen block, the ordered `din`-style object, the `ajr`-style token, the VM-derived device segment, and the `ver`/previous-value pair used to encrypt the body), recover them by execution, not by transcribing values that rotate per JS build:

1. **AST-lock the producer.** Find the call that produces the target object by structural shape (e.g. a `try/if/else/catch` block that only assembles the field when its guard is true, or a consumer that always takes the value at a fixed argument position), not by a readable name. Multiple stacked structural constraints narrow candidates when the JS has no `send`/`window`/`xhr` markers yet.
2. **Neutralize environment guards.** Replace detection `if(...)` guards with a truthy expression of similar length (to avoid format-length checks) so the main path runs, or env-patch the few `navigator`/`screen`/global fields the guard reads.
3. **Run with minimal environment + hook the boundary.** Provide only the globals the code touches (a stub `document`/`location`/`XMLHttpRequest` is often enough; targets are usually global-presence checks, not deep prototype walks) and hook the assembly/consumption point to capture the finished object.
4. **Classify each field before reuse.** Split fields into: fingerprint (collect once from a real browser, reuse from a config), per-request dynamic (timestamps, counters, random fields — recompute every request), and version-fixed constants (recover once per JS build). A JS build is reusable for minutes, so re-extract `ajr`/`din`/`ver` only when the build rotates, not per request.

Treat any recovered field value as build-specific and volatile; keep the recovery method here and the values in task-local cache, never frozen into stable code.

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
