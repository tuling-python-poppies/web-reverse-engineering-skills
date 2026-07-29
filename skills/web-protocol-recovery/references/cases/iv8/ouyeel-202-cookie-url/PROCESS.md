# Ouyeel 202 Cookie URL Reverse Process

Historical process evidence only. This case has no active implementation; code
declared by `case.json.historicalReferences` is study-only and requires fresh
current-target verification.

## Goal

Handle an HTTP 202 challenge by manually executing inline and external scripts in iv8, then capture the protected URL suffix from XHR and replay the API.

## Browser Findings

- The first business POST may return HTTP 202 with challenge HTML.
- The challenge page contains inline scripts and external JS that must execute in a specific order.
- The runtime writes a cookie and hooks XHR URL generation.

## Reconstruction Steps

1. POST the target business API.
2. If status is 202, save the challenge HTML.
3. Parse inline scripts and external script URLs from the HTML.
4. Seed a minimal DOM via `document.documentElement.innerHTML`.
5. Eval inline/external scripts in the same order used by the browser page.
6. Dispatch a `load` event when the page runtime expects it.
7. Create the target XHR inside iv8.
8. Read the final suffixed URL from `__iv8__.netLog.entries`.
9. Read `document.cookie` and replay the API with Python.

## Important Details

- This case intentionally does not use `page.load`; it preserves a manual eval order discovered from the challenge page.
- Do not skip the load event if the page runtime registers load handlers.
- Runtime HTML/JS belongs in the current workspace `js_reverse_cache/`.
