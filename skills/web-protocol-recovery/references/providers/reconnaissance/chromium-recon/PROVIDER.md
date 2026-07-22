# Chromium Recon Provider

## Select When

- Ordinary Web reconnaissance (default route).
- Explicit CloakBrowser / 指纹浏览器 / fingerprint / anti-detection / stealth browser wording (Cloak tier via js-reverse, not Camoufox).
- First fingerprint or observer-effect escalation after a clean Chrome/DevTools baseline, or after a documented no-window skip into js-reverse recon.

## Do Not Select When

- WMPF / AppService / miniapp debugger targets (WeChat provider).
- Explicit Camoufox or SpiderMonkey engine-level tracing (Camoufox provider).
- User only wants a reversible hook snippet with a known boundary (browser-hooks).

Use this provider for ordinary Web reconnaissance and the first fingerprint-browser escalation. It owns the lifecycle of `chrome-devtools-mcp` and `js-reverse-mcp` while its work order is active.

Architecture boundary: web-protocol-recovery owns route choice, `projectRoot`, layout, acceptance, and final delivery. This provider only captures bounded evidence, writes assigned cache artifacts under `web-protocol-recovery-simple/v1`, and returns the next narrow blocker or Provider recommendation.

## Tier Order

Before the first navigation, require `browserReconAllowed=true`, `browserNavigationSideEffectsApproved=true`, `automaticObservationStopThreshold >= 1`, the cumulative prior `observedAutomatic` state, an exact canonical top-level scheme/host/port/route, and one consumed navigation unit. Boolean gates use JSON `true`/`false` only (never `yes`/`no`). Threshold `0` denies navigation. Chrome DevTools cannot pre-intercept automatic browser traffic: add every canonical destination and kind to cumulative `observedAutomatic`, never claim it was blocked, and stop further page actions if the top-level leaves scope or the cumulative threshold is reached. Return the state for the next work order; any later Provider-initiated request/replay must pass the normal pre-egress scope and budget guard.

1. Start ordinary Web reconnaissance with Chrome DevTools visible clean baseline: capture redirects, page state, user-flow triggers, screenshots when needed, and one clean network baseline. This is the default first step when recon gates are recorded. Skip it only when the user explicitly requires no ordinary window / background-only recon; document that skip before opening js-reverse.
2. Park Chrome after saving evidence: retain a sacrificial `about:blank`, close sensitive target pages, and report `chrome=parked`, never `closed`.
3. Start or continue `js-reverse-mcp` normal Chrome for initiators, source search, breakpoints, paused scopes, wrappers, WebSocket, and runtime inspection. Prefer explicit `launch_browser({headless:true, cloakBinaryPath:""})` for this mutation pass (auto-launch / CLI default does not count). Call `browser_binary_info` (or equivalent) first; if residual normal Chrome has `effective_headless!=true` when headless is required, relaunch and pass Headless Acceptance before navigate/capture/debug. Do not use `headless:false` in normal Chrome unless the user explicitly asks for a visible ordinary browser. While the work order is active, prefer keeping the accepted session; do not mid-task `close_browser` only to re-open via auto-launch.
4. Switch to visible CloakBrowser only after explicit user wording or recorded fingerprint, automation, environment, headless/headful, or observer-effect evidence. Call `browser_binary_info` first and use its configured path; then launch with `launch_browser({headless:false, cloakBinaryPath:<configured path>})` unless the user explicitly asks for hidden Cloak. Never invent the path.

Explicit `CloakBrowser`, `指纹浏览器`, `fingerprint browser`, or `stealth browser` wording may enter the Cloak tier directly after scope confirmation. This is an engine selection, not permission for account state, verifier submission, mutation, or broad collection.

## Headless Acceptance (js-reverse normal Chrome only)

When the active step is js-reverse normal Chrome and headless is required for that pass, prove headless before any js-reverse navigation/capture/debug:

1. Prefer tool fields when present: normal Chrome (Cloak inactive / empty cloak path), `headless:true` request honored, and `effective_headless=true` or an equivalent field such as `headless=true` with no headful/window flag.
2. If the launch result omits `effective_headless`, do not invent it. Treat missing proof as incomplete: re-check launch args, call `get_page_info` / binary info if available, and confirm no ordinary OS browser window remains for this js-reverse task.
3. **Flash vs persistent window**: a brief OS window during relaunch from residual headful Chrome (old process closing) is allowed and is not acceptance by itself. After relaunch settles, require `effective_headless=true` and no lasting normal-Chrome main window for this task.
4. Fail closed when any of these hold after acceptance: a normal Chrome window is still visible for this js-reverse task, Cloak is active on a normal-Chrome step, launch reports headful/windowed mode, or headless cannot be proved from returned fields plus process/window observation.
5. On failure, return a tooling blocker naming the missing field or headful evidence; do not navigate on that residual, do not silently continue headful, and do not consume another navigation budget unit until relaunch is accepted.

This section does not apply to the default Chrome DevTools visible baseline or to Cloak (visible by default).

## close_browser And Residual Headful (js-reverse)

`close_browser` clears runtime headless/cloak overrides. The next js-reverse browser tool may auto-launch with CLI defaults (often headful when MCP was started without `--headless`). Skill procedure for the js-reverse segment:

1. During an active js-reverse work segment: keep the accepted session; avoid `close_browser` until handoff/cleanup unless an engine switch requires it.
2. After any `close_browser`, treat the session as `JS_CLOSED`. Before the next js-reverse navigate/capture/debug action, call `launch_browser({headless:true, cloakBinaryPath:""})` again (when headless is required) and pass Headless Acceptance. Do not navigate on auto-launched headful residual.
3. After task-end close: do not call tools that would auto-launch a browser unless the next work order starts with an explicit launch (DevTools baseline, headless js-reverse, or approved Cloak/visible).
4. Headful residual after close or auto-launch is `RESIDUAL_HEADFUL`: relaunch as required for the next intended mode (flash allowed when switching into headless); never treat residual headful auto-launch as an accepted recon mode.

## Lifecycle

Never call Chrome DevTools and js-reverse browser tools in the same parallel batch or attach them to the same profile unless the user explicitly accepts contamination. Save durable evidence before every engine/mode switch and mark old IDs stale. Ordinary Web starts with DevTools baseline unless a documented no-window skip applies. Before a js-reverse normal-Chrome pass that requires headless, relaunch or verify `launch_browser({headless:true, cloakBinaryPath:""})` and pass Headless Acceptance; auto-launch and CLI default are not substitutes for that call. Any headful normal-Chrome result after that acceptance is a blocker unless the user explicitly requested a visible ordinary browser. `launch_browser({headless:false, cloakBinaryPath})` relaunches js-reverse into visible Cloak mode; close js-reverse before returning to Chrome or escalating to Camoufox.

## Exit

Return the real request, initiator/source evidence, moving fields, environment/fingerprint evidence, saved artifact paths, lifecycle state, and the smallest next provider. Do not implement the final collector here.
