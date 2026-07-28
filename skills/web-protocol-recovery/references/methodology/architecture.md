# Architecture

This file is the stable architecture contract for web-protocol-recovery. `SKILL.md` remains the runtime dispatcher; this document defines ownership boundaries so methodology does not drift into Provider-local files.

## Decision Hub Contract

web-protocol-recovery is the only public protocol-recovery skill and the only decision owner. It owns:

1. intake, authorization, exact scope, request budget, and artifact policy;
2. success shape, gate family, route, and Provider sequencing;
3. `projectRoot`, `web-protocol-recovery-simple`, allowed paths, and promotion rules;
4. acceptance tests, Provider result acceptance/rejection, cleanup state, and final delivery.

Internal Providers are internal skills owned by this skill, not peer top-level skills. Same meaning: decision hub routes and accepts; each Provider is the executable skill for one capability. Providers are typed by role: `reconnaissance`, `protocol-recovery`, `implementation`, or `delivery`. A Provider receives one bounded work order, performs only its assigned capability, returns evidence/code/blockers, and gives control back to web-protocol-recovery.

## Dispatch Loop

Use this loop for every protocol task:

1. **Shape**: choose `evidence`, `local-proof`, `compact-replay`, or `collector`.
2. **Gate**: choose one primary gate family (`signer`, `challenge`, `verifier`, `decode`, `session`, or `transport`) and record only the authorization/scope/budget/execution fields needed before the next gated action.
3. **Route**: select `evidence-reuse` or one active Provider ID. `route` is never a gate family, strategy, profile, or file path.
4. **Layout**: before the first write, activate `project-layout.md` and bind one absolute `projectRoot` with `layout=web-protocol-recovery-simple`.
5. **Work order**: issue one `provider-work-order/v2` with exact allowed paths, active Provider role, optional protocol owner, optional implementation mode, and one acceptance test.
6. **Accept or reject**: accept only against web-protocol-recovery's acceptance test; Provider `complete` is not enough.
7. **Next move**: continue the same shape when only the Provider changes; expand shape only after explicit user scope confirmation.

## Provider Skill Boundary

Every Provider must obey these boundaries:

1. Do not choose, create, rename, or switch `projectRoot`.
2. Do not create a second project, wrapper tree, package framework, or alternate layout.
3. Do not write outside assigned `allowedPaths`.
4. Do not open a sibling Provider reference or case unless web-protocol-recovery issues a new work order.
5. Do not own final live egress unless the selected Provider is `python-collector` with role `delivery` under an accepted delivery work order.
6. Do not claim completion while task-owned browser/session/worker/runtime resources remain live.
7. Case library entries are offline-only. Bundled case `entry.py` and helpers must not perform live HTTP; final live egress belongs only to task-project `main.py` via `python-collector` under a validated work-order.

Provider-local references are operational manuals for that capability. They may explain how to use hooks, AST visitors, python-node strategies, iv8 APIs, pure-Python profiles, or verifier tactics, but they do not define the global methodology, escalation policy, project layout, or final delivery contract.

## Provider Roles And Implementation Modes

The canonical Provider inventory is `references/providers/registry.json`.

| Role | Providers | Responsibility |
|---|---|---|
| `reconnaissance` | `chromium-recon`, `camoufox`, `wechat-miniapp` | Locate requests, initiators, moving state, scripts, runtime blockers, and precise next capability. |
| `protocol-recovery` | `browser-hooks`, `ast`, `verifier`, `akamai`, `river-security` | Recover rules or own protocol-family state and acceptance criteria. |
| `implementation` | `iv8`, `python-node`, `pure-python` | Produce one local protocol artifact. |
| `delivery` | `python-collector` | Perform final Python-owned HTTP/WebSocket live egress and bounded collection. |

There are exactly three implementation modes: `iv8`, `python-node`, and `pure-python`. `env-patch` is a `python-node` strategy. `douyin-abogus-native` is a `pure-python` profile. `python-collector` is delivery, not an implementation mode.

Protocol owners stay active while implementation Providers run. Example: `akamai -> iv8 -> python-collector` means Akamai remains the protocol owner and acceptance owner while iv8 generates the collector artifact, then python-collector performs final egress.

## Unified Project Layout

The canonical tree is `references/methodology/project-layout.md`. This architecture file owns the layout invariant only:

1. all writes use `web-protocol-recovery-simple` under one absolute `projectRoot`;
2. only paths required by the current task are created, and a valid final delivery may contain only `main.py`;
3. reconnaissance, protocol-recovery, implementation, and sample artifacts stay in their assigned `js_reverse_cache/**` or `tests/**` paths until accepted; River Security artifacts reuse source/env/iv8/samples paths and do not own a separate cache namespace;
4. final Python HTTP, pagination, decode, storage, and output are owned by root `main.py` and assigned `utils/**` helpers.

Forbidden generated roots/directories are defined in `project-layout.md`; Providers must not restate or fork the tree.

## Acceptance Chain

The chain is always sequential:

```text
evidence/recon -> protocol recovery owner/technique -> one implementation Provider -> fixed-vector/local proof -> python-collector delivery -> approved live-egress replay -> optional scale
```

Browser, JS, WASM, python-node strategies, pure-Python profiles, and iv8 may produce only narrow artifacts such as a sign/header dict, cookie value, encoded frame, decoded payload, or callable helper. Python owns all final live egress through delivery.

## Maintenance Rule

When a new tactic or case teaches a reusable method, write it to the narrowest central playbook or methodology file first. Add Provider-local material only when it is executable or capability-specific. Do not create another top-level reverse skill or parallel project convention.
