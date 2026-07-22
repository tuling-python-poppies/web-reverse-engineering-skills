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

## Provider Selection

| Need | Select | Do not combine with |
|---|---|---|
| Ordinary Web flow, redirects, network, initiators, source, breakpoints, wrappers, WebSocket | `references/providers/reconnaissance/chromium-recon/PROVIDER.md` | Camoufox unless its engine criteria are met |
| Explicit CloakBrowser / 指纹浏览器 / fingerprint / stealth wording, or first proved fingerprint escalation | Chromium Recon Provider, Cloak tier | Camoufox as a name substitute |
| Explicit Camoufox/SpiderMonkey or engine-event property tracing | `references/providers/reconnaissance/camoufox/PROVIDER.md` (+ optional `camoufox/references/ops-ladder.md`) | Chromium contexts in parallel |
| WMPF/AppService/WeChat miniapp debugger | `references/providers/reconnaissance/wechat-miniapp/PROVIDER.md` (+ optional `wechat-miniapp/references/ops-playbook.md`) | Web browser reconnaissance |
| One known reversible observation boundary | `references/providers/implementation/browser-hooks/PROVIDER.md` | Broad unknown-entry discovery |
| Identified source region needs structural restoration | `references/providers/implementation/ast/PROVIDER.md` | Network ownership or final delivery |
| Concrete environment-read mismatch is proved | `references/providers/implementation/env-patch/PROVIDER.md` | Guessing broad browser surfaces |
| Narrow artifact needs host-visible JS semantics | `references/embedded-browser-runtime-playbook.md`, then `references/providers/implementation/iv8/PROVIDER.md` (API gate: `iv8/references/api-inventory.md`) | Full rendering/interaction as delivery |
| Captcha or one-shot verification owns the gate | `references/providers/implementation/verifier/PROVIDER.md` | Treating it as an ordinary signer |
| Protocol is proved and browser-free Python delivery remains | `references/providers/implementation/python-collector/PROVIDER.md` | Further reconnaissance without a blocker |

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
- missing environment read/identity/reflection surface -> env-patch
- browser-visible host semantics needed for one local artifact -> iv8
- verification round -> verifier
- proved protocol ready for delivery -> python-collector

If the selected Provider returns a new blocker, add one Provider/reference. Do not fan out across sibling implementations.

## Symptom Routing

| Symptom | First owner |
|---|---|
| H2 reset, TLS EOF, handshake timeout, UA/HTTP-version split before semantics | `transport-pre-gate-playbook.md` |
| Page and wire disagree on route | `decoy-and-real-request-playbook.md` |
| Wrapper changes query/body/header slots | `transport-wrapper-playbook.md` |
| Helper named md5/btoa/sha but fixed inputs disagree with stdlib | `patched-helper-playbook.md` (then `crypto-patterns.md`) |
| Browser vs local multi-layer mismatch; redirect/wrapper triage still open | `env-diff-playbook.md` (then `environment-patch-playbook.md`) |
| Live inspection unstable; debugger traps / self-rewriting sources | `anti-debug-playbook.md` (then `offline-inline-deob-playbook.md`) |
| Getter / XHR-fetch egress already emits decisive artifact | `challenge-artifact-harvest-playbook.md` |
| Same-endpoint `202`/JS then cookie then data; refresh function renews params | `server-js-cookie-bootstrap-playbook.md` |
| Tiny side script/WASM/font/config owns next-request state | `side-asset-bootstrap-playbook.md` |
| Full challenge session chain / envelope family / executionPolicy | `challenge-state-envelope-playbook.md` |
| Public passive key/config/nonce and encrypted wrapper | `public-bootstrap-envelope-playbook.md` |
| Captcha / one-shot verifier gates business request | `verifier-replay-playbook.md` (solver work: verifier Provider) |
| Output depends on navigator/DOM/reflection/native surfaces after env layer is named | `environment-patch-playbook.md` |
| Encoded/compressed/font/binary response | `response-decode-playbook.md` |
| Replay exists but `403`/`412`/`429`, business error, stale state, or pacing remains | `troubleshooting-playbook.md` |

## Local Helpers

- `scripts/check_reverse_env.py`: verify local reverse dependencies.
- `scripts/crypto_fingerprint.py`: classify suspicious digest/alphabet output.
- `scripts/protocol_diff.py`: compare captured wire structures.
- `scripts/providers/python-collector/scaffold_project.py`: create only approved missing `web-protocol-recovery-simple/v1` paths.
