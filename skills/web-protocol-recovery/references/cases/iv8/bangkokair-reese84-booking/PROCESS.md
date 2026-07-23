# Bangkok Air Reese84 Booking Availability Reverse Process

Read this first before using this case's `entry.py`.

## Goal

Reproduce Bangkok Airways public flight availability queries without a browser: harvest a fresh Reese84 cookie (via browser export or iv8 challenge solver), keep HTTP and cookies in the Python parent, obtain an OAuth token, then call `/v2/search/air-bounds` and parse real flight numbers, times, and fares.

### Success levels (do not collapse)

| Level | Predicate | Notes |
|---|---|---|
| **L1 business replay** | Fresh `reese84` present → OAuth 200 → `/v2/search/air-bounds` 200 with parseable `airBoundGroups` + `dictionaries.flight` | Current `entry.py` live path when `REESE84` / pull_live_state supplies cookie |
| **L2 challenge generate** | iv8 runs randomized challenge JS (page.load + pyHttp bridge) and obtains a **new** `reese84` without pasting browser cookie values into code | Higher cost; UA/Client-Hints/Canvas coherence required |
| **L3 two-session** | L2 (or L1 refresh) succeeds on two independent cold sessions | Required before claiming stable collector |

Default claimed success for this case library is **L1 + offline vectors**. L2/L3 are documented advancement, not automatic on import.

Success predicate (minimum for verificationClass freshly-verified L1): OAuth 200 + air-bounds 200 with flight number, depart/arrive datetime, total price, fare family.

## Match And Exclusion Signals

Select this case when at least two independent signals match:

- `vendor:imperva` / `vendor:reese84` — `reese84` cookie, `x-d-token` header, `Pardon Our Interruption` / interstitial, `/_Incapsula_Resource?SWJIYLWA=`
- `cookie:reese84` set after challenge solution POST (`token` + `renewInSec` + `cookieDomain`)
- `path:challenge-random` — randomized challenge script path (e.g. `/foot-I-not-binde-...` or `/o-exasphem-...`) with `initializeProtection` / solution envelope
- `api:amadeus-dapi` — host `api-des.bangkokair.com`, paths `/v1/security/oauth2/token` and `/v2/search/air-bounds`
- `site:bangkokair` — host `digital.bangkokair.com` booking SPA

Do not select for: pure Akamai sensor sites (use twayair-akamai case), Ruishu two-stage cookie, header-only sign sites with no Imperva challenge.

## Gate Family

Primary: **challenge** (Imperva Reese84 challenge-response; server scores the solution and issues `reese84` cookie).

Secondary (recorded, not the family): **session** (OAuth client_credentials token, short-lived), **transport** (TLS profile + UA/Client-Hints must match the approved Chrome baseline; bare clients often get error 15 / 403).

## Reconnaissance Choice

1. Chrome DevTools baseline first:
   - `GET /booking/availability/0` may return 403 + Imperva interstitial + challenge script injection.
   - Capture challenge script URL, solution POST shape (`{"solution":{"interrogation":{...}}}` or token echo), response fields `token` / `renewInSec` / `cookieDomain`.
2. Fingerprint escalation (Cloak tier via js-reverse) when document gate is hard-blocked:
   - Reach real booking SPA (title `Booking` / app shell).
   - Observe OAuth POST and (on successful search) `/v2/search/air-bounds`.

Canonical mutation point: **Reese84 challenge solution POST** (randomized path, body built by challenge JS) → server `token` written as `reese84` cookie and sent as `x-d-token` on API calls. Business search body is plain JSON after that gate.

## Request / State Chain

```text
GET digital.bangkokair.com/booking/availability/0
  └─ Set-Cookie: visid_incap_*, incap_ses_*
  └─ HTML injects randomized Reese challenge script
GET  /<random-challenge-path>?s=...
POST /<random-challenge-path>?d=digital.bangkokair.com
     body: solution envelope (or gpc then solution)
  └─ 200 {"token":"...","renewInSec":N,"cookieDomain":"bangkokair.com"}
  └─ cookie reese84=<token>
  └─ optional UTMVC: /_Incapsula_Resource?SWJIYLWA=... then SWKMTFSR beacon
GET  booking SPA assets (main.*.js, global.config.post.json, fare-families.json)
POST api-des.bangkokair.com/v1/security/oauth2/token
     Content-Type: application/x-www-form-urlencoded
     x-d-token: <reese84>
     body: client_id=...&client_secret=...&grant_type=client_credentials
  └─ 200 access_token (Bearer), expires_in ~1800
POST api-des.bangkokair.com/v2/search/air-bounds
     Authorization: Bearer <access_token>
     x-d-token: <reese84>
     Ama-Client-Ref: <uuid>
     body: {
       commercialFareFamilies: ["PGPROMO"],
       itineraries: [{
         originLocationCode, destinationLocationCode,
         departureDateTime: "YYYY-MM-DDT00:00:00.000",
         isRequestedBound: true
       }],
       travelers: [{ passengerTypeCode: "ADT" }],
       searchPreferences: { showSoldOut: false, showMilesPrice: false }
     }
  └─ 200 data.airBoundGroups + dictionaries.flight (numbers, times, prices)
```

Moving state (names only; values pulled live, never stored in the case library):

- Cookies: `reese84`, `visid_incap_*`, `incap_ses_*`, `nlbi_*`, optional `___utmvc`
- Headers: `x-d-token` (same value as reese84 on API host), `Authorization: Bearer ...`
- OAuth: `access_token`, `expires_in`
- Search: `commercialFareFamilies` (site codes e.g. PGPROMO / PGSAVER / PGFREEDOM — not generic CFFBAS)

## False Leads

- Treating localization JSON (`en-GB.json` ~2MB) as ticket data: it is UI strings only, not availability.
- Hardcoding a captured `reese84`: token expires / rotates; document gate returns interstitial or API returns 403 with SWJIYLWA.
- Invalid commercial fare family (e.g. `CFFBAS`): API returns error 36917; use site codes from `fare-families.json` (PGPROMO works for BKK-CNX).
- Wrapping body as `{airBoundsInputs: ...}` when Content-Type is JSON application path that expects the inner object at top level for this client: may 400 Unexpected attribute.
- Bare Chrome without matching TLS/UA/Client-Hints: OAuth may pass while search still 403.
- Shipping browser page fetch as final collector: violates browser-free delivery.

## Provider Order

1. `chromium-recon` (optional Cloak tier) — prove Imperva gate, capture challenge path, OAuth, air-bounds shape, fare family codes.
2. `iv8` (when generating reese84 offline) — run randomized challenge JS with page.load + pyHttp bridge; Python owns real HTTP for gpc/solution.
3. `python-collector` — OAuth + air-bounds + parse; progress via `utils/logger.py`; evidence only under project `js_reverse_cache/**`.

## Minimal Implementation (what entry.py demonstrates)

1. Load live state (reese84) from approved browser export selector (`pull_live_state.py`) — memory only.
2. Python `curl_cffi` session with Chrome-matching impersonate + Client-Hints.
3. POST OAuth client_credentials with `x-d-token`.
4. POST `/v2/search/air-bounds` with `commercialFareFamilies=["PGPROMO"]` and one ADT itinerary.
5. Parse `airBoundGroups` + `dictionaries.flight` into flight / depart / arrive / total / fare_family rows.
6. Log via shared logger; do not write secrets to disk.

## Fixed-Vector / Live Proof (executed 2026-07-22)

- Offline: fixture shape for air-bounds sample (groups present, flight dict keys, total price fields) — PASS via case tests.
- Live **L1** (approved session with fresh reese84): OAuth 200 → air-bounds 200; BKK→CNX sample date produced 13 priced bounds including PG215 08:00–09:20 PGPROMO 2630 THB; cheapest total matched parse — PASS.
- Live **L2** (in progress, 2026-07-23 project work):
  - **Done**: challenge script discovery; iv8 host-function capture (`page.load` / `eventLoop.*` / `data.pyHttp` — note `var host=__iv8__` loses the object); fetch/XHR bridge; hide `window.__iv8__` from GOPN; gpc POST 200; Protection API surface (`initializeProtection`, `startInternal`, `exportToken`, interrogator).
  - **Blocked**: after gpc, no valid solution POST / token; `exportToken` times out; `scriptInterrogationCount` advances but `currentToken` stays null. Treat as environment/interrogation gap, not discover/bridge wiring.
  - **Not claimed**: L2/L3 complete in case library until solution→token→air-bounds is green on two cold sessions.
- Layout lesson: dynamic evidence only under `projectRoot/js_reverse_cache/**`; no OS temp as primary storage; on-demand cache namespaces only.

### iv8 host binding quirk (critical for L2)

```text
typeof __iv8__            // may report undefined-ish behavior
!!__iv8__                 // false
var host = __iv8__        // loses object (host becomes useless)
__iv8__.page.load         // works
const load = __iv8__.page.load  // capture functions only
```

## Diagnostics: token/cookie present but still blocked

When OAuth works but air-bounds returns challenge HTML / 403 with `SWJIYLWA`:

1. Refresh `reese84` (export new browser state to `js_reverse_cache/private/`, do not reuse OS temp as only copy).
2. Confirm `x-d-token` equals current reese84 value on API host.
3. Align UA + Client-Hints + curl_cffi impersonate generation.
4. If interstitial/UTMVC markers appear, run UTMVC path before treating signer as broken.
5. Invalid `commercialFareFamilies` yields JSON error 36917 (not the same as Imperva 403 HTML).

## Dependencies

- python >= 3.11
- `curl_cffi` (TLS profile chrome-family matching UA)
- optional `iv8` when solving Reese challenge offline
- optional `loguru` (logger helper falls back to print)

## Invalidation Signals

- Challenge path or solution envelope field names change.
- API host or `/v2/search/air-bounds` path moves.
- Fare family codes for the market change (PGPROMO rejected).
- Imperva hard-blocks without cookie issuance (error 15 persistent).
- OAuth client_id/secret rotation (public SPA values; still treat as live-pulled secrets).

## Sensitive Materials Intentionally Excluded

- Raw `reese84` / incap / nlbi values
- OAuth `access_token` and client_secret values in committed fixtures
- Full browser_state.json / HAR / private response bodies
- Absolute local paths
