# Customs Ruishu Reverse Process

Historical process evidence only. This case has no active implementation; code
declared by `case.json.historicalReferences` is study-only and requires fresh
current-target verification.

## Goal

Reproduce a customs-site Ruishu-style two-stage cookie flow and capture both final URL and modified headers for JSON POST replay.

## Browser Findings

- The runtime follows the same staged challenge pattern as other Ruishu-style pages.
- The final XHR hook may modify headers as well as URL.
- Body serialization must remain exactly the same between iv8 capture and Python replay.

## Reconstruction Steps

1. Request the protected page and capture challenge HTML.
2. Extract and download the first protection script.
3. Load the snapshot in iv8 and wait for cookie generation.
4. Merge the generated cookie into the session.
5. Request the protected page again and load the second-stage runtime.
6. Trigger the target API XHR in iv8 with the exact JSON body string.
7. Read `entry.url`, `entry.headers`, `entry.cookieHeader`, and body metadata from `__iv8__.netLog.entries`.
8. Replay the request in Python with captured URL, captured headers, cookie header, and exact body bytes.

## Important Details

- Header casing and body bytes can matter; avoid reserializing JSON differently.
- Replay should use the captured hook output, not a guessed URL.
- Keep all downloaded challenge materials in runtime `js_reverse_cache/`.
