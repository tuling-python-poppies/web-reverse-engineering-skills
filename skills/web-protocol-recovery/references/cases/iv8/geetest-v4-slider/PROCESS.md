# Geetest v4 Slider Reverse Process

Read this before using this case's `entry.py`.

## Case Identity

Do not select a CAPTCHA case by vendor name alone.

| Field | Value |
| --- | --- |
| Provider | Geetest |
| Product version | v4 |
| CAPTCHA type | 滑块 |
| Protocol value | `slide` |
| Bootstrap page | `https://gt4.geetest.com/` |
| Load endpoint | `https://gcaptcha4.geetest.com/load` |
| Verify endpoint | `https://gcaptcha4.geetest.com/verify` |

This case is not an exact match for Geetest v3, click/点选, word/文字, icon,
invisible, one-pass, or any response whose `captcha_type` is not `slide`.

## Goal And Proven Result

The final path is browser-free at runtime: Python owns HTTP and iv8 executes the
official Geetest JavaScript needed to construct the verifier URL and encrypted
`w` parameter.

The verified proof used one `curl_cffi.requests.Session(impersonate="chrome")`,
concurrency 1, and at least 1.5 seconds between `/load` and `/verify`. The final
business response contained:

```text
status=success
data.result=success
data.fail_count=0
data.score=2
```

HTTP 200 alone is not accepted as proof.

## Fast Match Fingerprint

Before opening browser tools, send or inspect one authorized `/load` response.
Use this case directly when all of these are true:

- The target uses Geetest v4 endpoints or a compatible v4 host.
- Request `risk_type` is `slide`.
- Response `captcha_type` is `slide`.
- Response has `lot_number`, `payload`, `process_token`, and `payload_protocol`.
- Response has `bg`, `slice`, `static_path`, `js`, and `gct_path`.
- The main runtime is `.../v4/static/.../js/gcaptcha4.js`.
- The bundle still contains a verifier method matching `$_BBFs:function`.

If the network shape matches but webpack module IDs changed, keep the HTTP,
image, iv8 bootstrap, and replay path. Re-run only the bounded module search in
"Verifier Entry Discovery". Do not restart full-site analysis.

## Intake And Scope Used For The Proof

- Artifact: fresh target URLs; no initial request sample.
- Target family: verifier-gated, with signer/session secondary gates.
- Baseline: real browser environment collected during Chrome and Camoufox
  reconnaissance.
- Verification: fixed-input iv8 proof followed by one bounded live verifier
  request.
- Nearest prior case: `captcha/tencent-tdc-slider.py`, used only for CAPTCHA
  lifecycle and image-solving ideas. Tencent TDC's trusted pointer telemetry is
  not the Geetest v4 verifier design used here.

## Browser Evidence Collection

1. Open the Geetest v4 demo page in the authorized browser session.
2. Capture the `/load` request and response before solving the challenge.
3. Record the returned `static_servers`, `static_path`, `js`, `gct_path`, `bg`,
   `slice`, `lot_number`, `payload`, `process_token`, and `payload_protocol`.
4. Capture the official scripts loaded by the same page:
   - `/v4/gt4.js`
   - `/v4/static/<version>/js/gcaptcha4.js`
   - `/v4/gct/<hash>.js`
   - `/v4/static/<version>/i18n/zho.js`
5. Solve once in the browser and capture the final `/verify` request. Confirm it
   contains `captcha_id`, `client_type`, `lot_number`, `risk_type`, `payload`,
   `process_token`, `payload_protocol`, `pt`, and `w`.
6. Export the same browser/session's JS-visible `navigator`, `screen`, `window`,
   `location`, timezone, UA, request headers, and scoped cookies. These values
   form one browser baseline; do not merge fields from another engine or run.

When this work arrives from an approved web-protocol-recovery evidence chain, use the existing
Provider result. If its browser/session is still live, the evidence Provider
exports the current same-session environment. iv8 must not call its source IDs
through another MCP. If the browser is closed, consume the approved artifact-only
snapshot. Return a precise blocker when no same-origin snapshot exists and the
target depends on it.

## Runtime Roles

The four official resources have separate jobs:

- `gt4.js`: exposes `initGeetest4` and loads the challenge runtime.
- `gcaptcha4.js`: owns CAPTCHA state, verifier assembly, encryption, and dynamic
  resource loading.
- `gct4.js`: supplies current GCT fields used by the verifier.
- `zho.js`: supplies the requested language resource and completes startup.

Keep the scripts from one `/load` generation together. Do not combine a current
`gcaptcha4.js` with an unrelated historical GCT or language resource.

## Verifier Entry Discovery

The current minified bundle has two useful source anchors:

```text
loadCss:function(){
}return i[
```

Patch the webpack runtime marker only for local analysis:

```javascript
}window.__gtRequire=i;return i[
```

Then search loaded module functions for the verifier anchor:

```javascript
Object.keys(window.__gtRequire.m).filter(function(id) {
    return String(window.__gtRequire.m[id]).indexOf('$_BBFs:function') >= 0;
});
```

The verified bundle resolved the live backend through:

```javascript
var registry = window.__gtRequire(17).default;
var backend = registry.$_BEP(window.captchaObj.$_BAGF);
backend.$_BBFs(answer, callback, true);
```

The verifier implementation was associated with module 18, while module 17
provided the registry used to resolve the backend instance. Treat `17` and `18`
as version-specific evidence, not permanent API IDs. When they change:

1. Search `window.__gtRequire.m` for `$_BBFs:function`.
2. Inspect that module's exports and prototype.
3. Search loaded exports for an object exposing `$_BEP`.
4. Call `$_BEP(window.captchaObj.$_BAGF)`.
5. Confirm the returned object exposes `$_BBFs`.

This bounded search is the only source-analysis step normally needed for a new
v4 slider bundle.

## Plain Verifier Findings

A temporary analysis-only tap was inserted immediately before the function that
encrypts `w`. The assembled input contained:

- `setLeft`
- `passtime`
- `userresponse`
- POW fields
- lot/payload/process fields
- guard and device-check fields
- GCT-derived fields
- `em`, the environment summary

No separate drag trajectory array was present in the verifier plaintext for this
flow. An early trusted mouse-event probe was therefore removed from the compact
implementation. Do not import the Tencent TDC trajectory design unless a future
Geetest response or bundle proves that a telemetry array is required.

## Minimal iv8 Reconstruction

The official loader expects browser-style dynamic `<script>` and `<link>`
insertion. The minimal reconstruction does this:

1. Create `<head>`, `<body>`, and `<div id="captcha">`.
2. Add a native-looking `document.createElementNS` fallback with
   `__iv8__.wrapNative`.
3. Wrap `document.head.appendChild`.
4. For `/load?`, call the generated JSONP callback with the fresh Python `/load`
   data already exposed through `ctx.expose`.
5. For `/js/gcaptcha4.js`, `/gct/`, and `/i18n/`, eval the matching source from
   the same challenge generation.
6. Treat stylesheet load as complete. CSS has no verifier value and waiting for
   real CSS can stall the local runtime.
7. Initialize with `riskType: 'slide'`, render into `#captcha`, drain tasks, and
   allow the runtime to settle.
8. Resolve the backend and call `$_BBFs(answer, ..., true)`.
9. Capture the generated `/verify?...&w=...` URL from dynamic script insertion.
10. Invoke that generated verify JSONP callback with a local fake failure after
    capturing the URL. This closes the SDK's pending callback without sending a
    request from iv8. Python sends the real request afterward.

The final URL is accepted only when query parsing finds a non-empty `w`.

## Image And Coordinate Reconstruction

For the transparent 80x80-style slices used in the verified flow, treat the
`ddddocr` result as a versioned adapter boundary, not as a permanent API.
The 3.13 reference environment used a newer implementation that returned
`target=[center_x, center_y]`; the Python 3.9 `spider_base` environment used
`ddddocr 1.5.6`, which returned `target=[x1, y1, x2, y2]`. The old
`simple_target=False` path can also derive an empty crop from an RGBA slice.
Depending on the Pillow/OpenCV versions, this surfaces as `ValueError`,
`SystemError`, or OpenCV 4.13's assertion:

```text
ValueError: Coordinate 'lower' is less than 'upper'
cv2.error: ... (-215:Assertion failed) !_src.empty() in function 'cv::cvtColor'
```

Use the compatibility helper from the bundled case:

```python
import cv2


def match_slide_center(piece, background):
    matcher = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
    simple_target = False
    try:
        match = matcher.slide_match(piece, background, simple_target=False)
    except (ValueError, SystemError, cv2.error):
        simple_target = True
        match = matcher.slide_match(piece, background, simple_target=True)
    target = match.get("target") or []
    if len(target) >= 4:
        center_x = (float(target[0]) + float(target[2])) / 2
    elif target:
        center_x = float(target[0])
    else:
        raise RuntimeError(f"invalid slide target: {match!r}")
    match["simple_target"] = simple_target
    match["target_center_x"] = center_x
    return match, center_x

match, gap_x = match_slide_center(piece, background)
```

The required conversion after normalization is:

```python
move_distance = gap_x - piece_width / 2
scale = 0.8876 * 340 / background_width
set_left = round(move_distance * scale)
answer = {
    "setLeft": set_left,
    "passtime": random.randint(950, 1450),
    "userresponse": set_left / scale + 2,
}
```

Omitting `piece_width / 2` made repeated attempts overshoot by about 40 pixels.
For a new image format or dependency version, record the package versions and
verify whether the detector reports a left edge, center, or bounding box before
reusing this formula. A non-empty `w` only proves the iv8 signer ran; the live
acceptance gate remains `status=success` plus `data.result=success`.

## Fixed-Input Proof

Before any live verifier request, use saved public scripts and synthetic `/load`
metadata to check the local signer. The objective checks are:

- `initGeetest4` callback completed.
- No dynamic resource error was recorded.
- The generated URL host/path is the expected verify endpoint.
- Query `captcha_id` and `lot_number` match the supplied fixed input.
- Query `w` exists and is plausibly long; the verified test used `len(w) > 500`.

Fixed-input success proves runtime reconstruction, not CAPTCHA success.

## Live Replay

1. Create one `curl_cffi.requests.Session(impersonate="chrome")`.
2. Apply UA, language, and referer from the selected browser baseline.
3. Request a fresh `/load` with a fresh UUID challenge.
4. Reject the response unless `captcha_type == 'slide'`.
5. Download images and all official scripts through the same session.
6. Solve the image and build `answer`.
7. Generate the verify URL in iv8.
8. Wait until at least 1.5 seconds have elapsed since `/load`.
9. GET the generated verify URL with the same Python session.
10. Parse JSONP and require both transport and semantic success.

Stop after the first successful proof. Do not add retries, concurrency, or scale
without a separately approved request budget.

## Failure Matrix

| Symptom | Likely cause | Bounded check |
| --- | --- | --- |
| `initGeetest4` never completes | Dynamic load callback/resource order is wrong | Inspect intercepted script URLs and ensure load/gcaptcha/GCT/language callbacks run |
| Runtime waits forever | Verify JSONP callback or CSS load remains pending | Complete CSS locally and invoke the fake verify callback after URL capture |
| `window.__gtRequire` missing | Webpack exposure marker changed | Find the current module loader return statement; patch only that marker |
| `$_BBFs` missing on module 17 | Module IDs changed | Search module sources for `$_BBFs:function`, then find the current `$_BEP` registry |
| Verify URL has no `w` | Initialization, GCT, answer, or resource chain is incomplete | Check resource error, init flag, current load data, and matching script generation |
| Python 3.9 raises `lower < upper` or OpenCV reports `!_src.empty()` in `slide_match` | Old `ddddocr` RGBA crop path produced invalid or empty bounds | Record dependency versions; catch `ValueError`, `SystemError`, and `cv2.error`, then use `simple_target=True` plus target-shape normalization |
| Python 3.9 returns HTTP 200 / result fail after no exception | Old `target` is a bbox but code used `target[0]` as the center | Convert `[x1,y1,x2,y2]` to `(x1+x2)/2` before subtracting half the piece width |
| Script exits 0 after `data.result=fail` | Case only logged semantic fields | Raise after logging unless both transport status and business result are `success` |
| Every answer overshoots by about half a slice | OCR result is a center coordinate | Subtract `piece_width / 2` before scaling |
| HTTP 200 but verifier fails | Wrong answer, stale challenge, environment mismatch, or timing | Check semantic fields, same-session freshness, baseline, and load-to-verify delay |
| Browser evidence exists but iv8 differs | Runtime fields were mixed across engines/sessions | Rebuild from one owner-exported `browser_env.json` only |

## Reuse Decision

Use the shortest branch:

1. Exact `Geetest + v4 + slide` fingerprint and anchors match: run the bundled
   case with the current owner-exported browser baseline.
2. Network fingerprint matches but module IDs differ: redo only the bounded
   `$_BBFs`/`$_BEP` search.
3. Static path or verifier fields changed but `captcha_type=slide`: capture one
   new fixed-input vector, update the smallest failing patch, and keep the rest.
4. CAPTCHA type or Geetest generation differs: do not claim this is an exact
   case match; select or create a separately labeled case.
5. No trusted entry or same-origin browser artifact: return precise missing
   evidence instead of guessing in iv8.

## Bundled Implementation

The compact implementation is
This case's `entry.py` intentionally downloads
current official scripts into the caller's workspace `js_reverse_cache/` rather
than freezing versioned Geetest bundles inside the skill. Public demo endpoints
and the public demo CAPTCHA ID are retained; transient lot numbers, pass tokens,
verify URLs, and response payloads are not bundled.
