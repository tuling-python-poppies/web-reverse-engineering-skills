# Troubleshooting Playbook

Use this file after one bounded replay exists and an observed response/runtime symptom still blocks acceptance. It owns diagnosis by evidence. For preemptive checks against browser-backed delivery, stale-state hardcoding, broad hooks, rung skipping, or shape-only success, use `anti-patterns-playbook.md`.

## Symptom routing

### `403`, `412`, `429`

- compare headers
- compare cookies
- compare pacing
- compare sign freshness
- compare whether the challenged document URL itself succeeds after local bootstrap instead of after a guessed API pivot
- if failures start only after hooks or breakpoints, suspect observer effect and recapture a clean baseline

### `200` with business error

- compare query and body serialization
- compare timestamp precision
- compare transport wrapper outputs
- compare whether a verifier or cookie refresh step is now missing
- if subcodes change across attempts, map the ladder instead of treating each failure as unrelated noise

### `200` with gibberish or strings

- check decrypt path
- check fonts
- check hint arrays for page-specific header clues
- if raw bytes decode cleanly but saved files or terminal output still look garbled, separate local encoding or render issues from target-side decode gates before changing the protocol hypothesis

### the chosen login or session validator always looks valid

- tamper one decisive cookie, token, or session field and rerun the validator as a negative control
- if empty or tampered state still returns `200` or a page shell, treat that route as a false validator rather than proof of login
- find one stricter authenticated business endpoint that fails deterministically on bad state before persisting cookies or session artifacts

### first request works, replay fails

- check rotating cookies
- check in-memory refresh fields
- check whether bootstrap must run before each request
- prove cookie provenance before blaming the signer
- keep first-hop HTML, linked bootstrap assets, seed cookies, and generated state on one fresh session chain before widening environment patches
- if runtime egress exposes a full outbound `Cookie` header, compare that against the jar before blaming one cookie name or one refresh helper

### login looks accepted, but the target business route still redirects or rejects

- treat grant tickets, redirect handles, async follow-up URLs, and auth acks as authentication artifacts, not finished session proof
- capture post-auth callbacks, redirect exchanges, or session-establishing follow-up requests before changing the signer again
- diff cookie state before and after each post-auth hop so you know which step actually materializes the usable session

### local helper fails in a way that looks like target blocking

- check local runtime integrity first: broken symlinks, placeholder link files from copied `node_modules`, missing transitive deps, bad paths, and encoding-induced path resolution failures
- rerun the helper on frozen inputs and separate helper bootstrap failure from protocol failure before changing the signer hypothesis
- if the helper cannot load its own dependency tree, repair the local runtime before reopening target-side reverse work

### async artifact never appears or cannot be matched to one attempt

- establish the observation baseline first: mailbox cursor, webhook receiver, queue offset, or polling window
- trigger the flow only after the baseline is live
- diff pre-trigger and post-trigger artifacts so the attempt-to-artifact mapping is explicit
- treat timing, cursor state, and delayed delivery as part of the protocol workflow, not just operational noise

### user-defined latency threshold or honeypot budget

- if the user says a request or helper step that crosses `N` seconds should be treated as suspicious, encode that as a hard timeout in the collector
- abort immediately when that threshold is crossed instead of silently retrying it away
- report where the threshold is enforced so the handoff reflects the real safety contract

### the same request degrades into password-like or field-like errors after tight pacing

- repeat one previously understood request after a sufficient cooldown before changing fields that already matched
- compare the failure text or subcodes across slow and fast pacing, not just across code edits
- suspect punitive disguise or abuse cooldown when a field-looking error appears only after repeated attempts
- prefer cookie refresh or existing-session reuse over aggressive relogin loops when the target is rate-sensitive

### error or subcode shifts as each patch lands

- treat the changing sequence as evidence that one gate has been cleared and the next gate is now exposed
- distinguish "same failure again" from "different failure after progress"
- update the missing-gate hypothesis before rewriting the signer, wrapper, or bootstrap from scratch
- use the new code to decide whether the next move is cookie provenance, session admission, wrapper slot placement, verifier state, or simple pacing backoff

## Final rule

When a replay fails, route by the observed symptom and change one hypothesis at a time. If no replay exists yet, return to triage rather than treating setup uncertainty as troubleshooting.

## 环境与工具失败恢复

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

**规则**：当一个引擎连续失败 2 次（导航超时、JS 执行失败、状态丢失），**不要宣布「浏览器不可用」**——记录为工具失败条件，并评估下一个 capability adapter。这个 fallback 是工具恢复，不是协议 route 升级；只有 adapter 的选择条件已满足时才切换，不因固定产品链自动升级。exit code 21 / profile 残留按「浏览器启动失败诊断流程」先问用户，不进入自动 fallback：

```
Chrome 失败 x2      → 记录 failureClass，选择满足条件的 fallback adapter
CloakBrowser 失败 x2 → 记录 failureClass，只有 Camoufox criterion 成立才切换
全部适配器失败       → 记录 hard blocker
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
1. **用户确认任务自有 profile**：仅清理当前任务明确归属的浏览器资源，然后重新启动采集；不得按进程名批量终止，也不得操作外部或未确认的 profile 路径
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
