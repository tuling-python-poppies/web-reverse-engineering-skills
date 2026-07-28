# Case: T'way (`www.twayair.com`) IV8 protocol

Live-verified pure-protocol shape for a modern Akamai collector that uses
`bm_*` cookies more than classic `_abck` / `bm_sz`.

Project-local ops notes may live in the task repo. Keep **generic** lessons here;
keep **day-to-day runbook** in the project doc under the assigned project root.

## Evidence surfaces

- Random-path collector script on the origin (path rotates; role stable)
- Multi-stage sensor POST (`application/json`, body sizes vary, e.g. ~4.5k / ~0.3k / ~1.2k)
- Cookies: `ak_bmsc`, `bm_s`, `bm_so`, `bm_ss`, `bm_sv`, `bm_mi`, `bm_lso`
- Pixel branch: `/akam/13/<id>` script + `POST /akam/13/pixel_<id>`
- Business gate: `POST /app/booking/chooseItinerary` can 403 even when homepage/main/sensor are 200
- Under bad egress: even `GET /app/main` becomes Access Denied after a correct landing sensor
- Coexisting non-Akamai queue: NetFunnel (`csnf.twayair.com/ts.wseq`)

## Architecture that worked

```text
Python curl_cffi Session
  -> GET /
  -> GET collector (+ GET /akam/13/* pixel script when present)
  -> iv8 sensor stage (landing; multi-post settle; optional multi-pass)
  -> pixel fallback POST if IV8 did not emit pixel
  -> NetFunnel enter / complete
  -> GET /app/main
  -> iv8 sensor stage (main, multi-post settle toward ~3 posts)
  -> optional pre-choose sensor
  -> GET chkSaleRoute
  -> POST chooseItinerary
  -> if SBSD soft page: solve challenge then re-POST wrapped form
  -> POST layerAvailabilityList
  -> parse fares
```

Python owns every real HTTP request and the cookie jar.
IV8 only executes the live collector and emits XHR intent through a bridge.

## Failure modes observed

| Symptom | Real cause | Wrong rabbit hole |
|---|---|---|
| Browser OK, script `chooseItinerary` 403 | low-confidence sensor / incomplete multi-stage posts / no pixel | CSRF field missing |
| **Same code works after proxy node switch** | **egress reputation** | “code regressed again” |
| Landing sensor + NetFunnel OK, `GET /app/main` 403 | egress / session hard gate | NetFunnel ticket format |
| CSRF refresh says missing on HTTP 200 | extract from `meta[name=_csrf]` / form with `_extract_csrf` | session dead |
| Foreign `js_reverse_cache` works on author PC only | canvas / system color / WebGL bound to another GPU | code regression |
| Chrome MCP blocked, Edge manual passes | recon browser fingerprint | pure TLS alone |
| Same proxy IP: browser 200, curl root 403 | transport/IP reputation for non-browser clients | payload serialization |
| Sensor body always ~4.5KB once then stop | settle loop exits after first post | wrong Content-Type only |
| OW form 403 with “valid” CSRF | form fields diverge from **current** browser success capture | NetFunnel ticket |
| choose 200 ~4KB “Powered and protected by Privacy” | SBSD soft challenge, not business success | treat as tickets OK |
| IV8 floods HEAD `chrome-extension://...` | collector extension probe; bridge must drop quietly | allow_dynamic every path |

## Egress intermittency (2026-07 field note)

T'way is a textbook case where **implementation correctness and availability diverge**:

1. Correct multi-stage sensor + pixel + coherent TLS can still 403 on a dirty exit.
2. Switching to a clean residential/node exit can restore full tickets without code changes.
3. Under bad egress, even headed Edge with cleared cookies may Access Denied on `/app/main`.

Ops rule used successfully:

1. Browser-check `/app/main` on the **same exit**.
2. Access Denied in browser → **change node**, do not rewrite form fields first.
3. Browser OK, protocol only fails → inspect sensor post count, pixel, TLS/UA, form capture.

## Local fingerprint policy

Do **not** reuse another machine's:

- `cloak_canvas_profile.json` / `canvas_profile.json`
- `collector_canvas_profiles.json`
- `cloak_system_colors.json`
- hardcoded WebGL renderer strings (e.g. RTX 5070 Ti on a 3050 laptop)

Capture on the execution host:

1. canvas dataURL used by collector sizes
2. system colors
3. unmasked WebGL vendor/renderer
4. hardwareConcurrency / deviceMemory / screen / dpr

Align IV8 environment fields to that capture. Keep one baseline; do not mix
Chrome layout sample + Firefox TLS + foreign GPU strings.

## Multi-stage sensor settle

Browser success often emits **more than one** collector POST before business submit.

Implementation rules:

- do not stop the event loop after the first `postCount >= 1`
- keep advancing timers and emit light mouse/input events so later stages fire
- accept collector HTTP 200 and 202
- track post count growth; reset settle window when a new POST appears
- log body sizes; varied sizes (large then short) are a good signal
- landing may need **multi-pass** when the gate is elevated
- if pixel is present in HTML but IV8 never posts it, add a same-origin pixel fallback

## Business contract notes

- Prefer the real browser form serialization from a **fresh** successful capture
- For OW (2026-07 live Edge capture): only `availabilitySearches[0]` is filled;
  segments `1..4` stay **empty** (do not invent reverse airports unless the live
  capture shows them)
- `promoCode` may equal `defaultPromoCode` even when user promo is empty
- `chooseItinerary` is a document navigation POST; match Accept / Origin / Referer / UA / Client Hints
- After choose 200, availability is a separate XHR (`layerAvailabilityList`) with CSRF from the choose page
- TLS/UA must be co-generation (`chrome146` TLS + Chrome 146 headers). Edge/150 headers on chrome146 TLS was a real footgun

## Body-size taxonomy (quick)

| Body | Meaning |
|---|---|
| ~400–550B Access Denied | hard egress/session gate |
| ~4KB Privacy / `sec-if-cpt-container` | SBSD soft challenge |
| ~1MB choose HTML | business document success |
| ~300KB+ `layerAvailabilityList` | fare/list success |

## Recon browser preference

When ordinary Chrome automation is transport-gated:

1. Prefer `js-reverse` with **Microsoft Edge** (`launch_browser({browser:"edge"})`)
2. Use Camoufox only as anti-detect recon if Edge is insufficient
3. If automation still cannot submit business forms, open headed Edge/Camoufox and let the user operate while the MCP captures sensor/choose/layer packets

Never seed the final Python jar from those reconnaissance cookies. Use the capture only as shape evidence.

## Acceptance

A pure-protocol run is accepted only when:

- landing and main sensor posts succeed and rotate `bm_s`
- `chooseItinerary` returns 200 without Access Denied **and** without SBSD soft page
- availability parse returns flight/fare objects
- summary is written under task `js_reverse_cache/last_run_summary.json`

If success requires a specific proxy exit, document it as **egress-gated residual risk**, not as “implementation flaky”.
