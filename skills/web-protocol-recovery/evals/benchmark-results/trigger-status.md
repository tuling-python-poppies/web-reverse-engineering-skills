# Trigger eval status

## Latest full_test

| Field | Value |
|---|---|
| Score | **22/22** |
| Primary model | `deepseek/deepseek-v4-flash` |
| Retry model | `deepseek/deepseek-v4-pro` |
| Tested commit | `c193b4edddc50c542abbb4b5bb340cfed3cc9071` |
| Prompt SHA-256 | `18d1f4d4df13bbc1ece8aea86cd3dfc5df0333bec946838ec0b2209ec145b633` |
| Skill.md SHA-256 | `b915e09c693f90eddba88df0055f3a16cf9bc3018f9f95e56945704d9320755b` |
| Artifact | `evals/benchmark-results/trigger-deepseek-v4-flash-HEAD.json` |
| eval_mode | `full_test` |
| current_acceptance | true |

Failure taxonomy: under-trigger=0, over-trigger=0, runtime-error=0.

### Failures

| # | class | expected | model | query |
|---|---|---|---|---|
| - | none | - | - | all passed |

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
5. Session-reported Grok 15/22 without retained raw outputs is superseded by this artifact for HEAD.
