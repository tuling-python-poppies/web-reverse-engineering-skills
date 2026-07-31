# Trigger eval status

## Current HEAD full_test

| Field | Value |
|---|---|
| Score | **22/22** |
| Attempt final pass rate | `66/66` |
| Model | `deepseek/deepseek-v4-pro` |
| Run base commit | `c7889ae32e7cf82e41eee9b8ad758ddcb16fe69f` |
| Evaluated SKILL.md SHA-256 | `c9c6102dc8dc7478e26edd452cf6f79ce6953e00e095e859c923d9dbda1be8b0` |
| Prompt SHA-256 | `18d1f4d4df13bbc1ece8aea86cd3dfc5df0333bec946838ec0b2209ec145b633` |
| First-pass attempts | `54/66` |
| Retry | `12/12` with a 600-second per-query timeout |
| Artifact | `evals/benchmark-results/trigger-deepseek-v4-pro-current.json` |
| eval_mode | `full_test` |
| current_acceptance | true |
| runs_per_query | `3` |

Final taxonomy: under-trigger=0, over-trigger=0, runtime-error=0.

### Final Failures

| # | class | attempts | query |
|---|---|---|---|
| - | none | - | all query aggregates passed |

## Historical artifact

`trigger-deepseek-v4-flash-HEAD.json` remains a historical two-model union with
missing raw previews for four Flash first-pass failures. It is not used for
current acceptance.

## Notes

1. This run uses isolated temp skills plus provider credentials from local OpenCode config; no credentials are written to the repository.
2. Neighbor stubs for `skill-creator` and `darwin-skill` remain enabled for near-miss routing realism.
3. The current acceptance run uses `deepseek-v4-pro` only. It does not use DeepSeek Flash, GPT-5.6, or Grok.
4. The artifact retains first-pass attempt grades, retry attempt grades, and per-query aggregates. `runs_per_query=3`; no statistical caveat is required.
