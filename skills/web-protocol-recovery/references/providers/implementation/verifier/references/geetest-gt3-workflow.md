# Geetest GT3 Slide Workflow

Use this reference for classic Geetest GT3 slide challenges, especially pages that load `gt.js`, call `register-slide`, then use `fullpage.9.x` and `slide.7.x`.

## Recognition Signals

- Demo or business endpoint returns `gt`, `challenge`, and `new_captcha`.
- Loader calls `apiv6.geetest.com/gettype.php`.
- `gettype.php` returns `type: fullpage`, `fullpage.9.x`, `slide.7.x`, and `geetest.6.x`.
- The chain contains JSONP requests to `/get.php` and `/ajax.php`.
- Final slide request uses `$_BCm=0`, `client_type=web`, and a long `w`.
- Slide data contains `bg`, `fullbg`, `slice`, `c`, `s`, `ypos`, and challenge suffixes such as `...lc`, `...av`, or similar.

Do not treat this as GT4. GT3 has no `lot_number`, `process_token`, `pow_detail`, `pow_msg`, or `/gcaptcha4.geetest.com/load` flow.

## Verified Request Chain

1. `GET business/register-slide?t=<ms>`
   - Returns `gt`, base `challenge`, `new_captcha`.
2. `GET https://apiv6.geetest.com/gettype.php?gt=<gt>&callback=<jsonp>`
   - Confirms GT3 assets and type.
3. `GET https://apiv6.geetest.com/get.php`
   - Params: `gt`, base `challenge`, `lang`, `pt=0`, `client_type=web`, `w`, `callback`.
   - `w` is produced by `fullpage.9.x`.
   - Response returns fullpage config including first-round `c`, `s`, `api_server`.
4. `GET https://api.geevisit.com/ajax.php`
   - Params: `gt`, base `challenge`, `lang`, `pt=0`, `client_type=web`, `w`, `callback`.
   - This is the pre-radar click/check phase.
   - Response must be `{"status":"success","data":{"result":"slide"}}`.
5. `GET https://api.geevisit.com/get.php?is_next=true&type=slide3...`
   - Use the same base challenge.
   - Returns slide `challenge`, `bg`, `fullbg`, `slice`, second-round `c`, `s`, and `gct_path`.
6. `GET https://api.geevisit.com/ajax.php`
   - Params: `gt`, slide `challenge`, `lang`, `$_BCm=0`, `client_type=web`, final `w`, `callback`.
   - Success shape: `{"success":1,"message":"success","validate":"...","score":"1"}`.
7. Business validation usually posts:
   - `geetest_challenge=<slide_challenge>`
   - `geetest_validate=<validate>`
   - `geetest_seccode=<validate>|jordan`

## Fast Reproduction Path

Before reverse-engineering `fullpage.9.x` or `slide.7.x` from scratch, check the workspace and nearby project folders for an already working GT3 workbench. Search for these files first:

- `main.py` with `compat-flow`
- `gt3_protocol.py`
- `gt3_fullpage_helper.js`
- `gt3_current_helper.js`
- `gt3_w_helper.js`
- `cache/fullpage.9.2.0-guwyxh.js`
- `cache/slide.7.9.3.js`
- `cache/gct.b71a9027509bc6bcfef9fc6a196424f5.js`
- `cache/manual_points_success.json`

If a nearby project is known to be passing, prefer copying/adapting that workbench instead of rediscovering the SDK state machine. A proven layout is:

- `main.py compat-flow`: CLI wrapper that runs the full browser-free flow.
- `gt3_protocol.py`: Python `requests` chain, image restore, distance, trace selection, final submit, and demo business replay.
- `gt3_fullpage_helper.js`: local Node VM wrapper around raw `fullpage.9.2.0-guwyxh.js`, patched at `function j(e,t,n){...}` to capture `/get.php` and `/ajax.php` params and export `aeskey`.
- `gt3_current_helper.js`: local Node VM wrapper around raw `slide.7.9.3.js`, patched near `Y[$_CJEB(420)](window,oe);` to export internals such as `W`, `H`, `X`, `V`, `m`, `yt`, `bt`, and `U`.
- `cache/old_gt3_1.js`: optional legacy final helper for comparison only; prefer current raw `slide.7.9.3.js` helper when available.

Run the proven path first:

```bash
python main.py compat-flow
```

Passing evidence should include:

- `pre /ajax.php result: {"status":"success","data":{"result":"slide"}}`
- `final /ajax.php captcha result: {"success":1,"message":"success","validate":"..."}`
- business replay `demo_validate.status == "success"`
- `cache/latest_round.json` or equivalent containing `initial_w_len`, `pre_w_len`, `slide_get`, `distance`, `w_payload`, `final`, and business response.

This shortcut is especially important when the user says a sibling folder is already running. Do not spend time re-probing SDK globals until the reusable workbench has been inspected.

## Fullpage w Recovery

Patch the fullpage script in a local VM rather than driving a browser:

1. Intercept the internal JSONP request function, commonly shaped like `function j(e,t,n){...}`.
2. Capture `path`, params, and the config object.
3. Export the fullpage core/inner object if needed, for example by patching the assignment that creates `new nt(t)`.
4. Generate initial `/get.php` `w`.
5. Preserve the generated `aeskey` from the same fullpage config.
6. Generate pre `/ajax.php` `w` with the same `aeskey` and the real initial `/get.php` response.

The most important pitfall: do not generate initial `w` and pre-radar `w` in unrelated JS instances without carrying the `aeskey`. The server may return `param decrypt error` because pre-radar `w` depends on the same fullpage encryption session established by initial `w`.

If the raw SDK state machine is slow to drive, use the faster proven patch pattern from `gt3_fullpage_helper.js`: replace the internal `function j(e,t,n){` with a stub that pushes `{path, params, cfgKeys, aeskey}` into `window.__gt3FullpageRequests` and resolves mocked responses. Then instantiate `new window.Geetest(buildConfig(input))`. For pre-radar, call the exported core method observed as `core.$_CDIJ()` after `window.__gt3Core` is captured from the `new nt(t)` assignment. This avoids trying to simulate all asynchronous JSONP script loading and DOM events.

Useful environment patches observed for Node VM:

- `window.parseInt`, `parseFloat`, `isNaN`
- `encodeURIComponent`, `decodeURIComponent`, `encodeURI`, `decodeURI`
- `navigator`, `screen`, `location`, `performance.timing`
- Minimal `document`, `body`, `head`, `documentElement`, `createElement`, event methods, and `getBoundingClientRect`

Suppress asynchronous SDK console noise inside the VM, but keep the helper's stdout as strict JSON.

## Slide w Recovery

Use the current `slide.7.x` asset, not an old decoded or hand-edited copy. Patch it only enough to export internals.

Important payload fields:

- `lang`
- `userresponse`
- `passtime`
- `imgload`
- `aa`
- `ep`
- dynamic gct field such as `h9s9`
- `rp = md5(gt + challenge.slice(0, 32) + passtime)`

Observed current behavior:

- `ep.v` should match the slide script version, for example `7.9.3`, not the slide response `version: 6.0.9`.
- `gct_path` may append a dynamic field. Load the returned gct script locally when reproducing final `w`.
- `aa` is generated from trace compression and then mixed with the current round `c` and `s`.
- Final `w` success is sensitive to the slide challenge, second-round `c/s`, distance, `passtime`, `aa`, and `ep` being from the same round.

For current `slide.7.9.3.js`, the fastest stable route is to export internals rather than hand-port the algorithm:

- Patch the raw current slide asset at `Y[$_CJEB(420)](window,oe);` to assign `window.__gt3Internals={W,H,X,V,m,yt,bt,Y,oe,re,U}` before the original statement.
- Compute `userresponse` with `H(distance, challenge)`.
- Compute `aa` using `new W(trace[0])`, repeated `$_BBDu(point)`, then `$_BBEl(tracker.$_FDd(), c, s)`.
- Build `ep` with `v: "7.9.3"`, `$_BIT: false`, `me: true`, refreshed `tm`, and `td: -1`.
- Load current `gct_path` and apply `_gct` to inject dynamic fields such as `h9s9`.
- Compute `rp` as `X(gt + challenge.slice(0, 32) + passtime)`.
- Encrypt JSON payload with current internals: `V.encrypt(plain, key)`, pack with `m.$_FEu` or `m.$_GFm`, append RSA tail from `new U().encrypt(key)`, retry key until RSA tail length is `256`.

Manual trace templates can make final acceptance much faster. If `manual_points_success.json` or equivalent exists, scale its points to the current distance and refresh `ep.tm`; this often passes faster than fully synthetic traces. In one confirmed pure-protocol run, `motion_source` was `manual_points_success.json`, `final.success == 1`, and business `validate-slide` returned success.

## Image And Distance

Classic GT3 uses a 52-piece scrambled background:

```python
SLICE_POSITIONS = [
    39, 38, 48, 49, 41, 40, 46, 47, 35, 34, 50, 51, 33, 32, 28, 29, 27, 26,
    36, 37, 31, 30, 44, 45, 43, 42, 12, 13, 23, 22, 14, 15, 21, 20, 8, 9,
    25, 24, 6, 7, 3, 2, 0, 1, 11, 10, 4, 5, 19, 18, 16, 17,
]
```

Restore by cropping each 10x80 visible tile from source positions and pasting to a 260x160 image. Then compare restored `bg` and `fullbg` with `ddddocr.slide_comparison` or OpenCV. In one working implementation the submitted distance was `target_x - 6`.

## Manual Trace Capture

For reconnaissance, a good route is to inject observation hooks and let the user slide manually. Capture:

- final request URL and response
- plaintext payload before encryption if possible
- raw points, `aa`, `passtime`, `imgload`, `ep`
- slide round `gt`, challenge, `c`, `s`

Manual traces are useful as templates, but scale them to the current distance and refresh absolute `ep.tm` timestamps. Do not reuse old `w`, old challenge, old `c/s`, or old cookies across rounds.

## Pure Protocol Delivery Pattern

Final runtime can be:

- Python `requests` for all HTTP.
- PIL + `ddddocr` or OpenCV for image restore and distance.
- Small local Node helpers for current fullpage and slide `w` generation.

Do not use Selenium, Playwright, CDP, or an open browser in final runtime.

Recommended file layout for a GT3 deliverable:

- `main.py`: command entry, defaulting to `compat-flow` if possible.
- `gt3_protocol.py`: HTTP/session orchestration and verification evidence.
- `gt3_fullpage_helper.js`: initial/pre-radar `w` helper.
- `gt3_current_helper.js`: current slide final `w` helper.
- `gt3_w_helper.js`: optional legacy comparison helper.
- `cache/`: raw current GT3 JS assets, `gct` script, optional manual trace template, and `latest_round.json`.

Log these values during verification:

- initial `/get.php` status, first `s`, `c`
- pre `/ajax.php` result and pre `w` length
- slide challenge, second `s`, `c`, image paths
- detected distance, `passtime`, trace length, `aa` length
- final `/ajax.php` response including `validate`
- business validation response if present

## Troubleshooting

- Slow reproduction despite correct GT3 branch: first look for a passing sibling project or cached workbench and port its helper files. The GT3 branch is mature enough that starting with generic SDK probing is usually slower.
- `param decrypt error` at pre `/ajax.php`: carry the same `aeskey` from initial fullpage `w` generation into pre-radar `w`; also verify initial response is real and same round.
- Pre `/ajax.php` succeeds but final says `forbidden`: inspect final behavior payload, `aa`, `ep.tm`, gct field, distance, and whether slide challenge plus second-round `c/s` are used.
- Final `w` length differs significantly from browser success: compare plaintext fields first, then encryption envelope.
- Empty pre `w` compatibility paths may still return slide data on some endpoints, but can produce weaker or inconsistent server state. Prefer the real fullpage initial + pre-radar chain.
- `slide.decoded.js` or instrumented copies may be useful for reading, but final helpers should run the raw current asset.
