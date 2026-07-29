# Xiaohongshu Homefeed Reverse Process

Historical process evidence only. This case has no active implementation; code
declared by `case.json.historicalReferences` is study-only and requires fresh
current-target verification.

## Goal

Rebuild the Xiaohongshu PC homefeed signing flow from a real browser session, then reproduce it in iv8 + `requests`.

This notes file records the browser-side analysis path used to reconstruct the case after the workspace cache was deleted.

## What Was Observed In The Browser

The live page at `https://www.xiaohongshu.com/explore?language=zh-CN&channel_id=homefeed.food_v3` loads these relevant script classes:

- Page chunk bundle scripts under `https://fe-static.xhscdn.com/formula-static/xhs-pc-web/public/resource/js/...`
- Security/runtime scripts under `https://as.xiaohongshu.com/api/sec/v1/ds?appId=xhs-pc-web`
- Additional `as/v1/...` and `as/v2/...` scripts that populate the anti-spam runtime

The important live globals exposed on the page are:

- `window.mnsv2`
- `window._dsf`
- `window._dsn`
- `window._dsl`
- `window._webmsxyw`
- `window.anti_hp_sign_config`

The browser also holds the page seed in:

- Cookie keys such as `a1`, `webId`, `gid`, `webBuild`, `websectiga`, `loadts`, `sec_poison_id`
- LocalStorage keys such as `b1`, `b1b1`, `dsllt`, `dsl`, `sc`

## Analysis Flow

1. Open the real page with `js-reverse-mcp`.
2. Reload the page and list loaded scripts.
3. Confirm the page exposes `window.mnsv2`, `window._dsf`, `window._dsl`, and related anti-spam globals.
4. Save `vendor-dynamic.ad4eaf21.js` locally and search it for `window.mnsv2` and `X-S-Common`.
5. Locate the signing call site in that bundle: `window.mnsv2(u, m, w)`.
6. Find the exported module that defines `signV2Init`.
7. Confirm the module id is `62380` and that it exports `signV2Init`.
8. Verify that `https://as.xiaohongshu.com/api/sec/v1/ds?appId=xhs-pc-web` initializes `_dsf/_dsn/_dsl/_webmsxyw` but does not itself directly produce `mnsv2`.
9. Capture the current browser cookie/localStorage shape and save it as workspace runtime seed material.
10. Extract the `signV2Init()` source from the webpack module and store it in `js_reverse_cache/signV2Init_function.json`.
11. Build a minimal iv8 browser-like environment and call `signV2Init()` so `window.mnsv2` is available in iv8.
12. Recreate the `X-s`, `X-t`, and `X-S-Common` headers in a compact helper JS file.
13. Replay the real POST request with one `requests.Session`, rebuilding payload and headers on every page.

## Why The Cache Is Required

The main Python file does not auto-download everything needed for a fresh run.

The browser runtime split is:

- `api/sec/v1/ds` and the `as/v1` / `as/v2` scripts provide the anti-spam runtime pieces such as `_dsf`, `_dsn`, `_dsl`, and `_webmsxyw`
- `vendor-dynamic.ad4eaf21.js` contains the module that exports `signV2Init`
- `signV2Init()` in turn initializes `window.mnsv2`

So if `js_reverse_cache/` is deleted, you must re-run the browser capture flow above to rebuild the cached seed and entry source.

## Reconstructed Workspace Artifacts

The bundled case uses these frozen assets:

- `assets/signV2Init_function.json`
- `assets/xhs_header_sign.js`
- `fixtures/runtime_seed.sample.json`

The sample seed file only shows the expected structure. It does not store account secrets.

## iv8 Reconstruction Notes

The compact case script rebuilds the page runtime in this order:

1. Construct a browser-like `location`, `navigator`, `screen`, `window`, and storage environment.
2. Patch minimal DOM methods that the sign runtime checks, especially `removeChild` / `appendChild`.
3. Load the frozen `signV2Init_function.json` source into iv8.
4. Call `signV2Init()` and verify `window.mnsv2` exists.
5. Evaluate the header generation helper and expose `{payload, seed}`.
6. Build fresh headers for every page request and send the POST using `requests.Session`.

## Things Not To Copy Into Skill

- Real account cookies or personal tokens
- Full response JSON dumps
- One-off debug reports
- Absolute paths outside the skill case directory

## Short Takeaway

The `mnsv2` entry is not recovered from `api/sec/v1/ds` alone.

The real browser chain is:

`page bundle + anti-spam scripts -> vendor-dynamic module 62380 -> signV2Init() -> window.mnsv2 -> X-s / X-S-Common`
