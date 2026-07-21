# WeChat Miniapp Recon Provider

## Select When

- WMPF, WeChatAppEx, AppService, miniapp WebView, WMPFDebugger, or `127.0.0.1:62000` signals.
- User is debugging a local miniapp runtime they own.

## Do Not Select When

- Ordinary Web pages (Chromium).
- Camoufox/Cloak browser work.
- IDs from this lease must never be reused on Chromium, Camoufox, or iv8.

Use this provider for WMPF, WeChatAppEx, AppService, miniapp WebView, WMPFDebugger, or `127.0.0.1:62000` targets. web-protocol-recovery owns the reverse task; this provider owns WMPF process/lease custody, target selection, and miniapp runtime IDs for the duration of its work order.

Architecture boundary: web-protocol-recovery owns route choice, `projectRoot`, layout, acceptance, and final delivery. This provider only captures bounded evidence, writes assigned cache artifacts under `web-protocol-recovery-simple/v1`, and returns the next narrow blocker or Provider recommendation.

Before locating, starting, attaching to, or stopping WMPFDebugger, require `runtimeCustody.providerOwnsLease=true`. A false or omitted value blocks lifecycle work; never infer lease custody from the selected Provider.

## Startup

Lifecycle scripts are owned by the active `miniapp-reverse-mcp` installation, not bundled in this skill. Locate the MCP root from the running Python process whose command line names `run_mcp_server.py`, canonicalize and deduplicate roots, then require exactly one root with all of these fingerprints:

- `pyproject.toml` declares `name = "miniapp-reverse-mcp"`
- `run_mcp_server.py` imports `miniapp_cdp.server`
- `src/miniapp_cdp/server.py` exists
- `config/resolve-wmpf-root.ps1`, `config/start-wmpf-debugger.cmd`, `config/stop-wmpf-debugger.cmd`, and `config/wmpf-debugger-service.ps1` are local regular files with no reparse point in their path chain

Do not hardcode one installation path or select among multiple roots. If process inspection is unavailable or ambiguous, return a blocker and ask for the exact MCP root.

Resolve the WMPFDebugger root by strong project fingerprints, never by a guessed fixed path. Normal service startup may write `config/wmpf-debugger-state.json` for PID and lease custody, but it does not create or overwrite `config/wmpf-root.json`. A rootless start attaches to an already managed process using its recorded root; a persisted default affects cold starts only. Persisting a root is a separate confirmed operational write: call `<mcp-root>/config/resolve-wmpf-root.ps1 -Candidate <wmpf-root> -Persist`. Configuration, state, and atomic temporary files stay inside `<mcp-root>/config`; `%LOCALAPPDATA%` and this skill directory are not runtime storage. Any present but unreadable, non-regular, reparse, or invalid config/state fails closed. Acquire a task lease through `<mcp-root>/config/start-wmpf-debugger.cmd`. Unknown listeners on debugger ports are conflicts, not reusable services.

## Recon

Require the user to open the miniapp when needed. Enumerate targets, identify AppService versus WebView, attach only the selected target, and use `miniapp-reverse-mcp_list_network_requests` as the primary network entry. Capture request details, response body, initiator, scripts, paused scopes, runtime values, and WebSocket frames only as required by the acceptance test.

Save durable redacted artifacts under `js_reverse_cache/recon/miniapp/` before navigation, target switch, detach, or lease release. Runtime IDs cannot be used by Chromium, Camoufox, iv8, or another miniapp session.

Return the real request, initiator/source evidence, moving fields, environment/runtime evidence, saved artifact paths, lease state, and the smallest next provider. Do not implement the final collector here.

## Cleanup

Release only this work order's lease. Do not stop a service still owned by another lease. Return cleanup state and mark all released target/request/script IDs stale.
