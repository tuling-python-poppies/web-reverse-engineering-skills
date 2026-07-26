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

Architecture boundary: web-protocol-recovery owns route choice, `projectRoot`, layout, acceptance, and final delivery. This provider only captures bounded evidence, writes assigned cache artifacts under `web-protocol-recovery-simple`, and returns the next narrow blocker or Provider recommendation.

## Inputs

Require target URL/action, target field or request, exact scheme/host/port/route scope, artifact policy, previous Chromium/Cloak evidence or the explicit Camoufox reason it was skipped, and one evidence acceptance test. Project cache paths are required only when the approved work order writes artifacts; `writeMode=no-write` evidence keeps them `none` and saves nothing.

## Startup

1. Confirm js-reverse is closed and no other provider owns an active target browser.
2. Run the connected Camoufox MCP `check_environment` self-check before launching, then apply the normalized scope and budget guard before every Provider-initiated navigation/request/WebSocket send. Automatic redirects/subresources are blocked when interception exists and otherwise recorded only in cumulative `observedAutomatic`; they never consume a Provider-initiated budget category.
3. For a new provider-owned browser, record ownership and start metadata-only network capture.
4. For an existing user-owned browser, stay read-only: do not clear captures/state, install global persistent probes, reset, or close it.
5. Keep first navigation hook-free for signed challenge/JSVMP targets; establish redirect/status/request behavior before instrumentation.

## Evidence Ladder

Climb only while the named acceptance gap remains. Connected MCP tool schema is authoritative.

1. **Request metadata** — capture list + one target request; headers/query redacted per artifact policy.
2. **Initiator / source** — request initiator stack, then `search_code` / script get for the entry.
3. **Narrow hooks** — presets or single-function hooks for I/O boundaries (xhr/fetch/crypto/cookie) when the target is not signature-sensitive to observer effects.
4. **Source instrumentation** — `instrumentation(action='install')` on the VMP/script URL pattern; prefer AST; reload so probes run before page JS when scripts are sync-loaded.
5. **Transparent JSVMP probe** — `hook_jsvmp_interpreter(mode='transparent')` when property/call traffic must be seen without proxy wrapping.
6. **Engine trace** — custom-build `trace_property_access` only when SpiderMonkey/engine-level proof is the acceptance test.

Rules:

- Detectable `mode='proxy'` instrumentation is not a fallback for signed anti-bot targets (RS/Akamai-style). Prefer source instrumentation or transparent mode.
- Install hooks/routes **before** navigate for sync-loaded SDKs; if already navigated, use instrumentation reload rather than silent miss.
- Do not treat HTTP `200` or a non-empty signature as semantic success.
- Reusable cases only via root `references/cases/registry.json` → declared `python-node` PROCESS. Provider-local `references/jsdom-env-patches.md` only after a proved jsdom environment blocker.
- Historical case wording is evidence, not permission for navigation, target-code execution, account state, dependencies, or live replay.
- Provider templates under `templates/` are disabled-by-default evidence/local-artifact examples. They must be copied into an approved project and adapted under a work order before any bounded probe; they are never final Node collectors.

Operational step order and anti-patterns: `references/ops-ladder.md` when the work order names it.

Save approved artifacts only under the work order's `js_reverse_cache/recon/camoufox/` or `js_reverse_cache/source/` paths. Return request/source evidence, environment reads, fixed samples, observer-effect notes, and a precise next provider. Do not generate a second project or final collector.

## Failure Recovery

| Trigger | First fix | Still fails → stop |
|---|---|---|
| js-reverse still open | Close js-reverse; re-check exclusive ownership | Blocker: dual-engine contamination |
| check_environment fails | Report deps/browser residual; clear only if task-owned | Offline vectors only if possible |
| User-owned browser needs invasive hooks | Ask hub for new task-owned browser work order | Do not reset/close user browser |
| Sync SDK missed hooks | Install + instrumentation reload | Name script URL pattern blocker |
| Signed target breaks under proxy hooks | Drop proxy; use source instrumentation / transparent | Do not escalate to broader proxy |
| Generic 403/412 without Camoufox criterion | Return blocker for Chromium or evidence-reuse | Do not stay on Camoufox by default |

## Cleanup

Remove only task-owned hooks, routes, interceptors, captures, and browser state. Close only a task-owned browser. Mark volatile IDs stale after navigation, reload, cleanup, or close. `cleanup.complete=false` while any task-owned resource remains live.
