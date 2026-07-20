# Zhipin Stoken Reverse Process

Read this before using this case's `entry.py`.

## Goal

Handle Boss Zhipin anti-bot token generation where an API response returns `seed`, `name`, and `ts`, and browser JS computes `__zp_stoken__`.

## Browser Findings

- The business API can return a challenge response with `code=37`.
- The response includes fields needed to download a security JS file.
- The token is computed by `new window.ABC().z(seed, ts)`.
- In the validated workspace reproduction, the first retry only succeeded after replacing the stale `__zp_stoken__` cookie in the same session jar instead of adding a second value.

## Reconstruction Steps

1. Request the target API.
2. Detect challenge response and parse `seed`, `name`, and `ts`.
3. Download `security-js/{name}.js`.
4. Build a `security-check.html?...` location environment in iv8.
5. Provide any required canvas/fingerprint fields.
6. Load a small HTML snapshot with the security JS via `page.load`.
7. Call `encodeURIComponent((new window.ABC).z(seed, ts))`.
8. Replace the existing `__zp_stoken__`, `__zp_sseed__`, `__zp_sname__`, and `__zp_sts__` values in the same session cookie jar.
9. Retry the original API with the same `requests.Session`.

## Important Details

- Keep seed/name/ts from the same challenge response.
- Do not mix an old token with a new challenge.
- Canvas fingerprint patches should be minimal and target-specific.
- When a stale token already exists, clear or overwrite by cookie name before retrying.
