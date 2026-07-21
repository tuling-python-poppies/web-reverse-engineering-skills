# Camoufox Ops Ladder

Provider-local Camoufox MCP execution order. Read only when the work order names this file. Generic JSVMP methodology stays in root playbooks; this file maps the connected Camoufox MCP ladder only.

## Preconditions

- web-protocol-recovery selected `route: camoufox` with a Camoufox selection criterion or explicit user request.
- js-reverse closed; no parallel Chromium recon ownership.
- Scope, budget, and artifact policy recorded on the work order.

## Ownership

| Browser state | Allowed |
|---|---|
| New task-owned browser | Launch, capture, hooks, instrumentation, close |
| Existing user-owned browser | Read-only: page info, list requests, search; no clear/reset/global persistent probes/close |

## Default Climb (entry evidence)

```text
check_environment
→ network_capture start (metadata)
→ navigate (hook-free first for signed/JSVMP)
→ list_network_requests + get_request_initiator
→ search_code / scripts get
→ optional inject_hook_preset or hook_function (non-signed or proved-safe)
→ instrumentation install (url_pattern) + reload when sync scripts
→ hook_jsvmp_interpreter(mode=transparent) if needed
→ trace_property_access only if custom-build + hypothesis needs engine proof
→ save redacted artifacts → cleanup
```

## Signed / Observer-Sensitive Targets

1. First navigation without hooks.
2. Prefer `instrumentation` source rewrite over detectable Proxy wrappers.
3. If using `hook_jsvmp_interpreter`, use `mode=transparent` unless the work order explicitly accepts detectable proxy risk.
4. Do not use Playwright/browser-driving as the final cookie/sign delivery; return evidence for python-collector / env-patch / iv8.

## Sync-Loaded SDK Timing

1. Register instrumentation routes and persistent hooks **before** navigate when the script loads via page HTML.
2. If the page already loaded the SDK, `instrumentation(action='reload')` (or equivalent) so probes run first.
3. After reload, treat old request/script IDs as stale.

## Case And jsdom

- Case selection: only root `registry.json` → one `python-node` case PROCESS.
- `jsdom-env-patches.md`: only after hot-key / env-read evidence proves a jsdom gap.
- Fixed vectors offline before any approved live replay (live replay is hub/python-collector, not this ladder).

## Cleanup Checklist

1. Stop instrumentation routes; remove task hooks.
2. Stop/clear task network capture if task-owned.
3. Close only task-owned browser; leave user-owned sessions alone.
4. Return ID lifecycle records; no live task resources on `status=complete`.

## Anti-Patterns

- Opening Camoufox for generic 403/CAPTCHA without Camoufox criterion.
- Parallel js-reverse + Camoufox browsers.
- Proxy-mode JSVMP hooks as the default on RS/Akamai-style signed pages.
- Delivering browser-backed fetch as the final collector.
- Reusing Camoufox request/script IDs after navigation/close or on another engine.
