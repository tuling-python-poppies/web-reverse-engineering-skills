# PZDS Aliyun Captcha V2 Goods Public Process

Read this before using this case's `entry.py`.

## Goal

Recover the PZDS goods-list API guarded by Aliyun Captcha V2 and deliver a
browser-free Python collector that prints business JSON.

Success requires both layers:

```text
captcha:
  response.Success == true
  response.Result.VerifyCode == "T001"
  response.Result.VerifyResult == true

business:
  HTTP 200
  success == true
  code == "SUCCESS"
  data.records is a list
```

## Match And Exclusion Signals

Select this case when at least three independent signals match:

- `site:pzds`
- `api:goodsPublic/page`
- `vendor:aliyun-captcha-v2`
- `action:InitCaptchaV2`
- `action:VerifyCaptchaV2`
- `sidecar:DeviceConfig-Log2-Log3`
- `success:T001`
- `wasm:pzds-505c6f51-generate_sign`
- `header:X-Sign-Version-v18`

Do not select for Akamai, River Security, Geetest, Tencent TDC, pure-Python-only
runtimes, or tasks whose primary goal is browser UI automation.

## Default Protocol Path

This is the only default collector path.

1. **Session gate**
   - If the current task has no usable session, ask the user for username and
     password only for the authorized protocol login.
   - Keep credentials and the resulting token in memory by default. Persisting a
     profile, session, credential, cookie, or raw response requires the hub's
     `raw-secret-handling` confirmation with exact fields, a project path,
     repository exclusion, and a retention deadline. Never write those values to
     the case library, fixtures, tests, or reports.
   - Protocol login:
   - `POST /api/auth/oauth2/token` with password MD5 and client basic auth
   - `POST /api/web-client/v2/user/public/login/idtoken`
   - When persistence is explicitly approved, write the project-local session
     shape only to `js_reverse_cache/private/pzds/session.json`:
     `token`, optional `pzId`, `deviceId`, `globalId`.

2. **Trigger challenge**
   - `POST https://api.pzds.com/api/web-client/v2/public/goodsPublic/page`
   - compact JSON body from `build_goods_page_body`
   - PZDS PC headers including `X-Sign-Version: v18`
   - `Sign` / `PZTimestamp` / `Random` from local WASM helper
   - `Referer: https://www.pzds.com/`
   - `token` / optional `PZid` for login admission

3. **Parse challenge**
   - response is HTML containing `var requestInfo = {...}`
   - required fields: `sceneId`, `traceid`, `token`, `userId`, `userUserId`,
     optional `type`, `data`

4. **Pure FeiLin captcha**
   - InitCaptchaV2
   - Log2 / Log3 on device endpoint
   - VerifyCaptchaV2
   - accept only `T001/true`

5. **Business replay**
   - same compact body used for trigger and final POST
   - URL carries `u_atoken` and `u_asig`
   - regenerate v18 `Sign` / `PZTimestamp` / `Random` for the final body
   - Python owns final HTTP egress

6. **Print business JSON** to console and keep redacted project samples only.

## Live Prerequisites

Before claiming live complete, project root must provide:

| Item | Project path | Notes |
|---|---|---|
| FeiLin profile | `js_reverse_cache/private/pzds/t001_profile.json` | raw private state; only after `raw-secret-handling`; must match live `DeviceConfig.version` as a full package |
| Login session | `js_reverse_cache/private/pzds/session.json` | raw private state; requires `token`; only after `raw-secret-handling` |
| Accepted track seed | `js_reverse_cache/private/pzds/track_seed.json` | project-private behavior seed; derive a fresh track from this seed, or capture a new accepted seed before claiming live success |
| Optional credentials | in memory by default | persistence to `config.local.json` requires the same exact raw-secret approval and gitignore protection |

Use `pull_live_state.py inspect <projectRoot>` to report missing gates without
reading raw state. Add `--raw-secret-handling-confirmed` only after the hub has
recorded the exact persistence decision. Missing session => ask the user for
credentials and keep them in memory. Missing or stale profile => refresh the
full FeiLin profile package; do not only rewrite the version string.

## Login Landing

When the project has no usable session token, ask the user for username and
password, then run the login inside the project only. Do not create a session
file unless the hub has confirmed `raw-secret-handling` for its exact fields and
retention:

1. `POST https://api.pzds.com/api/auth/oauth2/token`
   - body: `username`, `password` (MD5), `scope=openid`,
     `grant_type=password`
   - header: `Authorization: basic <clientSecret>` where `clientSecret` is a
     project-local constant, never stored in the case library
   - keep v18 signed PC headers (`Sign` / `PZTimestamp` / `Random`)
2. `POST https://api.pzds.com/api/web-client/v2/user/public/login/idtoken`
   - body: `{"action":{"idToken":...,"registerWay":"PASSWORD"}}`
   - response `data.token` becomes the business token
3. Use `data.token`, `pzId`, `deviceId`, and `globalId` in memory for the
   current coherent session.
4. Only after the exact raw-secret decision, write that session to
   `js_reverse_cache/private/pzds/session.json`. Credentials remain in memory
   unless the same decision explicitly permits `config.local.json`.

Login failure handling:

- `HTTP 460` on `/auth/oauth2/token`: report it as a wind-control blocker;
  do not treat browser manual captcha as the default recovery path.
- `NOT_LOGGED_IN` on the business API: re-run login and refresh the session
  file before retrying captcha rounds.

## Profile Refresh Runbook

When `DeviceConfig.version` diverges from
`js_reverse_cache/private/pzds/t001_profile.json`
("FeiLin device profile is stale"), refresh the full profile package with the
project-local updater. Do not edit the version string only.

```text
python utils/t001_profile_refresh.py --preflight-only --version-samples 1 --preflight-attempts 1 --timeout 30
python utils/t001_profile_refresh.py --fast --rounds 3 --version-samples 1 --preflight-attempts 1 --online-attempts 5 --max-capture-attempts 8 --timeout 90 --headless
```

Requirements:

- The updater's challenge trigger must carry the project login `token` plus
  v18 signed PC headers; otherwise it gets `HTTP 401 NOT_LOGGED_IN`.
- The updater uses raw CDP instead of browser automation frameworks. Default
  `--browser auto` tries ordinary Chrome first, then falls back to CloakBrowser
  only when capture or online `T001/true` validation fails.
- `websocket-client` is the CDP dependency. Browser binaries are local tools;
  the case library stores neither browser profiles nor CDP artifacts.
- CDP browser lifecycle is part of acceptance: close the CDP WebSocket, then
  terminate the browser process; on Windows, kill the process tree if normal
  termination times out. Do not claim complete while a refresh browser remains
  live.
- A fresh FeiLin generation must extend generation-local ignored fields before
  the stability check passes. Observed current generations:
  - feilin123-126: `{52, 86, 136, 137}`
- Current accepted profile field counts are `111`, `133`, and `142`; reject
  other counts until a fixed vector or online `T001/true` proves the new shape.
- Success is only an online `T001 / true` verification before an exclusive,
  approved write of the new profile under `js_reverse_cache/private/pzds/`.

## Gate Family

Primary: **verifier** (`T001/true`).

Secondary:

- **session**: cold/missing login returns JSON `NOT_LOGGED_IN` instead of
  challenge HTML. Re-login; keep root referer `https://www.pzds.com/`.
- **signer**: business headers require v18 WASM `Sign` / `PZTimestamp` /
  `Random` at the wire request boundary.
- **transport**: use browser-equivalent TLS for live replay; do not silently
  downgrade impersonation profiles that fail challenge trigger.

## Canonical Mutation Point

Python constructs the final HTTP request immediately before egress. Local Node
WASM only returns narrow artifacts (`Sign`, `PZTimestamp`, `Random`, captcha
`data`/`arg`) and never owns live HTTP.

## False Leads

- Treating page SSR HTML as the business data source.
- Treating `decode__1174` as a required default gate for
  `goodsPublic/page` POST. It may appear in browser traffic and is not required
  once captcha admission and v18 headers are correct.
- Using manual captcha slider or browser page automation as the default
  collector path.
- Spending captcha retries while trigger still returns `NOT_LOGGED_IN`.
- Changing only `feilinVersion` text when server cohort changes.

## Implementation Notes

`entry.py` is import-safe and provides:

- compact goods body builder
- password MD5 / oauth body helper
- challenge parser
- Aliyun RPC HMAC-SHA1 helper
- device token helpers
- v18 WASM signer wrapper
- business URL builder and response classifier

Project live runners must keep:

- current FeiLin profile package under `js_reverse_cache/private/pzds/` only
  after `raw-secret-handling` approval
- login session under `js_reverse_cache/private/pzds/` only after the same
  approval
- v18 signer assets used by the project entry

Case library stores only redacted shapes, offline vectors, public frozen signer
assets, and process/code primitives. It does not store project-local live state.

## Project Delivery Files

When this case is used to generate a fresh collector, the stable project should
be assembled in the `web-protocol-recovery-simple` layout:

- root `main.py` as the default command (`python main.py`)
- `utils/logger.py` for bounded progress logs
- `utils/pzds_challenge.py` for goods body construction and challenge parsing
- `utils/pzds_goods.py` for business replay after `T001/true`
- `utils/aliyun_t001_runner.py`, `utils/aliyun_v2_core.py`, and
  `utils/aliyun_v2/protocol.py` for the Aliyun V2 protocol
- `utils/t001_profile_refresh.py` for CDP profile refresh
- `utils/pzds_wasm_sign.mjs`, `505c6f51.wasm`,
  `pzds_wasm_glue_64c90705.mjs`, `data_builder.js`, and `vm_codec.js` as
  narrow local helper assets
- `requirements.txt` with `curl_cffi`, `pycryptodome`, `requests`, and
  `websocket-client`

The generated code may support a local `config.local.json` for credentials only
after the hub records raw-secret handling. That file stays project-local and is
never a case asset. Stable helper modules should load FeiLin profile and session
state through project-private paths, not from the case directory.

Do not treat `fixtures/track-template.json` as a live-accepted trajectory. It is
an offline shape guard. A fresh project must either carry a project-private
accepted movement seed at `js_reverse_cache/private/pzds/track_seed.json` or
capture one in a current verifier round before running the Python collector.
The runtime may perturb timings, offsets, screen ratio, and `arg`, but it must
start from an accepted seed rather than arbitrary from-zero synthetic points.

## Fixed-Vector / Offline Proof

```text
python -m unittest discover -s tests -v
```

Vectors cover:

- goods body SHA-256 and request shape
- field21 classic vectors
- Aliyun RPC HMAC-SHA1
- deviceToken checksum / AES roundtrip
- `data_builder.js` fixed output
- v18 `pzds_wasm_sign.mjs` fixed timestamp/random/body
- challenge HTML parser

## Dependencies

- Python >= 3.10 for current project runners
- Node.js for `assets/data_builder.js` and `assets/pzds_wasm_sign.mjs`
- `pycryptodome` for AES helpers
- `curl_cffi` for live replay in project runners

## Invalidation Signals

- `X-Sign-Version` leaves `v18`
- WASM asset no longer matches `505c6f51` family
- challenge trigger no longer returns `var requestInfo` after login + signed
  headers + root referer
- `DeviceConfig.version` diverges from project profile and full profile refresh
  is not performed
- Verify no longer returns `T001/true` on a coherent same-round state
- business success leaves `success=true`, `code=SUCCESS`, and `data.records`

## Fresh Machine Shortest Path

When the project has no existing runner, profile, or updater (a new machine or a
new target directory), assemble the full chain from this case's primitives and
current live evidence. Routine browser recon, read-only live requests, and the
protocol-needed verifier submit stay inside the selected collector shape; do not
pause for those. Pause only for dependency installation, local execution of
target-supplied JS/WASM/HTML, raw-secret persistence, or larger scope/budget.

Order:

1. **Generate stable files** - create the `Project Delivery Files` above. The
   generated `main.py` must auto-refresh a stale login token when credentials
   are available, auto-run `utils/t001_profile_refresh.py` when FeiLin profile
   stale is detected, and print the final business JSON in Chinese-safe UTF-8.
2. **Login** - protocol login (`oauth2/token` MD5 + `idtoken`) and keep
   `token`, optional `PZid`, `deviceId`, and `globalId` in memory. Persist them
   only after the exact raw-secret confirmation to
   `js_reverse_cache/private/pzds/session.json`.
3. **Profile and movement bootstrap** - if no private FeiLin profile exists,
   use CDP capture to collect current `DeviceConfig`, `InitCaptchaV2`, browser
   `Log2`, sparse token, the combat baselines needed by Log3, and an accepted
   movement seed. Store the coherent package only under project-private paths.
   If a private seed profile exists, the CDP updater may refresh
   `fullDeviceFields`, `tokenFields`, `field21`, and version while retaining
   verified combat baselines and the accepted movement seed.
4. **Refresh validation** - run preflight version sampling, then CDP capture.
   Default to ordinary Chrome. Fall back to CloakBrowser only after the ordinary
   Chrome candidate fails capture or online `T001/true`. Every candidate profile
   must pass online `T001/true` before any write.
5. **Trigger and parse** - signed `goodsPublic/page` returns challenge HTML;
   parse `requestInfo` (`sceneId`, `traceid`, `token`, `userId`, `userUserId`,
   optional `type`, `data`, `refer`).
6. **Verifier round** - InitCaptchaV2 -> Log2 -> seed-derived track -> Log3 ->
   VerifyCaptchaV2. Accept only `T001/true` on a coherent same-round state.
   If `track_seed.json` is missing, stop and capture/derive it first; do not
   spend verifier attempts on a structural template alone.
7. **Business replay** - Python appends `u_atoken` and `u_asig`, regenerates v18
   `Sign` / `PZTimestamp` / `Random` at the wire boundary, and posts the compact
   goods body. The browser never owns final business egress.
8. **Accept** - business `HTTP 200`, `success=true`, `code=SUCCESS`, and
   `data.records` as a list. One non-empty sign, one HTTP 200, or a browser page
   JSON view is not enough.

If bootstrap lacks combat baselines, do not write a half-profile. Capture one
browser-accepted verifier round and extract Log3/combat material into the same
private profile package, or stop with that blocker. Never merge fields from
different FeiLin versions, browser engines, sessions, or target rounds.

Failure routing: `NOT_LOGGED_IN` -> re-login and keep root referer;
`F025` -> session/profile/token consistency; `F001` -> sidecar order first,
trajectory last; `T001` is the only pass.

## Sensitive Materials Intentionally Excluded

- username, password, raw token values, cookie values
- Authorization secrets
- full FeiLin profile bodies in the case library
- one-shot `u_atoken`, `u_asig`, `CertifyId`, `traceid`
- HAR, full private responses, absolute local paths
- project-local browser/CDP artifacts, profile-refresh captures, and transient
  business response bodies
- project-local accepted track seeds and raw `np` input/output captures; keep
  them under `js_reverse_cache/private/pzds/` in the active project or recapture
  them, not in the case library
- the historical project's local config and saved login state; regenerate these
  through protocol login and CDP bootstrap in the new project instead
