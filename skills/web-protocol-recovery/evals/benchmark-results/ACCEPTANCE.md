# Behavioral benchmark acceptance

## Run

- Date: 2026-07-28
- Skill HEAD base: `82c1610` (plus this results commit)
- Mode: with-skill vs baseline, **1 full round × 10 prompts** from `evals/evals.json`
- Artifact: `evals/benchmark-results/iteration-1-full10.json`

## Result

| Metric | Value |
|---|---|
| with-skill expectations | **10/10** pass |
| baseline expectations | **6/10** pass |
| Comparison | **with_skill_clear_win** |

## Historical git debt (not rewritten)

Commit `5b37aef` (`refactor web-protocol-recovery: split provider architecture`) remains a single subject-only commit that mixed provider migration, schemas, validators, and the 22-case hash cascade. Per project policy this history is **not** rewritten. Acceptance is on current HEAD behavior and preflight, not on rewriting that commit.

## Rounds note

`evals/evals.json` still documents `rounds: 3` as the preferred harness setting. This acceptance executed **one** full round for cost control. Optional follow-up: rounds 2–3 for variance.
