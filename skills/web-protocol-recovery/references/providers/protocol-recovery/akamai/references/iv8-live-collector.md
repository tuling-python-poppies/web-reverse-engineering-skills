# IV8 Live Collector

Use this route when the current collector is host-bound and a verified pure algorithm port is not the smallest reliable delivery. In web-protocol-recovery, the execution backend is the internal `iv8` Provider; this Akamai Provider retains collector state-machine acceptance.

## Runtime boundary

Python owns:

- every real HTTP request
- cookie jar and `Set-Cookie` handling
- dynamic HTML/script downloads
- retries, output, persistence, and business API validation

IV8 owns only:

- DOM/lifecycle needed by the collector
- sensor generation
- timer/challenge execution
- collector XHR intent

This is browser-free but not runtime-free.

## Required implementation shape

1. GET the live document with a fresh `curl_cffi.Session`.
2. Extract current collector and optional Pixel URLs from HTML.
3. Download both with the same session and Referer.
4. Save dynamic material under the task workspace `js_reverse_cache/`, never inside this skill.
5. Build one normalized environment matching the chosen transport profile.
6. Use `page.load` when parser order, external scripts, lifecycle, timers, or DOM structure matter.
7. Install an XHR bridge before loading the collector.
8. Send bridged requests through the same Python session.
9. Inject real responses into IV8 and update visible response cookies before callbacks.
10. Advance the event loop until the **observed multi-stage sensor request count** is reached, not merely the first POST.

## Egress containment

Treat the downloaded collector as untrusted remote code. Before execution build an allowlist from the exact URLs that Python already downloaded from the live HTML.

The Python bridge must enforce all of these:

- scheme is HTTPS
- origin exactly matches the page origin
- URL exactly matches the discovered collector or Pixel endpoint; do not allow arbitrary same-origin paths
- method is limited to the observed GET/POST contract
- redirects are disabled and any 3xx response is rejected
- collector-controlled `Cookie`, `Authorization`, `Proxy-Authorization`, `Host`, `Connection`, and forwarding headers are stripped
- Python's session jar is the only Cookie authority
- request body and response body have explicit size caps
- total bridged request count and per-request timeout are capped
- localhost, loopback, link-local, private-network, `file:`, `data:`, and non-HTTP destinations are rejected
- every blocked request is logged without forwarding it

Do not resolve or forward a collector-selected hostname. The exact downloaded URL and page origin are the authority.

## Environment policy

- Use one baseline. Do not merge UA from one browser, cookies from another, and screen/TLS from a third.
- It is acceptable to align an ordinary Chrome/Edge layout sample to the closest `curl_cffi` profile major version, but document the adaptation.
- Patch only observed surfaces such as `window.chrome`, WebGL, canvas, image/layout metrics, or timezone.
- Capture fingerprints on the **execution host**. Reject foreign `js_reverse_cache` canvas/systemColors/WebGL files as runtime inputs.
- A shorter second sensor often indicates missing lifecycle/layout/timer/input data. Compare structure before adding broad proxies.
- Do not exit the event loop after `postCount == 1` when browser captures show multiple collector POSTs with different body sizes.
- Keep advancing timers and emit light mouse/input events so later stages can fire.
- Accept collector HTTP 200 and 202 unless live evidence says otherwise.

## Verification

The local collector is accepted only when all pass:

- same multi-stage sensor POST count as live browser (or documented lower bound that still unlocks business)
- similar framing and body-size sequence
- correct response cookie continuity (`bm_s` / `_abck` rotates when the browser does)
- expected collector status/body
- route and business replay succeed

Local script load, non-empty sensor output, or a realistic-looking `_abck`/`bm_s` alone do not count.

## Artifacts

Save:

- live HTML
- collector and Pixel JS
- normalized environment without reconnaissance cookies
- local bridged request log
- browser sensor samples
- business success output
- failure diagnostics

Do not package dynamic target artifacts into this skill.
