# Verifier / Captcha Provider

## Select When

- The target is verifier-gated: a distinct captcha, proof, or one-shot verification round authorizes the business request.
- The user provides captcha request samples, images, `/get` / `/load` / `/convert` / `/verify` / `/check` links, or fields such as `challenge`, `token`, `randomKey`, `track`, `cb`, `data`, `w`, `captchaBody`, or `cyfreso`.
- The work is to reproduce the captcha protocol locally: slider, point-click, ordered text click, icon click, WAF captcha gateway, TDC telemetry, device sidecar, behavior track, proof body, or the final verify/check request.

## Do Not Select When

- The user only wants generic OCR, image classification, or a slider gap without verify/check protocol replay.
- The target is a generic WAF/cookie challenge with no captcha endpoints, images, or verifier response.
- The task is only browser hook code, generic signer entry location, ordinary Aliyun RPC signing, or non-captcha Douyin `a_bogus`.
- Live verify is requested without work-order permission for both live replay and verifier action class.

web-protocol-recovery owns intake, route choice, authorization, `projectRoot`, allowed paths, acceptance, runtime lifecycle, live-egress budget, and final delivery status. This Provider owns captcha family selection, same-round verifier state, perception/proof construction, platform-specific captcha workflows, and verifier success criteria.

## Family Router

Read only the selected family reference after the work order names one matching signal. Do not preload the whole tree.

| Signals | Reference |
|---|---|
| Tencent EdgeOne / TCaptcha / `cap_union_prehandle` / dynamic `tdc.js` / `TDC.getData(true)` / `cap_union_new_verify` / `errorCode=12` | `references/tencent-edgeone-tdc-workflow.md` |
| Ctrip `captcha/v4` / `risk_inspect` / `verify_jigsaw` / `verify_icon` | `references/ctrip-captcha-v4-workflow.md` |
| Baidu Passport spin/rotate V2 / `passport.baidu.com/cap/init` / `/cap/style` / `/cap/img` / `/cap/log` / `spin-0` / `backstr` / `ext.p` / `en_conf` / `cv=submit` | `references/baidu-passport-spin-v2-workflow.md` |
| ByteDance VerifyCenter / `/captcha/get` / `/captcha/verify` / `captchaBody` / `cyfreso` / BDMS+mssdk slider | `references/bytedance-verifycenter-workflow.md` |
| Aliyun Captcha V2 / `InitCaptchaV2` / `VerifyCaptchaV2` / `DeviceConfig` / `Log2` / `Log3` / `T001` / FeiLin daily update | `references/aliyun-captcha-v2-workflow.md` |
| Geetest GT3 / `register-slide` / `gettype.php` / `fullpage.9.x` / `slide.7.x` / `ajax.php` | `references/geetest-gt3-workflow.md` |
| Geetest GT4 / `/load` / `lot_number` / `pow_detail` / `payload` / `w` / `/verify` | `references/geetest-gt4-workflow.md` |
| Geetest GT4 nine-grid / `risk_type=nine` / `captcha_type=nine` / `imgs` / `ques` / `nine_nums` | `references/geetest-gt4-nine-grid-workflow.md` |
| Generic slider family selection: Yidun, Shumei, Yunpian, 360 Tianyu, Dingxiang, GT3/GT4 | `references/slide-captcha-overview.md` |
| Netease Yidun / `NECaptcha` / `api/v3/get` / `api/v3/check` / `cb` / `data` | `references/yidun-workflow.md` |
| Shumei / `captcha1.fengkongcloud.cn` / `register` / `fverify` / `rid` / DES params | `references/shumei-workflow.md` |
| Yunpian / `captcha.yunpian.com` / `captcha/get` / `captcha/verify` / `i` / `k` / `cb` | `references/yunpian-workflow.md` |
| 360 Tianyu / `captcha.jiagu.360.cn` / `auth` / `check` / `report` / `rsa_1.js` | `references/tianyu360-workflow.md` |
| Unknown captcha or one-shot verifier with no platform match | `references/replay-playbook.md` first, then return a blocker for new focused reference if still unclassified |

## Core Rules

1. Freeze one coherent verifier round: setup response, images/assets, cookies, callback/random keys, verifier token, proof-builder state, final verify/check request, and final response.
2. Never mix tokens, images, callbacks, proof fields, telemetry, sidecar logs, or dynamic scripts across neighboring rounds.
3. The final proof is the verifier server response, not OCR confidence, slider distance, non-empty `w`, HTTP `200`, or a decoded payload.
4. Point-click tasks separate prompt recognition, coordinate localization, coordinate mapping, and encrypted proof packaging.
5. Slider tasks separate original/restored image distance, displayed coordinate, submitted coordinate, behavior track, declared duration, and real wall-clock wait.
6. Sidecar/device models such as Aliyun FeiLin/TDC require full same-session profile, sparse token/counter, timestamps, and telemetry. A valid checksum on one packet does not prove cross-packet state consistency.
7. Browser automation is evidence only unless the user explicitly asked for UI automation. Final delivery is protocol replay plus local helpers; Python owns live HTTP egress.
8. When platform workflow requires iv8 or JS runtime, route the execution backend through web-protocol-recovery's internal `iv8` Provider or `python-node` with `strategy: env-patch`.
9. If the user only wants the verification layer, stop at captcha success and do not add business replay to the entry point or success condition.
10. `verify_has_w=true`, non-empty proof fields, or outer `status=success` with semantic verifier failure is current-round failure evidence, not success. Re-check perception, coordinate mapping, proof packaging, and current bundle entry before any retry.
11. GT4 point-click/ordered-text code must treat public `captchaObj` as a wrapper until proven otherwise. Discover the current bundle's submitter/registry path from live/cache evidence; do not ship hardcoded old module IDs or stale `$_BEP -> $_BBFs` assumptions.
12. Dynamic evidence, images, decoded payloads, forms, and responses must stay under assigned `js_reverse_cache/**`; do not write into this Provider directory.

## Optional Scripts

Provider-local scripts are reusable templates, not direct in-place runners. Copy or adapt them into the task project/cache before execution. Scripts that submit verifier requests require an explicit work order with live replay and verifier action approval; GT4 replay templates fail closed unless called with `--confirm-live-verify`.

| Script | Use |
|---|---|
| `references/providers/implementation/python-node/scripts/gt4_bundle_helper.js` | GT4 current bundle metadata, PoW, GCT, and `w` artifact helper. It receives `gctSource` or `biht`; it does not download target resources. |
| `references/providers/delivery/python-collector/scripts/verifier/gt4_replay.py` | GT4 same-round Python + Node helper replay template; Python owns `/load`, images, GCT, and `/verify`. |
| `references/providers/delivery/python-collector/scripts/verifier/gt4_pure_replay.py` | GT4 pure Python `/load -> OCR -> PoW/GCT/AES/RSA -> /verify` delivery template. |
| `scripts/aliyun_v2_profile_diff.py` | Aliyun V2 DeviceConfig/Log2/token/profile diff helper |

## Acceptance

All applicable checks must pass:

1. Family, product version, subtype, and request chain are identified; old/new vendor generations are not mixed.
2. One-round binding is proved: all tokens, images, callbacks, dynamic scripts, sidecars, proof fields, and verify/check requests belong to the same round.
3. Offline vectors or fixed-input regressions pass for encryption/signature/serializer/coordinate transforms when available.
4. Perception output includes confidence or an explicit fail-closed reason; low/tied confidence cannot authorize live verify by itself.
5. Live verify, when approved, returns platform-specific semantic success, such as Tencent `errorCode == "0"` with ticket/randstr, Aliyun `VerifyCode == "T001" && VerifyResult == true`, GT4 `data.result == "success"`, or the selected reference's success marker.
6. Linked business request succeeds only if it is in scope and explicitly required after captcha success.
7. Python owns final live egress; any local JS/iv8/WASM helper is a narrow artifact generator and has no browser/profile runtime dependency.

## Failure Recovery

| Trigger | First fix | Still fails -> stop |
|---|---|---|
| Family unclassified | Use endpoint/field/image/success-marker signals and one reference | Return blocker for a new focused reference |
| Round fields mixed or stale | Recapture one coherent round | Blocker: same-round state |
| OCR/CV weak or tied | Use platform-specific preprocessing/manual coordinate fallback/independent corroboration | No live verify |
| Verify semantic fail | Diff state, coordinate space, behavior timeline, proof packaging, sidecar, and transport in that order | Do not submit repeated guesses on one challenge |
| GT4 `w` generated but `data.result=fail` | Confirm current `gcaptcha4.js` version and submitter path before changing OCR only | Do not treat non-empty `w` or `status=success` as proof |
| Sidecar/device logs omitted | Add same-session telemetry proof per selected reference | Do not blame track first |
| Live verify denied | Stay offline with fixtures and proof inputs | No verifier submission |
| Platform workflow needs JS/iv8 host semantics | Return an internal work-order blocker for `iv8` or `python-node` with `strategy: env-patch` | Do not turn browser UI automation into delivery |

## Exit

Return: selected captcha family/reference, one-round state summary, proof-input shape, perception confidence, offline vector status, live verify state or offline-only blocker, artifact paths/hashes, sidecar/telemetry status, budget consumed/remaining, cleanup state, and next hub action (`python-collector`, `iv8`, `python-node` with `strategy: env-patch`, another verifier work order, or stop).
