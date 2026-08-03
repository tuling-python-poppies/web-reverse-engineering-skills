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

1. **Login gate**
   - If project session has no usable `token`, ask the user for username and
     password.
   - Credentials are used only inside the authorized project for protocol login.
     Write them only to project `config.local.json` (gitignored). Never write
     username/password into the case library, fixtures, tests, or reports.
   - Protocol login:
     - `POST /api/auth/oauth2/token` with password MD5 and client basic auth
     - `POST /api/web-client/v2/user/public/login/idtoken`
   - Persist project-local session shape to
     `js_reverse_cache/pzds_session.json`:
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
| FeiLin profile | `verifier/t001_profile.json` | must match live `DeviceConfig.version` as a full package |
| Login session | `js_reverse_cache/pzds_session.json` | requires `token`; prefer `pzId/deviceId/globalId` |
| Optional credentials | `config.local.json` | username/password only when login is needed; gitignore |

Use `pull_live_state.py inspect <projectRoot>` to report missing gates. Missing
session => ask user for username/password. Missing or stale profile => refresh
the full FeiLin profile package; do not only rewrite the version string.

## Login Landing

When the project has no usable session token, ask the user for username and
password, then run the login inside the project only:

1. `POST https://api.pzds.com/api/auth/oauth2/token`
   - body: `username`, `password` (MD5), `scope=openid`,
     `grant_type=password`
   - header: `Authorization: basic <clientSecret>` where `clientSecret` is a
     project-local constant, never stored in the case library
   - keep v18 signed PC headers (`Sign` / `PZTimestamp` / `Random`)
2. `POST https://api.pzds.com/api/web-client/v2/user/public/login/idtoken`
   - body: `{"action":{"idToken":...,"registerWay":"PASSWORD"}}`
   - response `data.token` becomes the business token
3. Write project-local `js_reverse_cache/pzds_session.json`:
   `token` (required), `pzId`, `deviceId`, `globalId`
4. Persist username/password only in project `config.local.json`
   (gitignored). Never write them into the case library, fixtures, tests, or
   reports.

Login failure handling:

- `HTTP 460` on `/auth/oauth2/token`: report it as a wind-control blocker;
  do not treat browser manual captcha as the default recovery path.
- `NOT_LOGGED_IN` on the business API: re-run login and refresh the session
  file before retrying captcha rounds.

## Profile Refresh Runbook

When `DeviceConfig.version` diverges from `verifier/t001_profile.json`
("FeiLin device profile is stale"), refresh the full profile package with the
project-local updater. Do not edit the version string only.

```text
python update_t001_profile.py --preflight-only --version-samples 3 --preflight-attempts 5 --timeout 30
python update_t001_profile.py --fast --rounds 3 --version-samples 3 --preflight-attempts 5 --timeout 45 --headless
```

Requirements:

- The updater's challenge trigger must carry the project login `token` plus
  v18 signed PC headers; otherwise it gets `HTTP 401 NOT_LOGGED_IN`.
- A fresh FeiLin generation must extend
  `GENERATION_SIGNATURE_IGNORED_FIELDS` in the updater with the observed
  varying fields before the stability check passes. Observed generations:
  - feilin123: `{52, 86, 136, 137}`
  - feilin124: `{52, 86, 136, 137}`
  - feilin125: `{52, 86, 136, 137}`
- Success is only an online `T001 / true` verification before atomic write of
  the new profile.
- The updater needs CloakBrowser + Playwright; they are project tools, not
  case assets.

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

- current FeiLin profile package under `verifier/`
- login session under `js_reverse_cache/`
- v18 signer assets used by the project entry

Case library stores only redacted shapes, offline vectors, and public frozen
signer assets.

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

## Sensitive Materials Intentionally Excluded

- username, password, raw token values, cookie values
- Authorization secrets
- full FeiLin profile bodies in the case library
- one-shot `u_atoken`, `u_asig`, `CertifyId`, `traceid`
- HAR, full private responses, absolute local paths
