# JD H5st Reverse Process

Read this before using this case's `entry.py`.

## Goal

Reproduce JD mobile `h5st` signing in iv8 and replay a signed `api.m.jd.com` request with Python-owned HTTP (`curl_cffi`). Default success path is **live signing bundle + product feed parse**, not a one-time frozen JS snapshot alone.

Success predicate (fresh verification 2026-07-22):

1. iv8 produces non-empty `h5st` via `window.ParamsSignMain`.
2. `GET https://api.m.jd.com/api` with `functionId=recommend_like_m` returns HTTP 200 JSON.
3. Response contains `data.feeds.content[]` product rows with `id` / `name` / `price` (or `jdPrice`).

## Match And Exclusion Signals

Select when at least two independent signals match:

- `parameter:h5st` on `api.m.jd.com` query
- `runtime:ParamsSignMain` (`new window.ParamsSignMain({appId})._$sdnmd(...).h5st`)
- `site:jd` / host `m.jd.com` or `api.m.jd.com`
- signing script under `storage.360buyimg.com/webcontainer/main/js_security_v3_main.js`
- optional companion: `cactus.jd.com/request_algo`, `js-security-v3-rac-beta.js`

Do not select for: pure cookie challenges (Reese/Imperva), Akamai sensor sites, or non-JD `h5st`-named params without `ParamsSignMain`.

## Gate Family

Primary: **signer** (`h5st` query parameter).

Secondary (recorded, not family):

- **session** optional cookies / `x-api-eid-token` / risk cookies (`3AB9D23F7A4B3C*`) can affect some APIs
- **transport** Chrome-like TLS + UA consistency helps

## Fresh Recon Findings (2026-07-22)

Chrome DevTools baseline on `https://m.jd.com/`:

1. Page still exposes `window.ParamsSignMain`.
2. Live bundle URL pattern:

```text
https://storage.360buyimg.com/webcontainer/main/js_security_v3_main.js?v=YYYYMMDD
```

3. Companion scripts often appear:

```text
https://storage.360buyimg.com/webcontainer/main/js-security-v3-rac-beta.js?v=YYYYMMDD
POST https://cactus.jd.com/request_algo
```

4. Signed business request example:

```text
GET https://api.m.jd.com/api
  ?appid=jd-cphdeveloper-m
  &functionId=recommend_like_m
  &body=<json string>
  &h5st=<multi-segment token, contains appId segment 2088b>
  &loginType=2
```

5. Product payload shape (business success):

```text
data.feeds.content[]:
  id, name, price, jdPrice, oriprice, link, imgprefix, imgbase, ext{cate1,cate2,cate3,shopId,brandId}, ...
```

## Critical Invalidation Lesson

| Asset | Size (observed) | `recommend_like_m` |
|---|---|---|
| Historical case frozen `assets/js_security_v3_main.js` | ~241829 B | **HTTP 403 empty body** |
| Live `js_security_v3_main.js?v=20260722` | ~238135 B | **HTTP 200 + feeds** |

Frozen historical JS can still **generate a non-empty h5st** and even pass lighter APIs (e.g. `m_search_promptwords`), yet fail the original recommend API. **Non-empty h5st is not success.** Prefer downloading the current bundle each run.

Historical frozen HTML/JS under `assets/` remain for offline structural smoke only; they are not a guarantee of live business acceptance.

## Reconstruction Steps

1. Download current `js_security_v3_main.js` (query `v=` is date-ish; do not hardcode forever).
2. Seed page HTML (live `m.jd.com` HTML or frozen snapshot).
3. iv8 context with `location` = `https://m.jd.com/` and matching UA/timezone.
4. Patch `MessageChannel` via `__iv8__.wrapNative` (bundle checks native-like async APIs).
5. `document.documentElement.innerHTML = <html>`.
6. Eval signing bundle with a realistic `name=` URL.
7. Optionally drain event loop briefly (`drainMicrotasks` / `drain`).
8. Python: `body_hash = sha256(body_json_string).hexdigest()`.
9. JS:

```js
const s = new window.ParamsSignMain({ appId: "2088b" });
const out = s._$sdnmd({
  appid: "jd-cphdeveloper-m",
  functionId: "recommend_like_m",
  body: body_hash, // SHA-256 hex, not raw JSON
});
const h5st = out.h5st;
```

10. Python `curl_cffi` GET `api.m.jd.com/api` with params + Chrome-like headers.
11. Parse products from `data.feeds.content`.

## Important Details

- Keep request body serialization **byte-identical** before hashing.
- `appId` for ParamsSignMain observed as `2088b` for this mobile recommend path.
- Do not treat `request_algo` response as a replacement for ParamsSignMain unless current evidence shows a new mutation point.
- Silent-import iv8 in re-runnable delivery code (`import_iv8_silent`); historical bare `import iv8` is not the new template.
- Progress logs: prefer shared logger pattern; case entry may use print for import-safety simplicity.
- Evidence paths for project work: only `projectRoot/js_reverse_cache/**` (never OS temp as primary storage).

## Provider Order

1. `chromium-recon` — capture live script URL, h5st sample request, response product shape.
2. `iv8` — generate `h5st` from live bundle + HTML seed.
3. `python-collector` — own live egress, parse products, bounds.

## Fixed-Vector / Live Proof (executed 2026-07-22)

- Offline: payload hash/sign input shape + product parser vectors — PASS (case tests).
- Live with **live** signing bundle: `recommend_like_m` HTTP 200, ~70KB+ JSON, `data.feeds.content` length ~20, product fields `id/name/price` present — PASS.
- Live with **historical frozen** bundle only: can still emit h5st; `recommend_like_m` often 403 — FAIL for business acceptance.

## Dependencies

- python >= 3.9
- `iv8` runtime
- `curl_cffi`

## Invalidation Signals

- Live `js_security_v3_main.js` hash/size changes and frozen-only path fails business API.
- `ParamsSignMain` renamed/removed or `appId` changes.
- `body` no longer hashed / hashing algorithm changes.
- Recommend API moves off `h5st` or adds mandatory eid/risk tokens.
- Product path leaves `data.feeds.content`.

## Sensitive Materials Intentionally Excluded

- Raw cookies / eid tokens / full browser state
- Full private recommendation payloads in committed fixtures (use redacted samples only)
- Absolute local project paths
