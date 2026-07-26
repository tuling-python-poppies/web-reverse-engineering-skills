---
name: web-protocol-recovery
description: >-
  唯一 Web 与小程序协议逆向入口。用于 sign/token/header/cookie/challenge/JSVMP/WASM/验证码/Akamai Bot Manager/River Security/瑞数/响应解码/WebSocket/GraphQL/protobuf/字体映射/会话协议及 browser-free Python collector。统一授权、分类、侦察路由后，再按需读取内部 Chromium+CloakBrowser、Camoufox、WeChat、hook、AST、env-patch、iv8、verifier、akamai、river-security、douyin-abogus-native 或 Python collector Provider。单点 hook/入口定位/已知 AST、补环境、完整验证码协议复现、River Security 412/$_ts/S-T Cookie、Akamai sensor/cookie 状态机或已有抖音 BDMS 纯 Python 维护也从本入口走快速路径，不升全链路 collector。不要为这些能力另选顶层逆向 skill。不触发：普通 HTTP/API 故障排查、静态抓取或公开文档 API client、浏览器 QA、仅安全头审计、纯 UI/CSS/组件开发、与协议无关的通用编程，以及 skill 本身的描述/评测维护（改走 skill-creator）。
argument-hint: "<target URL | request/source sample | artifact directory> [evidence|local-proof|compact-replay|collector]"
---

# Web Protocol Recovery

web-protocol-recovery is the only public reverse skill. It owns intake, scope, project root, evidence, provider routing, acceptance, and final delivery. Internal providers are modules, not peer skills.

Architecture contract: `references/methodology/architecture.md`. It defines web-protocol-recovery as the decision hub, Providers as internal skills, and `web-protocol-recovery-simple/v1` as the only landing layout.

## TL;DR

先用下面的人话规则做内部判断；协议任务的对外回复仍必须从四行机器头开始：

1. 用户只想“看 sign / token / 请求入口”时，先交 `evidence`：找真实请求、入口、状态来源或阻塞点，不写 collector。
2. 用户给了 HAR、源码、固定向量、响应样本，先走 `evidence-reuse` 或 `local-proof`，能不开浏览器就不开。
3. 用户明确说“不上线 / 本地证明 / 固定向量”，保持离线；不要要 live replay、账号、项目目录或请求预算。
4. 用户说小程序、Camoufox、Cloak、WebSocket、protobuf 等，只决定 `route` 或 gate，不自动升级到完整采集器。
5. 真要打开浏览器、发请求、写文件、用账号、装依赖、提交验证码或扩大采集前，先停下补 gate。
6. 最终 live egress（HTTP 请求、WebSocket handshake、sent frame）只能由 Python collector / local protocol client 发出；浏览器、JS、WASM、iv8 只能当窄工件生成器。
7. 简单只读证据任务走 Phase 0 的 Read-Only Evidence Fast Path，不要让用户填完整表。
8. **写文件前硬纪律**：证据只进 `<projectRoot>/js_reverse_cache/**`（按需建子目录）；禁止 OS temp / AppData temp 当主存储；iv8 交付默认 `utils/logger.py`；非空 sign / 单次 200 / 过期 cookie 都不是成功。

Plain terms: **gate family** = what blocks replay; **route** = selected Provider or `evidence-reuse`, never a gate family; **canonical mutation point** = where the wire payload is finally changed; **success shape** = smallest deliverable; **engine provenance** = which browser/runtime produced an ID. Cite stable section names, not line numbers; line numbers drift after edits.

Skill self-check after edits: `python scripts/preflight.py` from this skill root.

## Non-Negotiables

First response and every subsequent gated turn begin with these four lines. `route` is a short Provider ID or `evidence-reuse`, never a file path or gate family. Inline local-proof includes `acceptanceTest` and `result`. Exception: for a non-trigger boundary response, do not emit the four-line protocol header; state that the request is outside web-protocol-recovery and name the nearest normal workflow or skill.
```
shape: <evidence|local-proof|compact-replay|collector>
route: <selected Provider or evidence-reuse>
nextAsk: <only fields needed now>
nextRead: <paths per read-budget>
```

Header meanings: `shape` is deliverable depth; `route` is the selected Provider or `evidence-reuse`; `nextAsk` lists only gates or fields needed before the next action; `nextRead` lists exact paths allowed by the read budget. Per-shape scripts and gated overlays live in `references/methodology/success-shape-scripts.md`.

Four mandatory policy overlays when their trigger is hit — case read, scope/budget reset, Chrome auto-traffic gate, and denied live replay — are owned by `references/methodology/success-shape-scripts.md`.

1. Final delivery is browser-free. Python owns live egress (HTTP requests, WebSocket handshakes, and sent frames); local JS/WASM/iv8 only as narrow artifact generators.
2. Evidence precedes implementation: real request, moving state, mutation point, one objective acceptance test.
3. One `projectRoot` and `web-protocol-recovery-simple/v1`. Providers never choose another landing path or project shape.
4. All dynamic evidence (recon dumps, challenge JS/HTML, screenshots, browser state, probes, net logs, MCP exports) writes only under `<projectRoot>/js_reverse_cache/**`. Never default to `%TEMP%`, `AppData\Local\Temp`, `opencode` temp roots, skill directories, or any path outside the approved project root.
5. Load only the selected provider and at most one provider-local reference per work order. Case bundles and every expansion follow `references/methodology/read-budget.md`.
6. Browser engines/profiles are lifecycle-serialized. IDs never cross engine/session/target boundaries.
7. Account state, verifier submission, mutations, target-code execution, raw secrets, dependency installs, and collection scale need explicit confirmation.
8. When delivery uses iv8 (or the iv8 silent helper), also create `utils/logger.py` (optional `loguru` with PrintLogger fallback). Progress logs use `logger.info`; do not paste loguru/print fallbacks into every main script.

## Phase 0: Intake

Do not paste the full intake form on the first reply. Use the four-line template above; `nextAsk` lists only fields required by the next gated action.

If the user gives no success shape, default to `shape: evidence`. Choose `route` by the strongest Phase 2 signal, then ask only for gates needed before the next gated action.

First-turn routing rules:

1. Supplied artifacts or an exact registry case beat fresh recon: start with `route: evidence-reuse`; a URL alone never authorizes a browser launch.
2. Explicit offline/local/vector wording beats heavier routing: use `shape: local-proof` and stay offline until a named blocker requires one implementation Provider.
3. Platform/runtime words choose only the route, not the deliverable depth: miniapp means `route: wechat-miniapp`; Camoufox means `route: camoufox`; neither upgrades to `collector` by itself.
4. Strong captcha protocol signals choose `route: verifier`: captcha request samples, images, `/get` / `/load` / `/convert` / `/verify` / `/check`, `challenge`, `token`, `randomKey`, `track`, `cb`, `data`, `w`, `captchaBody`, `cyfreso`, Geetest GT3/GT4, Tencent TCaptcha/TDC, Yidun, Shumei, Yunpian, 360 Tianyu, Dingxiang, CSDN point-click, Ctrip captcha/v4, Aliyun Captcha V2/V3, or ByteDance VerifyCenter. Generic `403` plus the word captcha is still evidence first, not automatic solving.
5. Strong Akamai signals choose `route: akamai` only when an Akamai-native marker (`_abck`, `bm_sz`, `ak_bmsc`, `bm_s`, `bm_sv`, `sensor_data`, `/akam/13/pixel_*`, or confirmed random-path collector) has independent network/script/cookie-transition/transport corroboration. Generic `403`, `412`, H2 reset, or one cookie name is still evidence first, not Akamai proof.
6. Strong River Security signals choose `route: river-security` only when at least two independent observed markers corroborate the family: HTTP `412`, `$_ts.nsd` / `$_ts.cd`, `<script r="m">`, dynamic `_$...()` entry, server `*S` plus client `*T` cookies, protected XHR URL/header mutation, or a confirmed River Security protection script. A user guess such as "suspected RuiShu" or a generic `412` alone never routes and stays `shape:evidence` to collect HTML, headers, cookies, and script markers. River Security does not imply Camoufox; fresh URL reconnaissance starts with Chromium unless explicit Camoufox/SpiderMonkey/engine-level criteria are present.
7. Generic `403`, `412`, CAPTCHA, obfuscation, GraphQL, WebSocket, or protobuf wording is not a Camoufox criterion; use `shape: evidence` and the smallest matching route/gate.
8. Existing Douyin Web BDMS pure-Python maintenance wording chooses only `route: douyin-abogus-native` when the user names `douyin.com/aweme/v1/web/*`, `a_bogus`, an existing complete `pure_abogus.py`, and fixed BDMS 1.0.1.19 trace evidence. From-zero recovery, unknown version/entry/field layout, Hook/AST/env/iv8 requests, or non-Douyin `a_bogus` stay on the normal recon/implementation routes.
9. Mixed signals resolve to the smallest offline step. Put missing approvals in `nextAsk`; do not paste a full intake form, launch a browser, send live egress, or scaffold a collector on the first turn.
10. Non-protocol tasks such as public API client generation, ordinary HTTP debugging, browser QA, UI/CSS work, or skill editing are non-triggers; return the boundary instead of forcing a route.

Read-Only Evidence Fast Path:

Use this path when all conditions hold: `shape: evidence`; supplied artifact, request snippet, source sample, registry metadata, or static question is enough for the next step; no browser navigation, live egress, account/session use, target-code execution, dependency install, file write, raw artifact save, verifier submission, mutation, retry, scale-up, or retention is proposed.

Allowed actions: emit the four-line header, use `route: evidence-reuse` unless reading one selected Provider `PROVIDER.md` or one bounded Provider-local reference is the smallest next read, inspect supplied text/files and bounded references, name the request/function/state source/blocker, and ask only missing sample/context fields. Do not execute Provider tools or ask for `projectRoot`, write mode, live replay approval, request budget, artifact retention, or full authorization until a gated action becomes necessary.

If any fast-path condition becomes false, stop before the action and record the applicable gate below. The fast path never grants browser navigation, live egress, writes, account/session use, or broader collection.

Before navigation, live egress, account/session use, target-code execution, dependency install, or writes, record only the applicable gate fields from `references/methodology/provider-work-order.md`. An omitted gate is deny/offline. Unknown authorization, non-exact scope, empty budget, unapproved execution, unapproved artifacts, or unapproved session use stays offline. Pre-egress accounting and Chrome automatic-traffic handling are canonical in `provider-work-order.md` and `success-shape-scripts.md`; route switches never reset them. Public reachability is not account, mutation, or collection permission.

Smallest success shape:

| Shape | Deliverable |
|---|---|
| `evidence` | request, initiator, function, state source, or precise blocker |
| `local-proof` | fixed vectors, decode, restored source, or callable helper; a saved helper always reports vector acceptance state, artifact path, and SHA-256 |
| `compact-replay` | short root `main.py`, often with a narrow runtime helper |
| `collector` | stable browser-free Python path with bounds |

Local-proof can run pure data transforms on supplied samples offline. Executing target-supplied JS/WASM/HTML remains target-code execution and requires the `executionPolicy` gate even when no live egress is allowed.

Default scripts: `references/methodology/success-shape-scripts.md`.

## Phase 1: Project Root Gate

🔴 CHECKPOINT · 🛑 STOP before first save: read `references/methodology/project-layout.md`. Use user folder or ask once (cwd vs custom). Record absolute `projectRoot`, `web-protocol-recovery-simple/v1`, write mode, allowed paths. Read-only evidence may continue with `writeMode=no-write`.

## Phase 2: Evidence Or Recon

Prefer supplied artifacts or one registry case before opening a browser. Fresh recon picks exactly one route:

| Route | Signal | Provider entry |
|---|---|---|
| `chromium-recon` | Ordinary Web; Cloak/指纹/fingerprint/anti-detection/stealth browser wording starts here as a Chromium-tier question | `references/providers/reconnaissance/chromium-recon/PROVIDER.md` |
| `camoufox` | Explicit Camoufox, or engine-level/SpiderMonkey/Camoufox instrumentation, or untrustworthy Cloak result | `references/providers/reconnaissance/camoufox/PROVIDER.md` |
| `wechat-miniapp` | WMPF / WeChatAppEx / AppService / miniapp WebView / `127.0.0.1:62000` / WMPFDebugger | `references/providers/reconnaissance/wechat-miniapp/PROVIDER.md` |

CloakBrowser is a Chromium recon tier, not a `route`. Use `camoufox` only for explicit Camoufox/SpiderMonkey/engine-level criteria or after an untrustworthy Cloak result is recorded.

Chromium recon: after recon gates, fresh targets need a **mandatory paired pass** before the final collector — (1) `chrome-devtools` baseline, (2) park Chrome, (3) `js-reverse` mutation (explicit `launch_browser`; headless preferred unless user wants visible ordinary Chrome). Skip a half only with a real tool blocker or documented exception (evidence-reuse / offline local-proof / non-Chromium route). “No ordinary window” may skip only the **visible DevTools window**; js-reverse remains required. After paired pass, optional visible Cloak on 指纹/Cloak/stealth wording or fingerprint evidence; close js-reverse before any Camoufox route. js-reverse: no auto-launch default; after `close_browser`, relaunch headless before further actions; brief relaunch flash OK, persistent headful after acceptance is a blocker.

## Phase 3: Gate Family

Choose exactly one primary gate family: `signer-gated` · `challenge-gated` · `verifier-gated` · `decode-gated` · `session-gated` · `transport-gated`. Record other blockers as secondary gates; platform labels such as miniapp are not gate families. `akamai` and `river-security` are routes, not gate families: their primary gate is usually `challenge-gated`, with `transport-gated` or `session-gated` recorded as secondary when the evidence shows that blocker.

Canonical mutation order: wire request -> interceptor -> bootstrap asset -> exposed helper -> runtime egress -> WASM export -> server challenge -> response-refreshed state -> frame encoder.

## Phase 4: Providers

Read `references/methodology/provider-work-order.md` and issue one bounded work order. The architecture contract keeps global methodology in web-protocol-recovery; Provider files are capability manuals only:

| Need | Route | Provider entry |
|---|---|---|
| Known observation boundary, reversible hook | `browser-hooks` | `references/providers/implementation/browser-hooks/PROVIDER.md` |
| Whole-file/source structure recovery | `ast` | `references/providers/implementation/ast/PROVIDER.md` |
| Known JS entry in Node/vm/jsdom | `env-patch` | `references/providers/implementation/env-patch/PROVIDER.md` |
| Browser-like local runtime / XHR netLog / registry runtime case | `iv8` | `references/providers/implementation/iv8/PROVIDER.md`; stable Python import uses `utils/iv8_silent.import_iv8_silent()` |
| Existing Douyin Web BDMS 1.0.1.19 pure-Python `a_bogus` maintenance or request adapter | `douyin-abogus-native` | `references/providers/implementation/douyin-abogus-native/PROVIDER.md` |
| Akamai Bot Manager sensor/cookie state machine and business replay | `akamai` | `references/providers/implementation/akamai/PROVIDER.md` |
| River Security / 瑞数 412, `$_ts`, S/T Cookie, URL/header challenge state | `river-security` | `references/providers/implementation/river-security/PROVIDER.md` |
| Captcha protocol / verifier / slider / point-click / WAF captcha gateway | `verifier` | `references/providers/implementation/verifier/PROVIDER.md` |
| Stable browser-free Python delivery | `python-collector` | `references/providers/implementation/python-collector/PROVIDER.md` |

Chains are sequential (typical: recon -> AST -> env/iv8 -> collector; verifier -> iv8/env-patch -> python-collector for captcha proof builders; akamai -> iv8 -> python-collector for host-bound collectors; river-security -> env-patch/iv8 -> python-collector for challenge state; or evidence-reuse -> douyin-abogus-native -> python-collector when an existing pure implementation only needs adaptation). Validate each result before the next order. `env-patch` = minimal Node/jsdom gaps for a known entry; `iv8` = browser-like host when that is the smallest faithful runtime; `verifier` = captcha protocol branch and success criteria; `akamai` = Akamai Bot Manager collector/cookie/transport state machine; `river-security` = River Security 412/`$_ts`/S-T Cookie subtype selection and challenge artifact boundary; `douyin-abogus-native` = already-proved Douyin BDMS pure-Python work, not from-zero algorithm recovery. Runtime helper details, including iv8 import hygiene, live in the selected Provider docs.

## Phase 5: Verification

Runtime load, non-empty sign, HTTP `200`, or one lucky replay is not success:

1. Fixed-output parity or named checkpoints match captured truth.
2. For `compact-replay`, one approved minimal live replay succeeds on a coherent session; for `collector`, the minimal request repeats successfully or the next cursor/page is proved before scale.
3. Content type, challenge markers, business result, and data shape pass.
4. Signatures, cookies, headers, and wrapped bodies regenerate at the canonical request boundary.
5. Page/retry/concurrency/duration scale only after repeatable first request + confirmation.
6. Preserve the delivery invariant from Non-Negotiables: Python owns final live egress; local runtimes only produce narrow artifacts.

## Case Reuse And Writeback

Selector: only `references/cases/registry.json`; only `status=verified` entries are library-selectable. Read `verificationClass` and `selectableAs` on the registry row before load: `selectableAs=proof` (`freshly-verified`) may be current-target proof after offline vectors; `selectableAs=template` (`historical-user-attested`) is shape/process evidence only and always requires fresh current-target verification before live reuse. Match a structured exact scheme/host/port/route scope **or** ≥2 independent high-confidence signals (verifier cases need vendor/version/subtype). A user hypothesis such as "怀疑瑞数" is not an independent high-confidence signal. If more than one verified case matches the same exact scope or the same minimum signal set, do not select by registry order; stop case reuse until a discriminator such as runtime, algorithm, product subtype, or negative signal selects exactly one case. Never match on one generic param, status, `_0x`, or SDK string. All entries resolve to one hash-bound `web-protocol-recovery-case/v1` manifest. `freshly-verified` cases must carry executed test/evidence artifacts.

Load one selected case as `case.json` -> `PROCESS.md` -> declared puller/fixtures/tests/entry/assets within the read budget. An iv8 implementation additionally requires the Provider's accepted `api-inventory.md` gate before code use. A `python-node` evidence case has no implementation entry until fresh verification produces one. Offline vectors first; stop reuse if current evidence disagrees. A failed case does not authorize a sibling case.

Writeback after eligible verified work: read `references/methodology/case-writeback.md`. Flow: candidate summary -> user yes -> sanitize/dedupe + exact allowlist -> second confirm -> change-control. No case stores raw account/browser/HAR/private bodies, cookie/token values, or absolute local paths; current authorized state is pulled at reproduction time and kept out of the library.

## Failure Recovery

| Trigger | First fix | Still fails → stop |
|---|---|---|
| Missing auth / scope / budget for next gated action | Ask only those fields in `nextAsk`; stay offline | Do not invent scope; return precise blocker |
| Recon empty / no target request | Re-check route signals; one more bounded capture | Name blocker; do not open second recon engine |
| Provider `status!=complete` or acceptance fails | One corrective work order on same Provider | Switch only after naming a new mutation/gate blocker |
| Case disagrees with current evidence | Stop reuse immediately | Return to normal evidence routing; no sibling case |
| `requestBudget.remaining=0` | Offline vectors / local-proof only | No live egress until user raises budget |
| `cleanup.complete=false` or live task resource remains | Cleanup or record approved retention IDs | Reject `status=complete` |

When the same shape must expand (Provider change only keeps the shape; larger shape needs explicit scope confirmation), name:

```
blocker: <one sentence>
nextRead: <exactly one additional path>
why: <smallest honest move>
```

## Safety Checkpoints

🔴 CHECKPOINT · 🛑 STOP before: account secrets export; CAPTCHA/verifier/form/order/payment/mutation submit; page/retry/concurrency/rate/duration scale-up; untrusted dependency/code install; raw artifact save without approved fields; bundled case-library writes. Static reads, metadata-only indexes, redacted samples, and offline deterministic tests need no pause.

Gate mapping: account ↔ `accountOrSessionUse`, mutation ↔ `actionClass`, scale ↔ `requestBudget`, raw save ↔ `artifactPolicy`, target code/install ↔ `executionPolicy`, recon nav ↔ `browserReconAllowed` + Chrome side-effect approval, live egress ↔ `liveReplayAllowed`.

## Do Not

- Do not launch a browser before recording gates required for that navigation.
- Do not put a gate family (`signer-gated`, etc.) or file path in `route`.
- Do not ship browser-backed page `fetch`/CDP as the final collector.
- Do not scale page/retry/concurrency after one lucky HTTP `200`.
- Do not open Camoufox on ordinary Web without explicit Camoufox wording or recorded second-engine criteria.
- Do not route River Security/RuiShu to Camoufox from the vendor name, `412`, or historical case provenance alone.
- Do not open both Chromium and Camoufox recon without a Camoufox selection criterion.
- Do not load a sibling case after one registry match failed current evidence.
- Do not claim `complete` while task-owned resources remain live or `cleanup.complete=false`.
- Do not store raw cookies/tokens/HAR/private bodies or absolute local paths in the case library.
- Do not treat public reachability as account, mutation, or collection permission.
- Do not write task evidence under `%TEMP%`, `AppData\Local\Temp`, `opencode` temp roots, or any non-project path when `projectRoot` is known.
- Do not treat OS temp as primary storage; if a tool forces an absolute path outside the project, copy the artifact into `js_reverse_cache/**` immediately and stop depending on the external copy.
- Do not deliver iv8/collector scripts with only bare `print` for progress when `utils/logger.py` is the project standard.
- Do not pre-create empty `js_reverse_cache/recon|source|ast|env|iv8|akamai|samples|private` trees "for completeness".
- Do not treat non-empty sign/token, one HTTP 200, or an expired cookie/session export as semantic success.
- Do not mix case-library edits and darwin `results.tsv` score rows in the same commit when avoidable.

Full anti-pattern detail: `references/anti-patterns-playbook.md`.

## Completion

**Light** (`evidence`/`local-proof`): shape, route, decisive evidence, blocker/next step, browser lifecycle. Local-proof always includes `acceptanceTest` and `result`; with artifact, also path and SHA-256.

**Full** (replay/collector): gate family + provider chain; endpoint + moving state; project root + stable files; verification results; browser lifecycle; limits; case writeback offer. Keep logs bounded and redacted; point to artifacts. Reject complete when cleanup is incomplete.

## References

By symptom: `references/reference-router.md`. Anti-patterns: `references/anti-patterns-playbook.md`. Discipline mini suite: `references/discipline-self-test-min.md`. Preflight: `python scripts/preflight.py`. Methodology: `architecture.md`, `provider-work-order.md`, `project-layout.md`, `case-writeback.md`, `success-shape-scripts.md`, `read-budget.md`. Providers: `references/providers/`; cases: `references/cases/`. Nothing below overrides this file's scope, safety, lifecycle, layout, or verification.
