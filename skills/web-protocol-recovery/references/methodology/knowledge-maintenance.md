# web-protocol-recovery Knowledge Maintenance

Use this file only to place reusable web-protocol-recovery knowledge. Skill optimization, change control, eval execution, grading, and packaging belong to `skill-creator`.

## One Owner Per Lesson

| Knowledge | Canonical owner |
|---|---|
| Public dispatch, safety, route, and completion invariants | `SKILL.md` |
| Work-order, project, read-budget, success-shape, and writeback contracts | one file under `references/methodology/` |
| Family-level invariant or prohibition | `references/doctrine-index.md` |
| Symptom and shortest first move | `references/pattern-atlas.md` |
| Procedure for one protocol problem | one focused root playbook |
| Engine/tool/runtime API detail | selected Provider and its references |
| Tempting shortcut plus corrective self-check | `references/anti-patterns-playbook.md` |
| Compact target adaptation | root case registry through `case-writeback.md` |
| Regression expectation | `references/official-self-test-task-suite.md`, `references/methodology/forward-testing.md`, and local case/unit tests |

Do not create a second doctrine index, symptom list, tool inventory, project tree, report template, case index, or Provider-local copy of root policy.

## Deduplication Gate

Before adding or extending a reference:

1. Search the root router, doctrine index, pattern atlas, owning Provider, and focused playbooks.
2. Choose one canonical owner for the rule.
3. Merge only unique evidence or procedure; replace other copies with routing links.
4. Update router entries and self-test routes in the same change.
5. Delete obsolete material only after proving no inbound references remain.

Add a helper only when it deterministically removes repeated future work and has bounded inputs/outputs. Otherwise keep the lesson in its canonical document or task-local project.

## Script Placement

`scripts/` is categorized and every new script must be placed by role, never at the `scripts/` root. Taxonomy and rules: `scripts/README.md`.

| Directory | Role |
|---|---|
| `scripts/tools/` | Reverse-work diagnostics invoked during a task (each carries `--self-test`) |
| `scripts/gates/` | Skill preflight/validation gates run when editing the skill |
| `scripts/tests/` | Unit tests for the gates (`test_*.py`) |
| `scripts/providers/` | Provider-scoped helpers under a Provider subtree |

When adding a `scripts/tools/*` or `scripts/gates/forward_test_report.py`-style diagnostic that must stay green, register it in `scripts/gates/preflight.py` `DIAGNOSTIC_SELF_TESTS`. A script at the `scripts/` root is a placement defect.
