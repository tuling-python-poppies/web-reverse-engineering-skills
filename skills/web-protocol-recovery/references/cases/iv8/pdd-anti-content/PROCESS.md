# PDD Anti Content Reverse Process

Historical process evidence only. This case has no active implementation; code
declared by `case.json.historicalReferences` is study-only and requires fresh
current-target verification.

## Goal

Generate Pinduoduo PC `anti_content` by downloading current webpack chunks, capturing `__webpack_require__`, calling the internal obfuscated module, then replaying the goods API.

## Browser Findings

- The signing code is bundled in current Next.js / webpack chunks.
- The useful module can be required by id/name `fbeZ` after webpack runtime is initialized.
- The sign depends on a server time seed from `/api/server/_stm`.

## Reconstruction Steps

1. Request the PC category page and save the current HTML to runtime `js_reverse_cache/`.
2. Extract script URLs from the HTML.
3. Download the current webpack runtime, commons, `_app`, and page chunk scripts.
4. Request `/api/server/_stm` in the same session.
5. Create a browser-like iv8 environment with `location`, `navigator`, `screen`, and `window` fields.
6. Eval the downloaded chunks in iv8 in page order.
7. Push a small capture chunk into `window.webpackJsonp` to expose `__webpack_require__`.
8. Require module `fbeZ` and call `new fbeZ({serverTime}).messagePackSync()`.
9. Drain microtasks/timers and read the `anti_content` string.
10. Attach it to API params and send the real goods API request.

## Important Details

- This case intentionally rediscovers chunk URLs at runtime because hashes change.
- Rebuild `anti_content` per page/request when payload or server time changes.
- Do not copy live downloaded chunks into the skill unless creating an explicit bundled case. Sanitize values by default; retain raw values only after explicit confirmation of fields and private storage.
