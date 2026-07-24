# ByteDance VerifyCenter Slider Workflow

Use this workflow for ByteDance-family slider challenges whose final goal is a
browser-free protocol replay. The browser may be used for evidence collection,
but the delivered verifier must obtain a fresh challenge, solve it, sign it,
and submit it outside the browser.

## Recognition Signals

Strong signals include:

- `rmc.bytedance.com/verifycenter/captcha/v2`
- `verify.zijieapi.com/captcha/get` and `/captcha/verify`
- `captcha.js`, `captcha.wasm`, and `bdms.js` `1.0.1.x`
- `captchaBody`, `cyfreso`, `challenge_code`, `xx-tt-dd`, `msToken`, and
  `a_bogus`
- `mssdk.bytedance.com/web/r/token`
- an upstream login response containing `verify_center_decision_conf`, `fp`,
  `detail`, `verify_ticket`, or `server_sdk_env`

Do not route a normal Douyin API request here merely because it has
`a_bogus`. Generic signer entry tracing belongs to the JS reverse skill, and a
known non-captcha `a_bogus` pure implementation belongs to its dedicated
signer skill.

## Required End State

The complete chain is:

```text
fresh business login decision
  -> build VerifyCenter iframe URL
  -> mssdk token
  -> captcha/get
  -> download the two original images
  -> recognize and map the distance
  -> generate a track and plaintext
  -> captcha WASM encryption
  -> BDMS URL signing
  -> captcha/verify
  -> business continuation when required
```

Do not make a manually copied iframe URL part of the normal interface. Replay
the business login request and parse a fresh decision automatically. A manual
URL is acceptable only as a short-lived diagnostic input.

## Same-Round State

Keep these values from one decision and challenge round:

- `fp`, `detail`, `verify_ticket`, `server_sdk_env`, and `log_id`
- the mssdk response and `msToken`
- the `/captcha/get` challenge ID, images, `cyfreso`, and logger state
- the recognized distance, track, WASM plaintext/ciphertext, and final
  `a_bogus`

Preserve JSON types while rebuilding `verify_data`. Fields such as
`login_status`, `aid`, `cyfreso`, and mssdk numeric fields must remain numbers,
not numeric strings.

After `VerifyErr`, request a new login decision and a new captcha challenge.
Do not keep changing coordinates against one old challenge. A stale or
consumed challenge can return `NotFoundChallengeId` or the same generic
`VerifyErr` as a malformed payload.

## mssdk Long And Short Branches

The token packet has a long/short `strData` branch. Inspect the runtime packet
before replaying it; do not decide the branch only from an old capture.

Common numeric fields include `magic`, `version`, `dataType`,
`tspFromClient`, and `ulr`. Validate that booleans and strings have not leaked
into these fields. If a validated short packet is required, keep its numeric
fields and update only the fields known to be dynamic. Do not silently truncate
a long packet and assume it is equivalent.

## Image Coordinates And Track

For the common two-image slider recognition service, the returned `raw_x` is
the gap's left edge in the original background image. Map it to the displayed
background width:

```python
page_x = round(raw_x * displayed_background_width / natural_background_width)
```

One observed layout used `340 / 552`; treat both dimensions as runtime values
when possible. Keep the following coordinate systems separate:

1. original background pixels returned by recognition;
2. displayed background pixels used by the slider;
3. event coordinates and the final distance encoded in the behavior payload.

A plausible track should include a start position, dense movement, small
vertical noise, overshoot, correction, and a final release. More important
than a particular point count is consistency between:

- the track's final x and submitted distance;
- the track's last relative timestamp and declared duration;
- the declared duration and real wall-clock time before the request is sent.

## WASM Argument Boundary

Observe the public and internal calls separately. In the verified build:

- `captcha.verify(payload)` received one object argument;
- `wasm.encrypt(source)` received one string argument;
- the internal WASM entry was invoked as
  `entry("string", ["string", "number"], [source, utf8_byte_length])`.

The internal number is the UTF-8 byte length of the plaintext, not `cyfreso`
and not the JavaScript character count. Non-ASCII content can make byte length
and string length differ. Do not inject an extra public argument just because
the internal entry has a number parameter.

## BDMS Environment Evidence

Capture the actual generator input before inventing environment patches. One
verified iframe branch produced this semantic shape:

```javascript
{
  nWID: {extra: {err: TypeError("object is not a function")}},
  wID: {msgType: 3}
}
```

The exception type and message mattered; replacing it with a generic full
fingerprint or a `SecurityError` changed the signer path.

When tracing internal BDMS programs, distinguish stable environment bytes from
request-dependent bytes. For one `1.0.1.18` build, repeated browser samples
showed stable P145 differences at positions such as
`1,2,14,24,25,32,34,48`, while time/random/checksum positions changed between
calls. These positions are evidence for that bundle and profile, not global
constants.

Never copy a full P145 or S4 array from one browser request into later
requests. First-level programs can recurse, so instrumentation must guard the
first-level input rather than mutating every recursive call.

## Server Clock And Freshness Window

VerifyCenter can reject both ends of the timing window:

- **too fast**: the URL `tmp` is still in the future relative to the captcha
  server, or the request arrives before the declared track duration elapsed;
- **too old**: the challenge, `tmp`, track, or decision has exceeded its useful
  lifetime.

Use `/captcha/get` response header `x-tt-timestamp` as a server-clock sample
and a monotonic clock for elapsed local time:

```python
server_now = get_server_time_ms + elapsed_monotonic_ms
target_age = max(1800, track_duration_ms + 400)
wait_ms = max(0, verify_tmp_ms + target_age - server_now)
```

Reject an implausibly large wait and obtain a fresh decision instead. Do not
hardcode a sleep from one machine: one verified environment needed about 5.8
seconds because its local clock was roughly four seconds ahead, but that value
is not portable.

This check has higher diagnostic value than assuming every `VerifyErr` is
frequency control.

## Layered Diagnostic Ladder

Use controlled comparisons in this order:

1. **Recognition**: retain both original images, recognition response,
   natural width, mapped distance, and challenge ID.
2. **Captcha plaintext**: compare track count, final distance, duration,
   trusted-event flags, and UTF-8 length.
3. **WASM**: record public arguments, internal entry argument types, and
   ciphertext length.
4. **BDMS**: record the pre-sign URL, final network URL, generator input, and
   selected internal inputs without hardcoding dynamic arrays.
5. **Transport**: compare exact sent URL bytes, body hash/length, content type,
   header order, HTTP version/TLS profile, DNS/CDN route, and source IP.
6. **Timing**: compare `tmp`, server `x-tt-timestamp`, actual elapsed time, and
   challenge age.
7. **Business state**: only after captcha `code == 200` continue the login or
   protected business request.

A particularly strong differential test is to send the exact locally produced
URL and body from the reconnaissance browser. If that unmodified request
passes, image recognition, track payload, WASM ciphertext, and local signature
are already valid; focus on transport, timing, or session state. Inspect the
actual network URL first, because a browser interceptor may append a second
`a_bogus` and invalidate the comparison.

Do not infer success from `/captcha/get` returning `code == 200` or a generic
message. The decisive evidence is the final `/captcha/verify` response, such
as `code == 200`, `data == null`, and a success message.

## Evidence To Retain

Keep a compact artifact set for the latest attempt:

- login request and parsed fresh decision;
- token request/response and selected mssdk branch;
- `/captcha/get` URL/response and server timestamp;
- original background and slider images;
- recognition response, raw x, mapped distance, and track summary;
- raw/patched plaintext and WASM argument metadata;
- final verify URL, body, request headers, response, and body hash;
- failure-layer classification.

Do not write user credentials, captcha-service tokens, or reusable session
secrets into the skill reference or committed examples.

## Acceptance Criteria

The implementation is complete only when:

1. zero-argument or config-driven execution obtains a fresh decision without
   manual iframe copying;
2. final execution is browser-free and does not require a browser profile;
3. the number branch, coordinate mapping, WASM UTF-8 length, BDMS environment,
   and server-clock wait have focused tests or retained diagnostics;
4. at least two fresh end-to-end runs return final captcha success;
5. all temporary browser breakpoints and hooks used for reconnaissance are
   removed.
