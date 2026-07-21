# WeChat Miniapp Ops Playbook

Provider-local operational detail for `wechat-miniapp`. Read only when the work order names this file. web-protocol-recovery still owns scope, budget, layout, and acceptance.

## Network

1. Do not start capture until the work order has a field, API keyword, path, or explicit business action.
2. First call: `list_network_requests(include_preserved_requests=true, url_filter=<keyword>, wait_ms=0~1000)`.
3. No keyword yet: ask one minimal action/keyword; optional preserved scan without filter; do not treat an empty live buffer as “no traffic”.
4. Live wait: user re-triggers, then `wait_ms=1000~5000` with the same `url_filter` when available.
5. Detail path: `list_network_requests(reqid=...)` → `get_response_body` → `get_request_post_data` when body truncated → `get_request_initiator`.
6. Failures: inspect ExtraInfo and `loadingFailed` before guessing CORS/block/cancel causes.
7. Empty after preserved + re-trigger: switch AppService/WebView once if ambiguous, then source search. Do not open a second recon engine.

## Scripts And Search

Search order: interface path fragment → parameter name → header name → encrypt/sign function name → business word.

- `list_scripts(url_filter=...)` then `search_in_sources` then `get_script_source` for context.
- `save_script_source` only when the work order allows write and the whole file is required; state path and reason first.

## Breakpoint Discipline

1. Read the function body with `get_script_source` before any code breakpoint.
2. Break on a concrete interior statement (`var x=`, `return`, assignment inside the body). Never break only on the function name or the one-time assignment of a function expression in minified code.
3. Prefer narrow `break_on_xhr(url=fragment)` when the URL is known.
4. DOM events (`click`/`input`/`submit`/`key*`) via `set_event_listener_breakpoint`; remove after the entry is proved.
5. On pause: `get_paused_info(include_scopes=true)`, evaluate in the correct `frame_index`, step only as needed, then `resume_execution`.
6. Before target switch or exit: `list_breakpoints` and `remove_breakpoints(clear_all=true)`.

## Runtime Profiler And Coverage

Use only when network/initiator/source leave a named blind spot.

- `get_runtime_events` for console/exception/context.
- CPU profile: start → one user action → stop with a small `limit`. Do not leave profiling on.
- Precise coverage: start → action → take/stop. Use hits to re-enter source/breakpoints; coverage is not a substitute for initiator stacks.

## WebSocket

1. List connections without content first.
2. Inspect handshake status/headers and frame errors before payloads.
3. Pull content with `wsid`, optional `direction`, and `show_content=true` only for frames required by the acceptance test.

## AppService Vs WebView

- Logic/API/sign work usually starts on AppService.
- Rendering, DOM events, or page-only scripts may need WebView.
- Clean paused/breakpoints/profiler/coverage on the current target before `switch_target`.
- Do not random-switch among many targets; list title/url/type and confirm when ambiguous.

## Cleanup Order

Apply on success, abort, user stop, or handoff back to web-protocol-recovery:

1. Each task-touched target: switch back when possible; if gone, note and continue.
2. `resume_execution` if paused.
3. Clear all code/XHR breakpoints; remove event-listener breakpoints this task set.
4. Stop CPU profiler and precise coverage if started.
5. Release this task lease via MCP `stop-wmpf-debugger.cmd` with the task token when the work order ends and this provider owns the lease.
6. Do not port-kill unknown PIDs; status/stop code `4` is a conflict report.
7. Mark request/script/frame/target IDs stale. No cross-engine ID reuse.

## Report Shape (Provider → hub)

- target type + id + title/URL
- request method/URL/reqid/status + redacted summary
- initiator/source location
- optional paused scopes
- cleanup + lease + ID lifecycle
- one next Provider suggestion only when a named blocker requires it
