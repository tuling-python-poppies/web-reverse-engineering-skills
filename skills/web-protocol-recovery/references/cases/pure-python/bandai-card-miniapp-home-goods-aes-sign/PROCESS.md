# Bandai Miniapp Homepage Goods Pure-Python Case

## Goal

Preserve the narrow, browser-free protocol artifact for the Windoent Bandai Card WeChat miniapp homepage goods request. The case covers deterministic request signing, public query construction, and response-shape parsing. Final live HTTP remains outside this case entry and belongs to the project collector path.

## Success Predicate

1. `entry.py` imports without network traffic or file writes.
2. Fixed AES-CBC/Base64 vectors pass offline.
3. Fixed request parameters match `homeListH5(v)`.
4. A redacted response fixture parses into the expected goods shape.
5. Historical live proof records a successful `GET /h5/goods/index` response with non-empty product rows, while current reuse still requires fresh verification.

## Match And Exclusion Signals

Select only when the target matches the exact API scope or at least three independent signals:

- `platform:wechat-miniapp`
- `site:windoent`
- `api:/h5/goods/index`
- `api:appsevice.windoent.com/ct`
- `header:Mini-User-Agent`
- `algorithm:aes-cbc-server-time`
- `product:bandai-card`

Do not select for unrelated Windoent APIs, authenticated order/payment flows, browser-only delivery, or targets requiring a user session, verifier, challenge state, or target-code runtime.

## Gate Family And Mutation Point

Primary family: **signer**.

The canonical mutation point is the Python construction of the `signature` header immediately before the homepage goods request. The input is `str(serverTime) + SECRET_ID`; AES-CBC uses the embedded public client key and IV, PKCS#7 padding, and standard Base64 output.

## Provider Chain

1. `wechat-miniapp` for current package and request evidence.
2. `pure-python` for the deterministic signer and parser artifact.
3. `python-collector` for any future live delivery or pagination expansion.

## Current Endpoint

- Goods endpoint: `GET https://bdmatchapi.windoent.com/h5/goods/index`
- Server time endpoint: `GET https://appsevice.windoent.com/ct?<milliseconds>`
- Query parameters: `page`, `limit`, `categoryId`, `isHome`
- Static UA shape: `windoentMini/<mini-program-version>`
- Current tested endpoint does not require persisted cookies or a user Token.

## Verification

Offline tests are defined by `tests/test_vectors.py` and `fixtures/vectors.json`. The live result is historical provenance only; it must not be reused as current-target acceptance. A fresh target replay is required after app version, API route, key material, or response shape changes.

## Sensitive Material Excluded

No cookies, Token values, user identifiers, browser state, WMPF runtime IDs, HAR, full response bodies, absolute local paths, or complete miniapp source files are included. The AES constants are embedded public client protocol material and are retained only because they are required for the deterministic artifact.
