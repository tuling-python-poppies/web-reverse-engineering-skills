# Trigger eval status

This file tracks trigger-boundary acceptance for `evals/trigger-evals.json`.
It is not a substitute for a retained model run with per-query grades.

## Current inventory

| Surface | Count | Notes |
|---|---|---|
| `evals/trigger-evals.json` | 22 | 13 positive / 9 negative |
| `evals/route-regression.json` | 13 | static route/shape contract |
| `evals/evals.json` behavioral | 21 | with-skill vs baseline harness metadata |
| Historical full10 | 10 | `iteration-1-full10.json`; not current acceptance |

## Session-reported Grok result

- Claim heard in session: **Grok 15/22** effective completion on the trigger set.
- Repository state at the time of this note: **no retained raw outputs, no per-query pass/fail table, no integrity manifest**.
- Therefore **15/22 is not current acceptance** and must not be quoted as a score-advancing full_test.

## HEAD hardening already landed

1. `7b92d74` tightened the frontmatter trigger boundary: explicit protocol intent required; near-miss tooling/AST/Camoufox/GraphQL/browser wording stays out; skill maintenance routes to `skill-creator` / `darwin-skill`.
2. Follow-up description intent synonyms: `逆向` / `还原` / `抓入口` / `协议复现`, to reduce under-trigger on real positive wording while keeping the no-protocol-target negatives.
3. Body lead sentence aligned: public reverse entry only when protocol-recovery intent is explicit.
4. Static gates: `python scripts/preflight.py --strict` remains the acceptance bar for metadata; route regression stays separate from model trigger grading.

## Required next full_test

Re-run the full 22-query trigger set on the tested commit and retain:

1. tested commit SHA
2. model id / reviewer id
3. each query, expected `should_trigger`, model decision, pass/fail
4. aggregate score and failure taxonomy (`under-trigger` / `over-trigger` / `judge-noise`)
5. artifact path under `evals/benchmark-results/`

Until that artifact exists, status remains `pending_full_test` with **no score claim**.
