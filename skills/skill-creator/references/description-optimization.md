# Description Optimization

Use this reference when the user asks to improve skill triggering accuracy, optimize a description, add trigger evals, or reduce overlap between skills.

## Why This Matters

The `description` field in `SKILL.md` frontmatter is the primary trigger signal. It should say when to invoke the skill, what it does, and when not to use it if nearby skills compete.

## Generate Trigger Eval Queries

Create about 20 realistic queries with a mix of should-trigger and should-not-trigger cases.

Save them as JSON:

```json
[
  {"query": "the user prompt", "should_trigger": true},
  {"query": "another prompt", "should_trigger": false}
]
```

Good trigger evals are concrete and realistic. Include details like file paths, URLs, libraries, user constraints, adjacent workflows, and casual wording.

Avoid abstract prompts like `Create a chart` or `Format data`; they are too easy and do not test trigger boundaries.

## Coverage

For should-trigger queries, include:

1. Formal and casual wording.
2. Prompts that do not name the skill but clearly need it.
3. Uncommon but valid use cases.
4. Cases where this skill competes with another but should win.

For should-not-trigger queries, include near misses:

1. Same keywords, different intent.
2. Adjacent skills that should handle the task.
3. Ambiguous wording where a naive keyword match would over-trigger.
4. Cases that mention skill-related concepts but only as background.

## Human Review Of Eval Set

Use `assets/eval_review.html` when available:

1. Read the template.
2. Replace `__EVAL_DATA_PLACEHOLDER__` with the raw JSON array.
3. Replace `__SKILL_NAME_PLACEHOLDER__` with the skill name.
4. Replace `__SKILL_DESCRIPTION_PLACEHOLDER__` with the current description.
5. Write to a temporary file and open it with an OS-appropriate command.
6. After the user exports, check the most recent matching file in their Downloads folder.

This review step matters because bad eval queries produce misleading description changes.

## Run Optimization Loop

If the external CLI dependencies are available, run:

```bash
python scripts/run_loop.py \
  --eval-set <path-to-trigger-eval.json> \
  --skill-path <path-to-skill> \
  --model <model-id-powering-this-session> \
  --max-iterations 5 \
  --confirm-run \
  --verbose
```

Use the model ID powering the current session so trigger behavior matches the user's actual environment.

While it runs, periodically report iteration scores and notable failures.

The loop requires a non-zero train/test split, evaluates iterations only against the training prompts, and opens the holdout only after selecting the train-side candidate. It retains that candidate only when its conservative held-out gain meets `--min-effect` without regressing a previously passing prompt. Ties keep the earlier/smaller description.

## Apply Result

When the loop returns `best_description`, inspect `selection_reason`, confidence bounds, and `prompt_regressions`. The loop is proposal-only and never edits `SKILL.md`.

1. Show before/after text and report train/test scores plus residual risky near misses.
2. If the baseline was retained or `prompt_regressions` is non-empty, make no edit.
3. Ask the user to confirm the exact `SKILL.md` path, then create a change-control snapshot with `SKILL.md` allowlisted.
4. Update only the confirmed `description` field and run change-control `check`.
5. If neighboring skills overlap, propose their changes separately; do not widen the original allowlist silently.

## How Triggering Works

Skills appear to OpenCode as name + description metadata. The model decides whether to load a skill based on that metadata and task complexity.

Simple one-step prompts may not trigger any skill even if the description matches, because basic tools are enough. Trigger eval prompts should be substantive enough that a specialized workflow would actually help.
