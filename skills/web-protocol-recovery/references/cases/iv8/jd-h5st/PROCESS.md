# JD H5st Reverse Process

Read this before using this case's `entry.py`.

## Goal

Reproduce JD mobile `h5st` signing in iv8 using a frozen page DOM and signing bundle, then replay the API request with Python HTTP.

## Browser Findings

- The target API accepts an `h5st` query parameter.
- The page-side signing object is `window.ParamsSignMain`.
- The signing bundle expects browser-like DOM and timer APIs.
- The original page DOM influences the runtime enough that a frozen HTML snapshot is useful.

## Reconstruction Steps

1. Save the JD mobile page HTML as `jd_index.html`.
2. Save the signing bundle as `js_security_v3_main.js`.
3. Create an iv8 context with a JD mobile-like `location`.
4. Patch `MessageChannel` with `__iv8__.wrapNative` because the bundle checks native-like async APIs.
5. Seed `document.documentElement.innerHTML` with the frozen page HTML.
6. Eval the signing bundle with a useful source name.
7. Build API params and hash the request body in Python.
8. Call `new window.ParamsSignMain({appId})._$sdnmd(...).h5st` in iv8.
9. Attach `h5st` to query params and send the real request.

## Important Details

- Keep request body serialization identical before hashing.
- Keep `MessageChannel` patch local to this case; do not add it to unrelated scripts unless needed.
- Frozen assets are declared under this case's `assets/` directory.
