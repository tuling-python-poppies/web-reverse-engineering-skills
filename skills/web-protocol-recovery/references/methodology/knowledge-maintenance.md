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
| Regression expectation | `references/official-self-test-task-suite.md` and local case/unit tests |

Do not create a second doctrine index, symptom list, tool inventory, project tree, report template, case index, or Provider-local copy of root policy.

## Deduplication Gate

Before adding or extending a reference:

1. Search the root router, doctrine index, pattern atlas, owning Provider, and focused playbooks.
2. Choose one canonical owner for the rule.
3. Merge only unique evidence or procedure; replace other copies with routing links.
4. Update router entries and self-test routes in the same change.
5. Delete obsolete material only after proving no inbound references remain.

Add a helper only when it deterministically removes repeated future work and has bounded inputs/outputs. Otherwise keep the lesson in its canonical document or task-local project.
