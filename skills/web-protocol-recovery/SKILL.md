---
name: web-protocol-recovery
description: >-
  先排除非协议任务：Camoufox/浏览器截图、点击、QA、回归测试、页面自动化，普通 REST/GraphQL API client，skill/opencode/MCP 配置，前端/CSS/格式化/重命名/安全头/市场介绍，都不触发；即使出现 Camoufox、GraphQL、WebSocket、protobuf、Imperva、AST 或浏览器字样，只要没有协议恢复目标，也不要触发。仅在用户明确要恢复、定位、验证、交付、逆向、还原、抓入口、实现或协议复现 Web/小程序协议行为时触发；协议信号包括 sign/token/header/cookie/challenge/JSVMP/WASM/验证码/Akamai Bot Manager/River Security/瑞数/Reese84/响应解码/字体映射/会话协议，或 browser-free Python collector。明确要求实现时按 collector 交付处理。统一授权、分类、侦察路由后，再按需读取内部 Chromium+CloakBrowser、Camoufox、WeChat、hook、AST、verifier、akamai、river-security、reese84、iv8、python-node、pure-python 或 Python delivery Provider。单点 hook/入口定位/已知 AST、Node/jsdom 补环境、iv8 工件、纯 Python signer、完整验证码协议复现、River Security 412/$_ts/S-T Cookie、Akamai sensor/cookie 状态机、Reese84 challenge/cookie/x-d-token 状态机或已有抖音 BDMS 纯 Python 维护也从本入口走快速路径，不升全链路 collector。
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
5. **已选 shape 内的常规动作默认执行、不打断确认**：隔离浏览器 recon、只读 live 请求、写 `projectRoot`（未指定则用 cwd）、使用用户已给的 cookie/session、协议所需 verifier submit、首次记录预算内的合理规模采集。内部记账即可，不要把这些写进 `nextAsk`。
6. **`executionPolicy` 有两个 hard stop**：装依赖（`pip`/`npm` 等）、在本地 runtime 主动执行目标站 JS/WASM/HTML。普通隔离 recon 浏览器按页面正常加载目标代码属于 browser recon，不重复触发本地 target-code gate。
7. **scope/governance 仍需确认**：业务 `mutation-submit`（表单、下单、支付、账号变更等）、扩大 success shape、提高已记录预算、raw secret 持久化/导出、case-library 写回。
8. 最终 live egress（HTTP 请求、WebSocket handshake、sent frame）只能由 Python collector / local protocol client 发出；浏览器、JS、WASM、iv8 只能当窄工件生成器。
9. 简单只读证据任务走 Phase 0 的 Read-Only Evidence Fast Path，不要让用户填完整表。
10. **写文件前硬纪律**：证据只进 `<projectRoot>/js_reverse_cache/**`（按需建子目录）；禁止 OS temp / AppData temp 当主存储；iv8 交付默认 `utils/logger.py`；非空 sign / 单次 200 / 过期 cookie 都不是成功。
11. **实现请求的默认行为**：用户明确要求实现或完整代码时，直接选择 `shape: collector`；先生成稳定项目文件和离线向量证明，再处理当前 session/profile/track 等运行态。缺运行态只能阻塞 live acceptance，不能阻止先生成实现骨架。

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
nextAsk: <none | missing sample/context | executionPolicy | mutation-submit | scope-expansion | raw-secret-handling | case-writeback>
nextRead: <paths per read-budget>
```

Header meanings: `shape` is deliverable depth; `route` is the selected Provider or `evidence-reuse`; `nextAsk` is almost always `none` and names only the immediate missing technical input, execution hard stop, or scope/governance decision; `nextRead` lists exact paths allowed by the read budget. Per-shape scripts and gated overlays live in `references/methodology/success-shape-scripts.md`.

Policy overlays (case read, scope/budget accounting, Chrome auto-traffic **recording**, runtime cleanup) remain owned by `references/methodology/success-shape-scripts.md`. Routine fields are accounting/lifecycle rules. `executionPolicy`, business mutation, shape/budget expansion, raw-secret handling, and case writeback retain their explicit confirmation rules.

1. Final delivery is browser-free. Python owns live egress (HTTP requests, WebSocket handshakes, and sent frames); local JS/WASM/iv8 only as narrow artifact generators.
2. Evidence precedes implementation: real request, moving state, mutation point, one objective acceptance test.
3. One `projectRoot` and `web-protocol-recovery-simple`. Default `projectRoot` to the current working directory when the user did not name a folder; do not re-ask cwd vs custom. Providers never choose another landing path or project shape.
4. All dynamic evidence (recon dumps, challenge JS/HTML, screenshots, browser state, probes, net logs, MCP exports) writes only under `<projectRoot>/js_reverse_cache/**`. Never default to `%TEMP%`, `AppData\Local\Temp`, `opencode` temp roots, skill directories, or any path outside the approved project root.
5. Load only the selected provider and at most one provider-local reference per work order. Case bundles and every expansion follow `references/methodology/read-budget.md`.
6. Browser engines/profiles are lifecycle-serialized. IDs never cross engine/session/target boundaries.
7. **Standing approval (default for explicit protocol tasks, within the selected shape):** browser recon, read-only live egress, writes under `projectRoot`, use of user-supplied cookies/session, protocol-needed `verifier-submit`, and scale within the initially recorded immutable request budget are already approved—execute them, do not re-ask. Never auto-promote to `mutation-submit`, a larger shape, or a larger budget. Local target-code execution and dependency installation use `executionPolicy`; raw-secret handling and case-library writeback keep their governance confirmations.
8. When delivery uses iv8 (or the iv8 silent helper), also create `utils/logger.py` (optional `loguru` with PrintLogger fallback). Progress logs use `logger.info`; do not paste loguru/print fallbacks into every main script.

## Phase 0: Intake

Do not paste the full intake form on the first reply. Use the four-line template above; `nextAsk` is usually `none` or only missing technical samples. Name a confirmation field only when its exact hard stop or scope/governance action is about to happen.

If the user gives no success shape, default to `shape: evidence`. Choose `route` by the strongest Phase 2 signal, then **start the smallest next action** under operator standing approval.

First-turn routing rules choose `shape` and `route`. Under Non-Negotiables item 7, an explicit protocol-recovery task grants routine actions only inside that shape. It does **not** grant local target-code execution, dependency installation, business mutation, shape/budget expansion, raw-secret handling, or case-library writeback.

| Signal | First-turn decision |
|---|---|
| 明确要求“实现/写完整代码” | 选择 `shape: collector`；若命中已验证 implementation case，先用 `evidence-reuse` 读取案例原语和流程，再执行其 required current provider chain。 |
| Supplied artifacts or an exact registry case | Prefer `route: evidence-reuse`. A bare URL with no protocol-recovery intent is not enough; an explicit protocol-recovery request naming that URL may start bounded recon under standing approval unless the user requested offline/no-browser work. |
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

When the next step needs routine browser/live/write work inside the selected shape, leave the fast path and **just do it** under standing approval (record work-order fields internally; do not pause for user confirmation). Stop only when the next exact action matches one of the declared `nextAsk` confirmation kinds.

Before navigation, live egress, session use, writes, target-code execution, or dependency install, **record** the applicable fields from `references/methodology/provider-work-order.md` (internal bookkeeping). For routine protocol work, auto-fill: `actionClass=read-only` (or `verifier-submit` only for a protocol-needed verifier round), browser flags, `liveReplayAllowed=true`, one positive immutable request budget, redacted artifact policy under `js_reverse_cache/**`, supplied-session use, and the resolved absolute cwd when `projectRoot` is unset. Keep `mutation-submit` and all confirmation kinds blocked until the matching user decision. Pre-egress accounting and Chrome automatic-traffic **recording** stay canonical; route switches never reset or replenish the budget.

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

Prefer supplied artifacts or one registry case before opening a browser.

### WAF HTML 即时路由触发器

当业务 API 返回以下信号时，该响应是 Aliyun WAF Captcha V2 Challenge，而非普通业务错误：

- HTTP 200 但 `Content-Type: text/html`
- 且 body 包含 `aliyun_waf_aa` / `aliyun_waf_bb` meta 标签
- 或 body 包含 `var requestInfo = {` + 必需字段 `sceneId/traceid/token/userId/userUserId`
- 或 body 包含 `<textarea id="renderData"`

**立即动作**：不要猜测签名算法、不要尝试换 header、不要重试。直接切换到：
```
shape: collector
route: verifier
nextAsk: none
nextRead: references/providers/protocol-recovery/verifier/PROVIDER.md
```
然后由 verifier Provider 的 Family Router 按 `InitCaptchaV2` / `StaticPath sg.xxx` 信号选择 `aliyun-captcha-v2-workflow.md`。

注意：某些站点（如 PZDS）需要先带登录 token + 业务签名头才能触发 WAF HTML 响应（否则返回 `NOT_LOGGED_IN` JSON 而非 WAF HTML）。如果业务 API 返回 `401/code=NOT_LOGGED_IN`，不要归因为 WAF 问题——先补齐登录态和业务签名。

Fresh recon picks exactly one route:

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
2. For `compact-replay`, one recorded minimal live replay succeeds on a coherent session; for `collector`, the minimal request repeats successfully or the next cursor/page is proved before scale.
3. Content type, challenge markers, business result, and data shape pass.
4. Signatures, cookies, headers, and wrapped bodies regenerate at the canonical request boundary.
5. Page/retry/concurrency/duration scale only after a repeatable first request and only within the initially recorded `requestBudget`; exhaustion or any larger shape/budget requires `scope-expansion` confirmation.
6. Preserve the delivery invariant from Non-Negotiables: Python owns final live egress; local runtimes only produce narrow artifacts.

## Case Reuse And Writeback

### 多轮上下文检查点

每完成一个 Phase（或在 verifier 链路中每完成一个关键工件），必须输出一个检查点摘要；当 `writeMode` 已启用时写入 `js_reverse_cache/checkpoint.md`，纯只读 fast path / `writeMode=no-write` 阶段先在回复中报告，不为写 checkpoint 打破 no-write：

```markdown
## Checkpoint [timestamp]
- shape: collector
- route: verifier
- gate: verifier (Aliyun V2)
- 已有证据：
  - [ ] AK/SECRET 提取完成
  - [ ] Init+Log2+Log3+Verify 完整轮次捕获
  - [ ] DeviceConfig AES 验证
  - [ ] field21 算法确认
  - [ ] stream codec 验证
  - [ ] 轨迹 fixture 捕获
- 当前阻塞：[xxx]
- 下一步：[xxx]
- 关键文件状态：
  - js_reverse_cache/aliyun_v2_evidence/init_round.json: [存在/缺失]
  - utils/aliyun_v2/t001_profile.json: [存在/缺失]
```

这个检查点服务于两个目的：
1. **上下文压缩后恢复**：当上下文窗口被截断时，先读 `js_reverse_cache/checkpoint.md` 确认当前状态，而不是从记忆中重建
2. **避免重复工作**：如果检查点显示 AK/SECRET 已提取，不要再次提取

**浏览器残留进程恢复提示**：若任务因浏览器启动失败（进程残留）而暂停，checkpoint 需额外记录：
```markdown
- 浏览器状态：
  - 残留进程：[有/无]（上次启动失败错误特征：exit code / 错误信息）
  - 恢复步骤：先释放浏览器进程（杀 chrome.exe + 清理 profile 目录），再重新启动采集
```


Selector: only `references/cases/registry.json`; only `status=verified` entries are library-selectable. Read `verificationClass` and `selectableAs` on the registry row before load: `selectableAs=proof` (`freshly-verified`) means current checked-in offline vectors/tests prove the local artifact only; it is not live-current target acceptance. `selectableAs=template` (`historical-user-attested`) is shape/process evidence only and always requires fresh current-target verification before live reuse. Match a structured exact scheme/host/port/route scope **or** the declared minimum of independent high-confidence signals (normally ≥2; verifier cases need vendor/version/subtype). When `match.requiredSignalGroups` exists, non-scope selection must also match at least one observed signal from every disjoint group; labels and repeated observations cannot satisfy two groups. A user hypothesis such as "怀疑瑞数" is not an independent high-confidence signal. If more than one verified case matches the same exact scope or the same minimum signal set, do not select by registry order; stop case reuse until a discriminator such as runtime, algorithm, product subtype, or negative signal selects exactly one case. Never match on one generic param, status, `_0x`, or SDK string. All entries resolve to one hash-bound `web-protocol-recovery-case` manifest with typed historical and current Provider stages. `freshly-verified` cases must carry executed test/evidence artifacts.

Load one selected case as `case.json` -> `PROCESS.md` -> declared puller/fixtures/tests/entry/assets within the read budget. After the active case names a concrete missing implementation fact, at most one manifest-declared `historicalReferences` file may replace one implementation/asset slot in that same case bundle. It is study-only evidence: never import, execute, copy into delivery, install its historical dependencies, or treat its old live result as current acceptance. An iv8 implementation additionally requires the Provider's accepted `api-inventory.md` gate before code use. A `python-node` evidence case has no implementation entry until fresh verification produces one. Offline vectors first; stop reuse if current evidence disagrees. A failed case does not authorize a sibling case.

`caseKind=implementation` is different from a historical reference. For a selected verified implementation case, a manifest-declared `entry.py` or equivalent implementation artifact is an allowed narrow starting point after the current case match; only files declared as `historicalReferences` are study-only and forbidden from delivery. The entry is still not the final collector unless the case explicitly says so: assemble the stable project files named by `PROCESS.md`, preserve the case's live-state gates, and run the current acceptance chain.

## Fresh-Machine Case Delivery

Implementation cases can provide protocol primitives without the user's current
live state. Keep the split explicit:

- `entry.py` is a narrow starting point, not the final collector.
- `t001_profile_refresh.py` is an updater, not a bootstrapper; it still needs a
  current profile package with `combat511`/`combat504` and an accepted movement
  seed.
- FeiLin127 `field21` needs at least twelve capture rounds; three rounds and
  some six-round sets remain ambiguous.

Run offline vectors first, then the current verifier and business replay.

Writeback after eligible verified work: read `references/methodology/case-writeback.md`. Flow: candidate summary -> user yes -> sanitize/dedupe + exact allowlist -> second confirm -> change-control. No case stores raw account/browser/HAR/private bodies, cookie/token values, or absolute local paths; current authorized state is pulled at reproduction time and kept out of the library.

## Failure Recovery

### 工具失败 vs 协议失败分类

在诊断任何阻塞前，先分类失败来源：

| 信号 | 分类 | 处理 |
|---|---|---|
| MCP 工具调用返回同一错误 ≥2 次（如 `Could not save file`、`Execution context destroyed`、`timed out`） | 工具环境问题 | **不要重试同一调用**。记录 blocker，切换替代方法（如：`save_script_source` 失败 → 改用 curl + write 保存；`evaluate_js` 超时 → 改用 `search_in_sources` + 浏览器外分析）|
| 浏览器页面重置为 `about:blank` / 丢失上下文 | 工具环境问题 | 重新 `navigate` 后继续，不要归因为协议失败 |
| 中文路径导致文件操作失败 | 工具环境问题 | 优先在 `<projectRoot>/js_reverse_cache/ascii/**` 创建纯 ASCII 子路径；只有工具强制外部路径时才用临时 ASCII 路径，并立即复制回 `js_reverse_cache/**` 后清理外部副本 |
| HTTP 响应 status/body 与预期不符 | 协议失败 | 按协议诊断顺序处理 |
| HMAC/AES/签名与捕获包不一致 | 协议失败 | 检查参数/密钥/编码 |
| 同一代码修复后运行结果不变 | 可能是工具失败（文件未真正写入） | 先确认文件状态（`cat`/`sha256sum`）再继续 |

**核心原则**：工具失败消耗的轮次不应超过协议分析本身。如果连续 3 轮在处理工具问题而不是协议问题，停下来重新评估工具环境是否可用。

### 浏览器 fallback 链

MCP 环境中有多套浏览器引擎可用：
1. `js-reverse-mcp`（CloakBrowser / Chromium）
2. `camoufox-reverse-mcp`（Camoufox / Firefox SpiderMonkey）
3. `chrome-devtools-mcp`（普通 Chrome DevTools）

**规则**：当一个引擎连续失败 2 次（导航超时、JS 执行失败、状态丢失），**不要宣布「浏览器不可用」**——记录为工具失败条件，并切换到下一个可用引擎。这个 fallback 是工具恢复，不是协议 route 升级；exit code 21 / profile 残留按「浏览器启动失败诊断流程」先问用户，不进入自动 fallback：

```
Chrome 失败 x2      → 切 CloakBrowser
CloakBrowser 失败 x2 → 切 Camoufox
全部失败             → 记录 hard blocker
```

注意事项：
- Chrome（chrome-devtools-mcp 或 js-reverse-mcp 普通模式）：最简单稳定，优先使用
- CloakBrowser（js-reverse-mcp Cloak 模式）：指纹伪装，Chrome 无法通过时使用
- Camoufox（camoufox-reverse-mcp）：Firefox 引擎，最后手段，对 WAF JS 有不同处理逻辑
- 三者 MCP 工具 API 几乎一致（navigate/evaluate_js/list_network_requests/cookies），切换成本极低
- **绝不允许在一个引擎上重试 3 次以上然后宣布「浏览器不可用」**；但启动残留类错误必须先走用户决策，不自动杀进程也不自动换引擎隐藏该问题

### 浏览器启动失败诊断流程

启动浏览器（launch_browser / reset_browser_state）报错时，先分类错误特征：

| 错误特征 | 诊断 | 动作 |
|---|---|---|
| exit code 21 / 进程启动后立即 graceful close / `Target page, context or browser has been closed` | Chrome/CloakBrowser 单实例机制：已有进程占用 user-data-dir，新实例立即退出 | **不要自动杀进程**（用户可能正用浏览器），也不要盲目重试——直接询问用户 |
| 网络/连接错误、MCP server 未连接 | 环境问题 | 按 fallback 链切换引擎 |

**Chrome exit code 21 机制**：Chrome 启动时若检测到相同 user-data-dir 已有实例在运行，会把请求转发给已有实例然后以 exit 21 退出。残留进程锁住了 profile 目录，导致后续启动全部失败。

**用户决策选项**（发现进程残留时提问）：
1. **释放浏览器进程**：杀残留 chrome.exe + 清理 profile 目录（如 `D:\develop_software\CloakBrowser\js-reverse-mcp-local-cloak\chrome-reverse-profile`），然后重新启动采集
2. **暂停任务**：保留当前状态，用户自行处理后恢复

**规则**：
- 启动失败 ≤2 次且错误特征匹配进程残留 → 直接进入用户决策流程（不重试第 3 次）
- 用户选择释放 → 执行清理 → 重新启动 → 继续采集
- 用户选择暂停 → 记录 checkpoint，等待用户恢复

### MCP 浏览器操作纪律

| 规则 | 说明 |
|---|---|
| 一次一个引擎 | 不要同时操作 CloakBrowser 和 Camoufox，状态会互相干扰 |
| 调用批次上限 | 单次 tool call 批次不超过 3 个相关联的 MCP 调用；多了结果混乱无法追踪 |
| network_capture 时机 | `network_capture(action='start', capture_body=true)` **必须在 navigate 之前**调用 |
| pre_inject_hooks | 需要在页面加载前拦截网络请求时，使用 `navigate(pre_inject_hooks=[...])` 而不是 navigate 后 evaluate_js（后者在 reload 后会丢失） |
| 操作前确认状态 | navigate 后先 `get_page_info` 确认当前 URL/title 再做后续操作 |
| 清 cookie 导航策略 | 见下节 |

### WAF 页面导航策略

清 cookie 后导航到 WAF 保护的页面时，WAF JS Challenge 会阻塞 `domcontentloaded`（先执行 JS 验证、生成 cookie、再 302 重定向到真实页面）。

**正确做法（按优先级）**：
1. **不清 cookie**：保留 WAF session，通过业务请求头缺失/错误来触发 Captcha V2 层（而非 WAF JS 层）
2. **如果必须清 cookie**：把 WAF JS navigation 恢复记录为工具/页面恢复条件，使用 Camoufox（对 WAF JS 有更好的通过率）而不是 CloakBrowser；这不改变协议 route，最终 live egress 仍归 Python
3. **WAF 页面导航参数**：对 WAF 页面用 `wait_until: 'networkidle'` 而非 `domcontentloaded`；如果 networkidle 也超时，设定 15s 超时后检查 `get_page_info` 判断页面是否已在目标域

**绝不要**：清 cookie → CloakBrowser → `wait_until: domcontentloaded` → 超时 → 宣布失败。这是已验证的最大轮次浪费模式。

| Trigger | First fix | Still fails → stop |
|---|---|---|
| Missing target URL / sample / technical context | Ask only those fields in `nextAsk` | Do not invent the target; return precise blocker |
| About to install deps or run target JS/WASM | Put `executionPolicy` fields in `nextAsk`; stay blocked on that action only | Do not install or execute target code without confirm |
| Recon empty / no target request | Re-check route signals; one more bounded capture | Name blocker; do not open second recon engine |
| Provider `status!=complete` or acceptance fails | One corrective work order on same Provider | Switch only after naming a new mutation/gate blocker |
| Selected PZDS implementation case has no project profile/track/session | Generate the stable collector and offline proof, then name the exact missing current-state gate and capture it | Do not claim live complete; do not discard the implementation because state is absent |
| Case disagrees with current evidence | Stop reuse immediately | Return to normal evidence routing; no sibling case |
| `requestBudget.remaining=0` | Continue offline and put the exact requested increase in `nextAsk: scope-expansion` only when more live work is necessary | Do not replenish or reset the budget without user confirmation |
| `cleanup.complete=false` or live task resource remains | Cleanup or record approved retention IDs | Reject `status=complete` |

When the same shape needs another Provider, keep the shape. Before a larger shape, name the proposed scope and wait for `nextAsk: scope-expansion` confirmation:

```
blocker: <one sentence>
nextRead: <exactly one additional path>
why: <smallest honest move>
```

## Safety Checkpoints

🔴 CHECKPOINT · 🛑 STOP and confirm before: **dependency installation**; **local execution of target-supplied JS/WASM/HTML**; **business `mutation-submit`**; **success-shape or request-budget expansion**; **raw-secret persistence/export**; **bundled case-library writes**. Routine browser recon, read-only live egress, redacted project writes under `js_reverse_cache/**`, user-supplied session use, protocol-needed verifier submits, and scale inside the immutable budget do not pause under standing approval. Never invent or export secrets the user did not supply.

Gate mapping (record vs confirm): read-only/verifier action ↔ `actionClass` records; business mutation ↔ `actionClass=mutation-submit` confirms; scale ↔ immutable `requestBudget` records until expansion confirms; redacted save ↔ `artifactPolicy` records; raw-secret handling ↔ `artifactPolicy` confirms; target code/install ↔ `executionPolicy` confirms; recon nav ↔ browser flags records; live egress ↔ `liveReplayAllowed` records.

## Do Not

- Do not skip work-order accounting. Do not auto-approve `mutation-submit`, shape/budget expansion, raw-secret handling, case writeback, dependency installation, or local target-code execution. Do not invent credentials the user never supplied.
- Do not put a gate family, strategy, profile, or file path in `route` (Non-Negotiables owns this).
- Do not ship browser-backed page `fetch`/CDP as the final collector.
- 🛑 **HARD STOP — 滑块自动化**：如果你正在调用 `drag`/`click`/`evaluate_js` 来操作验证码滑块元素（如 `#aliyunCaptcha-sliding-slider`、`.geetest_slider_button`、任何 captcha DOM 元素），**立刻停止**。这是浏览器自动化，不是协议交付。恢复步骤：① 停止所有 DOM 操作 → ② 切换到 XHR 断点法采集协议证据 → ③ 按 verifier workflow 实现纯协议 T001。唯一例外：用户明确要求的一次性人工正样本采集（非交付主路径）。
- Do not scale page/retry/concurrency after one lucky HTTP `200`.
- Do not select `camoufox` or open a second recon engine without explicit Camoufox/SpiderMonkey/engine-level wording, recorded tool-failure fallback, WAF navigation recovery, or other recorded criteria. Fingerprint/Cloak/stealth wording, busy Chrome, a vendor name, `412`, Reese84 wording, and historical case provenance are all non-criteria (Phase 2 owns this).
- Do not route a vendor family on one marker, a label, or a guess; require independent corroboration (Phase 0 owns this).
- Do not load a sibling case after one registry match failed current evidence.
- Do not claim `complete` while task-owned resources remain live or `cleanup.complete=false`.
- Do not write task evidence outside `<projectRoot>/js_reverse_cache/**` when `projectRoot` is known, and do not treat OS temp as primary storage; if a tool forces an external absolute path, copy the artifact in immediately.
- Do not treat non-empty sign/token, one HTTP `200`, or an expired cookie/session export as semantic success.
- Do not store raw cookies/tokens/HAR/private bodies or absolute local paths in the case library, and do not mix case-library edits with darwin `results.tsv` score rows in one commit when avoidable.
- ❌ **禁止单引擎失败宣布「浏览器不可用」**：CloakBrowser 失败 2 次后必须尝试 Camoufox，全部引擎失败后才能记录 hard blocker（浏览器 fallback 链规则）。
- ❌ **禁止清 cookie 后用 CloakBrowser + domcontentloaded 导航 WAF 页面**：此操作必定超时（WAF 导航策略规则）。
- ❌ **禁止浏览器启动报错时盲目重试 3 次以上**：先诊断是否为进程残留（exit code 21 / 启动后立即 graceful close / `Target page, context or browser has been closed`），是则询问用户选择释放进程或暂停任务（浏览器启动失败诊断流程）。

Also enforced in `references/anti-patterns-playbook.md` (read it for the temptation / false-progress / self-check form): bare `print` instead of `utils/logger.py` in iv8/collector delivery; pre-created empty `js_reverse_cache/**` trees; hardcoded rotating cookies; broad hooks before a clean baseline; reversing the visible helper instead of the wire mutation point; rung-skipping escalation.

## Completion

**Light** (`evidence`/`local-proof`): shape, route, decisive evidence, blocker/next step, browser lifecycle. Local-proof always includes `acceptanceTest` and `result`; with artifact, also path and SHA-256. Pure read-only evidence does not require `分析报告.md`.

**Full** (replay/collector): gate family + provider chain; endpoint + moving state; project root + stable files; verification results; browser lifecycle; limits; case writeback offer; **and root `分析报告.md`**. Keep logs bounded and redacted; point to artifacts. Reject complete when cleanup is incomplete or when `compact-replay`/`collector` delivery wrote project files without `分析报告.md`. Template: `references/report-templates.md` section `分析报告.md`.

## References

By symptom: `references/reference-router.md`. Anti-patterns: `references/anti-patterns-playbook.md`. Discipline mini suite: `references/discipline-self-test-min.md`. Preflight: `python scripts/preflight.py`. Methodology: `architecture.md`, `provider-work-order.md`, `project-layout.md`, `case-writeback.md`, `success-shape-scripts.md`, `read-budget.md`. Providers: `references/providers/`; cases: `references/cases/`. Nothing below overrides this file's scope, safety, lifecycle, layout, or verification.
