---
name: web-protocol-recovery
description: >-
  先排除非协议任务：Camoufox/浏览器截图、点击、QA、回归测试、页面自动化，普通 REST/GraphQL API client，skill/opencode/MCP 配置，前端/CSS/格式化/重命名/安全头/市场介绍，都不触发；即使出现 Camoufox、GraphQL、WebSocket、protobuf、Imperva、AST 或浏览器字样，只要没有协议恢复目标，也不要触发。仅在用户明确要恢复、定位、验证、交付、逆向、还原、抓入口或协议复现 Web/小程序协议行为时触发；协议信号包括 sign/token/header/cookie/challenge/JSVMP/WASM/验证码/Akamai Bot Manager/River Security/瑞数/Reese84/响应解码/字体映射/会话协议，或 browser-free Python collector。统一授权、分类、侦察路由后，再按需读取内部 Chromium+CloakBrowser、Camoufox、WeChat、hook、AST、verifier、akamai、river-security、reese84、iv8、python-node、pure-python 或 Python delivery Provider。单点 hook/入口定位/已知 AST、Node/jsdom 补环境、iv8 工件、纯 Python signer、完整验证码协议复现、River Security 412/$_ts/S-T Cookie、Akamai sensor/cookie 状态机、Reese84 challenge/cookie/x-d-token 状态机或已有抖音 BDMS 纯 Python 维护也从本入口走快速路径，不升全链路 collector。
argument-hint: "<target URL | request/source sample | artifact directory> [evidence|local-proof|compact-replay|collector]"
---

# Web Protocol Recovery

web-protocol-recovery is the only public reverse skill, and only when protocol-recovery intent is explicit. It owns intake, scope, project root, evidence, provider routing, acceptance, and final delivery. Internal providers are modules, not peer skills.

Architecture contract: `references/methodology/architecture.md`. It defines web-protocol-recovery as the decision hub, Providers as internal skills, and `web-protocol-recovery-simple` as the only landing layout.

## TL;DR

先用下面的人话规则做内部判断；协议任务的对外回复仍必须从四行机器头开始：

1. 用户只想“看 sign / token / 请求入口”时，先交 `evidence`：找真实请求、入口、状态来源或阻塞点，不写 collector。
2. 用户给了 HAR、源码、固定向量、响应样本，先走 `evidence-reuse` 或 `local-proof`，能不开浏览器就不开。
3. 用户明确说“不上线 / 本地证明 / 固定向量”，保持离线；不要要 live replay、账号、项目目录或请求预算。
4. 用户说小程序、Camoufox、Cloak、WebSocket、protobuf 等，只决定 `route` 或 gate，不自动升级到完整采集器。
5. **协议任务常规动作默认执行、不打断确认**：浏览器 recon、live 请求、写 `projectRoot`（未指定则用 cwd）、用户已给的 cookie/session、协议所需验证码 submit、合理规模采集。内部记账即可，不要把这些写进 `nextAsk`。
6. **仅两类动作先确认再做**：装依赖（`pip`/`npm` 等）、执行目标站 JS/WASM/HTML（`executionPolicy`）。
7. 最终 live egress（HTTP 请求、WebSocket handshake、sent frame）只能由 Python collector / local protocol client 发出；浏览器、JS、WASM、iv8 只能当窄工件生成器。
8. 简单只读证据任务走 Phase 0 的 Read-Only Evidence Fast Path，不要让用户填完整表。
9. **写文件前硬纪律**：证据只进 `<projectRoot>/js_reverse_cache/**`（按需建子目录）；禁止 OS temp / AppData temp 当主存储；iv8 交付默认 `utils/logger.py`；非空 sign / 单次 200 / 过期 cookie 都不是成功。

Plain terms:

| Term | Meaning |
|---|---|
| gate family | what blocks replay |
| route | selected Provider or `evidence-reuse` |
| implementation mode | `iv8`, `python-node`, or `pure-python` |
| canonical mutation point | where the wire payload is finally changed |
| success shape | smallest deliverable |
| engine provenance | which browser/runtime produced an ID |

Cite stable section names, not line numbers; line numbers drift after edits.

Skill self-check after edits: `python scripts/preflight.py` from this skill root.

## Non-Negotiables

First response and every subsequent gated turn begin with these four lines. `route` is a short Provider ID or `evidence-reuse`, never a file path, gate family, strategy, or profile. Inline local-proof includes `acceptanceTest` and `result`. Exception: for a non-trigger boundary response, do not emit the four-line protocol header; state that the request is outside web-protocol-recovery and name the nearest normal workflow or skill.
```
shape: <evidence|local-proof|compact-replay|collector>
route: <selected Provider or evidence-reuse>
nextAsk: <none | missing sample/context | executionPolicy only>
nextRead: <paths per read-budget>
```

Header meanings: `shape` is deliverable depth; `route` is the selected Provider or `evidence-reuse`; `nextAsk` is almost always `none`—only missing technical samples, or the two hard stops (dependency install / target-code execution); `nextRead` lists exact paths allowed by the read budget. Per-shape scripts and gated overlays live in `references/methodology/success-shape-scripts.md`.

Policy overlays (case read, scope/budget accounting, Chrome auto-traffic **recording**, runtime cleanup) remain owned by `references/methodology/success-shape-scripts.md`. They are **accounting/lifecycle rules**, not user-confirmation prompts, except where `executionPolicy` still stops.

1. Final delivery is browser-free. Python owns live egress (HTTP requests, WebSocket handshakes, and sent frames); local JS/WASM/iv8 only as narrow artifact generators.
2. Evidence precedes implementation: real request, moving state, mutation point, one objective acceptance test.
3. One `projectRoot` and `web-protocol-recovery-simple`. Default `projectRoot` to the current working directory when the user did not name a folder; do not re-ask cwd vs custom. Providers never choose another landing path or project shape.
4. All dynamic evidence (recon dumps, challenge JS/HTML, screenshots, browser state, probes, net logs, MCP exports) writes only under `<projectRoot>/js_reverse_cache/**`. Never default to `%TEMP%`, `AppData\Local\Temp`, `opencode` temp roots, skill directories, or any path outside the approved project root.
5. Load only the selected provider and at most one provider-local reference per work order. Case bundles and every expansion follow `references/methodology/read-budget.md`.
6. Browser engines/profiles are lifecycle-serialized. IDs never cross engine/session/target boundaries.
7. **Standing approval (default for explicit protocol tasks):** browser recon, live egress, writes under `projectRoot`, user-supplied cookies/session, protocol-needed verifier submits, and bounded scale are already approved—execute them, do not re-ask. Confirm only **dependency install** and **target-code execution** (target-supplied JS/WASM/HTML). Never invent or export secrets the user did not supply; case-library writeback still needs a yes.
8. When delivery uses iv8 (or the iv8 silent helper), also create `utils/logger.py` (optional `loguru` with PrintLogger fallback). Progress logs use `logger.info`; do not paste loguru/print fallbacks into every main script.

## Phase 0: Intake

Do not paste the full intake form on the first reply. Use the four-line template above; `nextAsk` is usually `none` or only missing technical samples. Put dependency-install / target-code-execution only when those actions are about to happen.

If the user gives no success shape, default to `shape: evidence`. Choose `route` by the strongest Phase 2 signal, then **start the smallest next action** under operator standing approval.

First-turn routing rules choose `shape` and `route`. Under Non-Negotiables item 7, an explicit protocol-recovery task auto-grants browser recon, live egress, writes under default `projectRoot`, user-supplied session use, protocol-needed verifier submits, and bounded scale. It still does **not** auto-grant dependency install or target-code execution.

| Signal | First-turn decision |
|---|---|
| Supplied artifacts or an exact registry case | Prefer `route: evidence-reuse`; a URL alone never authorizes browser launch. |
| Explicit offline / local / fixed-vector wording | Use `shape: local-proof` and stay offline until a named blocker requires one implementation Provider. |
| Platform/runtime wording | Miniapp -> `route: wechat-miniapp`; explicit Camoufox -> `route: camoufox`; neither upgrades to `collector`. |
| Known implementation boundary or explicit implementation Provider request | Use the named Provider route only when the boundary/artifact is named, such as `route: browser-hooks`, `route: ast`, `route: python-node` with `strategy: env-patch`, `route: iv8`, or `route: pure-python`; otherwise stay evidence first. |
| Captcha family signals | Named captcha vendors (Geetest, TCaptcha/TDC, Yidun, Shumei, Yunpian, Tianyu, Dingxiang, Ctrip, Aliyun Captcha, ByteDance VerifyCenter) are verifier-priority evidence. Choose `route: verifier` only when paired with a sampled captcha round, protocol endpoint/field, semantic verifier failure, or a named active verifier delivery artifact. A lone `w` / `data` / `token` param, or generic `403` plus the word captcha, is evidence first. Field-level detail: verifier `PROVIDER.md` `Select When`. |
| Vendor-family signals (`akamai`, `river-security`, `reese84`) | Route to a protocol owner only when a vendor-native marker has independent corroboration from a second surface (network, script, cookie transition, transport, or business consumer); River Security needs two independent observed markers. Generic `403` / `412` / H2 reset, one cookie name, an Imperva label or error 15, an alias tag such as `alias:ruishu`, and a user guess ("怀疑瑞数") are never sufficient. Otherwise stay evidence first. Fresh URL recon starts with Chromium unless explicit Camoufox/SpiderMonkey/engine-level criteria are present. Marker lists and negative signals: each Provider's `Select When` / `Do Not Select When`. |
| Existing Douyin Web BDMS pure-Python maintenance | Use `route: pure-python` with `profile: douyin-abogus-native` only when the named target, existing complete implementation, and fixed BDMS trace all hold; from-zero recovery or unknown version/entry/layout stays on normal routes. Conditions: `profiles/douyin-abogus-native.md` `Select When`. |

Fallback rules:

1. Generic `403`, `412`, CAPTCHA, obfuscation, GraphQL, WebSocket, or protobuf wording is not a Camoufox criterion; use `shape: evidence` and the smallest matching route/gate.
2. Mixed signals resolve to the smallest offline step when samples are enough; otherwise start the smallest live recon under standing approval. Do not paste a full intake form or invent missing target URLs/samples.
3. Non-protocol tasks such as public API client generation, ordinary HTTP debugging, browser QA/screenshot/click tests, ordinary AST format/rename, Camoufox regression without protocol recovery, MCP/OpenCode config, UI/CSS work, or skill create/optimize/score are non-triggers; return the boundary instead of forcing a route.

Read-Only Evidence Fast Path:

Use this path when all conditions hold: `shape: evidence`; supplied artifact, request snippet, source sample, registry metadata, or static question is enough for the next step; no browser navigation, live egress, target-code execution, dependency install, or file write is needed yet.

Allowed actions: emit the four-line header, use `route: evidence-reuse` unless reading one selected Provider `PROVIDER.md` or one bounded Provider-local reference is the smallest next read, inspect supplied text/files and bounded references, name the request/function/state source/blocker, and ask only missing sample/context fields. Do **not** ask for `projectRoot`, write mode, live replay approval, request budget, artifact retention, or full authorization on this path.

When the next step needs browser/live/write work, leave the fast path and **just do it** under standing approval (record work-order fields internally; do not pause for user confirmation). Still stop and put `executionPolicy` in `nextAsk` before dependency install or target-code execution.

Before navigation, live egress, session use, writes, target-code execution, or dependency install, **record** the applicable fields from `references/methodology/provider-work-order.md` (internal bookkeeping). For protocol tasks under standing approval, auto-fill: `browserReconAllowed=true`, `browserNavigationSideEffectsApproved=true`, `liveReplayAllowed=true`, reasonable `requestBudget`, `artifactPolicy` under `js_reverse_cache/**`, `accountOrSessionUse` from user-supplied material, `projectRoot=cwd` when unset. **Still deny by default:** `executionPolicy.targetCodeExecution` and `executionPolicy.dependencyInstall` until the user confirms those two. Pre-egress accounting and Chrome automatic-traffic **recording** stay canonical; route switches never reset them.

Smallest success shape:

| Shape | Deliverable |
|---|---|
| `evidence` | request, initiator, function, state source, or precise blocker |
| `local-proof` | fixed vectors, decode, restored source, or callable helper; a saved helper always reports vector acceptance state, artifact path, and SHA-256 |
| `compact-replay` | short root `main.py`, often with a narrow runtime helper |
| `collector` | stable browser-free Python path with bounds |

Local-proof can run pure data transforms on supplied samples offline. Executing target-supplied JS/WASM/HTML remains target-code execution and still requires the `executionPolicy` confirmation even when no live egress is allowed.

Default scripts: `references/methodology/success-shape-scripts.md`.

## Phase 1: Project Root Gate

Before first save: read `references/methodology/project-layout.md`. If the user named a folder, use it; otherwise **default to cwd** and proceed (do not ask cwd vs custom). Record absolute `projectRoot`, `web-protocol-recovery-simple`, write mode, allowed paths. Read-only evidence may continue with `writeMode=no-write`.

## Phase 2: Evidence Or Recon

Prefer supplied artifacts or one registry case before opening a browser. Fresh recon picks exactly one route:

| Route | Signal | Provider entry |
|---|---|---|
| `chromium-recon` | Ordinary Web; Cloak/指纹/fingerprint/anti-detection/stealth browser wording starts here as a Chromium-tier question | `references/providers/reconnaissance/chromium-recon/PROVIDER.md` |
| `camoufox` | Explicit Camoufox, or engine-level/SpiderMonkey/Camoufox instrumentation, or untrustworthy Cloak result | `references/providers/reconnaissance/camoufox/PROVIDER.md` |
| `wechat-miniapp` | WMPF / WeChatAppEx / AppService / miniapp WebView / `127.0.0.1:62000` / WMPFDebugger | `references/providers/reconnaissance/wechat-miniapp/PROVIDER.md` |

CloakBrowser is a Chromium recon tier, not a `route`. Fingerprint-browser, Cloak, stealth, anti-detection, or busy-Chrome wording does not select `camoufox`; it selects `chromium-recon` with an optional Cloak tier. Use `camoufox` only for explicit Camoufox/SpiderMonkey/engine-level criteria or after a Cloak result is captured and recorded as untrustworthy. A busy Chrome profile or an occupied visible Chrome is a tool blocker, not target evidence; record it and do not touch that browser. Final live egress still belongs to Python.

Chromium recon (standing approval already covers launch; no user gate pause):

| Step | Action | Rule |
|---|---|---|
| 1 | `chrome-devtools` baseline | Capture ordinary request/initiator evidence, then park Chrome. |
| 2 | `js-reverse` mutation | Explicitly call `launch_browser`; headless is preferred unless the user asks for visible ordinary Chrome. |
| 3 | Optional Cloak tier | Use only for 指纹/Cloak/stealth wording or observed fingerprint evidence; this stays inside `chromium-recon`. |

Fresh ordinary Web targets need steps 1 and 2 before the final collector. Skip a half only with a real tool blocker or documented exception (`evidence-reuse`, offline `local-proof`, or non-Chromium route). "No ordinary window" may skip only the visible DevTools window; `js-reverse` remains required. Close `js-reverse` before any later `camoufox` route. `js-reverse` has no auto-launch default; after `close_browser`, relaunch headless before further actions. A brief relaunch flash is OK; persistent headful after acceptance is a blocker.

## Phase 3: Gate Family

Choose exactly one primary gate family: `signer` · `challenge` · `verifier` · `decode` · `session` · `transport`. Record other blockers as secondary gates; platform labels such as miniapp are not gate families. `akamai`, `river-security`, and `reese84` are routes, not gate families: their primary gate is usually `challenge`, with `transport` or `session` recorded as secondary when the evidence shows that blocker.

Canonical mutation order: wire request -> interceptor -> bootstrap asset -> exposed helper -> runtime egress -> WASM export -> server challenge -> response-refreshed state -> frame encoder.

## Phase 4: Providers

Read `references/methodology/provider-work-order.md` and issue one bounded work order. The architecture contract keeps global methodology in web-protocol-recovery; Provider files are capability manuals only:

| Need | Route | Role | Entry |
|---|---|---|---|
| Known observation boundary, reversible hook | `browser-hooks` | protocol-recovery technique | `references/providers/protocol-recovery/browser-hooks/PROVIDER.md` |
| Whole-file/source structure recovery | `ast` | protocol-recovery technique | `references/providers/protocol-recovery/ast/PROVIDER.md` |
| Captcha protocol / verifier / slider / point-click / WAF captcha gateway | `verifier` | protocol owner | `references/providers/protocol-recovery/verifier/PROVIDER.md` |
| Akamai Bot Manager sensor/cookie state machine and business replay | `akamai` | protocol owner | `references/providers/protocol-recovery/akamai/PROVIDER.md` |
| River Security / 瑞数 412, `$_ts`, S/T Cookie, URL/header challenge state | `river-security` | protocol owner | `references/providers/protocol-recovery/river-security/PROVIDER.md` |
| Reese84 challenge, randomized solution path, `reese84` cookie / `x-d-token`, and business admission | `reese84` | protocol owner | `references/providers/protocol-recovery/reese84/PROVIDER.md` |
| Browser-like local runtime / XHR netLog / registry runtime case | `iv8` | implementation mode | `references/providers/implementation/iv8/PROVIDER.md`; stable Python import uses `utils/iv8_silent.import_iv8_silent()` |
| Known JS entry in Node/vm/jsdom or Node/WASM sidecar | `python-node` | implementation mode | `references/providers/implementation/python-node/PROVIDER.md`; `env-patch` is `strategy: env-patch`, not a route |
| Portable signer/decoder/checksum/serializer in Python | `pure-python` | implementation mode | `references/providers/implementation/pure-python/PROVIDER.md`; Douyin BDMS maintenance is `profile: douyin-abogus-native` |
| Stable browser-free Python delivery | `python-collector` | delivery | `references/providers/delivery/python-collector/PROVIDER.md` |

Chains are sequential and role-aware (typical: recon -> AST -> python-node/iv8/pure-python -> python-collector; verifier -> iv8/python-node/pure-python -> python-collector for captcha proof builders; akamai -> iv8/python-node -> python-collector for host-bound collectors; river-security -> python-node with `strategy: env-patch` or iv8 -> python-collector for challenge state; reese84 -> iv8/python-node -> python-collector for challenge-cookie state and business admission; or evidence-reuse -> pure-python with `profile: douyin-abogus-native` -> python-collector when an existing pure implementation only needs adaptation). Validate each result before the next order. Implementation Providers produce narrow artifacts only; protocol owners keep acceptance while implementation runs; `python-collector` is delivery and owns final live egress.

## Phase 5: Verification

Runtime load, non-empty sign, HTTP `200`, or one lucky replay is not success:

1. Fixed-output parity or named checkpoints match captured truth.
2. For `compact-replay`, one approved minimal live replay succeeds on a coherent session; for `collector`, the minimal request repeats successfully or the next cursor/page is proved before scale.
3. Content type, challenge markers, business result, and data shape pass.
4. Signatures, cookies, headers, and wrapped bodies regenerate at the canonical request boundary.
5. Page/retry/concurrency/duration scale only after a repeatable first request; under standing approval, expand within the recorded `requestBudget` without re-asking unless the user set a hard cap.
6. Preserve the delivery invariant from Non-Negotiables: Python owns final live egress; local runtimes only produce narrow artifacts.

## Case Reuse And Writeback

Selector: only `references/cases/registry.json`; only `status=verified` entries are library-selectable. Read `verificationClass` and `selectableAs` on the registry row before load: `selectableAs=proof` (`freshly-verified`) means current checked-in offline vectors/tests prove the local artifact only; it is not live-current target acceptance. `selectableAs=template` (`historical-user-attested`) is shape/process evidence only and always requires fresh current-target verification before live reuse. Match a structured exact scheme/host/port/route scope **or** the declared minimum of independent high-confidence signals (normally ≥2; verifier cases need vendor/version/subtype). When `match.requiredSignalGroups` exists, non-scope selection must also match at least one observed signal from every disjoint group; labels and repeated observations cannot satisfy two groups. A user hypothesis such as "怀疑瑞数" is not an independent high-confidence signal. If more than one verified case matches the same exact scope or the same minimum signal set, do not select by registry order; stop case reuse until a discriminator such as runtime, algorithm, product subtype, or negative signal selects exactly one case. Never match on one generic param, status, `_0x`, or SDK string. All entries resolve to one hash-bound `web-protocol-recovery-case` manifest with typed historical and current Provider stages. `freshly-verified` cases must carry executed test/evidence artifacts.

Load one selected case as `case.json` -> `PROCESS.md` -> declared puller/fixtures/tests/entry/assets within the read budget. After the active case names a concrete missing implementation fact, at most one manifest-declared `historicalReferences` file may replace one implementation/asset slot in that same case bundle. It is study-only evidence: never import, execute, copy into delivery, install its historical dependencies, or treat its old live result as current acceptance. An iv8 implementation additionally requires the Provider's accepted `api-inventory.md` gate before code use. A `python-node` evidence case has no implementation entry until fresh verification produces one. Offline vectors first; stop reuse if current evidence disagrees. A failed case does not authorize a sibling case.

Writeback after eligible verified work: read `references/methodology/case-writeback.md`. Flow: candidate summary -> user yes -> sanitize/dedupe + exact allowlist -> second confirm -> change-control. No case stores raw account/browser/HAR/private bodies, cookie/token values, or absolute local paths; current authorized state is pulled at reproduction time and kept out of the library.

## Failure Recovery

| Trigger | First fix | Still fails → stop |
|---|---|---|
| Missing target URL / sample / technical context | Ask only those fields in `nextAsk` | Do not invent the target; return precise blocker |
| About to install deps or run target JS/WASM | Put `executionPolicy` fields in `nextAsk`; stay blocked on that action only | Do not install or execute target code without confirm |
| Recon empty / no target request | Re-check route signals; one more bounded capture | Name blocker; do not open second recon engine |
| Provider `status!=complete` or acceptance fails | One corrective work order on same Provider | Switch only after naming a new mutation/gate blocker |
| Case disagrees with current evidence | Stop reuse immediately | Return to normal evidence routing; no sibling case |
| `requestBudget.remaining=0` | Offline vectors / local-proof, or raise budget internally for standing-approval protocol tasks when the user set no hard cap | If user set a hard cap, stop live egress until they raise it |
| `cleanup.complete=false` or live task resource remains | Cleanup or record approved retention IDs | Reject `status=complete` |

When the same shape must expand (Provider change only keeps the shape; larger shape should be stated, then continue under standing approval unless the user forbade upgrade), name:

```
blocker: <one sentence>
nextRead: <exactly one additional path>
why: <smallest honest move>
```

## Safety Checkpoints

🔴 CHECKPOINT · 🛑 STOP and confirm only before: **untrusted dependency install**; **target-supplied JS/WASM/HTML execution**; **bundled case-library writes**; **exporting raw account secrets the user did not supply**. Protocol-needed browser recon, live egress, project writes under `js_reverse_cache/**`, user-supplied session use, captcha protocol submits, and bounded scale **do not pause for confirmation** under standing approval. Static reads, metadata-only indexes, redacted samples, and offline deterministic tests need no pause.

Gate mapping (record vs confirm): most fields are **recorded auto-approvals**; only target code/install ↔ `executionPolicy` still **confirms**. account ↔ `accountOrSessionUse`, mutation ↔ `actionClass`, scale ↔ `requestBudget`, raw save ↔ `artifactPolicy`, recon nav ↔ `browserReconAllowed` + Chrome side-effect flags, live egress ↔ `liveReplayAllowed`.

## Do Not

- Do not skip **recording** work-order fields for browser navigation, live egress, session use, writes, target-code execution, or dependency install. Do not skip **user confirmation** for dependency install or target-code execution. Do not invent credentials the user never supplied.
- Do not put a gate family, strategy, profile, or file path in `route` (Non-Negotiables owns this).
- Do not ship browser-backed page `fetch`/CDP as the final collector.
- Do not scale page/retry/concurrency after one lucky HTTP `200`.
- Do not select `camoufox` or open a second recon engine without explicit Camoufox/SpiderMonkey/engine-level wording or recorded criteria. Fingerprint/Cloak/stealth wording, busy Chrome, a vendor name, `412`, Reese84 wording, and historical case provenance are all non-criteria (Phase 2 owns this).
- Do not route a vendor family on one marker, a label, or a guess; require independent corroboration (Phase 0 owns this).
- Do not load a sibling case after one registry match failed current evidence.
- Do not claim `complete` while task-owned resources remain live or `cleanup.complete=false`.
- Do not write task evidence outside `<projectRoot>/js_reverse_cache/**` when `projectRoot` is known, and do not treat OS temp as primary storage; if a tool forces an external absolute path, copy the artifact in immediately.
- Do not treat non-empty sign/token, one HTTP `200`, or an expired cookie/session export as semantic success.
- Do not store raw cookies/tokens/HAR/private bodies or absolute local paths in the case library, and do not mix case-library edits with darwin `results.tsv` score rows in one commit when avoidable.

Also enforced in `references/anti-patterns-playbook.md` (read it for the temptation / false-progress / self-check form): bare `print` instead of `utils/logger.py` in iv8/collector delivery; pre-created empty `js_reverse_cache/**` trees; hardcoded rotating cookies; broad hooks before a clean baseline; reversing the visible helper instead of the wire mutation point; rung-skipping escalation.

## Completion

**Light** (`evidence`/`local-proof`): shape, route, decisive evidence, blocker/next step, browser lifecycle. Local-proof always includes `acceptanceTest` and `result`; with artifact, also path and SHA-256. Pure read-only evidence does not require `分析报告.md`.

**Full** (replay/collector): gate family + provider chain; endpoint + moving state; project root + stable files; verification results; browser lifecycle; limits; case writeback offer; **and root `分析报告.md`**. Keep logs bounded and redacted; point to artifacts. Reject complete when cleanup is incomplete or when `compact-replay`/`collector` delivery wrote project files without `分析报告.md`. Template: `references/report-templates.md` section `分析报告.md`.

## References

By symptom: `references/reference-router.md`. Anti-patterns: `references/anti-patterns-playbook.md`. Discipline mini suite: `references/discipline-self-test-min.md`. Preflight: `python scripts/preflight.py`. Methodology: `architecture.md`, `provider-work-order.md`, `project-layout.md`, `case-writeback.md`, `success-shape-scripts.md`, `read-budget.md`. Providers: `references/providers/`; cases: `references/cases/`. Nothing below overrides this file's scope, safety, lifecycle, layout, or verification.
