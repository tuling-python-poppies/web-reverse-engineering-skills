# Read Budget

Hard phase-local limits for loading web-protocol-recovery references. These override habit-based reading and cannot be extended repeatedly by renaming the same blocker.

A **dispatch window** begins at a new user request or an accepted Provider result and ends at the next evidence action, user question, or bounded Provider handoff. Each window has a fresh purpose but no hidden carry-over reads.

## Caps

| Window | Max paths | Allowed |
|---|---:|---|
| Initial dispatch | 3 total | First response reads 0-2 paths; one named blocker may add exactly one path once before the next evidence action |
| Provider handoff | 3 total | `provider-work-order.md`, the selected `PROVIDER.md`, and at most one Provider-local reference |
| Case selection | 1 | `references/cases/registry.json`; select at most one case |
| Selected case bundle | 8 total | `case.json` -> `PROCESS.md` -> optional implementation entry / live-state selector -> at most two fixture/test files -> up to four manifest-declared implementation/asset slots; after naming one concrete blocker, one `historicalReferences` file may replace one such slot |
| iv8 runtime case | 8 total | accepted API-inventory gate -> manifest/process -> entry -> only declared puller/assets; every historical case requires fresh current-target verification |
| python-node runtime case | 8 total | manifest/process -> optional verified Node entry -> declared puller/assets; an evidence-only case cannot be presented as executable implementation |
| Write gate | 1 | `references/methodology/project-layout.md` immediately before first save |
| Whole task | 24 distinct paths | Includes all methodology, Provider, case, fixture, implementation, asset, and playbook content reads; mechanically copying or executing an assigned opaque asset does not count until its content is opened or inspected. At cap, stop reading and return a precise blocker. The same task cannot extend or reset this cap. |

`SKILL.md` itself is always in context and does not count against the budget.

Sequential Providers start a new handoff window only after web-protocol-recovery accepts the previous result against its acceptance test. A failed case does not authorize a sibling case; return to normal evidence routing.

A historical reference is never a preload or executable asset. Open at most one file declared by the selected case, verify it through `references/case-live-reference-archive/MANIFEST.json`, count both the manifest and source against the same eight-path case window, and use it only to study an implementation fact. Do not import or execute it, install its historical dependencies, copy it into delivery, or use its former live result as current acceptance.

Provider work orders carry a `readPlan` object with `window`, `required`, and `optional` paths. Required paths must fit the active window cap before the handoff is issued. Optional paths are blockers, not preloads: the Provider may open at most one optional path only after naming the missing fact and only if the whole-task cap still has room.

`scripts/validate_architecture.py` keeps this contract executable by simulating the official routing chains as explicit path lists, including evidence reuse, Chromium/hooks, Chromium→AST→env-patch→collector, AST/env-patch, verifier implementation variants, Akamai, River Security→iv8 and River Security→env-patch, selected cases, and iv8 API inventory gates. Each simulated chain must reference existing files, keep every window within its cap, and stay within the 24-path whole-task cap after de-duplication.

## First Load Rules

1. Name the current blocker or success shape before opening any playbook.
2. Prefer the selected `PROVIDER.md` over generic essays.
3. Load generic references only through `references/reference-router.md` symptom matches.
4. Never preload "the whole references tree", all cases, or multiple sibling playbooks "just in case".
5. Do not open Camoufox docs on ordinary Web starts.
6. Do not open collector/project-layout docs for pure evidence-only work with no write planned.
7. Same symptom family: load only one canonical path per window (challenge -> `challenge-state-envelope-playbook.md`; River Security -> `references/providers/protocol-recovery/river-security/PROVIDER.md`, then at most one selected case; Akamai -> `references/providers/protocol-recovery/akamai/PROVIDER.md`, then exactly one selected Akamai reference; env -> `environment-patch-playbook.md` or `references/providers/implementation/python-node/strategies/env-patch/STRATEGY.md` after selecting `route: python-node`; verifier method -> `references/providers/protocol-recovery/verifier/PROVIDER.md`, then exactly one selected captcha family reference; anti-debug offline -> `offline-inline-deob-playbook.md`; crypto name-lie -> `crypto-patterns.md`).

## Path Base

Backtick reference paths resolve against the file that cites them, not against a single global root:

1. Hub and methodology files (`SKILL.md`, `references/*.md`, `references/methodology/*.md`) cite `references/...` from the **skill root**.
2. Provider files (`references/providers/**/PROVIDER.md` and their local `references/*.md`) cite `references/...` from **that Provider's own directory**. Example: a "references/ + api-inventory.md" citation inside the iv8 Provider resolves to `references/providers/implementation/iv8/references/api-inventory.md`, never to a same-named file at the skill root.
3. A cross-layer citation must spell the full skill-root-relative path instead of relying on the local base.
4. If a cited path does not resolve on the first try, do not scan the tree. Re-resolve once against the other base, then follow the accounting block below before opening any additional path.

## Reject These Requests

- "Read every playbook/case first"
- Opening both Chromium and Camoufox providers without a Camoufox selection criterion
- Opening implementation providers before a gate/mutation point is known, except explicit one-shot requests (hook snippet, known AST file, known env entry)
- Loading a second case after one registry match already failed current evidence
- Claiming another `+1` in the same dispatch window without an intervening evidence action, user answer, or accepted Provider result

## Accounting

When expanding the budget, state:

```text
readBudget: window=<initial|handoff|case|write> used=<n>/<cap> taskUsed=<n>/24 next=<path> blocker=<text>
```

If you cannot name the blocker, or the current window is at cap, do not read another file; ask one clarifying question or run one evidence action instead.
