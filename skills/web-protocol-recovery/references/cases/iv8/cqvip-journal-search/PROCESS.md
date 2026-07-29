# CQVIP River Security Journal Search Reverse Process

Historical process evidence only. This case has no active implementation; code
declared by `case.json.historicalReferences` is study-only and requires fresh
current-target verification.

## Goal

Handle a CQVIP River Security / 瑞数 HTTP 412 challenge by generating S/T cookies in iv8, then replaying the journal search form POST.

## Browser Findings

- The first page request receives HTTP 412 and a challenge page.
- The response sets or implies an `S` cookie and a JS-generated `T` cookie.
- The challenge page exposes River Security markers such as `$_ts.nsd` / `$_ts.cd`, `<script r="m">`, and a dynamic `_$...()` entry.
- The final business API is a form POST returning an HTML fragment, not JSON.

## Reconstruction Steps

1. Request the search page with one `requests.Session`.
2. Save the challenge HTML and extract the protection script URL.
3. Download the script with the same session and headers.
4. Load `{baseURL, html, headers, resources}` into iv8 using `__iv8__.page.load`.
5. Advance the event loop and read generated cookies.
6. Merge S/T cookies back into the session.
7. Build `searchParamModel` with keyword, page number, and page size.
8. POST the form body to `Search/SearchList`.
9. If another challenge appears, refresh cookies once and retry.

## Important Details

- Preserve form serialization; do not send JSON unless the target API expects JSON.
- Generate fresh cookies before page requests when the server invalidates stale values.
- Print the returned HTML fragment directly; do not save response JSON by default.
