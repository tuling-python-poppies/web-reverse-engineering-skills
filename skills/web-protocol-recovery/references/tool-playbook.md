# Tool Selection And Escalation

Use this file when the next tool family is unclear. It selects one Provider or focused reference; it does not duplicate MCP API recipes. The selected `PROVIDER.md` and the connected tool schema are authoritative for concrete calls.

## Proof Order

1. Capture one clean request/response baseline.
2. Identify the real route and initiator.
3. Diff moving wire fields.
4. Add the narrowest runtime proof that answers one named blind spot.
5. Reproduce one stable request locally.
6. Scale only after repeatability and semantic acceptance.

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

The ordinary dual-recon route is serialized:

```text
IDLE -> CHROME_ACTIVE -> CHROME_PARKED -> JS_ACTIVE_HEADLESS|JS_ACTIVE_HEADFUL -> JS_CLOSED
JS_ACTIVE_* -> JS_CLOSED -> CHROME_ACTIVE
```

- Never place `chrome-devtools-mcp` and `js-reverse-mcp` browser calls in one parallel batch.
- Keep profiles isolated unless the user explicitly accepts shared-state contamination.
- Save approved evidence before a switch; old page/request/script IDs become stale.
- Park Chrome with only a sacrificial `about:blank`; this isolates lifecycle but does not erase profile state.
- Close js-reverse before returning to Chrome or escalating to Camoufox.
- Clear task-owned hooks, routes, captures, cookies/storage/cache when the context is disposable; otherwise report owner, retained scope, reason, and deadline.

The Chromium Recon Provider owns exact launch, park, CloakBrowser-path, headless/headful, and cleanup calls. The Camoufox Provider owns its separate runtime lifecycle.

## Escalation Conditions

Move from normal Chrome to the Chromium Cloak tier only after explicit wording or evidence of fingerprint/automation/environment sensitivity, headless/headful divergence, or observer effect. Record the exact evidence and keep final delivery browser-free.

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
| `202`/`412` executable bootstrap, side asset, derived state, or runtime egress artifact | `challenge-state-envelope-playbook.md` |
| Public passive key/config/nonce and encrypted wrapper | `public-bootstrap-envelope-playbook.md` |
| Output depends on navigator/DOM/reflection/native surfaces | `environment-patch-playbook.md` |
| Encoded/compressed/font/binary response | `response-decode-playbook.md` |
| Replay exists but `403`/`412`/`429`, business error, stale state, or pacing remains | `troubleshooting-playbook.md` |

## Local Helpers

- `scripts/check_reverse_env.py`: verify local reverse dependencies.
- `scripts/crypto_fingerprint.py`: classify suspicious digest/alphabet output.
- `scripts/protocol_diff.py`: compare captured wire structures.
- `scripts/providers/python-collector/scaffold_project.py`: create only approved missing `web-protocol-recovery-simple/v1` paths.
