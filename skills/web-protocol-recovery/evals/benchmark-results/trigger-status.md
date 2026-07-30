# Trigger eval status

## Current HEAD full_test

| Field | Value |
|---|---|
| Score | **22/22** |
| Model | `deepseek/deepseek-v4-pro` |
| Run base commit | `3385b300900546a1e8c08a8cd4b20948420a41e6` |
| Evaluated SKILL.md SHA-256 | `68fe66ad71efdff0de854060712e9e8617f1663cec966a8a8a655a2be5ae1fdd` |
| Initial pass | `21/22`; one timeout on the WeChat miniapp positive |
| Retry | `1/1` with a 600-second per-query timeout |
| Artifact | `evals/benchmark-results/trigger-deepseek-v4-pro-current.json` |
| eval_mode | `full_test` |
| current_acceptance | true |

Final taxonomy: under-trigger=0, over-trigger=0, runtime-error=0.

### Final failures

| # | class | query |
|---|---|---|
| - | none | - | all passed after the timeout retry |

## Historical artifact

`trigger-deepseek-v4-flash-HEAD.json` remains a historical two-model union with
missing raw previews for four Flash first-pass failures. It is not used for
current acceptance.

## Notes

1. This run uses isolated temp skills plus provider credentials from local OpenCode config; no credentials are written to the repository.
2. Neighbor stubs for `skill-creator` and `darwin-skill` remain enabled for near-miss routing realism.
3. The current acceptance run uses `deepseek-v4-pro` only. It does not use DeepSeek Flash, GPT-5.6, or Grok.
4. The first pass had one timeout; the same query passed on a sequential retry with a 600-second timeout. Both first-pass and retry records are retained.
