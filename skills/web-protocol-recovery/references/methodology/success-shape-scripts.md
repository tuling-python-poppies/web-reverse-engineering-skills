# Default Scripts By Success Shape

Use these as the first path. Escalate only after naming a concrete blocker. Under standing approval (SKILL Non-Negotiables item 7), routine protocol actions inside the selected shape run without pausing the user: browser recon, read-only live egress, redacted project writes, user-supplied session use, protocol-needed verifier submit, and scale inside the immutable budget. When no budget is supplied, record an immutable `requestBudget` of `total=100` and `remaining=100`; do not ask the user for this routine value. Record routine fields internally. Use `nextAsk` only for execution hard stops or scope/governance decisions.

## Shared First Response

Emit four lines when starting work:

```text
shape: <evidence|local-proof|compact-replay|collector>
route: <selected Provider or evidence-reuse>
nextAsk: <none | missing sample/context | executionPolicy | mutation-submit | scope-expansion | raw-secret-handling | case-writeback>
nextRead: <paths per read-budget>
```

Do not paste the full intake form. Do not open Camoufox unless its Phase 2 criteria are already met.

For a non-trigger boundary response, do not emit the four-line protocol header. Say the request is outside web-protocol-recovery and name the nearest normal workflow or skill.

## evidence

1. Ask only for missing request/source/trigger context (URL, sample, field name). An explicit protocol-recovery request naming a URL authorizes bounded recon unless it also says offline/no-browser; a bare URL with no recovery intent does not. Before fresh Chrome recon, **auto-record** exact scope, browser flags, a positive immutable navigation budget (default task budget `total=100` when none was supplied), and prior cumulative `observedAutomatic`. Boolean gates use JSON `true`/`false` only (never `yes`/`no`).
2. Prefer supplied artifacts. Otherwise read the WeChat provider for miniapp signals, the Camoufox provider for an explicit Camoufox/SpiderMonkey request, or Chromium for ordinary Web — then launch recon.
3. Read-only evidence fast path: when supplied text/files, registry metadata, or a static question is enough and no browser/live/write is needed yet, keep `route: evidence-reuse`, inspect only supplied/bounded references, and do not ask for `projectRoot`, write mode, live replay approval, request budget, artifact retention, or full authorization.
4. If a no-write Provider read is the smallest next read, read exactly one selected Provider `PROVIDER.md` or one bounded Provider-local reference; do not execute Provider tools.
5. Capture real request, initiator, or precise blocker.
6. When durable evidence is needed, default `projectRoot` to cwd (or the user-named folder) and write under `js_reverse_cache/**` without asking.
7. A blocker may change the Provider route without changing shape. A larger deliverable requires `nextAsk: scope-expansion`; do not treat silence as permission to upgrade.

## local-proof

1. Begin with `shape: local-proof` and `route: evidence-reuse` for a self-contained deterministic proof, or the selected implementation Provider when one is needed. Never put `decode`, `decode-gated`, or another gate family in `route`.
2. Confirm fixed vectors, source path, or decoded sample inputs.
3. Read one active Provider or selected strategy/profile only when needed: `browser-hooks`, `ast`, `verifier`, `akamai`, `river-security`, `reese84`, `iv8`, `python-node`, `nv8`, or `pure-python`. For Node/jsdom gaps, use `route: python-node` and `strategy: env-patch`. For full Edge-compatible Akamai/Kasada sensor execution, use `route: nv8`. For Douyin BDMS pure-Python maintenance, use `route: pure-python` and `profile: douyin-abogus-native`. For captcha, read `verifier/PROVIDER.md` first, then at most one selected family reference. For Akamai, read `akamai/PROVIDER.md` first, then at most one selected Akamai reference. For River Security, read `river-security/PROVIDER.md` first and select at most one registry case. For Reese84, read `reese84/PROVIDER.md` first and select the template case only after current Reese84-native evidence passes the route gate. A self-contained deterministic decode may remain inline. Do not select `python-collector` for local-proof.
4. Enumerate every supplied fixed vector. Pure data transforms may run offline. Executing target-supplied JS/WASM/HTML still requires user-confirmed `executionPolicy.targetCodeExecution=local-only` or `approved-reviewed-hash` with matching SHA-256 approval, and must run through the Provider-owned bounded process launcher even when live egress is denied.
5. Execute approved vectors for a proof request; for a planning-only request, list them under `acceptanceTest` and report `result: not run (planning only)` rather than claiming parity.
6. Include labeled `acceptanceTest` and `result` fields even when the proof is inline and produces no saved artifact; include path and SHA-256 only when it does.
7. Stop at verified local proof unless the user asks for live replay or collector. Escalate only after acceptance passes.

## compact-replay

1. Record Phase 0 work-order fields under standing approval; when the user gave no budget, use immutable `requestBudget.total=100` and `requestBudget.remaining=100`; resolve cwd to the absolute `projectRoot` before writes.
2. Ordinary Web first response must include:
   ```text
   layout: web-protocol-recovery-simple
   reconSequence: mandatory paired pass (chrome-devtools clean baseline -> Chrome parked -> js-reverse mutation, explicit launch; headless preferred for mutation) -> visible CloakBrowser only after explicit/fingerprint selection
   ```
3. Recover one short root `main.py` path, often with a narrow iv8/helper artifact generator.
4. Write root `分析报告.md` before claiming Full complete (see `references/report-templates.md`).
5. Verify fixed vectors, then one minimal live replay (`liveReplayAllowed` auto-true under standing approval).
6. Do not add pagination, concurrency, or broad collection unless the user asked for collector scale.

## collector

1. Record work-order fields and resolve cwd to an absolute `projectRoot` before any write (no full intake form). If no budget was supplied, use immutable `requestBudget.total=100` and `requestBudget.remaining=100` without asking.
2. Same ordinary-Web first-response literals as compact-replay.
3. Prove real endpoint and moving state before scaffolding.
4. Read `references/providers/delivery/python-collector/PROVIDER.md` only after protocol proof.
5. Final path is browser-free Python; Python owns live egress. Scale after a repeatable first request within the initially recorded budget. Exhaustion or a larger budget requires `nextAsk: scope-expansion`.
6. Write root `分析报告.md` before claiming Full complete; scaffold may use `--report`.

## Stateful Response And Wire-Body Overlay

Apply this overlay to `compact-replay` and `collector` work whenever a request can move between challenge and trusted states:

1. Classify each response before applying the next gate: challenge/degraded, trusted/full, or business. A collector script or HTTP 200 alone does not identify the branch.
2. Tie each cookie assertion to its observed writer and next consumer. Do not require a challenge-only cookie on an already trusted/full response.
3. Compare the final serialized request body, including fields appended or normalized by page code immediately before submit, against the accepted wire request.
4. Accept the branch only after its semantic business marker/data shape passes; do not substitute a stage cookie, collector 200, or generic page shell for business success.

## WeChat Route Overlay

WeChat is a route, not a success shape. Keep the selected `evidence`, `local-proof`, `compact-replay`, or `collector` shape.

1. Use the user-named debugger endpoint or the default `127.0.0.1:62000` when they already said miniapp/WMPF.
2. Read `references/providers/reconnaissance/wechat-miniapp/PROVIDER.md`.
3. Initial target listing may run under `no-write`; promote to write/live under standing approval when evidence must be saved.
4. Use only user-supplied account/session material; do not invent credentials.
5. Keep miniapp IDs inside the WeChat lease; never reuse them on Chromium/Camoufox/iv8.

## Escalation Rule

When a script must grow, name:

```text
blocker: <one sentence>
nextRead: <exactly one additional path>
why: <smallest honest move>
```

Continue with the same shape when only the Provider changes. Before a larger shape, state the additional deliverable and wait for `nextAsk: scope-expansion` confirmation.

## Policy: Case-Read Overlay

When asked about case read policy, use `route: evidence-reuse` and echo the exact windows from `references/methodology/read-budget.md`: initial dispatch 0-2 + one blocker expansion, selected case bundle order/cap, whole-task non-resettable cap, no sibling case after mismatch.

## Policy: Scope / Budget-Reset Overlay

When asked about scope or budget reset, use `route: evidence-reuse`. Echo exact scheme/host/port/prefix, verify pre-egress check before every navigation/request/retry/WebSocket handshake/sent frame, state shared total/remaining and one-unit consumption, and note the Chrome automatic-network exception per `references/methodology/provider-work-order.md`.

## Maintenance note

`references/official-self-test-task-suite.md` is for skill self-test/maintenance only; do not load it on ordinary protocol tasks.

## Gate: Chrome Automatic-Traffic Overlay

Chrome automatic traffic is **recorded**, not user-confirmed. On protocol tasks under standing approval, auto-set `browserReconAllowed=true`, `browserNavigationSideEffectsApproved=true`, a positive `automaticObservationStopThreshold`, and at least one navigation unit before launch. Still:

```text
automaticTraffic: observed destinations are evidence, never extra host authorization; stop further actions when cumulative reaches threshold or top-level leaves scope
```

If the user **explicitly denied** browser recon, answer without launching, keep `nextAsk: none`, and record the offline/no-browser constraint in status.

## Gate: Denied Live-Replay Overlay

Default for protocol `compact-replay` / `collector` is `liveReplayAllowed=true` under standing approval. Use the blocked offline path only when the user **explicitly** said offline / no live / fixed-vector only, or set `liveReplayAllowed=false`.

If live is explicitly denied and the requested shape is `compact-replay`, answer:

```text
shape: compact-replay
route: evidence-reuse
nextAsk: none
nextRead: none
status: offline-only; HTTP request/retry/WebSocket handshake/sent-frame egress denied by user
requestBudget: consumed=0; remaining=<unchanged>
nextAction: continue offline fixed-vector verification only
```

If offline proof later requires local target-code execution, use a new gated turn with `nextAsk: executionPolicy`; do not encode two alternatives in one header value.

If the requested shape is `collector`, answer the same block with `shape: collector`. Never emit a combined or placeholder shape.

## Gate: Runtime Cleanup Overlay

Reject `status=complete` while any task-owned resource remains `live` or `cleanup.complete=false`. Approved retention records full runtime identity (resourceId, engine, contextId, targetId, navigationEpoch, lifecycle=retained), owner, reason, approval evidence, and release deadline; `cleanup.remainingResources` then contains exactly those retained IDs. Any other remaining resource requires cleanup and a blocked or failed result.

## Context Checkpoint Overlay

`checkpoint.md` template:

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
- firstDivergence：[stage/path/writer/firstConsumer 或 unknown]
- stageSettle：[stageCount/order/timing/framing/stateTransition]
- workOrderId：[stable-id]
- budget：[priorRemaining/consumed/remaining]
- 关键文件状态：
  - js_reverse_cache/aliyun_v2_evidence/init_round.json: [存在/缺失]
  - js_reverse_cache/private/pzds/t001_profile.json: [存在/缺失]
```

`checkpoint.json` 至少包含 `checkpointId`、`workOrderId`、`scopeDigest`、结构化 `budget`、结构化 `readBudget`、`firstDivergence`、`stageSettle`、`runtimeIds`、`browserState`、`blocker` 和 `nextStep`。恢复时不得重置 budget、read budget 或 runtime lifecycle。

这个检查点服务于两个目的：
1. **上下文压缩后恢复**：当上下文窗口被截断时，先读 `js_reverse_cache/checkpoint.md` 确认当前状态，而不是从记忆中重建
2. **避免重复工作**：如果检查点显示 AK/SECRET 已提取，不要再次提取

恢复时先读取 checkpoint，再读取当前 work-order；不得从对话记忆重建预算、runtime ID、scope 或已接受证据。浏览器与本地运行结果不一致时，先按 stage count -> stage order -> timing/framing -> cookie/header transition -> timer/promise/event-loop settle 的顺序定位 `firstDivergence`，不要从最终 HTTP 状态倒推 signer 修复。

浏览器残留进程恢复格式：若任务因浏览器启动失败（进程残留）而暂停，checkpoint 需额外记录：

```markdown
- 浏览器状态：
  - 残留进程：[有/无]（上次启动失败错误特征：exit code / 错误信息）
  - 恢复步骤：暂停并记录 blocker；不得自动终止用户浏览器或清理未确认归属的 profile。只有用户明确确认任务自有 profile 后，才使用对应浏览器生命周期工具清理并重新启动采集
```

## Case Delivery Overlay

Implementation cases can provide protocol primitives without the user's current
live state. Keep the split explicit:

- `entry.py` is a narrow starting point, not the final collector.
- `t001_profile_refresh.py` is an updater, not a bootstrapper; it still needs a
  current profile package with `combat511`/`combat504` and an accepted movement
  seed.
- FeiLin127 `field21` needs at least twelve capture rounds; three rounds and
  some six-round sets remain ambiguous.

Run offline vectors first, then the current verifier and business replay.
