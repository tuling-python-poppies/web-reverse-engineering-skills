# CHNG Ruishu Announcement Reverse Process

Read this before using this case's `entry.py`.

## Goal

Reproduce the Huaneng Electronic Commerce announcement API protected by a Ruishu-style `412` challenge, then trigger the protected announcement XHR inside iv8 to capture the dynamic `kbfJdf1e` URL suffix for Python replay.

## Browser And Network Findings

- Direct requests to `https://ec.chng.com.cn/channel/home/#/purchase?top=0` or the announcement API return `412` challenge HTML.
- The challenge response sets `S6J51OuUjLieO` and contains `$_ts.nsd`, `$_ts.cd`, and an `r="m"` protection script under `/H9Ml1X1DHajj/...js`.
- Loading the first challenge snapshot in iv8 emits `S6J51OuUjLieP` and keeps a valid page URL such as `https://ec.chng.com.cn/channel/home/?SlJfApAfmEBp=<timestamp>#/purchase?top=0`.
- A second page request with the stage-1 cookie returns the Vue app HTML and another Ruishu runtime script under `/H9Ml1X1DHajj/...js`.
- The business app scripts are `type="module"` and are not needed for this reproduction; the Ruishu runtime is enough to hook an iv8-created XHR.
- The target API body is JSON, not the home-page recommendation body. The verified shape is `{"start":10,"limit":10,"type":"103","search":"","ifend":""}`.
- Pagination uses offset semantics: first page `start=0`, second page `start=10`, third page `start=20` when `limit=10`.
- The useful output is the rewritten URL containing `?kbfJdf1e=...` plus the current `S6J51OuUjLieO/P` cookie header from `__iv8__.netLog.entries`.

## Reconstruction Steps

1. Build a browser-like environment for `https://ec.chng.com.cn/channel/home/?SlJfApAfmEBp=<timestamp>#/purchase?top=0`.
2. Request the page with one `requests.Session` and save the `412` challenge HTML into runtime `js_reverse_cache/`.
3. Extract the external `r="m"` protection script URL, download it with the same session, and save it into runtime `js_reverse_cache/`.
4. Load `{baseURL, html, headers, resources}` into iv8 through `window.__iv8__.page.load(...)` and advance the event loop.
5. Read `document.cookie` or the last `netLog` `cookieHeader`; merge `S6J51OuUjLieO/P` into the same Python session.
6. Request the page again with the stage-1 cookie, extract the second Ruishu script, and load this second snapshot into the same iv8 context.
7. For each offset, build the exact compact JSON body with `start`, `limit`, `type`, `search`, and `ifend`.
8. Create a `POST` `XMLHttpRequest` inside iv8 for `queryAnnouncementByTitle`; set `Accept`, `Content-Type: application/json`, and `X-Requested-With` headers.
9. Read the matching `queryAnnouncementByTitle` entry from `window.__iv8__.netLog.entries` and use its `url`, optional `headers`, and `cookieHeader`.
10. Replay the real POST request with Python `requests`, exact body bytes, captured URL suffix, and captured cookie header.

## Important Details

- Do not reuse an old `kbfJdf1e` value. Generate it by creating the XHR in iv8 for the current request body and cookie state.
- Keep the challenge stages and final replay in one `requests.Session`; merge each captured cookie header back into the session.
- Preserve JSON serialization with compact separators so the body used by the XHR hook and the Python replay are identical.
- `START_OFFSET` is an offset, not a page number. Use `0, 10, 20...` for `PAGE_SIZE = 10`.
- Keep TLS verification enabled. If an enterprise interceptor or incomplete chain is present, configure an explicit trusted CA bundle or approved route-scoped transport profile rather than disabling verification.
- Runtime challenge HTML, Ruishu JS, iv8 stage results, and XHR entries are saved under the current workspace `js_reverse_cache/`. No full business response JSON is saved by default.

## Verification Snapshot

- The workspace reproduction generated non-empty `S6J51OuUjLieO/P` cookies.
- iv8 captured a non-empty `queryAnnouncementByTitle?kbfJdf1e=...` URL.
- A live replay for `type=103`, `start=10`, `limit=10` returned HTTP `200` with JSON containing `"start": 10`, `"limit": 10`, and announcement rows whose `announcementType` is `103`.
