---
name: web-protocol-recovery
description: >-
  仅在用户明确要求恢复、定位、验证、实现、交付或复现 Web/小程序协议行为，或明确要求更新其授权 WMPFDebugger 的本地 native hook 地址/offset/config 时触发；WMPF 地址维护线索包括 LoadStartHookOffset、CDPFilterHookOffset、SceneOffsets、addresses.<version>.json、flue.dll、WeChatAppEx.exe。线索还包括 sign/token/header/cookie/challenge、JSVMP/WASM、验证码、Akamai、Kasada、River Security/瑞数、Reese84、响应解码、字体映射、会话协议或 browser-free Python collector。排除：Camoufox/浏览器截图点击/QA/回归测试/页面自动化、普通 REST/GraphQL client、skill/opencode/MCP 配置、前端/CSS、格式化/重命名、安全头和市场介绍；单独出现 Camoufox、GraphQL、WebSocket、protobuf、Imperva、AST 或浏览器也不触发。PZDS goodsPublic/page 与 Aliyun V2 InitCaptchaV2/UploadLog/Log2/Log3/VerifyCaptchaV2/T001/F001 + 业务重放按 collector；明确实现按 collector 交付。授权后按需读取 Chromium/Camoufox/WeChat、hook、AST、verifier、akamai、kasada、river-security、reese84、iv8、python-node、nv8、pure-python 或 Python delivery Provider。单点 hook、入口定位、已知 AST、Node/jsdom、NV8、iv8、纯 Python signer、Akamai/River/Reese84 状态机、抖音 BDMS 维护或 WMPF 本地地址适配可走快速路径，不自动升级 collector。
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
5. **默认执行 vs 必须确认**：已选 shape 内的常规动作（隔离 recon、只读 live 请求、写 `projectRoot`、用已给 cookie/session、协议所需 verifier submit、首次记录预算内的采集）默认执行、不打断。只有五项必须确认：装依赖、本地执行目标 JS/WASM/HTML（隔离浏览器按页面正常加载目标代码属于 recon，不算本地执行）、业务 `mutation-submit`、扩大 shape/预算、raw secret 持久化/导出与 case 写回。内部记账即可，不要写进 `nextAsk`。
6. **Browser Runtime Gate 只按需触发**：只有下一步确实要启动本地浏览器 runtime（Chromium/Cloak/Camoufox/miniapp debugger/正样本/用户明确浏览器自动化）时，才执行 runtime 检查。先使用已配置的 MCP/Provider adapter 解析默认 runtime；adapter 能启动或报告可用时直接 `nextAsk: none`，不询问根目录。仅当 adapter 没有可用默认 runtime、用户要求自定义 runtime，或 Provider 明确需要外部安装时，才询问浏览器根目录。纯协议、`evidence-reuse`、`local-proof`、`pure-python`、离线样本任务不问；依赖安装仍是 `executionPolicy`。
7. **实现请求的默认行为**：用户明确要求实现或完整代码时，直接选择 `shape: collector`；先生成稳定项目文件和离线向量证明，再处理当前 session/profile/track 等运行态。缺运行态只能阻塞 live acceptance，不能阻止先生成实现骨架。

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

Skill self-check after edits: `python scripts/gates/preflight.py` from this skill root. Claims about changed routing or agent behavior additionally require `references/methodology/forward-testing.md`; static preflight alone is not behavioral proof.

## Non-Negotiables

First response and every subsequent gated turn begin with these four lines. `route` is a short Provider ID or `evidence-reuse`, never a file path, gate family, strategy, or profile. Inline local-proof includes `acceptanceTest` and `result`. Exception: for a non-trigger boundary response, do not emit the four-line protocol header; state that the request is outside web-protocol-recovery and name the nearest normal workflow or skill.
```
shape: <evidence|local-proof|compact-replay|collector>
route: <selected Provider or evidence-reuse>
nextAsk: <none | missing sample/context | executionPolicy | governance>
nextRead: <paths per read-budget>
```

Header meanings: `shape` is deliverable depth; `route` is the selected Provider or `evidence-reuse`; `nextAsk` is almost always `none` and names only the immediate missing technical input, execution hard stop, or `governance` decision (`governance` = business mutation, shape/budget expansion, raw-secret handling, case writeback — the Safety Checkpoints table owns the exact record/confirm mapping); `nextRead` lists exact paths allowed by the read budget. Per-shape scripts and gated overlays live in `references/methodology/success-shape-scripts.md`.

### Route Response Completeness

The four-line header is the minimum, not a substitute for the decisive route facts. Include these facts in the same first response when the route matches:

- `kasada`: name two concrete independent evidence surfaces, state that `429` alone is insufficient, identify `nv8` as the narrow artifact generator when selected, and state `Python` as final live egress.
- `river-security`: name the two independent markers, state that challenge state and S/T Cookie conversion are recovered first, identify `python-node` with `strategy: env-patch` or `iv8` as the narrow artifact path, and state `Python` egress.
- `reese84` with incomplete evidence: keep `evidence-first`, use `route: evidence-reuse` or an explicit blocker, state that one cookie/header pair is insufficient, list the missing corroborating surface, and reject direct collector delivery.
- PZDS/Aliyun V2: name the Aliyun V2 workflow, require current live `session/profile/track`, and separate `verifier` proof from `python-collector` business delivery.
- GT4 word-click: name the current word workflow/bundle, transparent `ques`, the candidate text set, the `0..10000` coordinate shape, and the Python `/verify` handoff when collector delivery is requested.
- GT4 slide: name the current slide workflow/bundle, `bg/slice`, gap-center to `setLeft` mapping, `td/td_sign` when proven, iv8 narrow `w`, and the Python `/verify` handoff.
- GT4 nine-grid: name the nine-grid workflow/bundle, `risk_type=nine`, `captcha_type=nine`, `imgs/ques/nine_nums`, hash-verified model/checkpoint status, one-based `[row,col]` mapping, and the Python `/verify` handoff.
- When a GT4 success response contains `data.seccode`, record the post-verification credential shape (`captcha_output`, `pass_token`, `gen_time`, `captcha_id`, and same-round `lot_number`). Output it only under the requested secret policy; never place dynamic credentials in case fixtures.
- GT4 subtype routing is exclusive: `slide` requires `risk_type/captcha_type=slide` plus `bg/slice`; `word-click` requires `risk_type=word` plus `captcha_type=word` and `imgs/ques`; `nine-grid` requires `risk_type/captcha_type=nine` plus `imgs/ques/nine_nums`. Shared `/load` fields alone never select a subtype.
- fixed-vector local proof with target-supplied JS/WASM/HTML: state `固定向量离线`, set `nextAsk: executionPolicy`, and report `result: pending` until approved execution is available.

Policy overlays (case read, scope/budget accounting, Chrome auto-traffic **recording**, runtime cleanup) remain owned by `references/methodology/success-shape-scripts.md`. Routine fields are accounting/lifecycle rules. `executionPolicy`, business mutation, shape/budget expansion, raw-secret handling, and case writeback retain their explicit confirmation rules.

1. Final delivery is browser-free. Python owns live egress (HTTP requests, WebSocket handshakes, and sent frames); local JS/WASM/iv8 only as narrow artifact generators.
2. Evidence precedes implementation: real request, moving state, mutation point, one objective acceptance test.
3. One `projectRoot` and `web-protocol-recovery-simple`. Default `projectRoot` to the current working directory when the user did not name a folder; do not re-ask cwd vs custom. Providers never choose another landing path or project shape.
4. All dynamic evidence (recon dumps, challenge JS/HTML, screenshots, browser state, probes, net logs, MCP exports) writes only under `<projectRoot>/js_reverse_cache/**`. Never default to `%TEMP%`, `AppData\Local\Temp`, `opencode` temp roots, skill directories, or any path outside the approved project root.
5. Load only the selected provider and at most one provider-local reference per work order. Case bundles and every expansion follow `references/methodology/read-budget.md`.
6. Browser engines/profiles are lifecycle-serialized. At most one browser family is `TARGET_ACTIVE`; capability snapshots do not prewarm multiple target browsers, and IDs never cross engine/session/target boundaries.
7. **Standing approval (default for explicit protocol tasks, within the selected shape):** browser recon, read-only live egress, writes under `projectRoot`, use of user-supplied cookies/session, protocol-needed `verifier-submit`, and scale within the initially recorded immutable request budget are already approved—execute them, do not re-ask. If the user gives no budget, automatically record `requestBudget.total=100` and `requestBudget.remaining=100` for the selected routine protocol task. This default is internal accounting, not permission to exceed scope. Never auto-promote to `mutation-submit`, a larger shape, or a larger budget. Local target-code execution and dependency installation use `executionPolicy`; raw-secret handling and case-library writeback keep their governance confirmations.
8. When delivery uses iv8 (or the iv8 silent helper), also create `utils/logger.py` (optional `loguru` with PrintLogger fallback). Progress logs use `logger.info`; do not paste loguru/print fallbacks into every main script.

## Phase 0: Intake

Do not paste the full intake form on the first reply. Use the four-line template above; `nextAsk` is usually `none` or only missing technical samples. Name a confirmation field only when its exact hard stop or scope/governance action is about to happen.

If the user gives no success shape, default to `shape: evidence`. Choose `route` by the strongest Phase 2 signal, then **start the smallest next action** under operator standing approval.

First-turn routing rules choose `shape` and `route`. Under Non-Negotiables item 7, an explicit protocol-recovery task grants routine actions only inside that shape. It does **not** grant local target-code execution, dependency installation, business mutation, shape/budget expansion, raw-secret handling, or case-library writeback.

| Signal | First-turn decision |
|---|---|
| 明确要求“实现/写完整代码” | 选择 `shape: collector`；若命中已验证的稳定协议模式，先用 `evidence-reuse` 读取可复用原语和流程约束，再执行当前目标所需的 Provider 链。 |
| Supplied artifacts or a registry-selected reusable case | Prefer `route: evidence-reuse`. A bare URL with no protocol-recovery intent is not enough; an explicit protocol-recovery request naming that URL may start bounded recon under standing approval unless the user requested offline/no-browser work. |
| Explicit offline / local / fixed-vector wording | Use `shape: local-proof` and stay offline until a named blocker requires one implementation Provider. |
| Explicit WMPF address/offset/config maintenance | `shape: local-proof`, `route: wmpf-address-adapter`; local PE analysis and an exact assigned config write only; do not route to ordinary miniapp capture or collector. |
| Platform/runtime wording | Miniapp -> `route: wechat-miniapp`; explicit Camoufox -> `route: camoufox`; neither upgrades to `collector`. |
| Known implementation boundary or explicit implementation Provider request | Use the named Provider route only when the boundary/artifact is named, such as `route: browser-hooks`, `route: ast`, `route: python-node` with `strategy: env-patch`, `route: nv8`, `route: iv8`, or `route: pure-python`; otherwise stay evidence first. |
| Captcha family signals | Named captcha vendors (Geetest, TCaptcha/TDC, Yidun, Shumei, Yunpian, Tianyu, Dingxiang, Ctrip, Aliyun Captcha, ByteDance VerifyCenter) are verifier-priority evidence. Choose `route: verifier` only when paired with a sampled captcha round, protocol endpoint/field, semantic verifier failure, or a named active verifier delivery artifact. A lone `w` / `data` / `token` param, or generic `403` plus the word captcha, is evidence first. Field-level detail: verifier `PROVIDER.md` `Select When`. |
| Vendor-family signals (`akamai`, `river-security`, `reese84`) | Route to a protocol owner only when a vendor-native marker has independent corroboration from a second surface (network, script, cookie transition, transport, or business consumer); River Security needs two independent observed markers. Generic `403` / `412` / H2 reset, one cookie name, an Imperva label or error 15, an alias tag such as `alias:ruishu`, and a user guess ("怀疑瑞数") are never sufficient. Otherwise stay evidence first. Fresh URL recon starts with Chromium unless explicit Camoufox/SpiderMonkey/engine-level criteria are present. Marker lists and negative signals: each Provider's `Select When` / `Do Not Select When`. A Kasada response must name both concrete evidence surfaces; when `nv8` is requested, name it as the narrow artifact generator and state that Python owns final live egress. |
| Existing Douyin Web BDMS pure-Python maintenance | Use `route: pure-python` with `profile: douyin-abogus-native` only when the named target, existing complete implementation, and fixed BDMS trace all hold; from-zero recovery or unknown version/entry/layout stays on normal routes. Conditions: `references/providers/implementation/pure-python/profiles/douyin-abogus-native.md` `Select When`. |

Fallback rules:

1. Generic `403`, `412`, CAPTCHA, obfuscation, GraphQL, WebSocket, or protobuf wording is not a Camoufox criterion; use `shape: evidence` and the smallest matching route/gate.
2. Mixed signals resolve to the smallest offline step when samples are enough; otherwise start the smallest live recon under standing approval. Do not paste a full intake form or invent missing target URLs/samples.
3. Non-protocol tasks such as public API client generation, ordinary HTTP debugging, browser QA/screenshot/click tests, ordinary AST format/rename, Camoufox regression without protocol recovery, MCP/OpenCode config, UI/CSS work, or skill create/optimize/score are non-triggers; return the boundary instead of forcing a route.
4. Unrelated native targets remain out of scope: native binary/ELF/PE, `.so`/DLL, APK/Android, iOS/IPA, desktop or thick-client executables, firmware images, PCAP/raw TCP-UDP without a Web/miniapp surface, and native-only OLLVM/VM deobfuscation. The narrow exception is an explicitly authorized WMPFDebugger address-maintenance task, which uses `wmpf-address-adapter` and must not expand into general native reverse engineering.

Read-Only Evidence Fast Path:

Use this path when all conditions hold: `shape: evidence`; supplied artifact, request snippet, source sample, registry metadata, or static question is enough for the next step; no browser navigation, live egress, target-code execution, dependency install, or file write is needed yet.

Allowed actions: emit the four-line header, use `route: evidence-reuse` unless reading one selected Provider `PROVIDER.md` or one bounded Provider-local reference is the smallest next read, inspect supplied text/files and bounded references, name the request/function/state source/blocker, and ask only missing sample/context fields. Do **not** ask for `projectRoot`, write mode, live replay approval, request budget, artifact retention, or full authorization on this path.

Browser Runtime Dependency Gate:

Trigger this gate **only** when the next selected action requires launching a local browser runtime, such as `chromium-recon`, a Cloak tier, `camoufox`, WeChat miniapp debugger attachment, a browser positive-sample capture, or a user-explicit browser automation delivery. Do not trigger it for pure protocol work, `evidence-reuse`, offline `local-proof`, supplied artifacts that can be inspected statically, `pure-python`, or fixed-vector proof.

When the gate triggers, first probe the selected managed adapter's environment and default binary resolution. For configured MCP browser adapters, the adapter owns the browser root and the first response must keep `nextAsk: none`; use the Provider's default launch/check path and do not ask the user for a root directory. If that probe reports no usable default runtime, or the user explicitly requests a custom browser/runtime, ask the smallest browser-runtime question under `nextAsk: missing sample/context`:

```text
This step needs a local browser runtime. Do you already have one installed?
1. Yes: provide the browser root directory, not the executable path.
2. No: use the selected Provider/package default resolution, such as the `cloakbrowser` package default for CloakBrowser.
```

If the user supplies a browser root, record it as runtime configuration for the active Provider and let that Provider resolve the binary inside the root. Do not put a root path in `route`, do not treat it as a gate family, and do not copy it into case-library artifacts. If the package default path requires installing `pip`/`npm` dependencies, stop with `nextAsk: executionPolicy`; package defaults are not dependency-install approval.

For ordinary `chromium-recon` through configured `chrome-devtools` or `js-reverse` MCP adapters, use the adapter-managed default browser and set `nextAsk: none`. Ask for a root only after the adapter check fails, or when the user names a custom Chromium/Cloak/Camoufox installation. A routine managed-adapter lookup is not missing sample/context.

### Runtime Capability Adapter

The workflow is runtime-neutral at the capability level. Names such as `chrome-devtools-mcp`, `js-reverse-mcp`, and `camoufox-reverse-mcp` are concrete adapters, not required APIs. Map each requested capability to one available equivalent before starting the work order:

| Capability | Preferred adapter | Equivalent fallback | If unavailable |
|---|---|---|---|
| Page, network, and initiator evidence | browser inspector + `js-reverse` | Playwright/CDP, another browser network inspector, or supplied HAR | Stay at `evidence` and name the missing evidence surface |
| Source search and narrow hooks | `js-reverse` source/debug tools | browser debugger, Playwright/CDP init script, or offline source parser | Do not install broad hooks; report the exact observation blocker |
| Camoufox/SpiderMonkey engine proof | Camoufox engine-trace adapter | supplied engine trace or static artifact | Keep the selected route blocked; never claim engine proof from another engine |
| Local JS/WASM artifact generation | selected `iv8`, `python-node`, `nv8`, or `pure-python` Provider | another approved implementation Provider with the same acceptance test | Stop at the current shape and name the implementation blocker |
| Final live HTTP/WebSocket egress | task-project Python client | equivalent Python HTTP/WebSocket library | Do not use page fetch, CDP, or browser automation as delivery |

If a fallback changes the evidence quality or runtime provenance, record that as a blocker or residual risk in the Provider result. A missing adapter is not permission to skip the acceptance test or to select a heavier route.

Before navigation, live egress, session use, writes, target-code execution, or dependency install, **record** the applicable fields from `references/methodology/provider-work-order.md` (internal bookkeeping). For routine protocol work, auto-fill: `actionClass=read-only` (or `verifier-submit` only for a protocol-needed verifier round), browser flags, `liveReplayAllowed=true`, `requestBudget.total=100` and `requestBudget.remaining=100` when no budget was supplied, one positive immutable request budget, redacted artifact policy under `js_reverse_cache/**`, supplied-session use, and the resolved absolute cwd when `projectRoot` is unset. Keep `mutation-submit` and all confirmation kinds blocked until the matching user decision. Pre-egress accounting and Chrome automatic-traffic **recording** stay canonical; route switches never reset or replenish the budget.

Smallest success shape:

| Shape | Deliverable |
|---|---|
| `evidence` | request, initiator, function, state source, or precise blocker |
| `local-proof` | fixed vectors, decode, restored source, or callable helper; a saved helper always reports vector acceptance state, artifact path, and SHA-256 |
| `compact-replay` | short root `main.py`, often with a narrow runtime helper |
| `collector` | stable browser-free Python path with bounds |

Local-proof can run pure data transforms on supplied samples offline. Executing target-supplied JS/WASM/HTML remains target-code execution and still requires the `executionPolicy` confirmation even when no live egress is allowed.

For a fixed-vector request that supplies target JS/WASM/HTML, the first response must keep `shape: local-proof`, set `nextAsk: executionPolicy`, and report `result: pending` until the approved hash and a bounded process launcher are recorded. Do not silently execute target code because live egress is disabled.

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

### PZDS Aliyun V2 商品采集专用触发器

当业务目标是 `goodsPublic/page`（或同类列表接口）、最终交付是 JSON records，且证据同时包含 `InitCaptchaV2`、`UploadLog`、`Log2`、`Log3`、`VerifyCaptchaV2`、`T001/F001` 中至少三个信号时，直接选择 `shape: collector` + `route: verifier`，再读取 `references/providers/protocol-recovery/verifier/PROVIDER.md` 和唯一匹配的 `references/providers/protocol-recovery/verifier/references/aliyun-captcha-v2-workflow.md`。首响应必须点名 Aliyun Captcha V2 workflow，并写明当前目标的 live session/profile/track 是交付前置条件；不要把页面渲染结果当交付。

Hub 只保留以下不可省略的路由与验收约束：

1. 同轮生成并绑定 `sceneId`、`traceid/CertifyId`、`sessionId`、`version`、`ip`、`timestamp`、`encryptionKey`、业务 token/cookie、Log2 profile、Log3 combat、Verify track 和 `deviceToken counter`；禁止跨轮拼接。
2. `UploadLog` 是必发 sidecar。`T001 && VerifyResult=true` 后才能重放业务请求；`F001` 先按 Aliyun V2 reference 的 field21、profile/version、timestamp、counter、combat、track 和业务网关顺序 diff，不猜测轨迹。
3. `missing_or_stale_profile` 或版本不一致时停止 Verify 并刷新 profile；Log2/Log3 `200/true` 只代表 sidecar 接收，不代表业务成功。
4. 只有 `records` 非空且业务 `success=true/code=SUCCESS` 才算完成。`verifier` 负责验证证明，`python-collector` 负责最终业务 delivery；浏览器只提供取证、正样本或窄工件。缺少当前 profile/session/track 时不得声明 live complete。

River Security 首个动作：先恢复 challenge 状态并捕获 S/T Cookie 转换，再生成窄工件；不要先调轨迹或直接重放。

Fresh recon picks exactly one route:

| Route | Signal | Provider entry |
|---|---|---|
| `chromium-recon` | Ordinary Web; Cloak/指纹/fingerprint/anti-detection/stealth browser wording starts here as a Chromium-tier question | `references/providers/reconnaissance/chromium-recon/PROVIDER.md` |
| `camoufox` | Explicit Camoufox, or engine-level/SpiderMonkey/Camoufox instrumentation, or untrustworthy Cloak result | `references/providers/reconnaissance/camoufox/PROVIDER.md` |
| `wechat-miniapp` | WMPF / WeChatAppEx / AppService / miniapp WebView / `127.0.0.1:62000` / WMPFDebugger | `references/providers/reconnaissance/wechat-miniapp/PROVIDER.md` |

CloakBrowser is a Chromium recon tier, not a `route`. Fingerprint-browser, Cloak, stealth, anti-detection, or busy-Chrome wording does not select `camoufox`; it selects `chromium-recon` with an optional Cloak tier. Use `camoufox` only for explicit Camoufox/SpiderMonkey/engine-level criteria or after a Cloak result is captured and recorded as untrustworthy. A busy Chrome profile or an occupied visible Chrome is a tool blocker, not target evidence; record it and do not touch that browser. Final live egress still belongs to Python.

Cloudflare Turnstile managed / 五秒盾 with explicit CloakBrowser browser-automation delivery stays `route: chromium-recon`; after Browser Runtime Dependency Gate, read the provider-local reference `references/providers/reconnaissance/chromium-recon/references/cloakbrowser-turnstile-managed.md`. This is a user-explicit browser runtime delivery pattern, not a browser-free protocol collector and not case-library eligible unless a later protocol artifact proves browser-free acceptance.

Chromium recon (standing approval already covers launch; no user gate pause):

| Step | Action | Rule |
|---|---|---|
| 1 | `chrome-devtools` baseline | Capture ordinary request/initiator evidence, then park Chrome. |
| 2 | `js-reverse` mutation | Explicitly call `launch_browser`; headless is preferred unless the user asks for visible ordinary Chrome. |
| 3 | Optional Cloak tier | Use only for 指纹/Cloak/stealth wording or observed fingerprint evidence; this stays inside `chromium-recon`. |

Fresh ordinary application Web targets need steps 1 and 2 before the final collector. A transport-only target may skip step 2 when the work order already contains the complete wire sample, initiator/source boundary, frame order, and semantic consumer acceptance; record `jsReverseHalf=not-required`. Skip a half otherwise only with a real tool blocker or documented exception (`evidence-reuse`, offline `local-proof`, or non-Chromium route). "No ordinary window" may skip only the visible DevTools window; `js-reverse` remains required unless the transport-only exception is recorded. Close `js-reverse` before any later `camoufox` route. `js-reverse` has no auto-launch default; after `close_browser`, relaunch headless before further actions. A brief relaunch flash is OK; persistent headful after acceptance is a blocker.

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
| Kasada `x-kpsdk-*`, `KP_UIDz`, `KPSDK` bootstrap, `/tl` sensor and business admission | `kasada` | protocol owner | `references/providers/protocol-recovery/kasada/PROVIDER.md` |
| Browser-like local runtime / XHR netLog / registry runtime case | `iv8` | implementation mode | `references/providers/implementation/iv8/PROVIDER.md`; stable Python import uses `utils/iv8_silent.import_iv8_silent()` |
| Known JS entry in Node/vm/jsdom or Node/WASM sidecar | `python-node` | implementation mode | `references/providers/implementation/python-node/PROVIDER.md`; `env-patch` is `strategy: env-patch`, not a route |
| Full browser-compatible local runtime for Akamai/Kasada sensors | `nv8` | implementation | `references/providers/implementation/nv8/PROVIDER.md`; project-local npm package `nv8`, final live egress still belongs to Python |
| Portable signer/decoder/checksum/serializer in Python | `pure-python` | implementation mode | `references/providers/implementation/pure-python/PROVIDER.md`; Douyin BDMS maintenance is `profile: douyin-abogus-native` |
| Stable browser-free Python delivery | `python-collector` | delivery | `references/providers/delivery/python-collector/PROVIDER.md` |

Chains are sequential and role-aware (typical: recon -> AST -> python-node/nv8/iv8/pure-python -> python-collector; verifier -> iv8/python-node/pure-python -> python-collector for captcha proof builders; akamai -> nv8/python-node/iv8 -> python-collector for host-bound collectors; river-security -> python-node with `strategy: env-patch` or iv8 -> python-collector for challenge state; reese84 -> iv8/python-node -> python-collector for challenge-cookie state and business admission; kasada -> nv8/python-node -> python-collector for browser-free collector artifacts; or evidence-reuse -> pure-python with `profile: douyin-abogus-native` -> python-collector when an existing pure implementation only needs adaptation). Validate each result before the next order. Implementation Providers produce narrow artifacts only; protocol owners keep acceptance while implementation runs; `python-collector` is delivery and owns final live egress.

Provider handoff minimum:

1. Recon returns the real request, initiator/source boundary, moving state, runtime provenance, allowed artifact paths, and one named blocker or acceptance test.
2. A protocol owner returns the family evidence and acceptance conditions. For Kasada, name two concrete independent surfaces, state `nv8` when it is the selected narrow artifact generator, and state that Python owns final live egress; a marker count alone is insufficient.
3. A verifier returns same-round proof inputs and semantic verifier status only. For PZDS, name the Aliyun Captcha V2 workflow and state that current live session/profile/track is required before business replay. For GT4, select exactly one subtype workflow (exclusive conditions under Route Response Completeness above) before implementation, then include its answer shape, any `data.seccode` credential, and the Python `/verify` handoff. It does not own business delivery.
4. An implementation Provider returns one narrow artifact plus fixed-vector status. `python-collector` alone may return final live HTTP/WebSocket delivery and parsed business acceptance.

## Phase 5: Verification

Runtime load, non-empty sign, HTTP `200`, or one lucky replay is not success:

1. Fixed-output parity or named checkpoints match captured truth.
2. For `compact-replay`, one recorded minimal live replay succeeds on a coherent session; for `collector`, the minimal request repeats successfully or the next cursor/page is proved before scale.
3. Content type, challenge markers, business result, and data shape pass.
4. Signatures, cookies, headers, and wrapped bodies regenerate at the canonical request boundary.
5. State-dependent assertions must follow the observed response branch: classify a response as challenge/degraded, trusted/full, or business before enforcing stage-specific cookies. A cookie such as `bm_sc` is required only on the branch that produces it; a trusted/full page should be validated by its business markers and next request instead. For form workflows, compare the final serialized wire body, including fields appended by page code immediately before submit, rather than the static HTML form alone.
6. Page/retry/concurrency/duration scale only after a repeatable first request and only within the initially recorded `requestBudget`; exhaustion or any larger shape/budget requires `scope-expansion` confirmation.
7. Preserve the delivery invariant from Non-Negotiables: Python owns final live egress; local runtimes only produce narrow artifacts.

## Case Reuse And Writeback

### 多轮上下文检查点

每完成一个 Phase（或在 verifier 链路中每完成一个关键工件），必须输出检查点摘要；`writeMode` 已启用时写入 `js_reverse_cache/checkpoint.md`，纯只读 fast path / `writeMode=no-write` 阶段在回复中报告，不为写 checkpoint 打破 no-write。

机器状态优先保存为同目录的 `checkpoint.json`（字段契约见 `references/schemas/checkpoint.schema.json`），Markdown 只作为人读摘要。恢复顺序固定为 `checkpoint.json` -> 当前 work-order -> 允许的 `nextRead`；checkpoint 只保存 digest、路径状态、枚举和布尔状态，不得保存 cookie、token、profile、raw response 或账户凭据；恢复时不得从对话记忆重建预算、runtime ID、scope 或已接受证据，也不得重置 budget、read budget 或 runtime lifecycle。

`checkpoint.md` / `checkpoint.json` 模板、`firstDivergence` 定位顺序与浏览器残留记录格式见 `references/methodology/success-shape-scripts.md` 的 Context Checkpoint Overlay。

Selector: only `references/cases/registry.json`; only `status=verified` entries are library-selectable. Read `verificationClass` and `selectableAs` on the registry row before load: `selectableAs=proof` (`freshly-verified`) means current checked-in offline vectors/tests prove the local artifact only; it is not live-current target acceptance. `selectableAs=template` (`historical-user-attested`) is shape/process evidence only and always requires fresh current-target verification before live reuse. Match a structured exact scheme/host/port/route scope **or** the declared minimum of independent high-confidence signals (normally ≥2; verifier cases need vendor/version/subtype). When `match.requiredSignalGroups` exists, non-scope selection must also match at least one observed signal from every disjoint group; labels and repeated observations cannot satisfy two groups. A user hypothesis such as "怀疑瑞数" is not an independent high-confidence signal. If more than one verified case matches the same exact scope or the same minimum signal set, do not select by registry order; stop case reuse until a discriminator such as runtime, algorithm, product subtype, or negative signal selects exactly one case. Never match on one generic param, status, `_0x`, or SDK string. All entries resolve to one hash-bound `web-protocol-recovery-case` manifest with typed historical and current Provider stages. `freshly-verified` cases must carry executed test/evidence artifacts.

Load one selected case as `case.json` -> `PROCESS.md` -> declared puller/fixtures/tests/entry/assets within the read budget. After the active case names a concrete missing implementation fact, at most one manifest-declared `historicalReferences` file may replace one implementation/asset slot in that same case bundle. It is study-only evidence: never import, execute, copy into delivery, install its historical dependencies, or treat its old live result as current acceptance. An iv8 implementation additionally requires the Provider's accepted `api-inventory.md` gate before code use. A `python-node` evidence case has no implementation entry until fresh verification produces one. Offline vectors first; stop reuse if current evidence disagrees. A failed case does not authorize a sibling case.

`caseKind=implementation` is different from a study-only reference. For a selected verified reusable bundle, a manifest-declared `entry.py` or equivalent implementation artifact is an allowed narrow starting point after the current match; only files declared as `historicalReferences` are study-only and forbidden from delivery. The entry is still not the final collector unless the bundle explicitly says so: assemble the stable project files named by `PROCESS.md`, preserve the live-state gates, and run the current acceptance chain.

## Fresh-Machine Case Delivery

Implementation cases provide protocol primitives without current live state: `entry.py` 只是窄起点，不是最终 collector；`t001_profile_refresh.py` 是 updater 不是 bootstrapper；先跑离线向量，再跑当前 verifier 与业务重放。完整切分约束（`combat511`/`combat504` profile、FeiLin127 至少十二轮）见 `references/methodology/success-shape-scripts.md` 的 Case Delivery Overlay。

Writeback after eligible verified work: read `references/methodology/case-writeback.md`. Flow: candidate summary -> user yes -> sanitize/dedupe + exact allowlist -> second confirm -> change-control. No case stores raw account/browser/HAR/private bodies, cookie/token values, or absolute local paths; current authorized state is pulled at reproduction time and kept out of the library.

## Failure Recovery

### 工具失败 vs 协议失败分类

在诊断任何阻塞前，先分类失败来源：

| 信号 | 分类 | 处理 |
|---|---|---|
| MCP 工具同一错误 ≥2 次 / 页面重置 `about:blank` / 中文路径文件失败 / 修复后结果不变 | 工具环境问题 | 不重试同一调用；切换替代方法；先确认文件实际写入状态 |
| HTTP status/body 与预期不符 | 协议失败 | 按协议诊断顺序处理 |
| HMAC/AES/签名与捕获包不一致 | 协议失败 | 检查参数/密钥/编码 |

**核心原则**：工具失败消耗的轮次不应超过协议分析本身。连续 3 轮在处理工具问题而不是协议问题时，停下来重新评估工具环境是否可用。

浏览器 fallback 链、MCP 操作纪律、浏览器启动失败诊断与 WAF 页面导航策略见 `references/troubleshooting-playbook.md` 的「环境与工具失败恢复」。

| Trigger | First fix | Still fails → stop |
|---|---|---|
| Missing target URL / sample / technical context | Ask only those fields in `nextAsk` | Do not invent the target; return precise blocker |
| About to install deps or run target JS/WASM | Put `executionPolicy` fields in `nextAsk`; stay blocked on that action only | Do not install or execute target code without confirm |
| Recon empty / no target request | Re-check route signals; one more bounded capture | Name blocker; do not open second recon engine |
| Provider `status!=complete` or acceptance fails | One corrective work order on same Provider | Switch only after naming a new mutation/gate blocker |
| PZDS/Aliyun V2 collector lacks current profile/track/session | Generate the stable collector and offline proof, then name the exact missing current-state gate and capture it | Do not claim live complete; do not discard the implementation because state is absent |
| Reusable protocol bundle disagrees with current evidence | Stop reuse immediately | Return to normal evidence routing; do not load a neighboring bundle as a shortcut |
| `requestBudget.remaining=0` | Continue offline and put the exact requested increase in `nextAsk: governance` only when more live work is necessary | Do not replenish or reset the budget without user confirmation |
| `cleanup.complete=false` or live task resource remains | Cleanup or record approved retention IDs | Reject `status=complete` |

When the same shape needs another Provider, keep the shape. Before a larger shape, name the proposed scope and wait for `nextAsk: governance` confirmation:

```
blocker: <one sentence>
nextRead: <exactly one additional path>
why: <smallest honest move>
```

## Minimal Trigger Evals

After edits, run `python scripts/gates/preflight.py`; dry-run routing prompts and machine-checked expectations live in `test-prompts.json` and `evals/route-regression.json`. These are offline checks; do not open live egress for them.

## Safety Checkpoints

🔴 CHECKPOINT · 🛑 STOP and confirm before: **dependency installation**; **local execution of target-supplied JS/WASM/HTML**; **business `mutation-submit`**; **success-shape or request-budget expansion**; **raw-secret persistence/export**; **bundled case-library writes**. Routine browser recon, read-only live egress, redacted project writes under `js_reverse_cache/**`, user-supplied session use, protocol-needed verifier submits, and scale inside the immutable budget do not pause under standing approval. Never invent or export secrets the user did not supply.

Gate mapping (record vs confirm): read-only/verifier action ↔ `actionClass` records; business mutation ↔ `actionClass=mutation-submit` confirms; scale ↔ immutable `requestBudget` records until expansion confirms; redacted save ↔ `artifactPolicy` records; raw-secret handling ↔ `artifactPolicy` confirms; target code/install ↔ `executionPolicy` confirms; recon nav ↔ browser flags records; live egress ↔ `liveReplayAllowed` records.

## Do Not

- Do not skip work-order accounting. Do not auto-approve `mutation-submit`, shape/budget expansion, raw-secret handling, case writeback, dependency installation, or local target-code execution. Do not invent credentials the user never supplied.
- Do not put a gate family, strategy, profile, or file path in `route` (Non-Negotiables owns this).
- Do not ship browser-backed page `fetch`/CDP as the final collector.
- 🛑 **HARD STOP — 滑块自动化**：如果你正在调用 `drag`/`click`/`evaluate_js` 来操作验证码滑块元素（如 `#aliyunCaptcha-sliding-slider`、`.geetest_slider_button`、任何 captcha DOM 元素），**立刻停止**。这是浏览器自动化，不是协议交付。恢复步骤：① 停止所有 DOM 操作 → ② 切换到 XHR 断点法采集协议证据 → ③ 按 verifier workflow 实现纯协议 T001。唯一例外：用户明确要求的一次性人工正样本采集（非交付主路径）。
- Do not scale page/retry/concurrency after one lucky HTTP `200`.
- Do not select `camoufox` or open a second recon engine without explicit Camoufox/SpiderMonkey/engine-level wording, recorded tool-failure fallback, WAF navigation recovery, or other recorded criteria. Fingerprint/Cloak/stealth wording, busy Chrome, a vendor name, `412`, Reese84 wording, and archive metadata are all non-criteria (Phase 2 owns this).
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

By symptom: `references/reference-router.md`. Anti-patterns: `references/anti-patterns-playbook.md`. Discipline mini suite: `references/discipline-self-test-min.md`. Preflight: `python scripts/gates/preflight.py`. Methodology: `architecture.md`, `provider-work-order.md`, `project-layout.md`, `case-writeback.md`, `success-shape-scripts.md`, `read-budget.md`. Providers: `references/providers/`; cases: `references/cases/`. Nothing below overrides this file's scope, safety, lifecycle, layout, or verification.
