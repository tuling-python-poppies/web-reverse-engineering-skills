# Geetest GT4 Nine-Grid Pure-Python Case

## Goal And Success Predicate

Recover and reuse the Geetest GT4 `risk_type=nine` verifier boundary without a browser-backed final runtime. The protocol result is accepted only when a fresh same-round `/verify` response has `status=success`, `data.result=success`, and `data.fail_count=0`.

The checked-in active proof is offline-only: it binds the current entry, tests, protocol vectors, model, labels, and model manifest. Historical live proof records current-target provenance but is not reusable live authorization.

## Match Signals

Select this case only when at least three independent signals agree:

- `vendor:geetest`
- `version:v4`
- `captcha-type:nine-grid`
- request `risk_type=nine`
- response `captcha_type=nine`
- response fields `imgs`, `ques`, and `nine_nums`
- `/verify` with `lot_number/payload/process_token/payload_protocol/pt/w`

Do not select for GT3, slider (`bg/slice`), word/icon point-click coordinates, `svg_seed`, or generic nine-image UIs without the GT4 `/load` markers.

## Reconnaissance Choice

The target was the public `https://gt4.geetest.com/` Demo. Chromium DevTools established the baseline and showed that the page defaults to `risk_type=slide`. Selecting the right-side “九宫格验证” option before triggering the verifier produced a second `/load` carrying `risk_type=nine` and returning `captcha_type=nine`.

Current evidence showed:

- load host: `gcaptcha4.geetest.com`
- static host: `static.geetest.com`
- verifier host: `gcaptcha4.geetest.com`
- bundle version: `v1.9.6-1db46d`
- GCT name: `gct4.5a2e755576738ba0499d714db4f1c9e0.js`
- current `biht`: string `1426265548`

Browser IDs and live request IDs are not retained in this case. Final delivery uses Python for HTTP egress.

## Request And State Chain

1. `GET /load` with dynamic JSONP callback, `captcha_id`, `client_type=web`, `risk_type=nine`, and language.
2. Freeze one round's `lot_number`, `payload`, `process_token`, `payload_protocol`, `pt`, `pow_detail`, `static_path/js`, and `gct_path`.
3. Download the one `imgs` composite, each `ques[]` prompt, the current raw bundle, and the current raw GCT.
4. Split `imgs` using rounded grid boundaries. Current `nine_nums=3` yields nine tiles.
5. Run the bundled classifier, choose exactly three zero-based tile indices, and map them to one-based `[row, col]` pairs.
6. Extract `_lib` fixed fields and `lib._abo` lot rules from the current bundle.
7. Build PoW, raw-GCT `biht`, `gee_guard`, `em`, and compact JSON.
8. Encrypt `w` and submit `/verify` with the same round's outer fields.

## Canonical Mutation Point

The canonical mutation point is the compact JSON encrypted into `/verify` query parameter `w`. Nine-grid changes the `userresponse` member:

```python
[[index // count + 1, index % count + 1] for index in indices]
```

For indices `[1, 5, 6]`, the wire value is `[[1, 2], [2, 3], [3, 1]]`. Raw indices and pixel coordinates are not valid substitutes.

## Shared GT4 Shell

This subtype reuses the GT4 shell documented in `geetest-gt4-workflow.md`:

- PoW plaintext ends in `lot_number||nonce`.
- Current bundle metadata is extracted from the complete raw source; version samples are not hardcoded.
- GCT hashing uses JavaScript int32 and UTF-16 code-unit semantics on raw function source.
- The AES key is a 16-byte ASCII hex string.
- The AES IV is `b"0000000000000000"`, sixteen ASCII `0` bytes, not sixteen NUL bytes.
- `w` concatenates AES ciphertext hex then RSA PKCS#1 v1.5 encrypted-key hex.

## Recognition Boundary

The prompt is line-art while tiles are photo-like. Direct prompt classification can disagree sharply with tile classification. The bundled model therefore treats tile top-1 grouping as the primary signal and prompt classification as a tiebreaker:

1. one exact three-tile group -> use it;
2. multiple exact groups -> prompt probability selects among them;
3. no exact group -> rank tile probabilities for the prompt class;
4. prompt class absent from all tiles -> use the largest tile group as a bounded fallback.

The model may still miss an individual round. A live collector must use a fresh lot for any approved retry and may not enumerate combinations on one challenge. Retry count remains governed by the work-order request budget.

## Model Asset And Offline Reuse

The case contains:

- `assets/geetest_nine_model.pt` (10,483,069 bytes)
- `assets/labels.txt` (90 classes)
- `assets/MODEL.json` (hash, size, provenance, and cache policy)

`entry.verify_model_assets()` fails closed before model loading. `entry.install_model_pack(project_root)` can copy the pack into a new project without network access. `entry.configure_runtime_cache(project_root)` must be called explicitly before importing Ultralytics and pins all ML runtime caches under `<projectRoot>/js_reverse_cache/_runtime/**`.

The entry performs no network traffic and creates no files on import.

## False Leads And Recovery

| False lead | Evidence | Correction |
|---|---|---|
| Treating the Demo's first load as nine-grid | first load had `risk_type=slide`, `bg`, and `slice` | explicitly select nine-grid and require `captcha_type=nine` |
| Submitting raw tile indices | verifier expects a nested pair array | map to one-based `[row, col]` |
| Using NUL IV bytes | server returned `-50002 param decrypt error` | use sixteen ASCII `0` bytes |
| Reusing a consumed lot | server returned `-50306 process_token Error` | create a fresh same-round challenge |
| Reversing AES again after `result=fail` | outer status succeeded, fail_count became 1 | decryption worked; inspect model and answer shape |
| Trusting the line-art prompt alone | prompt target had near-zero probability across all tiles | use tile consensus and prompt tiebreak |

## Provider Order

Historical recovery:

1. `chromium-recon` for public Demo request and bundle evidence.
2. `verifier` as protocol owner.
3. `pure-python` for model inference and protocol helpers.
4. `python-collector` for gated `/load`, static downloads, and `/verify` delivery.

Current reuse must start from `verifier`, then use this `pure-python` artifact, then `python-collector`. Fresh recon is required when the current subtype, bundle fields, GCT behavior, model class map, or success marker disagrees.

## Verification

Offline acceptance covers:

- model bytes and SHA-256;
- labels bytes, SHA-256, and class count;
- index-to-wire mapping;
- inclusive lot slices;
- decodeURI reserved-byte behavior;
- djb2/JS int32 behavior;
- PoW shape and target verification;
- ASCII-zero AES IV fixed vector;
- import discipline and blocked implicit live egress.

Historical current-target evidence observed repeated fresh challenges ending in semantic success. The retained summary contains no cookies, tokens, payloads, `w`, raw challenge images, or absolute paths and is explicitly not current reuse authorization.

## Dependencies

- Python 3.9+
- Pillow
- pycryptodome
- torch
- ultralytics

No Node, iv8, ExecJS, jsdom, browser, or model download is required for the implementation artifact.

## Invalidation Signals

Stop reuse and return to verifier evidence when any of these change:

- `captcha_type` is not `nine`;
- `nine_nums` or answer cardinality changes;
- `userresponse` no longer accepts one-based row/column pairs;
- current bundle metadata extraction fails;
- GCT no longer exposes the 5381 hash shape;
- AES/RSA shell changes or server returns repeated decrypt errors;
- model class names or model SHA-256 differ;
- current evidence needs labels outside the bundled 90 classes.

## Sensitive Materials Excluded

The case stores no raw cookies, process tokens, payloads, `w`, account state, browser state, HAR, private response bodies, challenge images, or absolute local paths. Live state is pulled fresh under an approved work order and retained in memory only.
