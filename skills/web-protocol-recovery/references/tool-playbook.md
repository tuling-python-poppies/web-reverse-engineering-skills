# Tool Selection And Escalation

Use this file when the next tool family is unclear. It selects one Provider or focused reference; it does not duplicate MCP API recipes. The selected `PROVIDER.md` and the connected tool schema are authoritative for concrete calls.

## Proof Order

1. On fresh Chromium targets: complete the **mandatory lightweight paired pass** — `chrome-devtools` baseline, then `js-reverse` initiator/source/mutation (serial; report a real blocker if either half is unavailable).
2. Capture one clean request/response baseline (DevTools half owns the first clean network view).
3. Identify the real route and initiator (js-reverse half).
4. Diff moving wire fields.
5. Add the narrowest runtime proof that answers one named blind spot.
6. Optional fingerprint tier: visible CloakBrowser only after explicit wording or recorded fingerprint/observer evidence (does not replace the paired pass).
7. Reproduce one stable request locally.
8. Scale only after repeatability and semantic acceptance.

## Capability Snapshot

Before the first current-target browser action, record the available evidence surfaces without opening the target in more than one tool family:

- required browser families present or missing: `chrome-devtools`, `js-reverse`, Camoufox, WeChat miniapp debugger when applicable
- methods required by the selected Provider, including navigation, network list/detail/body, initiator/source, script export/search, breakpoints/hooks, storage/cookie inspection, and cleanup
- configured browser mode: launch, attach, headless/headful, Cloak tier availability, explicit WebSocket/debug endpoint when known
- optional passive or environment surfaces: HAR/Reqable, PCAP/Wire visibility, AdsPower/profile manager, local transport client
- blockers that make one paired-pass half unavailable

This snapshot is bookkeeping, not a permission grant. Source trees on disk do not prove MCP availability, and a local Python environment check cannot prove that an agent-side MCP server is mounted. Refresh the snapshot only when the tool registry, browser mode, target context, or control channel changes.

## Provider Selection

| Need | Select | Do not combine with |
|---|---|---|
| Ordinary Web flow, redirects, network, initiators, source, breakpoints, wrappers, WebSocket | `references/providers/reconnaissance/chromium-recon/PROVIDER.md` | Camoufox unless its engine criteria are met |
| Explicit CloakBrowser / 指纹浏览器 / fingerprint / stealth wording, or first proved fingerprint escalation | Chromium Recon Provider, Cloak tier | Camoufox as a name substitute |
| Explicit Camoufox/SpiderMonkey or engine-event property tracing | `references/providers/reconnaissance/camoufox/PROVIDER.md` (+ optional `camoufox/references/ops-ladder.md`) | Chromium contexts in parallel |
| WMPF/AppService/WeChat miniapp debugger | `references/providers/reconnaissance/wechat-miniapp/PROVIDER.md` (+ optional `wechat-miniapp/references/ops-playbook.md`) | Web browser reconnaissance |
| One known reversible observation boundary | `references/providers/protocol-recovery/browser-hooks/PROVIDER.md` | Broad unknown-entry discovery |
| Identified source region needs structural restoration | `references/providers/protocol-recovery/ast/PROVIDER.md` | Network ownership or final delivery |
| Concrete environment-read mismatch is proved | `references/providers/implementation/python-node/strategies/env-patch/STRATEGY.md` | Guessing broad browser surfaces |
| Narrow artifact needs host-visible JS semantics | `references/embedded-browser-runtime-playbook.md`, then `references/providers/implementation/iv8/PROVIDER.md` (API gate: `iv8/references/api-inventory.md`) | Full rendering/interaction as delivery |
| Captcha or one-shot verification owns the gate | `references/providers/protocol-recovery/verifier/PROVIDER.md` | Treating it as an ordinary signer or generic OCR |
| Akamai Bot Manager sensor/cookie state machine owns the gate | `references/providers/protocol-recovery/akamai/PROVIDER.md` | Guessing from generic 403, one cookie name, or treating sensor 200 as success |
| River Security / 瑞数 412, `$_ts`, S/T Cookie, URL/header challenge state owns the gate | `references/providers/protocol-recovery/river-security/PROVIDER.md` | Treating vendor name, suspicion, or 412 alone as proof; jumping to Camoufox by default |
| Reese84 challenge, solution token, `reese84` cookie / `x-d-token`, and business admission own the gate | `references/providers/protocol-recovery/reese84/PROVIDER.md` | Guessing from generic Imperva/interstitial/error 15/incap cookies, or treating a token/OAuth 200 as business success |
| Protocol is proved and browser-free Python delivery remains | `references/providers/delivery/python-collector/PROVIDER.md` | Further reconnaissance without a blocker |

## Browser Lifecycle Invariant

The ordinary dual-recon route is serialized (paired pass is mandatory on fresh Chromium targets):

```text
IDLE -> CHROME_ACTIVE_VISIBLE_BASELINE (paired half 1) -> CHROME_PARKED
     -> JS_ACTIVE_HEADLESS explicit launch (paired half 2) -> JS_CLOSED
     -> JS_CLOAK_VISIBLE (optional fingerprint tier)
IDLE | no-window exception -> JS_ACTIVE_HEADLESS (DevTools window skipped; js-reverse still required; document)
IDLE | RESIDUAL_HEADFUL -> JS_RELAUNCH_HEADLESS (brief flash OK) -> JS_ACTIVE_HEADLESS
JS_ACTIVE_HEADLESS -> JS_CLOSED -> CHROME_ACTIVE_VISIBLE_BASELINE
JS_ACTIVE_HEADLESS -> JS_CLOSED -> JS_CLOAK_VISIBLE
JS_CLOSED + auto-launch headful -> RESIDUAL_HEADFUL (must relaunch; do not navigate)
```

- Ownership states are explicit: `IDLE`, `CHROME_ACTIVE`, `CHROME_PARKED`, `JS_REVERSE_ACTIVE`, `JS_REVERSE_PARKED`, `JS_REVERSE_CLOSED`, `CAMOUFOX_ACTIVE`, `RETAINED_EXCEPTION`, and `CLOSED`. Process presence is not ownership.
- Never place `chrome-devtools-mcp` and `js-reverse-mcp` browser calls in one parallel batch.
- Keep profiles isolated unless the user explicitly accepts shared-state contamination.
- Save approved evidence before a switch; old page/request/script IDs become stale.
- Fresh Chromium targets: **both** DevTools baseline and js-reverse mutation evidence before the final collector, unless a real external blocker or documented exception (evidence-reuse / offline local-proof / non-Chromium route) applies.
- Ordinary Chromium reconnaissance starts with a **Chrome DevTools visible clean baseline** after recon gates (`browserReconAllowed`, side-effect approval, budget, exact scope). That visible window is the approved baseline step, not an uncontrolled auto-launch.
- User “no ordinary window / background-only” may skip only the **visible DevTools window**; do not treat that as permission to skip js-reverse.
- The js-reverse mutation/source pass prefers explicit `js-reverse-mcp_launch_browser({headless:true, cloakBinaryPath:""})` plus Headless Acceptance; MCP auto-launch and CLI defaults are not substitutes for that call.
- A brief window flash while closing residual headful Chrome during a headless relaunch is allowed; a normal-Chrome window that remains after headless acceptance is a blocker unless the user explicitly asked for a visible ordinary browser.
- `close_browser` clears runtime headless overrides; the next js-reverse tool may auto-launch CLI headful. After close, re-run explicit launch for the next intended mode before any further browser action, or stay closed.
- Cloak remains visible by default unless the user asks for hidden Cloak; that visibility exception applies only to Cloak, not normal Chrome. Cloak does not replace the paired pass.
- Park Chrome with only a sacrificial `about:blank`; this isolates lifecycle but does not erase profile state.
- Close js-reverse before returning to Chrome or escalating to Camoufox.
- Clear task-owned hooks, routes, captures, cookies/storage/cache when the context is disposable; otherwise report owner, retained scope, reason, and deadline.

### Sequential handoff gate

Before switching browser families or returning to a parked family:

1. save the clean request/response pair, redirect chain, final target URL, relevant page state, network identifiers, source coordinates, screenshots/snapshots when needed, and every artifact the next phase requires
2. record whether the current session, verifier round, in-memory secret, manual interaction, or challenge state is replayable
3. remove or disable invasive hooks when supported, resume paused runtimes, and quiesce target activity as far as the installed tool allows
4. record the resulting lifecycle state before granting `TARGET_ACTIVE` to the next family

Use `RETAINED_EXCEPTION` only when cleanup would destroy the only unreplayable session chain, verifier round, in-memory key, or manual verification result. A retained family must not be used while another family owns `TARGET_ACTIVE`; record why it cannot be rebuilt yet and the release deadline.

### Headless acceptance (`effective_headless`)

`effective_headless` is the preferred launch-result field meaning the process is actually headless (not merely requested). Scope: **js-reverse normal Chrome** when that pass requires headless — not the default DevTools visible baseline, and not Cloak.

1. Request: `launch_browser({headless:true, cloakBinaryPath:""})` (explicit; not auto-launch).
2. Prefer returned fields: Cloak inactive, and either `effective_headless=true` or an equivalent explicit headless confirmation (`headless=true` with no headful/window flag).
3. Missing `effective_headless` is not automatic pass or fail by itself: re-check launch args and available page/binary status; fail if a normal OS browser window remains for this js-reverse task after relaunch settles, or headless cannot be proved.
4. Relaunch from residual headful may flash once while the old process closes; that flash alone is not failure and not success—judge the settled state.
5. Fail closed on persistent visible normal Chrome after headless acceptance, Cloak active on a normal-Chrome step, or headful/windowed launch reports. Return a tooling blocker; do not navigate on that residual until relaunch is accepted.

Boolean authorization gates (`browserReconAllowed`, `browserNavigationSideEffectsApproved`, `liveReplayAllowed`, etc.) use JSON `true`/`false` only; never record `yes`/`no` for those fields.

The Chromium Recon Provider owns exact launch, park, CloakBrowser-path, headless/headful, and cleanup calls. The Camoufox Provider owns its separate runtime lifecycle.

## Escalation Conditions

Move from normal Chrome to the Chromium Cloak tier only after explicit wording or evidence of fingerprint/automation/environment sensitivity, headless/headful divergence, or observer effect. CloakBrowser remains visible by default unless the user explicitly asks for hidden Cloak. Record the exact evidence and keep final delivery browser-free.

Move from Chromium to Camoufox only for explicit Camoufox/SpiderMonkey requests or a proved need for Camoufox-specific engine tracing. A `403`, `412`, or `429` alone is not sufficient.

Move from reconnaissance to one implementation Provider only after naming the boundary:

- stable method/property/request boundary -> browser-hooks
- structural bundle blocker -> AST
- missing environment read/identity/reflection surface -> `python-node` with `strategy: env-patch`
- browser-visible host semantics needed for one local artifact -> iv8
- captcha / verification round -> verifier
- Akamai sensor/cookie state machine -> akamai
- River Security challenge state -> river-security
- Reese84 challenge-cookie and business-admission state -> reese84
- proved protocol ready for delivery -> python-collector

If the selected Provider returns a new blocker, add one Provider/reference. Do not fan out across sibling implementations.

## Symptom Routing

| Symptom | First owner |
|---|---|
| H2 reset, TLS EOF, handshake timeout, UA/HTTP-version split before semantics | `transport-pre-gate-playbook.md` |
| Page and wire disagree on route | `decoy-and-real-request-playbook.md` |
| Wrapper changes query/body/header slots | `transport-wrapper-playbook.md` |
| Helper named md5/btoa/sha but fixed inputs disagree with stdlib | `crypto-patterns.md` |
| One field has short/long bands or several writer call stacks | `multi-writer-field-playbook.md` |
| Browser vs local multi-layer mismatch; redirect/wrapper triage still open | `environment-patch-playbook.md` |
| Live inspection unstable; debugger traps / self-rewriting sources | `offline-inline-deob-playbook.md` |
| Challenge harvest / server-JS cookie / side asset / full envelope | `challenge-state-envelope-playbook.md` (one file only) |
| Public passive key/config/nonce and encrypted wrapper | `public-bootstrap-envelope-playbook.md` |
| Captcha / one-shot verifier gates business request | `references/providers/protocol-recovery/verifier/PROVIDER.md`, then one selected captcha family reference |
| Akamai `_abck` / `bm_*` / `sensor_data` / `/akam/13/pixel_*` gates business request | `references/providers/protocol-recovery/akamai/PROVIDER.md` |
| River Security / 瑞数 `412` + `$_ts` / S-T Cookie / `r="m"` gates business request | `references/providers/protocol-recovery/river-security/PROVIDER.md` |
| Reese84 cookie / `x-d-token` plus challenge script or token-response evidence gates business request | `references/providers/protocol-recovery/reese84/PROVIDER.md` |
| Output depends on navigator/DOM/reflection/native surfaces | `environment-patch-playbook.md` |
| Complete runtime profiles work but mixed fragments or later transform stages fail | `opaque-runtime-profile-playbook.md` |
| Accepted/rejected chains need secret-free normalization and first-divergence comparison | `reproducible-evidence-playbook.md` |
| Maintained impersonation backend cannot express one proved TLS/H2 field | `native-transport-profile-playbook.md` |
| Encoded/compressed/font/binary response | `response-decode-playbook.md` |
| Export/report uses create, task polling, delayed verification, and download | `async-export-job-playbook.md` |
| Replay exists but `403`/`412`/`429`, business error, stale state, or pacing remains | `troubleshooting-playbook.md` |

## Local Helpers

- `scripts/tools/check_reverse_env.py`: verify local reverse dependencies.
- `scripts/tools/crypto_fingerprint.py`: classify suspicious digest/alphabet output.
- `scripts/tools/protocol_diff.py`: compare captured wire structures.
- `scripts/tools/evidence_normalizer.py`: normalize HAR/transcript chains into secret-free ordered evidence.
- `scripts/tools/transcript_diff.py`: report the first structural difference between normalized chains.
- `scripts/tools/transform_trace_diff.py`: report the first stage and byte divergence in runtime traces.
- `scripts/tools/transport_profile_diff.py`: validate and compare ordered TLS/H2/connection profiles.
- `scripts/tools/grpc_frame_inspector.py`: inspect bounded gRPC/grpc-web frame and trailer structure without decoding payloads.
- `scripts/tools/practice_lab.py`: run seven deterministic protocol cases with negative controls.
- `scripts/providers/delivery/python-collector/scaffold_project.py`: create only approved missing `web-protocol-recovery-simple` paths.
