# Tencent TDC Slider Reverse Process

Read this before using this case's `entry.py`.

## Goal

Collect Tencent TDC behavior telemetry in iv8 using trusted pointer/mouse events, solve supporting POW/image steps in Python, and submit verification.

## Browser Findings

- The challenge response provides session identifiers, TDC JS path, POW parameters, and image resources.
- The target telemetry depends on trusted input events, not only synthetic JavaScript calls.
- TDC exposes data through `window.TDC.getData(true)` and related APIs.

## Reconstruction Steps

1. Request the CAPTCHA prehandle endpoint.
2. Extract `sess`, `sid`, TDC JS URL, POW params, image URLs, and slider config.
3. Download images and compute the slider gap with ddddocr（优先）or OpenCV（回退）.
4. Solve POW in Python.
5. Build a realistic drag trajectory.
6. Load TDC JS in iv8.
7. Expose trajectory and constants with `ctx.expose(...)`.
8. Dispatch trusted pointer/mouse events through `__iv8__.input`.
9. Sleep/advance logical time between movement points.
10. Read `collect` and `eks`, then submit verification with Python.

## Important Details

- Use iv8 trusted input APIs; plain `element.dispatchEvent` is not equivalent.
- Keep trajectory timing plausible.
- Do not store images or full challenge responses as bundled assets unless sanitized and necessary.
