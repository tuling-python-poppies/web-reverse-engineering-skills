# T'way Live Delivery Contract

This file is the from-zero live assembly contract for the T'way case. `entry.py`
remains offline-only by design; it proves the iv8 bridge without making network
requests. A live work order must assemble a project-local delivery entry that
implements the contract below.

## Required Project Shape

```text
<project-root>/
  main.py
  分析报告.md
  utils/logger.py
  utils/exit_selector.py       # optional when Mihomo is available
  tests/
  js_reverse_cache/
```

The live entry owns Python HTTP and cookies. The iv8 worker only runs the current
collector and sends XHR intent to the parent. Do not ship browser-page fetch or CDP
as the delivery path.

## Configuration Defaults

- `BASE_URL=https://www.twayair.com`
- `NETFUNNEL_BASE_URL=https://csnf.trinityairways.com`
- default TLS/UA tuple: the highest current profile supported by the installed
  `curl_cffi` build; the verified source run used `chrome146` with matching UA and
  Client Hints
- default one-way query: `ICN -> KIX`, host date plus seven days
- overrides: `AKAMAI_PROXY`, `AKAMAI_DEPARTURE`, `AKAMAI_ARRIVAL`,
  `AKAMAI_FLIGHT_DATE=YYYY-MM-DD`
- use the coherent fingerprint set captured for the runtime; override WebGL only
  after recapturing canvas, colors and WebGL together

Never hardcode rotating Cookie values, NetFunnel tickets, collector URLs, `bm_s`,
`bm_sc`, `SESSION`, or browser-export state.

## Required Live Order

1. `GET /` and parse the current random collector and optional Pixel script.
2. NetFunnel `5101` enter for `H_LandingPage`; retain its ticket in memory.
3. Load the collector bootstrap and the current `?v=` plus generated/derived `t`
   form; load `/akam/13/<id>` only when declared by the current HTML.
4. Run the landing iv8 worker. Parent forwards only same-origin collector/Pixel XHR,
   injects response bytes and visible Cookie transitions, and keeps the event loop
   alive after the first POST.
5. Complete the NetFunnel ticket with `5004` before requesting `/app/main`.
6. Classify `/app/main`:
   - full page around 1 MB: skip challenge-only Cookie assertions and continue;
   - challenge/degraded page around 2.6 KB: run its collector, merge response Cookies,
     then request `/app/main` again.
7. Run the main collector branch and accept a stage-dependent POST count. One main
   POST is valid on the trusted branch; do not require three universally.
8. Build the final OW form body, including the ten empty airport-name fields and the
   click-time fields `gaLocation`, repeated `pax`, `deptAirportCode`,
   `arriAirportCode`, and `schedule`.
9. Send synchronous `GET /ajax/booking/chkSaleRoute` with that exact serialized form.
   Explicit `success:false` stops the route; Access Denied is an exit-admission
   failure; a missing `success` key is unknown and must not be coerced to false.
10. Send `POST /app/booking/chooseItinerary`, classify the response as business HTML
    or SBSD/privacy shell, then send `POST /app/booking/layerAvailabilityList` with
    the CSRF from the choose response.
11. Parse non-empty flight/fare objects. HTTP 200 alone is not acceptance.

## Node Rotation

Exit admission is node-scoped. When Mihomo exposes `-ext-ctl-pipe`, discover that
named pipe from the `mihomo.exe` command line; do not assume a TCP controller port.
Probe candidates with `GET /` and `GET /app/main`, or rotate directly from the live
collector on these admission failures:

- landing transport/TLS failure after bounded retries;
- landing or `/app/main` Access Denied;
- `chkSaleRoute` Access Denied;
- `chooseItinerary` Access Denied.

Use a distinct `ExitAdmissionError`. CSRF, parser, inventory and protocol-shape
errors must not rotate nodes. Cap both node attempts and the process-wide live
request budget; each TLS retry consumes one request and failed requests are never
refunded. Leave the successful node selected.

## Acceptance

Accept only after:

- Landing and main sensor requests complete with response Cookie continuity;
- `chkSaleRoute`, `chooseItinerary` and `layerAvailabilityList` are all 200;
- parsed tickets/fare objects are non-empty;
- the same node repeats successfully and a changed date changes the result or body;
- all volatile evidence stays under `js_reverse_cache/` and no raw Cookie/ticket/body
  is promoted into the case library.

The current source delivery reached five ICN-KIX flights and a 73,400 KRW minimum
fare, then repeated on another date with a different fare. This is current source
acceptance for the contract; it does not promise that every future exit admits the
business routes.
