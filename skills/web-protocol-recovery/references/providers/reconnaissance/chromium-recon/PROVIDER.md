# Chromium Recon Provider

## Select When

- Ordinary Web reconnaissance (default route).
- Explicit CloakBrowser / 指纹浏览器 / fingerprint / anti-detection / stealth browser wording (Cloak tier via js-reverse, not Camoufox).
- First fingerprint or observer-effect escalation after ordinary js-reverse headless recon (or after an approved DevTools baseline when that was the only available evidence path).

## Do Not Select When

- WMPF / AppService / miniapp debugger targets (WeChat provider).
- Explicit Camoufox or SpiderMonkey engine-level tracing (Camoufox provider).
- User only wants a reversible hook snippet with a known boundary (browser-hooks).

Use this provider for ordinary Web reconnaissance and the first fingerprint-browser escalation. It owns the lifecycle of `chrome-devtools-mcp` and `js-reverse-mcp` while its work order is active.

Architecture boundary: web-protocol-recovery owns route choice, `projectRoot`, layout, acceptance, and final delivery. This provider only captures bounded evidence, writes assigned cache artifacts under `web-protocol-recovery-simple/v1`, and returns the next narrow blocker or Provider recommendation.

## Tier Order

Before the first navigation, require `browserReconAllowed=true`, `browserNavigationSideEffectsApproved=true`, `automaticObservationStopThreshold >= 1`, the cumulative prior `observedAutomatic` state, an exact canonical top-level scheme/host/port/route, and one consumed navigation unit. Boolean gates use JSON `true`/`false` only (never `yes`/`no`). Threshold `0` denies navigation. Chrome DevTools cannot pre-intercept automatic browser traffic: add every canonical destination and kind to cumulative `observedAutomatic`, never claim it was blocked, and stop further page actions if the top-level leaves scope or the cumulative threshold is reached. Return the state for the next work order; any later Provider-initiated request/replay must pass the normal pre-egress scope and budget guard.

1. Start ordinary reconnaissance with `js-reverse-mcp` normal Chrome via **explicit** headless launch (auto-launch / CLI default does not count as the default): call `browser_binary_info` (or equivalent). If residual normal Chrome has `effective_headless!=true`, or no accepted headless session exists, call `launch_browser({headless:true, cloakBinaryPath:""})` before any navigate/capture/debug step. Accept only when Headless Acceptance passes. If a normal browser window remains after acceptance, or headless cannot be proved, stop with a tooling blocker instead of navigating.
2. Use Chrome DevTools clean baseline only after the user explicitly approves a visible window/baseline, or after a named blocker requires DevTools-only page state, screenshots, or user-flow evidence. It captures redirects, page state, user-flow triggers, screenshots when needed, and one clean network baseline. DevTools is not the default first step.
3. Park Chrome after saving evidence: retain a sacrificial `about:blank`, close sensitive target pages, and report `chrome=parked`, never `closed`.
4. Continue `js-reverse-mcp` normal Chrome headless for initiators, source search, breakpoints, paused scopes, wrappers, WebSocket, and runtime inspection. Do not use `headless:false` in normal Chrome unless the user explicitly asks for a visible ordinary browser. While the work order is active, prefer keeping the accepted headless session; do not mid-task `close_browser` only to re-open via auto-launch.
5. Switch to visible CloakBrowser only after explicit user wording or recorded fingerprint, automation, environment, headless/headful, or observer-effect evidence. Call `browser_binary_info` first and use its configured path; then launch with `launch_browser({headless:false, cloakBinaryPath:<configured path>})` unless the user explicitly asks for hidden Cloak. Never invent the path.

Explicit `CloakBrowser`, `指纹浏览器`, `fingerprint browser`, or `stealth browser` wording may enter the Cloak tier directly after scope confirmation. This is an engine selection, not permission for account state, verifier submission, mutation, or broad collection.

## Headless Acceptance

Ordinary js-reverse normal-Chrome launch must prove headless before any navigation:

1. Prefer tool fields when present: normal Chrome (Cloak inactive / empty cloak path), `headless:true` request honored, and `effective_headless=true` or an equivalent field such as `headless=true` with no headful/window flag.
2. If the launch result omits `effective_headless`, do not invent it. Treat missing proof as incomplete: re-check launch args, call `get_page_info` / binary info if available, and confirm no ordinary OS browser window was opened for this task.
3. **Flash vs persistent window**: a brief OS window during relaunch from residual headful Chrome (old process closing) is allowed and is not acceptance by itself. After relaunch settles, require `effective_headless=true` and no lasting normal-Chrome main window for this task.
4. Fail closed when any of these hold after acceptance: a normal Chrome window is still visible for this task, Cloak is active on a normal-Chrome step, launch reports headful/windowed mode, or headless cannot be proved from returned fields plus process/window observation.
5. On failure, return a tooling blocker naming the missing field or headful evidence; do not navigate, do not silently continue headful, and do not consume another navigation budget unit until relaunch is accepted.

## close_browser And Residual Headful

`close_browser` clears runtime headless/cloak overrides. The next js-reverse browser tool may auto-launch with CLI defaults (often headful when MCP was started without `--headless`). Skill procedure:

1. During an active recon work order: keep the accepted headless session; avoid `close_browser` until handoff/cleanup unless an engine switch requires it.
2. After any `close_browser`, treat the session as `JS_CLOSED`. Before the next navigate/capture/debug browser action, call `launch_browser({headless:true, cloakBinaryPath:""})` again and pass Headless Acceptance. Do not navigate on auto-launched headful residual.
3. After task-end close: do not call tools that would auto-launch a browser unless the next work order starts with an explicit headless (or approved Cloak/visible) launch first.
4. Headful residual after close or auto-launch is `RESIDUAL_HEADFUL`: relaunch headless (flash allowed), then accept; never treat residual headful as the ordinary recon default.

## Lifecycle

Never call Chrome DevTools and js-reverse browser tools in the same parallel batch or attach them to the same profile unless the user explicitly accepts contamination. Save durable evidence before every engine/mode switch and mark old IDs stale. Before an ordinary js-reverse pass, relaunch or verify `launch_browser({headless:true, cloakBinaryPath:""})` and pass Headless Acceptance; auto-launch and CLI default are not substitutes for that call. Any headful normal-Chrome result after acceptance is a blocker unless the user explicitly requested a visible ordinary browser. `launch_browser({headless:false, cloakBinaryPath})` relaunches js-reverse into visible Cloak mode; close js-reverse before returning to Chrome or escalating to Camoufox.

## Exit

Return the real request, initiator/source evidence, moving fields, environment/fingerprint evidence, saved artifact paths, lifecycle state, and the smallest next provider. Do not implement the final collector here.
