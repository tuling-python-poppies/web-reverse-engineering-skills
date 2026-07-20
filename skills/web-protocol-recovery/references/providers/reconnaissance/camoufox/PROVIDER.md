# Camoufox Recon Provider

## Select When

- User explicitly requests Camoufox.
- Engine-level property tracing, Firefox/SpiderMonkey differential proof, or Camoufox-specific source instrumentation is required.
- Chromium/Cloak evidence is recorded and untrustworthy, so a second engine is justified.

## Do Not Select When

- Generic `403` / `412` / CAPTCHA / obfuscation with no Camoufox-specific need.
- Ordinary Web first recon without an explicit Camoufox/SpiderMonkey selection or recorded second-engine criterion (use Chromium).
- Cloak/指纹浏览器 wording (Cloak via js-reverse, not Camoufox).
- WeChat miniapp debugger targets.

Camoufox is web-protocol-recovery's deep browser route, not the default ordinary-Web route. Select it directly when the user explicitly requests Camoufox. Otherwise use it only for custom-build engine-level property tracing, Firefox/SpiderMonkey differential evidence, Camoufox-specific source instrumentation, or an untrustworthy Chromium/Cloak result. Close js-reverse before opening Camoufox.

## Inputs

Require target URL/action, target field or request, exact scheme/host/port/route scope, artifact policy, previous Chromium/Cloak evidence or the explicit Camoufox reason it was skipped, and one evidence acceptance test. Project cache paths are required only when the approved work order writes artifacts; `writeMode=no-write` evidence keeps them `none` and saves nothing.

## Startup

1. Confirm js-reverse is closed and no other provider owns an active target browser.
2. Run Camoufox environment self-check before launching, then apply the normalized scope and budget guard before every Provider-initiated navigation/request/WebSocket send. Automatic redirects/subresources are blocked when interception exists and otherwise recorded only in cumulative `observedAutomatic`; they never consume a Provider-initiated budget category.
3. For a new provider-owned browser, record ownership and start metadata-only network capture.
4. For an existing user-owned browser, stay read-only: do not clear captures/state, install global persistent probes, reset, or close it.
5. Keep first navigation hook-free for signed challenge/JSVMP targets; establish redirect/status/request behavior before instrumentation.

## Evidence Ladder

Use request metadata and initiators first, then source search, narrow page hooks, source instrumentation, transparent JSVMP probes, and custom-build `trace_property_access` only when the hypothesis requires it. Detectable proxy instrumentation is not a fallback for signed anti-bot targets. The connected MCP tool schema is authoritative; do not infer arguments from old recipes. If web-protocol-recovery selected a reusable case, consume it only through the root registry.

The root registry exposes four historical `python-node` patterns: dual-sign `cacheOpts` interception, universal VMP source instrumentation, JSVMP XHR-interceptor `a_bogus` env emulation, and Ruishu 6 `412` cookie sdenv rebuild. Select one only through `references/cases/registry.json`, then open its declared `references/cases/python-node/<case-id>/PROCESS.md` in a bounded work order. Use Provider-local `references/jsdom-env-patches.md` only for a proven jsdom environment blocker. Historical wording is evidence, not permission for navigation, target-code execution, account state, dependencies, or live replay.

Save approved artifacts only under the work order's `js_reverse_cache/recon/camoufox/` or `js_reverse_cache/source/` paths. Return request/source evidence, environment reads, fixed samples, observer-effect notes, and a precise next provider. Do not generate a second project or final collector.

## Cleanup

Remove only task-owned hooks, routes, interceptors, captures, and browser state. Close only a task-owned browser. Mark volatile IDs stale after navigation, reload, cleanup, or close.
