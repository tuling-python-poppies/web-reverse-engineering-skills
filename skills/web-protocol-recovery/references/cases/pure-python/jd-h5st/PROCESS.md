# JD H5st Pure-Python Reverse Process

Read this before using this case's `entry.py`.

## Goal

Reproduce JD mobile `h5st` signing for `recommend_like_m` with pure Python: no browser, no Node, no iv8, and no local execution of `js_security_v3_main.js`. Python owns both signer generation and live HTTP egress.

Success predicate (fresh verification 2026-07-23):

1. `entry.py` imports without network traffic.
2. Offline vectors prove the JD `_seData`, SHA256 input perturbation, custom environment Base64, body hash, synthetic h5st shape, and product parser.
3. The project implementation using this case pattern returned HTTP 200 from `GET https://api.m.jd.com/api` with `functionId=recommend_like_m` and parsed 20 product rows.

## Match And Exclusion Signals

Select when at least two independent signals match:

- `parameter:h5st` on `api.m.jd.com/api`
- `site:jd` / `m.jd.com` / `api.m.jd.com`
- `api:recommend_like_m`
- `request_algo:cactus.jd.com/request_algo`
- `appId:2088b`
- `body:sha256-hex`
- pure Python code contains JD `_seData` suffix alphabet `nLvT3b-jHrPzX7fD`

Do not select for non-JD `h5st`, cookie-only challenges, Akamai/Imperva/Ruishu verifier flows, or cases that still need JS runtime execution.

## Gate Family

Primary: **signer** (`h5st` query parameter).

Secondary notes:

- **transport** Chrome-like TLS and UA consistency are used through `curl_cffi`.
- **session** optional risk cookies and eid tokens are intentionally not persisted; this case worked without them for the tested public recommend endpoint.

## Evidence And Mutation Point

Canonical mutation point: Python builds the final `h5st` query parameter before `GET https://api.m.jd.com/api`.

The earlier iv8 case proved the live `ParamsSignMain` path. This pure-Python case ports the remote-algorithm branch instead:

1. POST `https://cactus.jd.com/request_algo?g_ty=ajax` with `version=5.3`, `appId=2088b`, generated `fp`, and Chrome-like headers.
2. Extract `tk`, server-returned `fp`, and `rd` from the returned `algo` function.
3. Build the timestamp segment `yyyyMMddHHmmssSSS`.
4. Compute `signKey = jd_sha256(tk + fp + timeSegment + "54" + appId + rd)`.
5. Compute `bodyHash = sha256(compactBodyJson)`.
6. Compute `signature = jd_sha256(signKey + "appid:<appid>&body:<bodyHash>&functionId:<functionId>" + signKey)`.
7. Build the environment JSON, encode it with JD's custom Base64 wrapper, and compute the environment digest using `appid:appid&functionid:functionId`.
8. Join the 10 h5st segments.

## Pure-Python Algorithms

JD hash wrappers:

- `_seData(text)` splits `text` into 6 contiguous buckets. The first five buckets have `len(text)//6` characters; the final bucket consumes the remainder. Each bucket maps `sum(ord(char)) & 0xF` through `nLvT3b-jHrPzX7fD`, and the 6-character suffix is appended to `text`.
- `jd_sha256(text)` hashes `(_seData(text) + "RvI<7|").encode("utf-8")` with standard SHA-256.
- `jd_md5(text)` uses the same byte perturbation with standard MD5.

JD environment encoder:

- Standard Base64 without `=` padding.
- Map alphabet `ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/` to `rqponmlkjihgfedcbaZYXWVUTSRQPONMLKJIHGFEDCBA-_9876543210zyxwvuts`.
- Reverse the mapped string.
- Prefix by original byte length mod 3: `0 -> of7r`, `1 -> pj`, `2 -> q`.

## Provider Order

1. `chromium-recon` / existing JD h5st evidence to identify endpoint and response shape.
2. `iv8` as reverse-engineering evidence only, to observe live `ParamsSignMain` internal checkpoints.
3. `python-collector` for the final pure-Python signer and business request.

## Fixed-Vector / Live Proof

Offline tests:

```text
python -m unittest discover -s tests -v
```

Vectors cover:

- default recommend body SHA-256
- `_seData("abcdefg")`
- JD MD5/SHA256 wrappers for `abc`
- custom Base64 for empty, `abc`, and `{"a":1}`
- deterministic synthetic h5st shape and signature
- redacted product parser sample

Live proof from project implementation on 2026-07-23:

```text
python -B main.py --use-cache
HTTP 200, productCount=20, responseBytes ~= 76KB
```

Redacted live proof summary: `fixtures/live-proof.summary.json` (no live `tk`, `fp`, cookies, eid token, HAR, or private response body).

## Dependencies

- Python >= 3.9
- `curl_cffi` for live replay only
- no `iv8`, Node, browser, or local JS runtime in final delivery

## Invalidation Signals

- `request_algo` response stops returning `tk/fp/algo` or hides `rd` differently.
- `appId` segment changes from `2088b`.
- h5st version changes away from `5.3` / `h5_file_v5.3.4` semantics.
- `signKey` timestamp input no longer uses `timeSegment + "54"`.
- `recommend_like_m` adds mandatory eid/risk/session state.
- Product rows leave `data.feeds.content`.

## Sensitive Materials Intentionally Excluded

- No cookies, eid tokens, Authorization, browser state, HAR, raw private response, or absolute project path.
- No live `tk` value is stored in fixtures; synthetic material is used for offline h5st vector tests.
- `response.sample.json` contains a minimal redacted product shape only.
