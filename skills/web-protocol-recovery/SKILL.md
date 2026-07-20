---
name: web-protocol-recovery
description: >-
  唯一 Web 与小程序协议逆向入口。用于 sign/token/header/cookie/challenge/JSVMP/WASM/验证码/响应解码/WebSocket/GraphQL/protobuf/字体映射/会话协议及 browser-free Python collector。统一授权、分类、侦察路由后，再按需读取内部 Chromium+CloakBrowser、Camoufox、WeChat、hook、AST、env-patch、iv8、verifier 或 Python collector Provider。单点 hook/入口定位/已知 AST 或补环境也从本入口走快速路径，不升全链路 collector。不要为这些能力另选顶层逆向 skill。不触发：普通 HTTP/API 故障排查、静态抓取或公开文档 API client、浏览器 QA、仅安全头审计、纯 UI/CSS/组件开发、与协议无关的通用编程，以及 skill 本身的描述/评测维护（改走 skill-creator）。
argument-hint: "<target URL | request/source sample | artifact directory> [evidence|local-proof|compact-replay|collector]"
---

# Web Protocol Recovery

web-protocol-recovery is the only public reverse skill. It owns intake, scope, project root, evidence, provider routing, acceptance, and final delivery. Internal providers are modules, not peer skills.

## TL;DR

先用下面的人话规则做内部判断；对外回复仍必须从四行机器头开始：

1. 用户只想“看 sign / token / 请求入口”时，先交 `evidence`：找真实请求、入口、状态来源或阻塞点，不写 collector。
2. 用户给了 HAR、源码、固定向量、响应样本，先走 `evidence-reuse` 或 `local-proof`，能不开浏览器就不开。
3. 用户明确说“不上线 / 本地证明 / 固定向量”，保持离线；不要要 live replay、账号、项目目录或请求预算。
4. 用户说小程序、Camoufox、Cloak、WebSocket、protobuf 等，只决定 `route` 或 gate，不自动升级到完整采集器。
5. 真要打开浏览器、发请求、写文件、用账号、装依赖、提交验证码或扩大采集前，先停下补 gate。
6. 最终 live HTTP 只能由 Python collector 发出；浏览器、JS、WASM、iv8 只能当窄工件生成器。
7. 简单只读证据任务走 Phase 0 的 Read-Only Evidence Fast Path，不要让用户填完整表。

Plain terms: **gate family** = what blocks replay; **route** = selected Provider or `evidence-reuse`, never a gate family; **canonical mutation point** = where the wire payload is finally changed; **success shape** = smallest deliverable; **engine provenance** = which browser/runtime produced an ID. Cite stable section names, not line numbers; line numbers drift after edits.

## Non-Negotiables

First response and every subsequent gated turn begin with these four lines. `route` is a short Provider ID or `evidence-reuse`, never a file path or gate family. Inline local-proof includes `acceptanceTest` and `result`.
```
shape: <evidence|local-proof|compact-replay|collector>
route: <selected Provider or evidence-reuse>
nextAsk: <only fields needed now>
nextRead: <paths per read-budget>
```

Human meaning of the four-line header:

| Field | Plain-language meaning |
|---|---|
| `shape` | Deliverable depth: evidence only, local proof, minimal replay, or full collector. |
| `evidence` | Find the real request, initiator, state writer, mutation point, or precise blocker; do not write the collector. |
| `local-proof` | Prove fixed vectors, decode, restored source, or helper output offline; do not send live HTTP. |
| `compact-replay` | Build the smallest browser-free replay, usually one short `main.py`, then verify one approved request. |
| `collector` | Build the stable browser-free Python collector with explicit bounds. |
| `route` | Tool path: `evidence-reuse`, `chromium-recon`, `camoufox`, `wechat-miniapp`, or one implementation Provider. |
| `nextAsk` | The only user fields or approvals needed before the next gated action. |
| `nextRead` | The exact internal reference path(s) allowed by the read budget. |

Four mandatory policy overlays when their trigger is hit — case read, scope/budget reset, Chrome auto-traffic gate, and denied live replay — are owned by `references/methodology/success-shape-scripts.md`.

1. Final delivery is browser-free. Python owns live HTTP; local JS/WASM/iv8 only as narrow artifact generators.
2. Evidence precedes implementation: real request, moving state, mutation point, one objective acceptance test.
3. One `projectRoot` and `web-protocol-recovery-simple/v1`. Providers never choose another landing path.
4. Load only the selected provider and at most one provider-local reference per work order. Case bundles and every expansion follow `references/methodology/read-budget.md`.
5. Browser engines/profiles are lifecycle-serialized. IDs never cross engine/session/target boundaries.
6. Account state, verifier submission, mutations, target-code execution, raw secrets, dependency installs, and collection scale need explicit confirmation.

## Phase 0: Intake

Do not paste the full intake form on the first reply. Use the four-line template above; `nextAsk` lists only fields required by the next gated action.

If the user gives no success shape, default to `shape: evidence`. Choose `route` by the strongest Phase 2 signal, then ask only for gates needed before the next gated action.

First-turn routing rules:

1. Supplied artifacts or an exact registry case beat fresh recon: start with `route: evidence-reuse`; a URL alone never authorizes a browser launch.
2. Explicit offline/local/vector wording beats heavier routing: use `shape: local-proof` and stay offline until a named blocker requires one implementation Provider.
3. Platform/runtime words choose only the route, not the deliverable depth: miniapp means `route: wechat-miniapp`; Camoufox means `route: camoufox`; neither upgrades to `collector` by itself.
4. Generic `403`, `412`, CAPTCHA, obfuscation, GraphQL, WebSocket, or protobuf wording is not a Camoufox criterion; use `shape: evidence` and the smallest matching route/gate.
5. Mixed signals resolve to the smallest offline step. Put missing approvals in `nextAsk`; do not paste a full intake form, launch a browser, replay live HTTP, or scaffold a collector on the first turn.
6. Non-protocol tasks such as public API client generation, ordinary HTTP debugging, browser QA, UI/CSS work, or skill editing are non-triggers; return the boundary instead of forcing a route.

Read-Only Evidence Fast Path:

Use this path when all conditions hold: `shape: evidence`; supplied artifact, request snippet, source sample, registry metadata, or static question is enough for the next step; no browser navigation, live HTTP/WebSocket send, account/session use, target-code execution, dependency install, file write, raw artifact save, verifier submission, mutation, retry, scale-up, or retention is proposed.

Allowed actions: emit the four-line header, use `route: evidence-reuse` unless reading one selected Provider `PROVIDER.md` or one bounded Provider-local reference is the smallest next read, inspect supplied text/files and bounded references, name the request/function/state source/blocker, and ask only missing sample/context fields. Do not execute Provider tools or ask for `projectRoot`, write mode, live replay approval, request budget, artifact retention, or full authorization until a gated action becomes necessary.

If any fast-path condition becomes false, stop before the action and record the applicable gate below. The fast path never grants browser navigation, live egress, writes, account/session use, or broader collection.

Before navigation, live HTTP, account/session use, target-code execution, dependency install, or writes, record the applicable gate from `references/methodology/provider-work-order.md`: authorization basis, exact scheme/host/port/absolute-route-prefix and query scope, action class, account/session disposition, browser recon, navigation side-effects, live replay, shared request budget, artifact policy, and execution policy. An omitted gate is deny/offline, never implied approval. Unknown authorization, non-exact scope, or empty budget stays offline. Pre-egress: canonicalize scope, reserve one mutually exclusive unit; a consumed unit is never refunded. Route switches never reset budget or automatic-observation state. Public reachability is not account/mutation/collection permission.

Chrome baseline blocked unless `browserNavigationSideEffectsApproved=yes` AND `automaticObservationStopThreshold>=1`. Observed automatic destinations are evidence, never authorization.

Smallest success shape:

| Shape | Deliverable |
|---|---|
| `evidence` | request, initiator, function, state source, or precise blocker |
| `local-proof` | fixed vectors, decode, restored source, or callable helper; a saved helper always reports vector acceptance state, artifact path, and SHA-256 |
| `compact-replay` | short root `main.py`, often with a narrow runtime helper |
| `collector` | stable browser-free Python path with bounds |

Default scripts: `references/methodology/success-shape-scripts.md`.

## Phase 1: Project Root Gate

🔴 CHECKPOINT · 🛑 STOP before first save: read `references/methodology/project-layout.md`. Use user folder or ask once (cwd vs custom). Record absolute `projectRoot`, `web-protocol-recovery-simple/v1`, write mode, allowed paths. Read-only evidence may continue with `writeMode=no-write`.

## Phase 2: Evidence Or Recon

Prefer supplied artifacts or one registry case before opening a browser. Fresh recon picks exactly one route:

| Route | Signal | Provider entry |
|---|---|---|
| `chromium-recon` | Ordinary Web; Cloak/指纹/fingerprint/anti-detection/stealth browser wording | `references/providers/reconnaissance/chromium-recon/PROVIDER.md` |
| `camoufox` | Explicit Camoufox, or engine-level/SpiderMonkey/Camoufox instrumentation, or untrustworthy Cloak result | `references/providers/reconnaissance/camoufox/PROVIDER.md` |
| `wechat-miniapp` | WMPF / WeChatAppEx / AppService / miniapp WebView / `127.0.0.1:62000` / WMPFDebugger | `references/providers/reconnaissance/wechat-miniapp/PROVIDER.md` |

Chromium ladder: Chrome DevTools baseline -> Chrome parked -> js-reverse normal Chrome -> Cloak only after explicit selection or fingerprint/observer evidence -> close js-reverse before Camoufox.

## Phase 3: Gate Family

Choose exactly one primary gate family: `signer-gated` · `challenge-gated` · `verifier-gated` · `decode-gated` · `session-gated` · `transport-gated`. Record other blockers as secondary gates; platform labels such as miniapp are not gate families.

Canonical mutation order: wire request -> interceptor -> bootstrap asset -> exposed helper -> runtime egress -> WASM export -> server challenge -> response-refreshed state -> frame encoder.

## Phase 4: Providers

Read `references/methodology/provider-work-order.md` and issue one bounded work order:

| Need | Route | Provider entry |
|---|---|---|
| Known observation boundary, reversible hook | `browser-hooks` | `references/providers/implementation/browser-hooks/PROVIDER.md` |
| Whole-file/source structure recovery | `ast` | `references/providers/implementation/ast/PROVIDER.md` |
| Known JS entry in Node/vm/jsdom | `env-patch` | `references/providers/implementation/env-patch/PROVIDER.md` |
| Browser-like local runtime / XHR netLog / registry runtime case | `iv8` | `references/providers/implementation/iv8/PROVIDER.md` |
| OCR / slider / click / coordinates | `verifier` | `references/providers/implementation/verifier/PROVIDER.md` |
| Stable browser-free Python delivery | `python-collector` | `references/providers/implementation/python-collector/PROVIDER.md` |

Chains are sequential (typical: recon -> AST -> env/iv8 -> collector). Validate each result before the next order. `env-patch` = minimal Node/jsdom gaps for a known entry; `iv8` = browser-like host when that is the smallest faithful runtime.

## Phase 5: Verification

Runtime load, non-empty sign, HTTP `200`, or one lucky replay is not success:

1. Fixed-output parity or named checkpoints match captured truth.
2. One approved minimal live replay succeeds on a coherent session.
3. Content type, challenge markers, business result, and data shape pass.
4. Signatures, cookies, headers, and wrapped bodies regenerate at the canonical request boundary.
5. Page/retry/concurrency/duration scale only after repeatable first request + confirmation.
6. Final live HTTP is browser-free; local JS/WASM/iv8 only as narrow artifact generators.

## Case Reuse And Writeback

Selector: only `references/cases/registry.json`; only `status=verified` entries are selectable. Match a structured exact scheme/host/port/route scope **or** ≥2 independent high-confidence signals (verifier cases need vendor/version/subtype). Never match on one generic param, status, `_0x`, or SDK string. All entries resolve to one hash-bound `web-protocol-recovery-case/v1` manifest. `historical-user-attested` cases always require fresh current-target verification; `freshly-verified` cases must carry executed test/evidence artifacts.

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

Gate mapping: account ↔ `accountOrSessionUse`, mutation ↔ `actionClass`, scale ↔ `requestBudget`, raw save ↔ `artifactPolicy`, target code/install ↔ `executionPolicy`, recon nav ↔ `browserReconAllowed` + Chrome side-effect approval, live HTTP ↔ `liveReplayAllowed`.

## Do Not

- Do not launch a browser before recording gates required for that navigation.
- Do not put a gate family (`signer-gated`, etc.) or file path in `route`.
- Do not ship browser-backed page `fetch`/CDP as the final collector.
- Do not scale page/retry/concurrency after one lucky HTTP `200`.
- Do not open Camoufox on ordinary Web without its Phase 2 criteria.
- Do not open both Chromium and Camoufox recon without a Camoufox selection criterion.
- Do not load a sibling case after one registry match failed current evidence.
- Do not claim `complete` while task-owned resources remain live or `cleanup.complete=false`.
- Do not store raw cookies/tokens/HAR/private bodies or absolute local paths in the case library.
- Do not treat public reachability as account, mutation, or collection permission.

Full anti-pattern detail: `references/anti-patterns-playbook.md`.

## Completion

**Light** (`evidence`/`local-proof`): shape, route, decisive evidence, blocker/next step, browser lifecycle. Local-proof always includes `acceptanceTest` and `result`; with artifact, also path and SHA-256.

**Full** (replay/collector): gate family + provider chain; endpoint + moving state; project root + stable files; verification results; browser lifecycle; limits; case writeback offer. Keep logs bounded and redacted; point to artifacts. Reject complete when cleanup is incomplete.

## References

By symptom: `references/reference-router.md`. Anti-patterns: `references/anti-patterns-playbook.md`. Methodology: `provider-work-order.md`, `project-layout.md`, `case-writeback.md`, `success-shape-scripts.md`, `read-budget.md`. Providers: `references/providers/`; cases: `references/cases/`. Nothing below overrides this file's scope, safety, lifecycle, or verification.
