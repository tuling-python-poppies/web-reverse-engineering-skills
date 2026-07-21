# Architecture

This file is the stable architecture contract for web-protocol-recovery. `SKILL.md` remains the runtime dispatcher; this document defines ownership boundaries so methodology does not drift into Provider-local files.

## Decision Hub Contract

web-protocol-recovery is the only public protocol-recovery skill and the only decision owner. It owns:

1. intake, authorization, exact scope, request budget, and artifact policy;
2. success shape, gate family, route, and Provider sequencing;
3. `projectRoot`, `web-protocol-recovery-simple/v1`, allowed paths, and promotion rules;
4. acceptance tests, Provider result acceptance/rejection, cleanup state, and final delivery.

Internal Providers are internal skills owned by this skill, not peer top-level skills. Same meaning: decision hub routes and accepts; each Provider is the executable skill for one capability. A Provider receives one bounded work order, performs only its assigned capability, returns evidence/code/blockers, and gives control back to web-protocol-recovery.

## Dispatch Loop

Use this loop for every protocol task:

1. **Shape**: choose `evidence`, `local-proof`, `compact-replay`, or `collector`.
2. **Gate**: record only the authorization/scope/budget/execution fields needed before the next gated action.
3. **Route**: select `evidence-reuse`, one reconnaissance Provider, or one implementation Provider.
4. **Layout**: before the first write, activate `project-layout.md` and bind one absolute `projectRoot` with `layout=web-protocol-recovery-simple/v1`.
5. **Work order**: issue one `provider-work-order/v1` with exact allowed paths and one acceptance test.
6. **Accept or reject**: accept only against web-protocol-recovery's acceptance test; Provider `complete` is not enough.
7. **Next move**: continue the same shape when only the Provider changes; expand shape only after explicit user scope confirmation.

## Provider Skill Boundary

Every Provider must obey these boundaries:

1. Do not choose, create, rename, or switch `projectRoot`.
2. Do not create a second project, wrapper tree, package framework, or alternate layout.
3. Do not write outside assigned `allowedPaths`.
4. Do not open a sibling Provider reference or case unless web-protocol-recovery issues a new work order.
5. Do not own final live egress unless the selected Provider is `python-collector` under an accepted delivery work order.
6. Do not claim completion while task-owned browser/session/worker/runtime resources remain live.

Provider-local references are operational manuals for that capability. They may explain how to use hooks, AST visitors, env modules, iv8 APIs, or verifier tactics, but they do not define the global methodology, escalation policy, project layout, or final delivery contract.

## Unified Project Layout

All writes use `web-protocol-recovery-simple/v1`:

```text
<project-root>/
  main.py
  main.js
  mod.js
  utils/
  tests/
  output/
  js_reverse_cache/
    recon/
    source/
    ast/
    env/
    iv8/
    samples/
    private/
```

Only create paths required by the current task. A valid final delivery may contain only `main.py`.

Stable code is promoted only after fixed-vector or approved live semantic acceptance passes:

1. reconnaissance artifacts stay under `js_reverse_cache/recon/**` and `js_reverse_cache/source/**`;
2. AST intermediates stay under `js_reverse_cache/ast/**`;
3. env-patch probes stay under `js_reverse_cache/env/**`, with verified helpers promoted to root `mod.js` and `main.js` only when assigned;
4. iv8 probes, assets, net logs, and runtime snapshots stay under `js_reverse_cache/iv8/**` or `js_reverse_cache/source/**`;
5. fixed redacted vectors belong under `js_reverse_cache/samples/**` or stable `tests/**`;
6. final Python HTTP, pagination, decode, storage, and output are owned by root `main.py` and narrow `utils/**` helpers.

Forbidden layout roots and mandatory directories: `collector/`, `analysis/`, `input/`, `logs/`, provider-specific project folders, and any second landing directory.

## Acceptance Chain

The chain is always sequential:

```text
evidence/recon -> one implementation Provider -> fixed-vector/local proof -> python-collector or compact replay -> approved live-egress replay -> optional scale
```

Browser, JS, WASM, env-patch, and iv8 may produce only narrow artifacts such as a sign/header dict, cookie value, encoded frame, decoded payload, or callable helper. Python owns all final live egress.

## Maintenance Rule

When a new tactic or case teaches a reusable method, write it to the narrowest central playbook or methodology file first. Add Provider-local material only when it is executable or capability-specific. Do not create another top-level reverse skill or parallel project convention.
