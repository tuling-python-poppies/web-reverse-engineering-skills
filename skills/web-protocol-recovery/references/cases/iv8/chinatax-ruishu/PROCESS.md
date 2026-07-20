# ChinaTax Ruishu Reverse Process

Read this before using this case's `entry.py`.

## Goal

Reproduce a Ruishu-style two-stage cookie flow, then trigger the protected XHR inside iv8 to capture a signed/suffixed URL for Python replay.

## Browser Findings

- The first protected page returns challenge HTML and a script marked with `r="m"`.
- The first script emits an intermediate cookie.
- A second protected page load with that cookie returns another script/runtime stage.
- The final API URL suffix is produced only when an XHR is created under the protected runtime.

## Reconstruction Steps

1. Request the protected page with `requests.Session`.
2. Extract the first challenge script URL and download it.
3. Load the page snapshot into iv8 via `__iv8__.page.load`.
4. Sleep logical time and read `__iv8__.netLog.entries[-1].cookieHeader` or `document.cookie`.
5. Request the page again with the first-stage cookie.
6. Extract and load the second-stage script in the same iv8 context.
7. Create the target XHR inside iv8.
8. Read the final URL and cookie/header metadata from `netLog`.
9. Replay the final POST request with Python.

## Important Details

- Preserve cookie continuity across both page stages and final replay.
- Use `page.load` when script order, cookies, and resources matter.
- The reusable pattern is “two-stage cookie then XHR-hook suffix”.
