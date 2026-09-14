# Adidas HK Akamai NV8 Process

Read this first before using this case's `entry.py` (offline proof).

## What `entry.py` is

`entry.py` is an offline proof for the reusable Adidas HK Akamai shape with two layers:

- fixed vectors: validates the redacted sensor request contract, derives the sensor POST
  endpoint from the sensor script URL without query data, parses SFCC
  `Search-UpdateGrid` product HTML fixtures, and refuses live egress;
- NV8 executor chain (when an NV8 install + a supported Node runtime are available): runs
  `sensor_runner.mjs`, which executes the synthetic sensor inside an NV8
  `EdgeSandbox`, captures the sensor POST at the offline network boundary, and validates
  the narrow artifact (endpoint rule / JSON single key `body` / >= 4000 bytes).

The live collector shape (challenge page + sensor script fetched live, sensor run in NV8,
captured POST forwarded with `curl_cffi`, `Search-UpdateGrid` parsed and printed) is
implemented as a **separate delivery project**, not shipped in this offline-only case
library: the skill gates forbid live HTTP and `curl_cffi` imports inside cases. The
re-verified live run is recorded in `case.json` as `historicalLiveProof` provenance only.

The real adidas HK sensor JavaScript is sensitive material and is intentionally absent;
`fixtures/sensor.synthetic.js` reproduces only the documented observable
contract. Live HTTP remains a delivery task: the Python collector owns the approved HTTP
requests; NV8 only produces the narrow Akamai sensor artifact.

## Goal

Document a browser-free Adidas HK catalog collection pattern: run the Akamai Bot Manager sensor in an Edge 150/151 compatible local sandbox, forward the captured sensor POST with Python, receive Akamai cookies, then request the SFCC grid API and parse product tiles.

Case-local success predicate: case tests pass offline, proving endpoint derivation,
request-shape validation, product parsing, the live-egress refusal guard, and (when the
environment provides NV8 + a supported Node runtime) a validated NV8 sensor artifact.

Delivery success predicate: one approved collector run obtains Akamai admission cookies, fetches `Search-UpdateGrid`, and parses product rows with stable IDs and names.

## Match And Exclusion Signals

Select this case when at least three independent signals match:

- `vendor:akamai` with Bot Manager sensor behavior
- `cookie:ak_bmsc` after a sensor POST
- `script:sensor-v-uuid` on `www.adidas.com.hk` (random mount path marked by `?v=<uuid>`)
- `runtime:nv8` as the local sensor executor
- `api:sfcc-search-updategrid`
- `site:adidas-hk`

Do not select for River Security, Reese84, webmssdk, pure header signing, or T'way NetFunnel flows.

## Gate Family

Primary: `challenge`.

Secondary blockers may include session freshness and transport reputation, but the reusable protocol boundary is the Akamai sensor challenge.

## Reconnaissance Choice

Use Chromium recon first for current evidence: document request, challenge shell, sensor script URL, sensor POST shape, cookies set by the response, and the final business consumer.

Canonical mutation point: the sensor-owned XHR/fetch POST to the same randomized sensor mount path as the sensor script (marked by `?v=<uuid>`), with query parameters removed.

## Request And State Chain

```text
GET /zh/summer_cs_promotion_2
  -> may answer a 301 redirect-admission hop first (follow with accumulated cookies)
  -> challenge HTML contains a sensor script URL on a random mount path (?v=<uuid>)
GET sensor script with challenge cookies
  -> obfuscated Akamai sensor JavaScript
NV8 (`EdgeSandbox`, driven by `sensor_runner.mjs`) executes the synthetic sensor
  -> network capture records JSON sensor POST {"body":"..."} answered by replay
Python validates the narrow artifact (endpoint rule, JSON single key, >= 4000 bytes)
Python forwards that POST to the derived sensor endpoint (script path without query)
  -> Akamai admission cookies, including ak_bmsc
Python GET Search-UpdateGrid?cgid=summer_cs_promotion_2&format=ajax&start=N&sz=48
  -> SFCC product tile HTML
Python parses tiles into product JSON
```

Moving state names only:

- Cookies: `ak_bmsc`, `_abck`, `bm_sz`, `bm_sv`, `akacd_*` (redirect admission), and other `ak_` / `bm_` names when present
- Sensor script identity: random multi-segment mount path marked by `?v=<uuid>` (variants `&t=<challengeId>`, `&ch=true`); the raw HTML attribute carries `&amp;` and must be entity-decoded
- Sensor POST body: JSON object with a large encoded `body` string
- Business cursor: `start` and `sz` query parameters

## False Leads

- Treating the sensor body as a deterministic signer output. It is environment observation data scored by the server.
- Posting the sensor body to the page URL. The POST must target the sensor endpoint derived from the script URL.
- Treating one HTTP 200 or one non-empty cookie as completion. Business HTML must parse into product rows.
- Shipping browser-backed fetch as delivery. The collector must use Python for live egress.

## Provider Order

1. `chromium-recon` - capture current request evidence and the business consumer.
2. `akamai` - own the Bot Manager sensor/cookie state machine and acceptance.
3. `nv8` - run the sensor in Node 24 NV8 and return the narrow sensor artifact.
4. `python-collector` - forward the sensor POST, own cookies and HTTP, request SFCC, parse, and bound scale.

## Minimal Implementation

The delivery project needs:

1. Python entry that locates Node 24 and checks `node_modules/nv8/package.json`.
2. Project-local npm dependency named `nv8`.
3. Node sensor helper importing `EdgeSandbox` from `nv8`.
4. NV8 page seeded with the target URL, challenge cookies, stable fingerprint fields, and network capture.
5. Python `curl_cffi` session that forwards the captured sensor POST and then requests `Search-UpdateGrid`.
6. HTML parser that extracts product ID, name, price, image, and URL fields when present.

This case carries the offline form of items 1–3 (`entry.py` + `sensor_runner.mjs`) plus
the synthetic challenge/sensor fixtures, and the parser fixture for item 6. Items 4–6 in
live form belong to the separate delivery project; the skill case library stays
offline-only.

## Fixed-Vector Proof

Case-local proof is offline-only:

- sensor endpoint derivation removes the version query
- redacted sensor request shape validates method, content type, endpoint marker, and encoded body size
- SFCC fixture parses into three products
- `run(live=True)` refuses live egress
- NV8 executor segment (environment-gated: `NV8_ROOT` or case-local `node_modules/nv8`,
  plus a supported Node runtime): `sensor_runner.mjs` executes the synthetic sensor, the POST is
  captured with JSON single key `body` and >= 4000 bytes, and the endpoint equals the
  derived rule; the test skips with a reason when the environment is absent
- console data: `python entry.py` prints the sensor artifact and the parsed product rows
  by default (`--print-body` for the full captured body, `--json` for machine output);
  vector data still prints when the NV8 segment is unavailable or fails

The verified live acceptance during case preparation returned Akamai cookies, fetched the SFCC grid HTML, and parsed 82 product rows. That result is not stored as live-current acceptance for future targets; future use still re-verifies the current target.

Live collector provenance (not current acceptance): the separate delivery project's
collector was re-verified on 2026-09-14 — the live challenge page + 500KB sensor script
were fetched, NV8 captured a ~4.5KB sensor POST, the forwarded POST returned 200, and
`Search-UpdateGrid` returned 48 parsed products. A same-day protocol-shape check found
the mount name had rotated away from the `pomCpnC` literal (now a random multi-segment
path marked by `?v=<uuid>`, with a possible 301 redirect-admission first hop). This is
recorded as `historical-project-provenance` with `currentAcceptance=false`; any new
target still requires a fresh run.

## Dependencies

- Python >= 3.9 for the case tests
- NV8 executor segment only: Node.js >= 18.18 (matrix covers 18/20/22/24; 22+ advised for
  Edge-equivalent fingerprint order; 24 is the usual baseline) and an NV8 install
  referenced by `NV8_ROOT` (or a case-local `node_modules/nv8`)
- Delivery project (external to this offline case library): project-local `nv8` npm
  dependency (`file:<nv8-root>`), `curl_cffi`, and an HTML parser such as
  `beautifulsoup4` (`loguru` optional)

## Invalidation Signals

- Sensor script query no longer carries `v=<uuid>` (the mount-name literal is not a signal)
- Sensor POST no longer uses JSON with a large encoded `body` string
- Forwarded sensor POST does not set Akamai admission cookies
- `Search-UpdateGrid` returns challenge HTML instead of SFCC product HTML
- Product tiles no longer expose stable product IDs
- NV8 execution captures no POST after the event-loop pump

The 2026-09-14 mount rotation (`pomCpnC` literal -> `?v=<uuid>` marker, optional 301
redirect-admission hop) is absorbed in revision 6: select this case by the marker rule,
never by a fixed mount name.

## Sensitive Materials Excluded

- Cookie values
- Encoded sensor bodies
- Full sensor JavaScript
- Full live response bodies
- Browser state exports
- Account/session data
- Proxy details
- Local machine locations
