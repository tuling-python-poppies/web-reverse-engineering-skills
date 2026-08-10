# Adidas HK Akamai EdgeSandbox Process

Read this first before using this case's `entry.py`.

## What `entry.py` is

`entry.py` is an offline proof for the reusable Adidas HK Akamai shape:

- validates the redacted sensor request contract
- derives the sensor POST endpoint from the sensor script URL without query data
- parses SFCC `Search-UpdateGrid` product HTML fixtures
- refuses live egress and target-code execution from the case library

Live HTTP remains a delivery task. The Python collector owns the approved HTTP requests; Node 24 plus EdgeSandbox only produces the narrow Akamai sensor artifact.

## Goal

Document a browser-free Adidas HK catalog collection pattern: run the Akamai Bot Manager sensor in an Edge 150/151 compatible local sandbox, forward the captured sensor POST with Python, receive Akamai cookies, then request the SFCC grid API and parse product tiles.

Case-local success predicate: case tests pass offline, proving endpoint derivation, request-shape validation, product parsing, and the live-egress refusal guard.

Delivery success predicate: one approved collector run obtains Akamai admission cookies, fetches `Search-UpdateGrid`, and parses product rows with stable IDs and names.

## Match And Exclusion Signals

Select this case when at least three independent signals match:

- `vendor:akamai` with Bot Manager sensor behavior
- `cookie:ak_bmsc` after a sensor POST
- `script:pomCpnC-sensor` on `www.adidas.com.hk`
- `runtime:edge-sandbox` as the local sensor executor
- `api:sfcc-search-updategrid`
- `site:adidas-hk`

Do not select for River Security, Reese84, webmssdk, pure header signing, or T'way NetFunnel flows.

## Gate Family

Primary: `challenge`.

Secondary blockers may include session freshness and transport reputation, but the reusable protocol boundary is the Akamai sensor challenge.

## Reconnaissance Choice

Use Chromium recon first for current evidence: document request, challenge shell, sensor script URL, sensor POST shape, cookies set by the response, and the final business consumer.

Canonical mutation point: the sensor-owned XHR/fetch POST to the same randomized `pomCpnC` endpoint as the sensor script, with query parameters removed.

## Request And State Chain

```text
GET /zh/summer_cs_promotion_2
  -> challenge HTML contains a pomCpnC sensor script URL
GET pomCpnC sensor script with challenge cookies
  -> obfuscated Akamai sensor JavaScript
EdgeSandbox evaluates the sensor script
  -> network capture records JSON sensor POST {"body":"..."}
Python forwards that POST to the derived pomCpnC endpoint
  -> Akamai admission cookies, including ak_bmsc
Python GET Search-UpdateGrid?cgid=summer_cs_promotion_2&format=ajax&start=N&sz=48
  -> SFCC product tile HTML
Python parses tiles into product JSON
```

Moving state names only:

- Cookies: `ak_bmsc`, `_abck`, `bm_sz`, `bm_sv`, and other `ak_` / `bm_` names when present
- Sensor script identity: randomized `pomCpnC` URL plus version query
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
3. `python-node` with `strategy=edge-sandbox` - run the sensor in Node 24 EdgeSandbox and return the narrow sensor artifact.
4. `python-collector` - forward the sensor POST, own cookies and HTTP, request SFCC, parse, and bound scale.

## Minimal Implementation

The delivery project needs:

1. Python entry that locates Node 24 and checks `node_modules/edge-sandbox/package.json`.
2. Project-local npm dependency named `edge-sandbox`.
3. Node sensor helper importing `EdgeSandbox` from `edge-sandbox`.
4. EdgeSandbox page seeded with the target URL, challenge cookies, stable fingerprint fields, and network capture.
5. Python `curl_cffi` session that forwards the captured sensor POST and then requests `Search-UpdateGrid`.
6. HTML parser that extracts product ID, name, price, image, and URL fields when present.

## Fixed-Vector Proof

Case-local proof is offline-only:

- sensor endpoint derivation removes the version query
- redacted sensor request shape validates method, content type, endpoint marker, and encoded body size
- SFCC fixture parses into three products
- `run(live=True)` refuses live egress

The verified live acceptance during case preparation returned Akamai cookies, fetched the SFCC grid HTML, and parsed 82 product rows. That result is not stored as live-current acceptance for future targets; future use still re-verifies the current target.

## Dependencies

- Python >= 3.9 for the case tests
- Delivery only: Node.js 24.x
- Delivery only: project-local `edge-sandbox` npm dependency
- Delivery only: `curl_cffi` and an HTML parser such as `beautifulsoup4`

## Invalidation Signals

- Sensor script no longer contains `pomCpnC`
- Sensor POST no longer uses JSON with a large encoded `body` string
- Forwarded sensor POST does not set Akamai admission cookies
- `Search-UpdateGrid` returns challenge HTML instead of SFCC product HTML
- Product tiles no longer expose stable product IDs
- EdgeSandbox execution captures no POST after the event-loop pump

## Sensitive Materials Excluded

- Cookie values
- Encoded sensor bodies
- Full sensor JavaScript
- Full live response bodies
- Browser state exports
- Account/session data
- Proxy details
- Local machine locations
