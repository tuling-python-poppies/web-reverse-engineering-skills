# Evaluation Workflow

Use this reference when the task asks to test a skill, add evals, benchmark whether a skill helps, compare iterations, or review generated outputs.

## Prepare Test Cases

1. Create 2-3 realistic prompts first; expand later after the first iteration.
2. Save prompts to `evals/evals.json` using the schema in `references/schemas.md`.
3. For each test case, create an `eval_metadata.json` in the run workspace with the prompt and assertions.
4. Prefer objective assertions when outputs can be checked reliably; use qualitative review for subjective skills.

Minimal `evals/evals.json` shape:

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's task prompt",
      "expected_output": "Description of expected result",
      "confirmation_required": true,
      "files": [],
      "expectations": [
        "The output satisfies the primary requirement"
      ]
    }
  ]
}
```

## Run Layout

Put results in `<skill-name>-workspace/` as a sibling to the skill directory.

Use this structure:

```text
<skill-name>-workspace/
└── iteration-1/
    └── eval-<name>/
        ├── with_skill/outputs/
        ├── without_skill/outputs/     # new skill baseline
        └── old_skill/outputs/         # existing skill baseline, if applicable
```

When improving an existing skill, first confirm the exact edit allowlist and run `scripts/change_control.py snapshot` into the workspace, including the session results file with `--ledger`. Retain the printed `manifest_sha256` outside that manifest and pass it to every later control command. Use the generated baseline archive as the old-skill baseline and `check` after each iteration. The guard detects changes to the surrounding Git index and tracked/nonignored non-allowlisted worktree. Append results only with `append-ledger --manifest-sha256 <digest> --expected-state <last-hash> --line <row>`. The snapshot is required before editing; `--confirm` is only a CLI acknowledgement.

## Spawn Runs

Before spawning runs, confirm the model, worker count, timeout, runs per query, output directory, and whether browser/network tools or dependency installation are allowed. Do not create benchmark artifacts or start subagents from an `eval-only` request without this confirmation.
After confirmation, pass `--confirm-run` to `run_eval.py` or `run_loop.py`; both CLIs refuse to spawn workers without it.
Trigger and description-improvement subprocesses run with external plugins disabled, deny-by-default tool permissions, a filtered environment, and an empty temporary project directory. Environment-only provider credentials are intentionally not forwarded; configure model authentication through OpenCode's credential store.

For each test case, spawn the with-skill run and baseline run in the same turn where possible.

With-skill prompt template:

```text
Execute this task:
- Skill path: <path-to-skill>
- Task: <eval prompt>
- Input files: <eval files if any, or "none">
- Save outputs to: <workspace>/iteration-<N>/eval-<ID>/with_skill/outputs/
- Outputs to save: <what the user cares about>
```

Baseline prompt uses the same user prompt and saves to `without_skill/outputs/` for new skills or `old_skill/outputs/` for existing skills.

## Draft Assertions While Runs Execute

Do not just wait. Draft or refine assertions and explain them to the user.

Good assertions are:

1. Objective enough to grade consistently.
2. Written in human-readable language.
3. Specific to the value the skill is supposed to add.
4. Not so broad that baseline runs pass just as often.

Update both `eval_metadata.json` and `evals/evals.json` when adding assertions.

## Capture Timing

When a subagent completion includes `total_tokens` and `duration_ms`, immediately save it to `timing.json` in that run directory:

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

This information may not be available later, so capture it as each run completes.

## Grade Runs

Grade each run after outputs are available using an agent/model identity different from `eval_metadata.json.executor_id`.

Use `agents/grader.md` for grader instructions. If an assertion is programmatically checkable, prefer a small script over manual judgment.

`grading.json` must use this field shape:

```json
{
  "expectations": [
    {
      "text": "The output includes a runnable command",
      "passed": true,
      "evidence": "Found `npm run decode` in the output."
    }
  ]
}
```

Use `text`, `passed`, and `evidence`; viewer tooling depends on these exact fields. The summary counts and pass rate must exactly match the expectation verdicts.

After grading, create the provider-neutral integrity record:

```bash
python scripts/create_review_manifest.py <run-dir> --reviewer <independent-grader-id> --confirm
```

The helper hashes `grading.json`, `transcript.md`, and every regular file under `outputs/`, rejects symlinks and self-review, and publishes `review_manifest.json` exclusively. Any later grading or artifact edit invalidates aggregation.

## Aggregate Benchmark

Run:

```bash
python scripts/aggregate_benchmark.py <workspace>/iteration-N --skill-name <name> --confirm
```

This produces `benchmark.json` and `benchmark.md` with pass rate, timing, tokens, and deltas. Aggregation requires verified primary and baseline runs with identical eval/run coverage; it rejects missing manifests, mismatched hashes, self-review, incomplete evidence, and grading summaries inconsistent with their verdicts.

## Analyze Results

Read `agents/analyzer.md` for the analyst pass.

Look for:

1. Assertions that both with-skill and baseline always pass.
2. High-variance or flaky prompts.
3. Token/time tradeoffs caused by the skill.
4. Cases where the skill over-constrains or over-expands the solution.

Selection is a ratchet, not a highest-mean contest:

1. Compare repeated-run accuracy with variance or a conservative lower bound.
2. Require a declared minimum effect before accepting a candidate.
3. Reject a candidate that turns any previously passing semantic assertion or trigger prompt into a failure.
4. Treat ties as `no_change`; keep the earlier/smaller version.
5. Record `eval_mode` as `dry_run` when no real run occurred and never mix dry-run scores with executed benchmark scores.
6. Apply a winning description or skill edit only after user review; `run_loop.py` proposes `best_description` but does not edit `SKILL.md`.

## Review Surface

Prefer a review surface that shows qualitative outputs and quantitative benchmark data.

Use `eval-viewer/generate_review.py` if present. If it is not present, use the best fallback:

1. Present outputs inline in the conversation.
2. Generate a static HTML review page.
3. Save benchmark artifacts and ask the user to review files from disk.

In headless environments, avoid long-running local browser servers unless necessary.

## Feedback Loop

When the user is done reviewing, read `feedback.json` if a review artifact produced one.

Focus improvements on cases with specific complaints. Empty feedback usually means the output was acceptable.

After changes:

1. Rerun test cases into `iteration-<N+1>/`.
2. Include a baseline again.
3. For iteration 2+, include previous iteration artifacts in the review surface when possible.
4. Repeat until the user is satisfied or improvements stop being meaningful.
