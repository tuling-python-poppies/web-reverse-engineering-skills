# NMPA MD5 Cookie Reverse Process

Read this before using this case's `entry.py`.

## Goal

Combine a Python-computable business MD5 header sign with a JavaScript challenge cookie generated in iv8 when the API is blocked.

## Browser Findings

- The business API sign is deterministic and can be reproduced with sorted params, URL encoding, timestamp, and MD5.
- When blocked, the response page contains challenge HTML and a protection script reference.
- The challenge script writes a cookie that must be reused in the same request session.

## Reconstruction Steps

1. Build API params and timestamp in Python.
2. Compute the MD5 sign header in Python.
3. Request the API with a single `requests.Session`.
4. If the response is not successful, save the challenge HTML to runtime `js_reverse_cache/`.
5. Extract the protection script URL from the challenge page.
6. Download the protection script with the same session and headers.
7. Load a `{baseURL, html, headers, resources}` snapshot into iv8 via `__iv8__.page.load`.
8. Advance the event loop and read `document.cookie`.
9. Merge the cookie into the same session and retry the original signed request.

## Important Details

- Do not recompute the business sign with a different timestamp during retry unless the target requires it.
- Challenge JS and HTML are runtime materials and belong in the current workspace `js_reverse_cache/`.
- The reusable pattern is “simple Python sign plus browser-generated challenge cookie”.
