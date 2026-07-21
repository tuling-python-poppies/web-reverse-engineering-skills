# Chromium Recon Provider

## Select When

- Ordinary Web reconnaissance (default route).
- Explicit CloakBrowser / 指纹浏览器 / fingerprint / anti-detection / stealth browser wording (Cloak tier via js-reverse, not Camoufox).
- First fingerprint or observer-effect escalation after a clean Chrome baseline.

## Do Not Select When

- WMPF / AppService / miniapp debugger targets (WeChat provider).
- Explicit Camoufox or SpiderMonkey engine-level tracing (Camoufox provider).
- User only wants a reversible hook snippet with a known boundary (browser-hooks).

Use this provider for ordinary Web reconnaissance and the first fingerprint-browser escalation. It owns the lifecycle of `chrome-devtools-mcp` and `js-reverse-mcp` while its work order is active.

Architecture boundary: web-protocol-recovery owns route choice, `projectRoot`, layout, acceptance, and final delivery. This provider only captures bounded evidence, writes assigned cache artifacts under `web-protocol-recovery-simple/v1`, and returns the next narrow blocker or Provider recommendation.

## Tier Order

Before the first navigation, require `browserReconAllowed=true`, `browserNavigationSideEffectsApproved=true`, `automaticObservationStopThreshold >= 1`, the cumulative prior `observedAutomatic` state, an exact canonical top-level scheme/host/port/route, and one consumed navigation unit. Threshold `0` denies navigation. Chrome DevTools cannot pre-intercept automatic browser traffic: add every canonical destination and kind to cumulative `observedAutomatic`, never claim it was blocked, and stop further page actions if the top-level leaves scope or the cumulative threshold is reached. Return the state for the next work order; any later Provider-initiated request/replay must pass the normal pre-egress scope and budget guard.

1. Chrome DevTools captures redirects, page state, user-flow triggers, screenshots when needed, and one clean network baseline.
2. Park Chrome after saving evidence: retain a sacrificial `about:blank`, close sensitive target pages, and report `chrome=parked`, never `closed`.
3. Start `js-reverse-mcp` in normal Chrome mode with `launch_browser({headless:true, cloakBinaryPath:""})` for initiators, source search, breakpoints, paused scopes, wrappers, WebSocket, and runtime inspection. Normal js-reverse reconnaissance is headless by default.
4. Switch to visible CloakBrowser only after explicit user wording or recorded fingerprint, automation, environment, headless/headful, or observer-effect evidence. Call `browser_binary_info` first and use its configured path; then launch with `launch_browser({headless:false, cloakBinaryPath:<configured path>})` unless the user explicitly asks for hidden Cloak. Never invent the path.

Explicit `CloakBrowser`, `指纹浏览器`, `fingerprint browser`, or `stealth browser` wording may enter the Cloak tier directly after scope confirmation. This is an engine selection, not permission for account state, verifier submission, mutation, or broad collection.

## Lifecycle

Never call Chrome DevTools and js-reverse browser tools in the same parallel batch or attach them to the same profile unless the user explicitly accepts contamination. Save durable evidence before every engine/mode switch and mark old IDs stale. `launch_browser({headless:false, cloakBinaryPath})` relaunches js-reverse into visible Cloak mode; close js-reverse before returning to Chrome or escalating to Camoufox.

## Exit

Return the real request, initiator/source evidence, moving fields, environment/fingerprint evidence, saved artifact paths, lifecycle state, and the smallest next provider. Do not implement the final collector here.
