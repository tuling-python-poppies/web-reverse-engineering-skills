# Xiaohongshu Homefeed Reverse Process

Current implementation evidence for the Xiaohongshu PC `mnsv2` signer. The
historical `signV2Init_function.json` and archived entry remain study-only;
the current implementation is the frozen local iv8 runtime plus a Python-owned
HTTP collector.

## Match And Scope

Select only with at least two independent signals:

- `site:xhs`
- `runtime:mnsv2`
- headers `x-s`, `x-t`, and `x-s-common`
- legacy PC signer version `4.4.1`

Current business routes proven by the project are:

- `POST https://edith.xiaohongshu.com/api/sns/web/v1/homefeed`
- `GET https://edith.xiaohongshu.com/api/sns/web/v2/comment/page`

The comment route is a business consumer of the same signer, not a separate
case or signer family.

## Recovered Wire Flow

1. Build the canonical path and compact UTF-8 JSON body.
2. Compute `u = MD5(path + body)` and `p = MD5(path)`.
3. Load the frozen `assets/mnsv2_runtime.js` into iv8.
4. Apply the narrow `Node.prototype.removeChild` compatibility wrapper needed
   by the runtime's initialization cleanup.
5. Call `window.mnsv2(c, u, p)` locally, where `c = path + body`.
6. Assemble `x-s`, `x-t`, and `x-s-common` in Python.
7. Send the request with Python `requests`; the local runtime never performs
   network I/O.

`x-s-common` uses current in-memory state selected by `pull_live_state.py`:
`a1`, `b1`, `b1b1`, `dsllt`, `dsl`, and optional session cookies. Do not persist
those values in the case.

## Runtime Recovery

The current page bundle exported module `63552` for `signV2Init`; the older
historical notes naming module `62380` are retained as provenance only. The
browser page generated an anonymous eval runtime containing the complete
`mnsv2` closure. Running only the extracted low-level `6545.js` exports is not
equivalent: it produces internal 144-byte transforms, not the accepted public
`window.mnsv2(c,u,p)` entry.

The accepted local runtime is `assets/mnsv2_runtime.js`. It is frozen, checked
by SHA-256, and must not be refreshed from the network by the case entry.

## Homefeed Request Shape

The first request uses a JSON body shaped like:

```json
{
  "cursor_score": "",
  "num": 30,
  "refresh_type": 1,
  "note_index": 0,
  "unread_begin_note_id": "",
  "unread_end_note_id": "",
  "unread_note_count": 0,
  "category": "homefeed_recommend",
  "search_key": "",
  "need_num": 0,
  "image_formats": ["jpg", "webp", "avif"],
  "need_filter_image": false
}
```

The response is accepted only when HTTP 200, `success=true`, and `data.items`
contains business records. Each note is read from `item.id`, `item.note_card`,
and `item.xsec_token`; pagination advances with `data.cursor_score`.

## Comment Request Shape

Comments use query parameters `note_id`, `cursor`, `top_comment_id`,
`image_formats`, and optional `xsec_token`. A page is accepted only when HTTP
200, `success=true`, and `data.comments` is structurally valid. The default
collector boundary is one page per feed note; later cursors remain session-
dependent and must be re-accepted before scale.

## Verification

Offline proof:

- `tests/test_vectors.py` parses redacted vectors.
- Canonical `u/p` hashes match fixed synthetic input.
- The frozen runtime mounts `window.mnsv2` in iv8 and returns an `mns*` value.
- The project-level signer tests prove the captured 144-byte low-level parity
  and the full runtime mount.

Current-target proof, historical provenance only and not stored here:

- browser-free homefeed returned HTTP 200, `success=true`, and a non-empty note
- browser-free comments returned HTTP 200, `success=true`, main comments, and
  nested comments

## False Leads And Exclusions

- Do not use the old `signV2Init_function.json` as the current executable entry.
- Do not treat low-level `_1619d7` output as the public `mnsv2` result.
- Do not load live scripts, cookies, b1 values, tokens, full responses, or
  absolute workstation paths into this case.
- Do not let iv8 send business HTTP; Python owns final egress.

## Artifacts

- `entry.py`: offline-only case entry and vector helpers
- `assets/mnsv2_runtime.js`: frozen current runtime
- `fixtures/vectors.json`: synthetic canonical vectors and accepted shapes
- `tests/test_vectors.py`: executable offline proof
- `pull_live_state.py`: memory-only current state selector
