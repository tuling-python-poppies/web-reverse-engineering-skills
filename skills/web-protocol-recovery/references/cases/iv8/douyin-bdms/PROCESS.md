# Douyin BDMS Reverse Process

Historical process evidence only. This case has no active implementation; code
declared by `case.json.historicalReferences` is study-only and requires fresh
current-target verification.

## Goal

Initialize Douyin/ByteDance BDMS in iv8, trigger a protected XHR, read the rewritten URL from `netLog`, and replay with Python HTTP.

## Browser Findings

- The SDK mutates outgoing XHR/fetch rather than exposing a clean `sign()` function.
- A BDMS runtime bundle can be initialized with target path configuration.
- The final rewritten URL is visible from iv8 network logging.

## Reconstruction Steps

1. Load the frozen BDMS runtime JS.
2. Create a Douyin page-like `location`, `navigator`, and `window` environment.
3. Patch `MessageChannel` with `__iv8__.wrapNative` when required.
4. Eval the BDMS JS.
5. Call `window.bdms.init(...)` with target path config.
6. Create an XHR for the protected API URL in iv8.
7. Read the final URL, headers, and cookie metadata from `__iv8__.netLog.entries`.
8. Send the captured request with Python.

## Important Details

- Use `netLog` output as the source of truth.
- Do not reimplement the URL mutation if the runtime hook already produces it.
- Keep runtime initialization config consistent with the target endpoint.
