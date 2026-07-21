# T'way Akamai Bot Manager Availability Reverse Process

Read this first before using this case's `entry.py`.

## Goal

Reproduce T'way Airlines public flight availability queries without a browser: run the Akamai Bot Manager collector in an isolated `iv8` process (sensor generation only), keep HTTP and cookies in the Python parent, then parse the public availability response.

Success predicate: a fresh run passes the offline bridge vector (post_count=1, signal_count=116, worker_message_count=1, runtime_error_count=0) and one approved live chain returns availability HTTP 200 with parseable flight/fare structures.

## Match And Exclusion Signals

Select this case when at least two independent signals match:

- `vendor:akamai` — `akamai-cache-status` / `x-akamai-transformed` response headers, edgesuite error pages
- `cookie:bm_s` rotated by sensor POSTs; companion `bm_so`/`bm_ss`/`bm_sv`/`bm_mi`/`bm_lso`
- `cookie:ak_bmsc` set via `/akam/<n>/pixel_<id>` POST
- Collector under a randomized path like `/espO2PwrZm/pjPoR2OF/qN/.../dUFms_Ek0M?v=<uuid>` with response header `stored-attribute-sha-checksum`
- `queue:netfunnel` — `csnf.<site>/ts.wseq` opcode 5101 enter / 5004 complete, `NetFunnel_ID` cookie
- `site:twayair` — host `www.twayair.com`

Do not select for: pure header-sign sites (no sensor POST), verifier-image gates (use verifier family), Ruishu two-stage cookie (different vendor; same `challenge` family but different subtype).

## Gate Family

Primary: **challenge** (Akamai Bot Manager sensor challenge-response; server scores the sensor and rotates `bm_s`/`ak_bmsc` cookies — no deterministic offline sign function exists).
Secondary (recorded, not the family): **session** (NetFunnel queue ticket), **transport** (TLS profile + egress IP: clean Chrome document gets 403 on `/app/main`; a proxy or fingerprint-consistent client is required).

## Reconnaissance Choice

Chrome DevTools baseline first:

- `GET /app/main` → 403 edgesuite "Access Denied" with Reference `#18.x`; Akamai collector script is still injected into the 403 shell and its sensor POST still returns 200 + `Set-Cookie: bm_s`.

Fingerprint escalation (Cloak tier via js-reverse) then reaches the real page:

- title `T'way Air`, full cookie family, NetFunnel enter/complete accepted.
- Sensor initiator: async parent function `UQG` inside the collector bundle (~`:1:370992`); the collector rewrites `XMLHttpRequest.prototype.open` and owns its own egress to the same randomized path.

Canonical mutation point: **collector-owned XHR POST** to the collector path (same path as the script URL, no `/_abck`-style fixed path), carrying the JSON sensor body.

## Request / State Chain

```text
GET /  (redirect to /app/main; bare client often 403 here)
  └─ NetFunnel enter:  GET  csnf.<site>/ts.wseq?opcode=5101&aid=H_LandingPage&...
       → result '5002:200:key=<hex>&nwait=0...' → set NetFunnel_ID cookie
  └─ GET  /<random>/<...>/dUFms_Ek0M?v=<uuid>          (collector, ~150-450KB)
  └─ POST /<random>/<...>/dUFms_Ek0M                    (sensor JSON ~4KB)
       → 200, empty body, Set-Cookie: bm_s (rotates every POST)
  └─ POST /akam/<n>/pixel_<id>                          → Set-Cookie: ak_bmsc
  └─ NetFunnel complete: GET ts.wseq?opcode=5004&key=<hex>
  └─ main page 200 → second collector pass (same pattern)
  └─ POST /app/booking/chooseItinerary   (form, _csrf, trip fields)
  └─ POST /app/booking/layerAvailabilityList  (X-Requested-With, _csrf)
       → availability HTML (flight numbers, fares, sold-out flags)
```

Moving state (names only; values are pulled live and never stored):

- Cookies: `bm_s`, `bm_so`, `bm_ss`, `bm_sv`, `bm_mi`, `bm_lso`, `ak_bmsc`, `NetFunnel_ID`, `SESSION`, `SETTINGS_REGION/LANGUAGE/CURRENCY`
- Storage: `ak_bm_tab_id` (sessionStorage)
- Sensor: ~116 signals per POST (count varies by stage; >=110 required)
- NetFunnel ticket: hex key 64..1024 chars in `5002:200:key=` envelope

## False Leads

- Treating it as `signer`: there is no stable sign function; the sensor is environment-observation data scored server-side. Reimplementing the collector in Python is not viable — run it in a faithful JS runtime instead.
- Replaying one captured `bm_s`: cookies rotate on every sensor POST; single-cookie replay fails.
- Bare Chrome replay: document gate 403s `/app/main` even with perfect sensor, due to TLS/IP profile mismatch.
- Shipping browser-driven fetch as delivery: violates the browser-free delivery invariant.

## Provider Order

1. `chromium-recon` (Cloak tier) — prove the 403/document gate, capture collector path, sensor POST shape, NetFunnel envelope, cookie family names.
2. `iv8` — isolated JSContext runs the real collector; a parent-owned XHR bridge forwards only the collector's requests; stats gate on `postCount>=1 && signalCount>=110 && active==0`.
3. `python-collector` — parent process owns all live egress (curl_cffi TLS profile), cookies, NetFunnel, business forms, parse, and bounds.

## Minimal Implementation (what entry.py demonstrates)

1. Python parent loads the challenge (page HTML + collector JS) and constructs the iv8 environment (UA/screen/canvas/system-colors consistent with the approved profile).
2. iv8 child installs the in-case XHR bridge (`__akamaiBridge.take/fulfill/stats`), evaluates the collector, and never performs network itself.
3. Parent executes each forwarded request against the live site, fulfills the staged XHR with body/status/headers (and optional `context.add_resource` after page load), returns changed visible cookies to the child, merges JS-set cookies into the Python cookie jar.
4. Gate: exactly 1 sensor POST, >=110 signals, 1 SharedWorker message, 0 runtime errors, no pending XHR at settle.
5. Then NetFunnel enter/complete, main navigation with full document Sec-Fetch headers, chooseItinerary form POST, layerAvailabilityList XHR POST, parse.

## Fixed-Vector / Live Proof (executed 2026-07-21)

Offline bridge (case-local `python entry.py` / unittest): post_count=1, signal_count=116, worker_message_count=1, runtime_error_count=0 — PASS.
Case-local unit tests: parser + vectors shape + offline probe — PASS.
Live chain (source project, approved proxy; shape only): landing 200 → collector 200 → sensor 200 → NetFunnel OK → main 200 → choose 200 → availability 200 (~314KB); flights TW301/TW303/TW305/TW307; parse produced structured fares.

## Dependencies

- python >= 3.11 (spawned iv8 worker via multiprocessing Pipe)
- `iv8` runtime installed
- `curl_cffi` (TLS profile chrome; UA/Client-Hints must match the approved browser profile)
- `beautifulsoup4` + `lxml`
- Optional egress proxy via environment variable

## Invalidation Signals

- Collector `stored-attribute-sha-checksum` changes (new collector build) → re-capture recon.
- `signal_count` drops below 110 or worker pass missing → environment drift in iv8 profile.
- `/app/main` returns 403 with consistent fingerprint → egress IP reputation changed; re-check proxy.
- NetFunnel envelope type/code mismatch (`5002:200:` expected) → queue behavior changed.
- Availability response lacks `price_list` items → page layout or gate changed.

## Sensitive Materials Intentionally Excluded

- All cookie values, SESSION, NetFunnel keys, sensor POST bodies, full collector JS (identity kept as response-header checksum only), absolute local paths, proxy address, and raw HAR snapshots.
