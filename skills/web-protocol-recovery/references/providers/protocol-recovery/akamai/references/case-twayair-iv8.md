# Case: T'way (`www.twayair.com`) IV8 protocol

Live-verified pure-protocol shape for a modern Akamai deployment that leans on
`bm_*` cookies rather than classic `_abck` / `bm_sz`.

Status: business acceptance reached (choose 200 + availability 200 + parsed fares),
reproduced three times including a date change. Keep **generic** lessons here; keep
day-to-day runbook in the task project doc under the assigned project root.

## Evidence surfaces

- Random-path collector script on the origin (path rotates every session; role stable)
- Sensor POST to that same random path, `application/json`, body roughly 4.5–4.9 KB
- Pixel branch: `/akam/13/<id>` script plus `POST /akam/13/pixel_<id>`, body ~3.7 KB
- Cookies: `ak_bmsc`, `bm_s`, `bm_so`, `bm_ss`, `bm_sv`, `bm_mi`, `bm_lso`, `bm_sc`
- Business gate: `POST /app/booking/chooseItinerary` can be denied while the homepage,
  `/app/main` and the collector are all 200
- Coexisting non-Akamai queue: NetFunnel `ts.wseq`. The legacy `csnf.` host on the
  airline domain serves a certificate valid only for the operator's other domain;
  use the certificate-covered alias, not the airline-domain hostname.

## Verified architecture

```text
Python curl_cffi session (owns every real request and the cookie jar)
  -> GET /
  -> GET /js/lib/netfunnel.js
  -> NetFunnel enter (queue ticket)
  -> GET collector bootstrap, then GET collector with ?v=&t=
  -> GET /akam/13/<id> when the page declares it
  -> iv8 sensor stage (pixel POST then collector POST)
  -> NetFunnel complete            <-- before the document request, not after
  -> GET /app/main
  -> iv8 sensor stage on the main page
  -> GET /ajax/booking/chkSaleRoute with the full serialized form
  -> POST /app/booking/chooseItinerary
  -> POST /app/booking/layerAvailabilityList
  -> parse fares
```

IV8 only executes the live collector and emits XHR intent through a bridge.

### NetFunnel ordering

The accepted browser flow completes the queue ticket **before** requesting the
document gate. Completing after a 200 response leaves a fresh session on the wrong
queue state. Each ticket is completed exactly once; a retry acquires a new ticket.

### `chkSaleRoute` is not optional

The page runs a synchronous `GET /ajax/booking/chkSaleRoute` with `frm.serialize()`
immediately before submit, and aborts the submit when the JSON says the route is not
on sale. Omitting this request makes the submit sequence diverge from the accepted
flow. Mirror the abort: treat an explicit `success: false` as "pick another route or
date", not as a protocol failure. A response without the key at all is not a stop
signal — do not let a defensive default turn an unknown shape into a hard abort.

## Form wire contract

Reproduce the **final serialized body**, not the static HTML controls. For a one-way
search the live form emits, in order:

1. `_csrf`, `searchDate` (today as `MMdd`), `promoCode`, `cmpIndDiv`,
   `defaultPromoCode`, `bookingTicket`, `tripType`, `bookingType`,
   `promoCodeDetails.promoCode`, `validPromoCode`
2. `availabilitySearches[0..4].{depAirport,arrAirport,flightDate}` — only segment 0
   is filled; segments 1..4 stay empty. Do not invent a return leg.
3. `paxCountDetails[0..2].paxCount`
4. `availabilitySearches[0..4].{depAirportName,arrAirportName}` — ten empty fields
   that the form still serializes. These are easy to miss by reading only the
   visible inputs.
5. Fields the submit handler appends at click time: `gaLocation`, `pax` repeated
   once per passenger bucket, `deptAirportCode`, `arriAirportCode`, `schedule`

`promoCode` may equal `defaultPromoCode` even when the user promo box is empty.
`chooseItinerary` is a document-navigation POST: match Accept, Origin, Referer, UA
and Client Hints. Availability is a separate XHR whose CSRF comes from the choose
response.

## Response taxonomy

| Response | Meaning |
|---|---|
| `/app/main` ~2.6 KB, 200 | challenge/degraded page; this branch mints `bm_sc` |
| `/app/main` ~1.05 MB, 200 | trusted/full business page |
| ~400–550 B Access Denied | hard edge/exit admission gate |
| ~4 KB privacy page / `sec-if-cpt-container` | SBSD soft challenge, not success |
| choose ~1 MB HTML | business document success |
| availability ~350 KB+ | fare list success |

Classify the branch before asserting stage cookies. The same URL returns different
branches depending on current state.

## `bm_sc` and the collector `t` parameter

Verified from a clean browser capture:

- The `/app/main` document response mints `bm_sc` on the challenge branch.
- `bm_sc` has the shape `<counter>~1~<tab-id>~<blob>`, and the collector URL's `?t=`
  equals that third field. So the browser **derives** `t` from `bm_sc`.
- On the trusted branch the document returns the full page directly and never mints
  `bm_sc`.

Two consequences that matter:

1. `bm_sc` is **not** required for the business submit. A run with no `bm_sc` at all,
   a single main-stage collector POST, and no main-page pixel reached choose 200 and
   availability 200. Do not treat a missing `bm_sc` as the blocker.
2. When `bm_sc` is absent, a client-generated nine-digit `t` is accepted. Only derive
   `t` from `bm_sc` when the cookie exists.

Running the landing sensor before the first `/app/main` request makes the session
trusted, so the document skips the challenge branch. That is a legitimate path, not a
defect — but it means you cannot study the `bm_sc` branch without deferring the
landing sensor.

## Transport coherence

TLS impersonation, UA major, Client Hints, sensor navigator values, language,
timezone and the proxy exit must be coherent **and current**.

Verified failure mode: downgrading the impersonation profile and the UA major
together — coherently, both to the same older Chrome — still turned
`GET /ajax/booking/chkSaleRoute` from 200 into Access Denied, while the project's
default current-Chrome pair returned `success: true` on the same exit minutes later.
The lesson is not only "keep the tuple self-consistent" but also "do not downgrade a
working profile while debugging". Pin the profile that the delivery was verified
with, and change it only as a deliberate, separately measured experiment.

## Fingerprint coherence beats fingerprint provenance

The cached canvas data URLs, system colors and WebGL vendor/renderer strings form
**one capture set**. The rule is coherence, not provenance:

- Replacing only the WebGL renderer string while keeping canvas and system colors
  from an older capture produces an incoherent set. That is worse than keeping the
  whole original set, even when the original set came from different hardware.
- If you want host-local values, recapture the whole set on the execution host in one
  pass: canvas data URLs for the sizes the collector uses, system colors, unmasked
  WebGL vendor/renderer, `hardwareConcurrency`, `deviceMemory`, screen and DPR.
- Keep one baseline. Never mix a Chrome layout sample, Firefox TLS and a third
  machine's GPU strings.

Also verify the plumbing after any fingerprint change: an override that is read in
JavaScript but never passed through the runtime bootstrap silently falls back to the
local runtime's own values, so a whole debugging session can run on values nobody
selected. Assert the value the runtime actually reports, not the value you intended.

## Exit admission is node-scoped

This target is the textbook case where implementation correctness and availability
diverge. Verified in one session with a single code build:

- One node: homepage 200, `/app/main` 200, `chkSaleRoute` 200, choose 200, fares parsed.
- A different node **in the same region**: `/app/main` 403.
- Other regions: homepage 200 but `/app/main` 403, or homepage denied outright.
- On a node where Python was denied at the submit, a real fingerprint browser driving
  the page's own submit handler was denied too — that is exit reputation, not payload.

So do not reason about regions. Probe per node.

Operational loop that works:

1. Probe candidate nodes cheaply: homepage, then `/app/main`. Any 200 on `/app/main`
   (challenge or full page) means the node admits documents.
2. Denied in a real browser on the same node -> change node; do not rewrite payloads.
3. Browser fine but protocol denied -> inspect sensor stage count, pixel, TLS/UA
   tuple, and the serialized form against a fresh capture.

Automating this inside the collector is worthwhile, with one hard requirement:
**separate admission failures from protocol failures**. Raise a distinct error type
only for landing gate, document gate, Access Denied `chkSaleRoute`, and Access Denied
business submits, and rotate
nodes only on that type. If parsing faults, missing CSRF or signature mismatches also
trigger rotation, a code defect gets laundered into "the exit was bad" and stays
hidden. Cap the total rotations and the process-wide live request count, because each
attempt otherwise starts a fresh per-client budget and multiplies real egress.

A local proxy core may expose its controller over a named pipe rather than a TCP
port, in which case port scanning finds nothing. Read the core process command line
to discover the control channel before concluding the controller is disabled.

## Sensor stage count

Browser success often emits more than one collector POST, but the count is
stage- and branch-dependent, not a protocol constant:

- Landing stage: pixel POST plus collector POST (two) on the verified path.
- Main stage on the trusted branch: a single collector POST was sufficient.
- The main page may declare no `/akam/13/` pixel at all; absence there is normal and
  is not a missing-pixel defect.

Implementation rules that still hold: do not stop the loop at the first
`postCount >= 1`; keep advancing timers and emit light pointer/scroll activity so
later stages can fire; accept 200 and 202; reset the settle window when a new POST
appears; log body sizes, since varied sizes are a good signal. Treat a target POST
count as a hypothesis to verify per stage, never as an acceptance threshold.

## Recon browser preference

1. Ordinary Chromium first for baseline request/initiator evidence.
2. A fingerprint Chromium tier when ordinary automation is transport-gated. Select it
   by binary path plus headless flag through the recon Provider's launch tool; there
   is no `browser` name argument.
3. Camoufox only when the Chromium tiers are insufficient or a recorded tool failure
   requires the fallback.
4. If automation still cannot submit the business form, drive the page's own submit
   handler in a real browser once as a positive sample and capture the request.

Never seed the final Python jar from reconnaissance cookies. Use the capture as shape
evidence only.

## Failure triage

| Symptom | Real cause | Wrong rabbit hole |
|---|---|---|
| Browser OK, script submit denied | exit reputation for non-browser or for that node | CSRF field missing |
| Same code works after node switch | exit admission | "the code regressed again" |
| Landing sensor + NetFunnel OK, `/app/main` denied | node does not admit documents | NetFunnel ticket format |
| `/app/main` 200 full page but no `bm_sc` | trusted branch; `bm_sc` is challenge-only | chasing `bm_sc` as the blocker |
| One business endpoint flips 200 -> denied after a tuple change | downgraded impersonation profile | server-side change |
| Submit body accepted in browser, rejected from script | missing serialized fields such as the empty `*AirportName` set or the click-time appended fields | sensor confidence |
| CSRF refresh reports missing on a 200 | read it from the form input or the meta tag | session dead |
| Cached fingerprint works on one machine only | canvas / system colors / WebGL bound to another capture | code regression |
| Sensor body ~4.5 KB once then stops | settle loop exits after the first POST | wrong Content-Type |
| choose 200 ~4 KB "privacy" page | SBSD soft challenge | treating it as tickets OK |
| Runtime floods `HEAD chrome-extension://...` | collector extension probe; the bridge must drop it quietly | allowlisting every path |

## Acceptance

A pure-protocol run is accepted only when all of these hold:

- landing and main sensor posts succeed and rotate `bm_s`
- `chooseItinerary` returns 200 without Access Denied and without an SBSD soft page
- availability parsing returns flight and fare objects
- the run repeats, and changing the search date changes the returned fares and body
  size (a repeated identical response can be a cached shell)
- the summary is written under the task `js_reverse_cache/` path

If success requires a specific exit node, document it as **egress-gated residual
risk** with the probe procedure, not as "implementation flaky".
