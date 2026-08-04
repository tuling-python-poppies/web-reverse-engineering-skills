# Trigger eval status

## Historical bounded-recovery full_test (stale for current HEAD)

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
The historical run accepted the bounded-recovery routing surface for the recorded
SKILL.md hash only; it does not accept current HEAD or claim first-pass stability.

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
3. The historical run uses `deepseek-v4-pro` only. It does not use DeepSeek Flash, GPT-5.6, or Grok.
4. The artifact retains first-pass attempt grades, retry attempt grades, exact timeout overruns, and per-query aggregates. Retry granularity is one bounded retry per failed `(query_id, attempt)`; one query can therefore have multiple retries only when multiple n-run attempts failed independently. `runs_per_query=3`; no sample-count caveat is required, but the failed first-pass stability result remains explicit.

## Note

`current_acceptance` was withdrawn after the standing-approval policy edit. Re-run trigger full_test to restore routing acceptance, and run the separate standing-policy behavioral cases before claiming the gate behavior itself is accepted.

Case revision 4 then changed the first stage of `requiredCurrentProviderChain` from
`camoufox` to `chromium-recon` in four `python-node` cases. The static surface of that
change is verified: `validate_architecture.py` now fails closed on a current-chain
camoufox stage without a declared `camoufoxCriterion`, three contract tests cover the
shipped defect and guard the still-legal historical chain, and the regenerated
`registry.json` projection was checked directly. What is **not** retested is model-side
routing on that path — eval `15` (positive `route:camoufox` with an explicit
engine-level criterion) and eval `12` (negative: no camoufox from generic evidence).
Those two are not runnable with the current toolchain at all: `run_eval.py` and
`run_loop.py` both score trigger rate over `trigger-evals.json` (does OpenCode load the
skill), not the `expectations` in `evals.json`. The behavioral set has no automated runner
here. Note also that `single_model_required: true` binds the trigger gate to one executor
model, so running it under a different model produces a separate observation and does not
restore this acceptance.

## Harness defect: isolated runs silently lose provider credentials

A `deepseek-v4-flash` trigger attempt on 2026-08-04 returned `0/3` on all 22 queries,
including every positive. That result is void and was discarded; it is not a description
regression. `run_eval.py` isolates each worker by repointing `HOME`, `USERPROFILE`,
`APPDATA`, and `LOCALAPPDATA` at a temp directory and writing an isolated config holding
only `permission`, which drops the `provider` block. Its one credential-restore path,
`copy_opencode_credentials`, reads `~/.local/share/opencode/auth.json` — a location this
setup does not use, because the provider keys live inline in
`~/.config/opencode/opencode.json` under `provider.*.options.apiKey`. Every worker
therefore launched with no credentials, the provider returned
`UnknownError / Unexpected server error`, and `_parse_triggered` reported not-triggered for
all of them. `_SAFE_ENVIRONMENT_KEYS` is a fixed allowlist with no `*_API_KEY`, so an
environment variable cannot substitute.

Reproduced under probe: injecting the real `provider` block into the isolated config makes
the same positive query emit the `tool_use` / `tool: skill` event that `_parse_triggered`
expects. The fix belongs to `skill-creator/scripts/run_eval.py` and is out of scope for
this skill. Until it lands, a `0/N` sweep from this harness is evidence about credentials,
not about routing — confirm a `skill` tool_use event exists in the raw stream before
reading any trigger sweep as a regression.
