# WeChat Miniapp Recon Provider

## Select When

- WMPF, WeChatAppEx, AppService, miniapp WebView, WMPFDebugger, or `127.0.0.1:62000` signals.
- User is debugging a local miniapp runtime they own.

## Do Not Select When

- Ordinary Web pages (Chromium).
- Camoufox/Cloak browser work.
- IDs from this lease must never be reused on Chromium, Camoufox, or iv8.

Use this provider for WMPF, WeChatAppEx, AppService, miniapp WebView, WMPFDebugger, or `127.0.0.1:62000` targets. web-protocol-recovery owns the reverse task; this provider owns WMPF process/lease custody, target selection, and miniapp runtime IDs for the duration of its work order.

Architecture boundary: web-protocol-recovery owns route choice, `projectRoot`, layout, acceptance, and final delivery. This provider only captures bounded evidence, writes assigned cache artifacts under `web-protocol-recovery-simple/v1`, and returns the next narrow blocker or Provider recommendation. It does not implement the final collector.

## Target Gate

Before start, attach, network capture, source save, or breakpoints, classify the user goal:

| User input | Action |
|---|---|
| Only miniapp name / open instruction | Confirm WMPFDebugger service + DevTools URL; wait for business action |
| API keyword, field name, request sample, or explicit click action | After target context, run network/source/breakpoint chain |
| Full request + stack + params already proved; goal is browser-free replay | Cleanup, then return blocker recommending implementation Provider |
| Ordinary Web URL | Return blocker for Chromium route; do not attach WMPF |

No field, API, request sample, or business action → do not blind-capture network, save scripts, or set breakpoints. Allowed only: service status, target presence, DevTools URL, status report, wait.

## Lease And Startup

Before locating, starting, attaching to, or stopping WMPFDebugger, require `runtimeCustody.providerOwnsLease=true`. A false or omitted value blocks lifecycle work; never infer lease custody from the selected Provider.

Lifecycle scripts are owned by the active `miniapp-reverse-mcp` installation, not bundled in this skill. Locate the MCP root from the running Python process whose command line names `run_mcp_server.py`, canonicalize and deduplicate roots, then require exactly one root with all of these fingerprints:

- `pyproject.toml` declares `name = "miniapp-reverse-mcp"`
- `run_mcp_server.py` imports `miniapp_cdp.server`
- `src/miniapp_cdp/server.py` exists
- `config/resolve-wmpf-root.ps1`, `config/start-wmpf-debugger.cmd`, `config/stop-wmpf-debugger.cmd`, and `config/wmpf-debugger-service.ps1` are local regular files with no reparse point in their path chain

Do not hardcode one installation path or select among multiple roots. If process inspection is unavailable or ambiguous, return a blocker and ask for the exact MCP root.

Resolve the WMPFDebugger root by strong project fingerprints, never by a guessed fixed path. Normal service startup may write `config/wmpf-debugger-state.json` for PID and lease custody, but it does not create or overwrite `config/wmpf-root.json`. A rootless start attaches to an already managed process using its recorded root; a persisted default affects cold starts only. Persisting a root is a separate confirmed operational write: call `<mcp-root>/config/resolve-wmpf-root.ps1 -Candidate <wmpf-root> -Persist`. Configuration, state, and atomic temporary files stay inside `<mcp-root>/config`; `%LOCALAPPDATA%` and this skill directory are not runtime storage. Any present but unreadable, non-regular, reparse, or invalid config/state fails closed. Acquire a task lease through `<mcp-root>/config/start-wmpf-debugger.cmd`. Unknown listeners on debugger ports are conflicts, not reusable services.

Startup sequence:

1. Read-only status via `<mcp-root>/config/wmpf-debugger-service.ps1 -Action Status` when recent ready evidence is missing. Code meanings: `0` ready/starting under this launcher, `3` not running, `4` unmanaged listener on 9421/62000, `6` lifecycle lock busy. On `6`, wait 250–500 ms and retry once; still `6` → report lock busy and stop. On `4`, report conflict PIDs and stop; do not hijack unknown listeners.
2. When this work order needs a managed service, call `start-wmpf-debugger.cmd` once to acquire or reuse this task lease; record the lease token only in task context, never in final reports or cases.
3. After start, at most two short probes within 5 s total (ready log lines or port check). On ready log, stop further MCP target/network calls and tell the user to open or reopen the miniapp. Do not hang the turn waiting for targets.
4. Call `miniapp-reverse-mcp_list_targets` only after the user says the miniapp is open, is already running, or has triggered the target action.
5. On empty or timed-out targets, report wait state; do not hammer retries. Ask the user to reopen the miniapp.

Do not check or install WMPFDebugger yarn/`node_modules`/frida; those belong to the user's WMPFDebugger tree. Prefer `call` when invoking `.cmd` from shell tools. Do not run raw long-lived `start` or log-follow in the agent shell.

DevTools UI: after targets succeed, give the user `devtools://devtools/bundled/inspector.html?ws=127.0.0.1:62000` to open manually. Do not drive ordinary browser MCP to open it. Only if the user reports the link fails, give a system-browser fallback.

## Capability Matrix

| Goal | Primary tools | Stop when |
|---|---|---|
| Service + target | `list_targets` → `switch_target` | One AppService or WebView confirmed |
| DevTools UI | Emit DevTools URL only | User can open inspector |
| Target request | `list_network_requests` | Matching reqid + params/response summary |
| Response / POST body | `list_network_requests(reqid=...)` → `get_response_body` / `get_request_post_data` | Body or failure evidence recorded |
| Initiator | `get_request_initiator` → `get_script_source` | Stack + script URL/line/column |
| Search | `list_scripts` → `search_in_sources` → `get_script_source` | Function/param location |
| Save large script | `save_script_source` | Path + reason stated; only if work order allows write |
| XHR breakpoint | `break_on_xhr` → user action → `get_paused_info` | Narrow URL fragment hit |
| Code breakpoint | read body first → `set_breakpoint_on_text` on interior statement | Scope/stack captured |
| DOM event entry | `set_event_listener_breakpoint` → event → `get_paused_info` | Entry proved; then resume/clean |
| Runtime / profiler | `get_runtime_events` / `start_cpu_profile`…`stop` / `precise_coverage` | Hot path or exception; keep short |
| WebSocket | `get_websocket_messages` | Connection + frames needed by acceptance |
| Cleanup | resume → list/remove breakpoints → stop profiler/coverage → release lease | No live task breakpoints/paused; lease released or retained per work order |

Primary network entry is `miniapp-reverse-mcp_list_network_requests`. Prefer `include_preserved_requests=true` and `url_filter` when the user gave a domain/path/keyword. For live waits use `wait_ms=1000~5000` only after the user can re-trigger the action.

## Standard Workflow

1. **Target context** — `list_targets` → optional `switch_target`. Clean paused/breakpoints/profiler on the old target before switch. State AppService vs WebView.
2. **Network** — preserved + filter first; then user re-trigger + wait; then `reqid` detail, response body, POST data, ExtraInfo/`loadingFailed`, initiator.
3. **Scripts** — search order: path fragment → param name → header → function name → business word.
4. **Breakpoints** — read function body first; break on interior statements only, never function-name or assignment-only sites. After pause: scopes, evaluate in frame, step, resume promptly.
5. **Runtime / profiler** — only when network/source are insufficient; stop profiler/coverage after one focused action.
6. **WebSocket** — list connections, then handshake/errors, then bounded content.
7. **Cleanup** — always on complete report, implementation handoff, error abort, or user stop. See Cleanup.

Operational detail for filters, breakpoint discipline, and release order: `references/ops-playbook.md` (at most one Provider-local reference per handoff).

## Failure Recovery

| Trigger | First fix | Still fails → stop |
|---|---|---|
| miniapp MCP unavailable | Report MCP not ready; do not substitute Chromium/Camoufox | Blocker: install/restart miniapp MCP |
| Port 62000 connect fail | Managed start via MCP `start-wmpf-debugger.cmd` only | Blocker with log path; no dependency install |
| Status code 4 | Report unmanaged listener PIDs | Do not kill by port |
| Status code 6 after one retry | Report lifecycle lock busy | Stop concurrent lifecycle |
| Ready but no targets | Ask user to open/reopen miniapp | Wait; no blind capture |
| Multiple targets | List title/url/type; ask AppService vs WebView | Do not random-switch |
| Empty live network | preserved + filter + other target + re-trigger | Then source search; name blocker |
| Save/breakpoint side effects | Require work-order write/debug allow or explicit user ask | Stay offline for that action |

## Exit

Return to web-protocol-recovery:

- current target type, target id, title/URL
- key request(s): method, URL, reqid, status, redacted param/response summary
- initiator/source evidence: stack, script URL, line/column, function/statement
- dynamic evidence when used: paused scopes, eval results
- moving fields and environment/runtime notes
- saved artifact paths under assigned `js_reverse_cache/recon/miniapp/` (if any)
- lease state, cleanup state, and every runtime ID with lifecycle
- smallest next Provider recommendation (never final collector implementation here)

## Cleanup

Release only this work order's lease and this task's debug state.

1. For each target this task used: switch back when possible; if a target is gone, record it and continue others.
2. If paused → `resume_execution`.
3. `list_breakpoints` → `remove_breakpoints(clear_all=true)`; remove any event-listener breakpoints set.
4. Stop open CPU profiler or precise coverage.
5. If this task holds a lease token and the work order ends (success, abort, or handoff), call `<mcp-root>/config/stop-wmpf-debugger.cmd "<lease-token>"`. Other leases keep the service; last lease stops only the launcher process tree. No port-based kill trees. Code 4 on stop → report conflict, do not force-kill.
6. User-started external WMPFDebugger: clean MCP debug state only; do not stop their process unless they explicitly require it.
7. Mark all released request/script/frame/target IDs stale. Never pass miniapp IDs to Chromium, Camoufox, or iv8; only redacted saved artifacts may leave this lease.

If stop fails, report `cleanup.complete=false` with reason; do not claim complete while task-owned resources remain live.
