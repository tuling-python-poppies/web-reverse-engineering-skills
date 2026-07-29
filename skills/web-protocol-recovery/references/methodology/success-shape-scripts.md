# Default Scripts By Success Shape

Use these as the first path. Escalate only after naming a concrete blocker. Full Phase 0 fields still apply before navigation, live egress, account/session use, target-code execution, dependency install, or writes become relevant.

## Shared First Response

Emit four lines when starting work:

```text
shape: <evidence|local-proof|compact-replay|collector>
route: <selected Provider or evidence-reuse>
nextAsk: <only fields needed now>
nextRead: <paths per read-budget>
```

Do not paste the full intake form. Do not open Camoufox unless its Phase 2 criteria are already met.

For a non-trigger boundary response, do not emit the four-line protocol header. Say the request is outside web-protocol-recovery and name the nearest normal workflow or skill.

## evidence

1. Ask only for missing request/source/trigger context. Before fresh Chrome recon, require authorization basis, exact scheme/host/port/absolute route prefix, `browserReconAllowed=true`, one navigation budget unit, prior cumulative `observedAutomatic`, and explicit approval for unpreventable automatic browser-network side effects. Boolean gates use JSON `true`/`false` only (never `yes`/`no`).
2. Prefer supplied artifacts. Otherwise read the WeChat provider for miniapp signals, the Camoufox provider for an explicit Camoufox/SpiderMonkey request, or Chromium for ordinary Web.
3. Read-only evidence fast path: when supplied text/files, registry metadata, or a static question is enough and no browser navigation, live egress, account/session use, target-code execution, dependency install, file write, raw artifact save, verifier submission, mutation, retry, scale-up, or retention is proposed, keep `route: evidence-reuse`, inspect only supplied/bounded references, and do not ask for `projectRoot`, write mode, live replay approval, request budget, artifact retention, or full authorization.
4. If a no-write Provider read is the smallest next read, read exactly one selected Provider `PROVIDER.md` or one bounded Provider-local reference; do not execute Provider tools.
5. Capture real request, initiator, or precise blocker.
6. Stop before any engine/session/target transition that requires durable evidence. Do not ask for `projectRoot`, retention, or scale when no write/live replay is proposed; if such a transition becomes necessary, activate the project-root gate and ask once before the save or switch.
7. A blocker may change the Provider route without changing shape. Expand the deliverable only when the user expands scope or explicitly accepts the smallest larger shape.

## local-proof

1. Begin with `shape: local-proof` and `route: evidence-reuse` for a self-contained deterministic proof, or the selected implementation Provider when one is needed. Never put `decode`, `decode-gated`, or another gate family in `route`.
2. Confirm fixed vectors, source path, or decoded sample inputs.
3. Read one active Provider or selected strategy/profile only when needed: `browser-hooks`, `ast`, `verifier`, `akamai`, `river-security`, `reese84`, `iv8`, `python-node`, or `pure-python`. For Node/jsdom gaps, use `route: python-node` and `strategy: env-patch`. For Douyin BDMS pure-Python maintenance, use `route: pure-python` and `profile: douyin-abogus-native`. For captcha, read `verifier/PROVIDER.md` first, then at most one selected family reference. For Akamai, read `akamai/PROVIDER.md` first, then at most one selected Akamai reference. For River Security, read `river-security/PROVIDER.md` first and select at most one registry case. For Reese84, read `reese84/PROVIDER.md` first and select the template case only after current Reese84-native evidence passes the route gate. A self-contained deterministic decode may remain inline. Do not select `python-collector` for local-proof.
4. Enumerate every supplied fixed vector. Pure data transforms may run offline. Executing target-supplied JS/WASM/HTML still requires `executionPolicy.targetCodeExecution=approved-reviewed-hash`, matching SHA-256 approval, and a capability-denied sandbox even when live egress is denied.
5. Execute approved vectors for a proof request; for a planning-only request, list them under `acceptanceTest` and report `result: not run (planning only)` rather than claiming parity.
6. Include labeled `acceptanceTest` and `result` fields even when the proof is inline and produces no saved artifact; include path and SHA-256 only when it does.
7. Stop at verified local proof unless the user asks for live replay or collector. Escalate only after acceptance passes.

## compact-replay

1. Complete applicable Phase 0 fields and the project-root gate before writes.
2. Ordinary Web first response must include:
   ```text
   layout: web-protocol-recovery-simple
   reconSequence: mandatory paired pass (chrome-devtools clean baseline -> Chrome parked -> js-reverse mutation, explicit launch; headless preferred for mutation) -> visible CloakBrowser only after explicit/fingerprint selection
   ```
3. Recover one short root `main.py` path, often with a narrow iv8/helper artifact generator.
4. Write root `分析报告.md` before claiming Full complete (see `references/report-templates.md`).
5. Verify fixed vectors, then one approved minimal live replay.
6. Do not add pagination, concurrency, or broad collection.

## collector

1. Full intake + project-root gate before any write.
2. Same ordinary-Web first-response literals as compact-replay.
3. Prove real endpoint and moving state before scaffolding.
4. Read `references/providers/delivery/python-collector/PROVIDER.md` only after protocol proof.
5. Final path is browser-free Python; Python owns live egress. Scale only after repeatable first request and explicit confirmation.
6. Write root `分析报告.md` before claiming Full complete; scaffold may use `--report`.

## WeChat Route Overlay

WeChat is a route, not a success shape. Keep the selected `evidence`, `local-proof`, `compact-replay`, or `collector` shape.

1. Confirm the debugger endpoint belongs to the user.
2. Read `references/providers/reconnaissance/wechat-miniapp/PROVIDER.md`.
3. Initial target listing may run under `no-write` and `liveReplayAllowed=false`.
4. Complete intake before account/session payloads, triggered actions, or saved evidence.
5. Keep miniapp IDs inside the WeChat lease; never reuse them on Chromium/Camoufox/iv8.

## Escalation Rule

When a script must grow, name:

```text
blocker: <one sentence>
nextRead: <exactly one additional path>
why: <smallest honest move>
```

Continue with the same shape when only the Provider changes. Before a larger shape, state the additional deliverable and obtain explicit scope confirmation.

## Policy: Case-Read Overlay

When asked about case read policy, use `route: evidence-reuse` and echo the exact windows from `references/methodology/read-budget.md`: initial dispatch 0-2 + one blocker expansion, selected case bundle order/cap, whole-task non-resettable cap, no sibling case after mismatch.

## Policy: Scope / Budget-Reset Overlay

When asked about scope or budget reset, use `route: evidence-reuse`. Echo exact scheme/host/port/prefix, verify pre-egress check before every navigation/request/retry/WebSocket handshake/sent frame, state shared total/remaining and one-unit consumption, and note the Chrome automatic-network exception per `references/methodology/provider-work-order.md`.

## Maintenance note

`references/official-self-test-task-suite.md` is for skill self-test/maintenance only; do not load it on ordinary protocol tasks.

## Gate: Chrome Automatic-Traffic Overlay

When a baseline is requested but Chrome-specific approval is missing, answer without launching:

```text
shape: evidence
route: chromium-recon
nextAsk: browserReconAllowed=true, browserNavigationSideEffectsApproved=true, automaticObservationStopThreshold=<positive integer>, requestBudget.remaining>=1 navigation unit, prior observedAutomatic object
nextRead: none
scope: scheme=<exact> host=<exact> port=<exact> route=<absolute prefix>
chromeBaseline: blocked pending side-effect approval
automaticTraffic: observed destinations are evidence, never authorization; stop when cumulative reaches threshold
```

## Gate: Denied Live-Replay Overlay

For a requested `compact-replay` or `collector` with `liveReplayAllowed=false`, preserve that requested shape but keep execution offline.

If the requested shape is `compact-replay`, answer:

```text
shape: compact-replay
route: evidence-reuse
nextAsk: explicit liveReplayAllowed=true only if live verification is still requested
nextRead: none
status: blocked; HTTP request/retry/WebSocket handshake/sent-frame egress denied
requestBudget: consumed=0; remaining=<unchanged>
nextAction: continue offline fixed-vector verification only
```

If the requested shape is `collector`, answer the same block with `shape: collector`. Never emit a combined or placeholder shape.

## Gate: Runtime Cleanup Overlay

Reject `status=complete` while any task-owned resource remains `live` or `cleanup.complete=false`. Approved retention records full runtime identity (resourceId, engine, contextId, targetId, navigationEpoch, lifecycle=retained), owner, reason, approval evidence, and release deadline; `cleanup.remainingResources` then contains exactly those retained IDs. Any other remaining resource requires cleanup and a blocked or failed result.
