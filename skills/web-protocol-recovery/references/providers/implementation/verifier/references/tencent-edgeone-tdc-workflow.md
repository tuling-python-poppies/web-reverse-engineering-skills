# Tencent EdgeOne / TCaptcha TDC Workflow

Use this workflow for Tencent CAPTCHA protocol chains built around a fresh
`cap_union_prehandle` response, dynamic `tdc.js`, TDC telemetry, POW, and
`cap_union_new_verify`. It covers EdgeOne `click_verify` as well as the shared
TDC stage used by interactive TCaptcha variants.

## Recognition Signals

Strong signals include:

- `captcha.eo.qq.com` or Tencent CAPTCHA static domains;
- `/cap_union_prehandle` and `/cap_union_new_verify`;
- response fields such as `sess`, `sid`, `comm_captcha_cfg`, `dyn_show_info`,
  `tdc_path`, and `pow_cfg`;
- runtime APIs `TDC.setData`, `TDC.getData(true)`, and `TDC.getInfo()`;
- verify fields `collect`, `tlg`, `eks`, `ans`, `pow_answer`, and
  `pow_calc_time`;
- a final response containing `errorCode`, `ticket`, and `randstr`.

Do not route an ordinary EdgeOne 403, 412, or JavaScript Cookie challenge here
unless the CAPTCHA endpoints or TDC state machine are present. Unknown
multi-layer protection stays in web-protocol-recovery's normal challenge/cookie
routes; locating an unknown TDC entry or browser call stack requires a new
bounded work order to the internal reconnaissance or `browser-hooks` Provider.

## Required End State

The browser-free chain is:

```text
optional protected-page first hop
  -> fresh cap_union_prehandle
  -> download that round's dynamic tdc.js
  -> construct one observed iframe environment in iv8
  -> reproduce the observed TDC.setData sequence
  -> TDC.getData(true) + TDC.getInfo().info
  -> solve that round's POW
  -> cap_union_new_verify
  -> optional ticket/Cookie business-page check
```

The browser is an evidence source, not the delivered runtime. The final script
must obtain new challenge state and dynamic JavaScript on every run.

## Same-Round State

Keep all of the following in one HTTP Session and one run directory:

- page cookies and request identity when the protected page contributes them;
- prehandle `sess`, `sid`, `pow_cfg`, `tdc_path`, and `dyn_show_info`;
- the exact dynamic TDC response downloaded from that `tdc_path`;
- iframe globals, widget-derived `ft`, tracker data, `collect`, and `eks`;
- POW answer, verify form, verify response, and optional ticket replay.

Never combine an old TDC file with a new `sess`, reuse `collect/eks`, or carry a
POW answer into another challenge. Treat a failed or consumed verify as the end
of that round unless direct evidence proves retry semantics.

An optional protected-page first hop can fail independently because of
transport admission. Record the failure and decide whether the CAPTCHA layer
actually depends on its Cookie. Do not silently create a second Session for
prehandle or verify.

## Browser Evidence Collection

Collect evidence in this order:

1. Clear network capture and trigger one fresh challenge.
2. Save prehandle request/response, final dynamic TDC URL, TDC response, verify
   form, verify response, and the request initiator.
3. Hook `TDC.setData`, `TDC.getData`, and `TDC.getInfo` before the challenge
   action. Preserve argument order, return values, and stacks.
4. Read `dyn_show_info.show_type` before deciding whether this is a slider,
   image challenge, or `click_verify`.
5. Capture the actual iframe baseline: frame URL, `document.referrer`,
   `window.name`, `TCaptchaSid`, `TCaptchaReferrer`,
   `TCaptchaIframeClientPos`, viewport, screen, UA/Client Hints, and observable
   `window.top` behavior.
6. Export one browser fingerprint baseline. Do not merge navigator from one
   browser, screen from another, and TLS identity from a third.

The most useful dynamic observation is the exact `setData` sequence. A
verified `click_verify` branch used this semantic order:

```javascript
TDC.setData({isNewEntry: 1});
TDC.setData(trackerPayload);
TDC.setData({ft});
const collect = decodeURIComponent(TDC.getData(true) || "");
const eks = (TDC.getInfo() || {}).info || "";
```

Do not assume this order for a new widget build without capturing it. Preserve
the order when it is observed because TDC keeps internal mutable state.

## Widget Data And `ft`

The outer widget can build data that is later fed into TDC. In the verified
branch, the tracker payload contained:

- `slideValue`;
- `verifyBtnPos`;
- `opAreaPos`;
- `clientSize`.

Capture these values at the `setData` boundary instead of reconstructing them
from property names alone. Positions and viewport dimensions are layout
values, not universal constants.

The `ft` value was produced by a small widget webpack module before the final
`setData`. Extract and execute the current bundle's producer in iv8. A module
index observed in one build, or one previously returned `ft` string, is only a
locator clue; neither is a stable protocol constant.

## iv8 Reconstruction

Use web-protocol-recovery's internal `iv8` Provider as the execution backend
while this Provider remains the owner of the CAPTCHA state machine and success
criteria.

1. Load a minimal HTML document using the observed iframe URL as `baseURL`.
2. Apply one exported browser baseline and only evidence-backed environment
   patches.
3. Set challenge globals before evaluating dynamic TDC. Important examples are
   `TCaptchaSid`, `TCaptchaReferrer`, `TCaptchaIframeClientPos`, and
   `window.name`.
4. Evaluate the fresh TDC source and assert that `getData` and `getInfo` exist.
5. Execute the current widget `ft` producer.
6. Reproduce the captured `setData` calls in order.
7. Drain required timers/microtasks, then read `collect` and `eks`.
8. Reject empty output before sending verify.

Keep UA, `sec-ch-ua`, platform, timezone, screen, and the HTTP impersonation
profile coherent. When `curl_cffi` is needed for transport admission, use the
same identity as the iv8 baseline rather than changing only the TLS profile.

### Environment Differential

When TDC initializes but verify returns a generic risk code, do not add random
DOM stubs. Instrument safe property reads in the current TDC build and compare
the browser and iv8 property sets.

Prioritize evidence-backed differences in:

- navigator and UAData;
- screen, viewport, DOM geometry, and frame hierarchy;
- performance/resource timing;
- Permissions, WebGPU, network information, Audio, WebGL, and WebRTC;
- referrer, frame URL, `window.name`, and cross-origin `window.top` semantics.

Use selective AST rewriting or engine-level tracing and cap the rewrite set.
Record browser-only and iv8-only properties separately. Similar access counts
do not prove equivalent values or exception behavior. `window.top` can remain
a hard residual because a real CAPTCHA iframe observes a cross-origin parent
while a local runtime often aliases the current Window; isolate that mismatch
instead of rewriting the whole environment around it.

## Passive And Active Behavior

Do not import slider assumptions into `click_verify`.

- Start from the smallest behavior model observed at the real `setData`
  boundary. A verified EdgeOne `click_verify` branch passed with passive
  tracker data and no dense trusted pointer path.
- Keep a diagnostic active mode that emits trusted iv8 pointer/mouse events
  when browser evidence shows those events are consumed.
- For a real slider, follow the slider branch: solve the image, keep coordinate
  systems separate, use trusted input, and align path duration with wall time.
- In either branch, let real time elapse before verify when the browser does.
  Do not write a long duration into telemetry and submit immediately.

Collect length is not a quality target. Fresh successful runs can legitimately
produce different lengths. Tune state and semantics, not padding.

### Runtime Compression

Optimize wait time only after a stable same-round implementation passes. For a
`click_verify` passive branch, do not preserve a long browser dwell as a fixed
sleep without proving that the server requires it.

Use fresh challenges to probe a descending ladder such as:

```text
known passing wait -> 2.0 -> 1.5 -> 1.0 -> 0.5 -> 0 seconds
```

For every point, download a new TDC, solve a new POW, and require final Tencent
success. Record requested wait, local behavior elapsed time, process wall time,
POW time, collect length, and the final business fields. A verified passive
EdgeOne branch continued to pass at zero additional wait; this is evidence for
that `click_verify` branch, not a global TCaptcha constant.

Keep mode-aware defaults:

- passive `click_verify` may default to zero extra wait only after at least two
  consecutive fresh successes;
- active/trusted-event mode keeps the minimum wall time established by its
  event path and rejects an explicitly shorter value;
- image sliders preserve real recognition, drag, and track duration even when
  a passive branch can run immediately;
- retain an explicit wait override for conservative replay and version-change
  diagnosis.

Separate performance layers before changing code. If local TDC behavior takes
about a few hundred milliseconds but the command is slow, inspect first-hop,
prehandle, dynamic-TDC download, verify, page-check, TLS, and POW separately.
A TLS failure before prehandle never reached the CAPTCHA timing gate and must
not be counted as evidence that a tested wait value failed. Do not cache old
`sess`, TDC, telemetry, or POW to reduce network time.

## POW And Verify Form

Use the algorithm named by the current `pow_cfg`. For the observed MD5 branch,
find a nonce such that:

```text
md5(prefix + decimal_nonce) == pow_cfg.md5
```

Send the matching concatenated answer and measured calculation time. Do not
copy either from a browser sample.

The common verify form is:

```text
collect=<decoded TDC.getData(true) output>
tlg=<exact length of the transmitted collect string>
eks=<TDC.getInfo().info>
sess=<fresh prehandle sess>
ans=<answer object for the current show_type>
pow_answer=<fresh solved value>
pow_calc_time=<measured calculation time>
```

For an observed `click_verify` branch, `ans` used
`DynAnswerType_TIME`. Derive this from the current widget/prehandle branch; do
not reuse it for a slider or image challenge.

Preserve the browser's content type, Origin, Referer, and form serialization.
Save a redacted request manifest plus exact local `collect` and `eks` files.

## Success And Failure Diagnosis

Prehandle `state == 1` only means challenge setup succeeded. Verify HTTP 200 is
also insufficient.

Tencent verification is successful only when all are true:

```text
errorCode == "0"
ticket is non-empty
randstr is non-empty
```

Treat `errorCode == "12"` as a broad risk rejection, not proof that one named
field is wrong. Diagnose it in this order:

1. stale or cross-round `sess/tdc.js/collect/eks/POW`;
2. wrong `show_type`, answer shape, `setData` values, call order, or `ft`;
3. fake elapsed time or events that finish after the request is sent;
4. iframe/global/environment first divergence;
5. UA, Client Hints, Cookie, Origin/Referer, TLS/HTTP2, proxy, or source-IP
   incoherence;
6. hard residuals such as cross-origin `window.top` or WebGL branches.

If an exact locally generated request succeeds when replayed from the browser,
the cryptographic and serialization layers are likely correct; focus on
Session, timing, transport, and environment admission. If browser and local
both fail, refresh the challenge before changing the model.

## Artifacts To Retain

Create one immutable directory per attempt under project `js_reverse_cache/`:

- initial protected page or first-hop error;
- prehandle response and exact request URL;
- dynamic `tdc.js` and its source URL;
- browser baseline and TDC environment-diff summary;
- captured `setData/getData/getInfo` sequence;
- current widget `ft` producer;
- `collect`, `eks`, tracker summary, and POW metadata;
- redacted verify request, raw verify response, and final summary;
- optional ticket replay result kept separate from CAPTCHA success.

Do not copy one-time `sess`, ticket, cookies, full fingerprint dumps, or target
secrets into this skill.

## Acceptance Criteria

The implementation is complete only when:

1. each run obtains a fresh prehandle response and its dynamic TDC;
2. final execution is Python + iv8 with no browser process;
3. challenge globals, widget data, POW, telemetry, and verify remain same-round;
4. success uses `errorCode == "0"` plus non-empty ticket and randstr;
5. at least two consecutive fresh runs pass;
6. optional business-page replay is reported separately from CAPTCHA success;
7. Python files pass `py_compile` and reconnaissance hooks/routes are removed.
