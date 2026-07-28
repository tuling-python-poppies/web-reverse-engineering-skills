# Baidu Passport Spin V2 Workflow

Use this reference for Baidu Passport rotate/spin captchas where the visible UI says Baidu security verification and the network chain uses `passport.baidu.com/cap/*`.

## Signals

Select this workflow when at least two independent signals appear:

1. Requests to `https://passport.baidu.com/cap/init`, `/cap/style`, `/cap/img`, and `/cap/log`.
2. `style` response contains `captchalist[0].id == "spin-0"`, `type == "spin"`, `backstr`, `ext.p`, or `ext.en_conf`.
3. JavaScript sources include `mkd_v2.js`, `work.js`, `fingerprint.js`, `getNewKey`, `powMap`, `rzData`, `secondHandle`, `dataSubmit`, or `verifyScreen`.
4. The final verifier submit is a `POST /cap/log` whose form includes `cv=submit`, `typeid=spin-0`, and a long `fs` value.

Do not use this workflow for ordinary Baidu login SMS checks, site-owner business forms, generic Baidu analytics beacons, or non-spin Passport captcha types until current evidence shows the same `spin-0` proof builder.

## Request Chain

Freeze one coherent round. Do not mix `tk`, `as`, `backstr`, image URL, `ext.p`, `en_conf`, PoW, or `fs` across adjacent rounds.

1. `POST https://passport.baidu.com/cap/init`
   - request fields: `_`, `ak`, `as`, `ds`, `refer`, `reinit`, `scene`, `tk`, `ver=2`
   - response fields: `tk`, `as`, `ds`, `ls`, `conf`
2. `POST https://passport.baidu.com/cap/style`
   - request fields: `_`, `ak`, `isios=0`, `refer`, `scene`, `tk`, `type=click`, `ver=2`
   - response fields: `backstr`, `captchalist[].source.back.path`, `ext.p`, `ext.en_conf`
3. `GET https://passport.baidu.com/cap/img?...`
   - returns the circular rotated image for the same round
4. `POST https://passport.baidu.com/cap/log`
   - telemetry and verifier submit share this URL
   - verifier submit includes `cv=submit`, `typeid=spin-0`, `fuid` optional, and encrypted `fs`

## Success Marker

`/cap/log` is overloaded. `code == 0` and `msg == "Success"` are not enough.

Verifier success is:

```text
response.code == 0 && response.data.op == 1
```

Observed meanings:

| Field | Meaning |
|---|---|
| `data.op == 1` | spin verification passed |
| `data.op == 2` | single-step success / intermediate state in multi-step flows |
| `data.op == 3` | failed verification; refresh the round before the next guess |
| no `data.op` | usually telemetry-only `/cap/log`, not a verifier submit |

To identify the real verification packet in a browser capture, filter `cap/log` and then inspect payload/response:

1. real submit: request has `cv=submit` and `typeid=spin-0`; response has `data.op`
2. telemetry: request has only `_`, `refer`, `ak`, `as`, `scene`, `tk`, `ver`, `fs`; response has only `as`, `ds`, `tk`

## JavaScript Anchors

Primary source is `mkd_v2.js`. `work.js` owns the PoW loop. `fingerprint.js` may provide `fuid` through `window.passFingerPrint()`.

Useful searches:

1. `getNewKey` for key derivation.
2. `.fs=` or `n.fs=` for the double AES packaging.
3. `this.rzData` for the plaintext proof shape.
4. `secondHandle` and `en_conf` for the first AES layer configuration.
5. `powMap`, `originStr`, `fillZero`, `md5Pow`, `sha1Pow` for PoW.
6. `dataSubmit` for the real submit event that sets `cv=submit` and `typeid`.
7. `verifyScreen` and `setScreen` for `captchalist[id].cr` and `captchalist[id].back` geometry.

## Crypto And Proof Builder

### `getNewKey(as)`

The key material is `as + "appsapi2"`. Choose the hash by the last character of `as`, then take the first 16 hex chars.

| Last char | Hash |
|---|---|
| `A-G` / `a-g` | MD5 |
| `H-N` / `h-n` | SHA1 |
| `O-T` / `o-t` | SHA256 |
| `U-Z` / `u-z` | SHA512 |
| `0-4` | SHA3-256 |
| `5-9` | SHA3-512 |

Important: CryptoJS `SHA3` is Keccak. Python `hashlib.sha3_*` is not compatible; use `Crypto.Hash.keccak` from `pycryptodome` for parity.

### AES

`encryptMap` uses AES-ECB with CryptoJS ZeroPadding and Base64 output. The key is `params.key || getNewKey(params.as)`.

`ext.en_conf` decrypts with `getNewKey(as)` and usually yields a `secondHandle` like:

```json
{"method":"aes-ecb","key":"","custom":"","as":"<current-as>"}
```

### PoW

`style.data.ext.p` drives PoW.

| Field | Meaning |
|---|---|
| `q["spin-0"]` | origin string |
| `m == "s"` | SHA1 |
| `m == "m"` | MD5 |
| `c` | number of leading zero hex chars |

Find `an` such that:

```text
hash(q[id] + an).substring(0, c) == "0" * c
```

Submit `p` as the result object, for example `{ "an": 3441, "t": 0 }` or a measured `t` value.

### `ac_c`

For spin, the page submits a ratio, not raw degrees.

Source behavior:

```text
ac_c = Number((distance / (trackWidth - knobWidth)).toFixed(2))
```

Observed desktop values: `trackWidth ~= 290`, `knobWidth = 52`, denominator `238`. If a visual solver returns a correction angle in degrees, a practical mapping is:

```text
distance = (angle % 360) / 360 * 238
ac_c = round(distance / 238, 2)
```

Angle perception is the weak point. Treat image angle as a candidate; server `op` is the proof. A fast OpenCV scan can be sub-second, but keep a bounded retry path for ambiguous scenes.

### `rzData`

The first AES layer encrypts compact JSON of `rzData`.

Minimum useful shape:

```json
{
  "common": {
    "cl": [],
    "mv": [],
    "sc": [],
    "kb": [],
    "sb": [],
    "sd": [],
    "sm": [],
    "cr": {
      "screenTop": 0,
      "screenLeft": 0,
      "clientWidth": 1920,
      "clientHeight": 969,
      "screenWidth": 1920,
      "screenHeight": 1080,
      "availWidth": 1920,
      "availHeight": 1040,
      "outerWidth": 1920,
      "outerHeight": 1040,
      "scrollWidth": 1920,
      "scrollHeight": 2000
    },
    "simu": 0,
    "ac_c": 0
  },
  "backstr": "<style.backstr>",
  "captchalist": {
    "spin-0": {
      "ac_c": 0.81,
      "p": {"an": 3441, "t": 0},
      "cr": {"left": 700, "top": 200, "width": 360, "height": 360},
      "back": {"left": 755, "top": 255, "width": 250, "height": 250}
    }
  }
}
```

Notes:

1. `common.mv` should stay an empty list unless live evidence proves a track is required. Non-empty simulated motion has caused failures.
2. `common.cr` is a screen-info object, not an array.
3. `captchalist[id].cr` and `captchalist[id].back` come from `verifyScreen`; exact pixels are less important than including coherent geometry.
4. `fuid` may be fixed or omitted for some contexts, but if the browser supplies it, preserve it with the same session.

### `fs` Packaging

Source behavior:

```text
common_en = encryptMap(JSON.stringify(rzData), secondHandle)
fs = encryptMap(
  JSON.stringify({ common_en, backstr }),
  { key: newKey, as: currentAs, method: "aes-ecb" }
)
```

Use compact JSON separators in Python to reduce accidental byte-shape differences. The final `/cap/log` form must include:

```text
_ refer ak as scene tk ver fs cv=submit typeid=spin-0 fuid=<optional>
```

Missing `cv=submit` or `typeid=spin-0` can produce `code=0` with no `op`, which is not a verification result.

## Replay Strategy

1. Export current browser state only under `<projectRoot>/js_reverse_cache/private/**` when live replay is approved.
2. Use Python `requests.Session` for final egress; browser/CDP is evidence only.
3. Run one fresh round per angle attempt. After `op=3`, discard the round and fetch new `init/style/img`.
4. Default fast path: one round, no artificial sleep, no image write, small OpenCV angle scan. A successful local run can complete in about 0.6 seconds when network is warm.
5. Reliability path: add one or two fresh-round retries or a slower angle search. Do not repeatedly submit many guesses against the same challenge.

## Acceptance

Local proof should include fixed tests for:

1. `getNewKey(as)` including Keccak SHA3 cases.
2. AES-ECB ZeroPadding roundtrip and `en_conf` decrypt.
3. PoW result validation against `ext.p`.
4. `fs` double-layer decrypt sanity: outer contains `{common_en, backstr}`; inner contains `captchalist["spin-0"].ac_c`, `p`, `cr`, and `back`.

Live proof, when approved, must show:

```text
code == 0 && data.op == 1
```

Record only redacted summaries such as `op`, `code`, `angle`, `ac_c`, `elapsed_ms`, and response field lengths. Do not store raw cookies, raw account state, full private headers, or unsanitized session artifacts outside `js_reverse_cache/private/**`.

## Failure Triage

| Symptom | First check |
|---|---|
| `code=0` but no `op` | request is telemetry; add `cv=submit` and `typeid=spin-0` |
| `op=3` | wrong angle or stale/mixed round; refresh `init/style/img` before retry |
| `opp=3` or risk message | diff `fs` packaging, geometry, `fuid`, and session state before blaming OCR |
| Empty or wrong `en_conf` decrypt | verify `getNewKey` and Keccak-vs-SHA3 implementation |
| Browser passes but Python does not | diff form field set, JSON serialization, `rzData` geometry, cookies, and transport timing in that order |
| Slow runtime | remove artificial sleeps, skip image writes, use fast angle scan, and keep retries bounded |

## Do Not

1. Do not treat every `/cap/log` as a verifier submit.
2. Do not accept `HTTP 200`, `code=0`, or `msg=Success` as success without `data.op == 1`.
3. Do not mix `tk/as/backstr/ext.p/image` from neighboring rounds.
4. Do not store raw browser state or cookies outside the approved project root.
5. Do not ship browser-backed fetch as final delivery; Python owns final live egress.
