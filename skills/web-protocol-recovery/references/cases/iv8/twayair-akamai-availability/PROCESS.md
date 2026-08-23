# T'way Akamai Bot Manager Availability Reverse Process

Read this first before using this case's `entry.py`.

## What `entry.py` is (and is not)

This case's `entry.py` is an **offline probe** for the reusable iv8 sensor-bridge pattern:

- runs a synthetic collector through the parent/child XHR bridge
- gates on fixed offline vectors (`post_count=1`, `signal_count=116`, worker/runtime counters)
- imports and runs with no live network when exercised by the case-local unit tests / offline probe

It is **not** the full live T'way delivery script. Live egress (`curl_cffi` TLS profile, flight date, route, proxy) lives in project delivery code guided by this PROCESS, not in the offline `entry.py`.

Env names below (`AKAMAI_CURL_PROFILE`, `AKAMAI_UA_MAJOR`, `AKAMAI_FLIGHT_DATE`, `AKAMAI_DEPARTURE`, `AKAMAI_ARRIVAL`, `AKAMAI_PROXY`, `AKAMAI_DIRECT_FALLBACK`, `AKAMAI_AUTO_SWITCH_EXIT`, `AKAMAI_EXIT_PREFIX`, `AKAMAI_MAX_EXIT_ATTEMPTS`, `AKAMAI_MAX_TOTAL_REQUESTS`, `AKAMAI_BATCH`, `AKAMAI_BATCH_ROUTES`, `AKAMAI_BATCH_DATES`, `AKAMAI_BATCH_CONCURRENCY`, `AKAMAI_RESULT_PAGE_SIZE`, `AKAMAI_RESULT_PAGE_NUM`) are **recommended delivery knobs**. They are not implemented by this offline `entry.py`.

Read `LIVE_DELIVERY.md` after this offline entry and before writing project delivery
code. It is the complete from-zero live assembly contract for the current case.

## Goal

Document and reuse a browser-free T'way Airlines availability recovery pattern: run the Akamai Bot Manager collector in an isolated `iv8` process (sensor generation only), keep HTTP and cookies in the Python parent, then parse the public availability response.

Case-local success predicate (what this library entry proves offline): a fresh run of `entry.py` / case unit tests passes the offline bridge vector (`post_count=1`, `signal_count=116`, `worker_message_count=1`, `runtime_error_count=0`).

Delivery success predicate (source project / live work order, not this offline entry): one approved live chain returns availability HTTP 200 with parseable flight/fare structures (non-empty itinerary for a day that has inventory).

## Match And Exclusion Signals

Select this case when at least two independent signals match:

- `vendor:akamai` — `akamai-cache-status` / `x-akamai-transformed` response headers, edgesuite error pages
- `cookie:bm_s` rotated by sensor POSTs; companion `bm_so`/`bm_ss`/`bm_sv`/`bm_mi`/`bm_lso`
- `cookie:ak_bmsc` set via `/akam/<n>/pixel_<id>` POST
- Collector under a randomized path like `/Q8z3ErVBPJQsy6QbzGjaKJ3V/.../PEIV?v=<uuid>` with response header `stored-attribute-sha-checksum`
- `queue:netfunnel` — `csnf.trinityairways.com/ts.wseq` opcode 5101 enter / 5004 complete, `NetFunnel_ID` cookie
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
  └─ NetFunnel enter:  GET  csnf.trinityairways.com/ts.wseq?opcode=5101&aid=H_LandingPage&...
       → result '5002:200:key=<hex>&nwait=0...' → set NetFunnel_ID cookie
  └─ GET  /<random>/<...>/dUFms_Ek0M?v=<uuid>          (collector, ~150-450KB)
  └─ POST /<random>/<...>/dUFms_Ek0M                    (sensor JSON ~4KB)
       → 200, empty body, Set-Cookie: bm_s (rotates every POST)
  └─ POST /akam/<n>/pixel_<id>                          → Set-Cookie: ak_bmsc
  └─ NetFunnel complete: GET csnf.trinityairways.com/ts.wseq?opcode=5004&key=<hex>
  └─ main page 200 → second collector pass (same pattern)
  └─ GET  /ajax/booking/chkSaleRoute    (final frm.serialize() body in query)
  └─ POST /app/booking/chooseItinerary   (form, _csrf, trip fields)
  └─ POST /app/booking/layerAvailabilityList  (X-Requested-With, _csrf)
       → availability HTML (flight numbers, fares, sold-out flags)
```

Moving state (names only; values are pulled live and never stored):

- Cookies: `bm_s`, `bm_so`, `bm_ss`, `bm_sv`, `bm_mi`, `bm_lso`, `ak_bmsc`, `NetFunnel_ID`, `SESSION`, `SETTINGS_REGION/LANGUAGE/CURRENCY`
- Storage: `ak_bm_tab_id` (sessionStorage)
- Sensor: ~116–120 signals per POST (count varies by stage; >=110 is a completeness heuristic)
- NetFunnel ticket: hex key 64..1024 chars in `5002:200:key=` envelope

## False Leads

- Treating it as `signer`: there is no stable sign function; the sensor is environment-observation data scored server-side. Reimplementing the collector in Python is not viable — run it in a faithful JS runtime instead.
- Replaying one captured `bm_s`: cookies rotate on every sensor POST; single-cookie replay fails.
- Bare Chrome replay: document gate 403s `/app/main` even with perfect sensor, due to TLS/IP profile mismatch.
- Shipping browser-driven fetch as delivery: violates the browser-free delivery invariant.

## Provider Order

1. `chromium-recon` (ordinary Chromium, then optional Cloak tier) — prove the 403/document gate, capture collector path, sensor POST shape, NetFunnel envelope, cookie family names.
2. `iv8` — isolated JSContext runs the real collector; a parent-owned XHR bridge forwards only the collector's requests; stats gate on `postCount>=1 && signalCount>=110 && active==0`.
3. `python-collector` — parent process owns all live egress (curl_cffi TLS profile), cookies, NetFunnel, business forms, parse, and bounds.

### curl_cffi TLS profile (live delivery only)

Applies to **live delivery code**, not this case's offline `entry.py` (which does not import `curl_cffi`).

Pick `impersonate=` from the **installed** curl_cffi build, not from a stale
browser capture. The current source verification used `chrome146` with
matching UA and Client Hints. Probe the installed build before changing that tuple.

Recommended pattern in live delivery:

1. Prefer the highest **supported current** profile on the current env.
2. Keep HTTP `User-Agent` / `Sec-CH-UA` on the same verified browser generation;
   do not downgrade both values as a blind workaround.
3. Optional: resolve profile dynamically from `curl_cffi.requests.impersonate.BrowserType`
   / package version, then record the chosen tuple in the work order.

### Search date / empty itinerary (live delivery only)

Protocol success (sensor 116, NetFunnel, choose 200) can still end with Korean empty inventory:

`조회된 여정이 없습니다. 여정을 재검색해 주세요.`

That is **business inventory**, not Akamai failure. Do not hardcode “today” as `FLIGHT_DATE` — same-day OW is often empty/sold-out.

Recommended live delivery defaults (not implemented by offline `entry.py`):

- `FLIGHT_DATE = (date.today() + timedelta(days=7)).isoformat()` from the host clock
- Overrides: `AKAMAI_FLIGHT_DATE=YYYY-MM-DD`, optional `AKAMAI_DEPARTURE` / `AKAMAI_ARRIVAL`
- Empty-body diagnostics must print the configured `dep-arr date` so operators can change inventory without re-debugging the sensor

## Minimal Implementation

### What this case's `entry.py` demonstrates offline

1. Synthetic collector through the iv8 parent/child XHR bridge (`__akamaiBridge.take/fulfill/stats`).
2. Offline request answers for CPR params + sensor POST only (no live site egress).
3. Offline gate: exactly 1 sensor POST, 116 signals, 1 SharedWorker message, 0 runtime errors.

### What live delivery must still implement outside this offline entry

1. Python parent loads the real challenge (page HTML + collector JS) and constructs the iv8 environment (UA/screen/canvas/system-colors consistent with the approved profile).
2. iv8 child installs the XHR bridge, evaluates the real collector, and never performs network itself.
3. Parent executes each forwarded request against the live site with a **supported** `curl_cffi` TLS profile, fulfills staged XHR, and merges cookies.
4. Offline gate: exactly 1 synthetic sensor POST, >=110 signals, 1 SharedWorker message, 0 runtime errors, no pending XHR at settle. Live stage counts are branch-dependent.
5. Then NetFunnel enter/complete, main navigation with full document Sec-Fetch headers, `chkSaleRoute` GET, chooseItinerary form POST, layerAvailabilityList XHR POST, parse.

## Fixed-Vector / Live Proof

Offline bridge (case-local `python entry.py` / unittest): post_count=1, signal_count=116, worker_message_count=1, runtime_error_count=0 — PASS (2026-07-21).
Case-local unit tests: parser + vectors shape + offline probe — PASS.

Current source live verification:

1. The verified source tuple used the installed `chrome146` profile with matching UA/CH.
2. Forcing an older `chrome136 / UA136` tuple changed `chkSaleRoute` from 200 to 403 on
   the same exit; preserve the verified current tuple unless deliberately measuring a
   new supported build.
3. Full protocol chain reached availability HTML; empty itinerary copy is inventory/date
   state, not automatically a sensor failure.
4. Default flight date = host `date.today() + 7 days`; override via `AKAMAI_FLIGHT_DATE`.

## Dependencies

- python >= 3.11 (spawned iv8 worker via multiprocessing Pipe)
- `iv8` runtime installed (required for offline probe and live delivery)
- `beautifulsoup4` + `lxml` (parser tests / live parse)
- Live delivery only: `curl_cffi` with a TLS profile supported by the **installed** build;
  the verified source project used `chrome146`.
- Live delivery optional egress proxy via environment variable (e.g. `AKAMAI_PROXY`)

## Invalidation Signals

- Collector `stored-attribute-sha-checksum` changes (new collector build) → re-capture recon.
- `signal_count` drops below 110 or worker pass missing → environment drift in iv8 profile.
- `/app/main` returns 403 with consistent fingerprint → egress IP reputation changed; re-check proxy.
- NetFunnel envelope type/code mismatch (`5002:200:` expected) → queue behavior changed.
- Availability response lacks `price_list` items → page layout or gate changed.
- `ImpersonateError: Impersonating chromeNNN is not supported` → curl_cffi too old for hardcoded profile; probe installed `BrowserType` and drop TLS profile.
- Availability 200 with Korean empty-itinerary copy and valid sensor chain → inventory/date problem; advance date, do not rework Akamai first.

## Sensitive Materials Intentionally Excluded

- All cookie values, SESSION, NetFunnel keys, sensor POST bodies, full collector JS (identity kept as response-header checksum only), absolute local paths, proxy address, and raw HAR snapshots.
