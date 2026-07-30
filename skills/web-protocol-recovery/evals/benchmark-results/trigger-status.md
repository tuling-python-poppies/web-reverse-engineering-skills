# Trigger eval status

> **STALE — not current acceptance.** SKILL.md changed after the run below
> (Phase 0 vendor criteria sunk to PROVIDER.md, Do Not compressed to pointers,
> duplicate Camoufox/`route` rules removed, plain terms table). The recorded
> `Skill.md SHA-256` no longer matches HEAD. Re-run trigger `full_test` before
> treating any score as current acceptance.

## Last recorded full_test (historical)

| Field | Value |
|---|---|
| Score | **22/22 — union of two models**, not a single-model result |
| Primary model | `deepseek/deepseek-v4-flash`, **18/22 alone** |
| First-pass taxonomy (flash only) | under-trigger=0, over-trigger=1, runtime-error=3 |
| Retry model | `deepseek/deepseek-v4-pro`, 4/4 on the 4 flash failures |
| Tested commit | `11bb8b16fbe20cb5fe05da7a77a4bf264a95f172` |
| Prompt SHA-256 | `18d1f4d4df13bbc1ece8aea86cd3dfc5df0333bec946838ec0b2209ec145b633` |
| Skill.md SHA-256 | `b915e09c693f90eddba88df0055f3a16cf9bc3018f9f95e56945704d9320755b` |
| Artifact | `evals/benchmark-results/trigger-deepseek-v4-flash-HEAD.json` |
| eval_mode | `full_test` |
| current_acceptance | false (stale, see banner) |

Post-union failure taxonomy: under-trigger=0, over-trigger=0, runtime-error=0.
That taxonomy is what remains *after* the stronger retry model absorbed the
first-pass failures; read it together with the first-pass row above.

### First-pass failures (deepseek-v4-flash), all cleared on retry

| # | class | query |
|---|---|---|
| 1 | runtime-error | River Security positive |
| 2 | runtime-error | Reese84 positive |
| 3 | runtime-error | Imperva → Reese84 triage positive |
| 4 | over-trigger | Camoufox QA negative |

These four are the most ambiguous descriptions in the set. A flash-only
acceptance claim is not supported by this artifact.

## Inventory

| Surface | Count | Notes |
|---|---|---|
| `evals/trigger-evals.json` | 22 | 13 positive / 9 negative |
| `evals/route-regression.json` | 13 | static route/shape contract |
| `evals/evals.json` behavioral | 21 | with-skill vs baseline harness metadata |
| Historical full10 | 10 | `iteration-1-full10.json`; not current acceptance |

## Notes

1. Isolated temp skills include `skill-creator` and `darwin-skill` stubs so skill-maintenance negatives are not forced onto the only available skill.
2. Provider credentials come from local OpenCode config and are not written into the skill repository.
3. Trigger detection follows skill-creator `run_eval.py`: OpenCode JSON event stream `tool_use` / `skill` with matching skill name.
4. Failed queries from the first pass were retried sequentially with `deepseek/deepseek-v4-pro`.
5. Session-reported Grok 15/22 without retained raw outputs is superseded by this artifact.
6. `Tested commit` was originally recorded as `c193b4e`, whose SKILL.md hashes to
   `d1c273cb...` and therefore was never the tested version. Corrected to `11bb8b1`,
   which reproduces the recorded `Skill.md SHA-256`. A regression baseline checked
   out at `c193b4e` would have compared against untested content.
