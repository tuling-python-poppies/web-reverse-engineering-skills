# iv8 Case Taxonomy

The root `references/cases/registry.json` is the only case selector. This file explains iv8 runtime coverage after a registry match; it is not an index and grants no permission to execute historical targets.

## Runtime Boundary

An `iv8` case uses Python for live HTTP and iv8 only for the browser-dependent artifact generator: cookie, signed URL, header set, wrapped body, verifier proof, or decoded payload. Cases that need Node.js/jsdom instead are grouped under `python-node`; implementations requiring no JavaScript runtime belong under `pure-python`.

## Restored iv8 Cases

| Case ID | Family | Runtime artifact |
|---|---|---|
| `iv8-chinatax-ruishu` | challenge | two-stage cookie and XHR suffix |
| `iv8-chng-ruishu-announcement` | challenge | 412 cookie and announcement request suffix |
| `iv8-cqvip-journal-search` | challenge | 412 state cookie and form replay |
| `iv8-customs-ruishu` | challenge | two-stage cookie plus URL/header mutation |
| `iv8-ouyeel-202-cookie-url` | challenge | 202 challenge cookie and signed URL |
| `iv8-douyin-bdms` | signer | final rewritten URL from iv8 netLog |
| `iv8-geetest-v4-slider` | verifier | slider perception inputs and official proof builder |
| `iv8-geetest-v4-word-click` | verifier | ordered OCR points and official proof builder |
| `iv8-jd-h5st` | signer | `ParamsSignMain` h5st output |
| `iv8-nmpa-md5-cookie` | signer | Python MD5 plus iv8 challenge cookie |
| `iv8-pdd-anti-content` | signer | webpack runtime module output |
| `iv8-tencent-tdc-slider` | verifier | trusted input, POW, and telemetry |
| `iv8-xhs-homefeed` | signer | X-s and X-S-Common headers |
| `iv8-zhipin-stoken` | session | challenge-bound `__zp_stoken__` |

`nmpa-md5-cookie` and `jd-h5st` remain iv8 cases: the former needs iv8 for the challenge cookie even though its business sign is Python MD5; the latter executes `ParamsSignMain` in `iv8.JSContext`.

## Load Order

1. Select exactly one entry from the root registry.
2. Verify and read its `case.json`.
3. Complete the Provider's `references/api-inventory.md` gate.
4. Read that case's `PROCESS.md`, then its entry and only the declared assets needed by the acceptance test.
5. Pull current cookies/storage through `pull_live_state.py` when declared; never reuse persisted historical values.
6. Reverify against the current target before treating any historical case as working implementation.

New case ingestion is governed only by root `references/methodology/case-writeback.md` and the Provider-local `references/case-ingestion-rules.md` maintenance summary.
