# Historical behavioral benchmark summary

This file preserves the reported result of the 2026-07-28 run. It is not current acceptance: the original 20 model outputs and independent grading artifacts were not retained, so the aggregate verdicts cannot be independently reproduced from repository contents.

## Run

- Date: 2026-07-28
- Skill base commit: `82c1610917b84adfce1eaa9df67d754c6c33ee43`
- Result record commit: `385b11d019fd9d6d3c432d27c5518754fc2815dc`
- Prompt file SHA-256: `348dad72d97ea3e469c582390fe5fc97e9fdc22b8aa032fa8c07b2977234ee36`
- Mode: with-skill vs baseline, **1 full round × 10 prompts** from `evals/evals.json`
- Artifact: `evals/benchmark-results/iteration-1-full10.json`

## Result

| Metric | Value |
|---|---|
| with-skill expectations | **10/10** pass |
| baseline expectations | **6/10** pass |
| Comparison | **with_skill_clear_win** |

These are reported aggregate values, not independently verified acceptance evidence. A future acceptance run must retain each with-skill output, baseline output, assertion grade, reviewer identity/configuration, and an integrity manifest that binds them to the prompt set and tested commit.

## Historical git debt (not rewritten)

Commit `5b37aef` (`refactor web-protocol-recovery: split provider architecture`) remains a single subject-only commit that mixed provider migration, schemas, validators, and the 22-case hash cascade. Per project policy this history is **not** rewritten. Acceptance is on current HEAD behavior and preflight, not on rewriting that commit.

## Rounds note

`evals/evals.json` still documents `rounds: 3` as the preferred harness setting. This acceptance executed **one** full round for cost control. Optional follow-up: rounds 2–3 for variance.
