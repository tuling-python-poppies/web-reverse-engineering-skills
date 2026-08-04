# Trigger eval status

## Current HEAD bounded-recovery full_test

| Field | Value |
|---|---|
| Bounded-recovery score | **22/22** |
| Attempt final pass rate | `66/66` after declared retries |
| Model | `deepseek/deepseek-v4-pro` |
| Run base commit | `c7889ae32e7cf82e41eee9b8ad758ddcb16fe69f` |
| Evaluated SKILL.md SHA-256 | `c9c6102dc8dc7478e26edd452cf6f79ce6953e00e095e859c923d9dbda1be8b0` |
| Prompt SHA-256 | `18d1f4d4df13bbc1ece8aea86cd3dfc5df0333bec946838ec0b2209ec145b633` |
| First-pass attempts | `54/66` |
| First-pass semantic correctness | `54/60`; stability threshold `60/60`, **not accepted** |
| First-pass runtime errors | `6/66`; within the declared maximum rate of `10%` |
| Retry | `12/12` failed attempts, at most one retry per `(query_id, attempt)`, with a 600-second timeout |
| Timeout semantics | Requested worker soft limit; six first-pass overruns are recorded by exact `(query_id, attempt, duration_ms)` |
| Artifact | `evals/benchmark-results/trigger-deepseek-v4-pro-current.json` |
| eval_mode | `full_test` |
| current_acceptance | false |
| runs_per_query | `3` |

First-pass taxonomy: under-trigger=2, over-trigger=4, runtime-error=6. Final
taxonomy after bounded retry: under-trigger=0, over-trigger=0, runtime-error=0.
The run accepts the bounded-recovery routing surface only; it does not claim
first-pass stability.

### Final Failures

| # | class | attempts | query |
|---|---|---|---|
| - | none | - | all query aggregates passed |

### Auxiliary current-local integration run (2026-07-31)

| Field | Value |
|---|---|
| Artifact | `evals/benchmark-results/trigger-deepseek-v4-pro-integration-20260731.json` |
| Model | `deepseek/deepseek-v4-pro` |
| Eval mode | `integrated-current-opencode-selection` |
| Runs | `22 queries × 3 attempts = 66/66` collected |
| Strict query aggregates | `18/22` |
| Nominal attempt agreement | `60/66` (`6` positive under-trigger attempts) |
| Execution failures | `9/66`, all `Insufficient Balance` on negative queries 20–22 |
| Current acceptance | **false** |

This run used the active local OpenCode provider configuration and per-attempt
state/cache directories. It retained event summaries, selected skill names,
bounded previews, and output hashes, but not complete raw transcripts. It is a
diagnostic integration rerun and does not supersede the isolated,
retry-backed `full_test` artifact above or make a score claim.

### Auxiliary failure taxonomy

| class | query IDs | result |
|---|---|---|
| positive under-trigger | `trigger-06`, `trigger-07`, `trigger-16`, `trigger-18` | 6 attempts did not load `web-protocol-recovery` |
| provider execution failure | `trigger-20`–`trigger-22` | 9 attempts returned `Insufficient Balance` before selection |
| negative over-trigger | none observed | all completed negative attempts kept WPR unloaded |

## Historical artifact

`trigger-deepseek-v4-flash-HEAD.json` remains a historical two-model union with
missing raw previews for four Flash first-pass failures. It is not used for
current acceptance.

## Notes

1. This run uses isolated temp skills plus provider credentials from local OpenCode config; no credentials are written to the repository.
2. Neighbor stubs for `skill-creator` and `darwin-skill` remain enabled for near-miss routing realism.
3. The current acceptance run uses `deepseek-v4-pro` only. It does not use DeepSeek Flash, GPT-5.6, or Grok.
4. The artifact retains first-pass attempt grades, retry attempt grades, exact timeout overruns, and per-query aggregates. Retry granularity is one bounded retry per failed `(query_id, attempt)`; one query can therefore have multiple retries only when multiple n-run attempts failed independently. `runs_per_query=3`; no sample-count caveat is required, but the failed first-pass stability result remains explicit.

## Note

`current_acceptance` withdrawn after standing-approval gate policy edit to SKILL.md. Re-run trigger full_test to restore acceptance.
