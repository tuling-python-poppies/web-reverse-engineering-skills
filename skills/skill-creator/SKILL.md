---
name: skill-creator
description: Create, revise, evaluate, and package OpenCode skills. Use this when the user wants to create a new skill, clean up one existing skill, improve a skill description, add eval prompts, run a targeted benchmark, package a skill, or review overlap to tighten trigger boundaries. Trigger phrases include "turn this workflow into a skill", "improve this skill", "test this skill", "add evals", "optimize the description", and "package this skill". Do not trigger for bulk/all-skill scoring, optimization history, or autonomous score→edit→ratchet loops; use darwin-skill. Do not trigger for applying a domain skill to a normal task, or for opencode config/MCP/agent/plugin edits without changing a skill definition.
---

# Skill Creator

A workflow for creating, revising, evaluating, optimizing, and packaging OpenCode skills.

Prefer the smallest skill that reliably triggers and gives clear execution guidance. For one named skill, read neighboring descriptions to diagnose overlap but edit only that skill's confirmed allowlist. Any request to score or jointly tighten two or more installed skills belongs to `darwin-skill`.

Do not use this skill when the user is applying an existing skill to a normal task, such as reversing a website or writing a hook. Use it only when the object of work is a skill definition, description, eval, packaged resource, or trigger boundary.

If the user is editing `opencode.json`, agents, plugins, MCP servers, or permission rules and is not changing a skill, do not use this skill. Follow the active OpenCode configuration workflow available in the current environment instead of inventing a skill handoff.

If the user wants scoring, trigger-boundary review, or score → edit → measure → keep-or-rollback work across two or more installed skills, that is `darwin-skill`. This includes phrases like "复评所有 skills", "优化所有 skills", "这几个 skills 的触发边界", "skill 质量打分", or "查看优化历史". Use `skill-creator` for authoring, describing, eval-harnessing, and packaging one explicitly named skill; use `darwin-skill` for multi-skill audits and ratcheting existing skill sets.

## Core Loop

1. Capture the skill's intent and success criteria.
2. Draft or revise `SKILL.md` and any bundled resources.
3. Add realistic eval prompts and, where useful, objective assertions.
4. Run the skill against test prompts and compare against a baseline when feasible.
5. Review qualitative outputs and quantitative benchmark data with the user.
6. Improve the skill based on feedback and rerun.
7. Package the final skill when the user is satisfied.

Adapt the depth of this loop to the user's request. If they ask for a lightweight cleanup, do not force a full benchmark. If they ask whether a skill is actually helping, run the evaluation workflow.

For any mode that edits a skill, use the change-control gate before the first edit:

```bash
python scripts/change_control.py snapshot --skill-path <skill> --manifest <workspace>/change-control.json --confirm --allow SKILL.md --allow <each-approved-path> --ledger <skills-root>/auto-optimize-results.tsv
```

For `create`, run the gate before creating the target directory. The parent directory must already exist, the user must have confirmed the exact new path, and the allowlist must include `SKILL.md`:

```bash
python scripts/change_control.py snapshot --skill-path <new-skill> --allow-missing-target --manifest <workspace>/change-control.json --confirm --allow SKILL.md --allow <each-approved-new-file> --ledger <skills-root>/auto-optimize-results.tsv
```

A missing-target restore removes only files named in that manifest and prunes only empty directories on their parent chains. It refuses when the new skill contains any non-allowlisted file, so it cannot recursively delete concurrent work.

The snapshot prints an external `manifest_sha256`; retain it outside the manifest and pass it to every `check`, `append-ledger`, and `restore`. The manifest records the exact allowlist, ledger state, and surrounding Git index plus tracked/nonignored worktree state. After editing, run `check --manifest-sha256 <digest>` and retain `current_state_sha256`. Append the ledger only through `append-ledger --expected-state <last-hash> --line <tsv-row>`, which locks, rechecks, appends, fsyncs, and returns the new hash. `restore` also requires both hashes and refuses after protected state changes. `--confirm` is only a CLI acknowledgement and cannot prove human authorization.

## Mode Selection

Pick the smallest mode that satisfies the user's intent before acting:

| User says | Mode | Actions |
|-----------|------|---------|
| "create / make / turn workflow into skill" | `create` | Confirm exact target/allowlist → missing-target snapshot → draft SKILL.md → propose eval prompts → confirm |
| "clean up / revise / fix / improve" | `revise` | Read current → find focused issues → one scoped edit → verify |
| "evaluate / score / review quality" | `eval-only` | Read-only; design/generate test prompts → baseline scoring → report gaps |
| "package / install / publish" | `package` | Validate skill → run package_skill.py → exclude local artifacts |
| "check overlap / tighten trigger / optimize description" | `description-optimize` | Audit trigger/near-miss prompts → adjust frontmatter description |
| "test / benchmark / prove it helps" | `benchmark` | Run with-skill vs baseline on 2-3 prompts → compare outputs |

If unclear, ask. Do not upgrade `eval-only` to editing files without confirmation.

## Confirmation Checkpoints

Match the user's requested mode before editing anything.

Pause and confirm before:

1. Creating a new skill directory, overwriting an existing `SKILL.md`, or moving long content into new `references/`, `scripts/`, `assets/`, or `evals/` files.
2. Adding eval prompts that include real target URLs, cookies, tokens, proprietary workflows, or other sensitive samples.
3. Running a benchmark that will spawn subagents, call browser/network tools, install dependencies, or generate large result artifacts.
4. Packaging, publishing, copying into an installed skills directory, or changing an active skill used by the current OpenCode session.

For benchmark runs, confirm the model, worker count, timeout, run count, output directory, and whether external tools or network access are allowed. For packaging, confirm the source directory and output directory; the packager refuses to overwrite an existing archive.

If the user asks for review, scoring, trigger analysis, or explanation only, stay read-only and return findings plus proposed edits. Do not silently upgrade a review into file modification.

## Communicating With The User

Match the user's technical level.

1. Use terms like evaluation, benchmark, JSON, and assertion when the user appears comfortable with them.
2. Briefly define terms when the user may not know them.
3. For lightweight requests, give concise findings and edits.
4. For evaluation-heavy requests, explain what will be tested and how the user can review results.

## Creating Or Revising A Skill

### Capture Intent

Extract what you can from the current conversation before asking questions.

Clarify only what is needed:

1. What should this skill enable OpenCode to do?
2. When should this skill trigger, and when should it not?
3. What output should a successful run produce?
4. Should this skill include evals, scripts, templates, references, or assets?

### Research Nearby Skills

Check available skills and adjacent trigger areas before editing.

Common overlaps:

1. Browser hook injection vs crypto entry tracing.
2. Crypto entry tracing vs Node.js environment patching.
3. AST deobfuscation vs runtime debugging.
4. General workflow guidance vs a narrow task-specific skill.

When overlap exists, tighten all relevant surfaces:

1. Frontmatter `description`.
2. Trigger boundary section.
3. Handoff guidance.
4. Near-miss negative eval prompts.

### Write `SKILL.md`

Required frontmatter:

1. `name`: kebab-case skill identifier.
2. `description`: primary trigger signal; include concrete trigger contexts and nearby non-trigger cases.

Optional frontmatter:

1. `compatibility`.
2. `argument-hint`.
3. `allowed-tools`.
4. `metadata`.

Recommended structure:

```text
skill-name/
├── SKILL.md
├── scripts/       # deterministic helpers or templates
├── references/    # detailed docs loaded as needed
├── assets/        # templates, icons, HTML review pages
└── evals/         # local test prompts, usually excluded from package output
```

Keep `SKILL.md` focused. If it approaches 500 lines, move long procedures to `references/` and leave clear pointers.

## Writing Guidance

1. Put trigger guidance in the frontmatter `description`, not only in the body.
2. Use imperative instructions.
3. Explain why important constraints exist instead of relying only on rigid MUST/NEVER wording.
4. Include examples when output format matters.
5. Bundle scripts only for repeatable work that future runs would otherwise recreate.
6. Do not include malware, credential exfiltration, misleading behavior, or surprising capabilities.

## Testing And Evaluation

Use `references/evaluation-workflow.md` when the user asks to test, benchmark, add evals, compare iterations, or prove that a skill helps.

Short version:

1. Save realistic prompts to the evals/evals.json file in the target skill.
2. Run with-skill and baseline outputs when feasible.
3. Draft objective assertions while runs execute.
4. Save timing and grading data, then create an independently reviewed integrity manifest.
5. Aggregate with `scripts/aggregate_benchmark.py`; missing baselines or unverified grading fail closed.
6. Present qualitative outputs and benchmark results for user review.

For dry-run or lightweight evaluation, still return one record per prompt with `baseline_behavior`, `with_skill_behavior`, `delta`, `decision`, and `eval_mode`. Mark `eval_mode` as `dry_run` when no subagent benchmark or script actually ran, and keep the decision limited to `keep`, `revise`, or `no_change`.

Use `agents/grader.md`, `agents/analyzer.md`, and `agents/comparator.md` when grading, analyzing benchmarks, or doing blind comparisons.

## Description Optimization

Use `references/description-optimization.md` when the user asks to improve trigger accuracy, optimize a description, add trigger evals, or reduce skill overlap.

Use `references/trigger-eval-quickcheck.md` when the user only wants a lightweight review of existing trigger evals without running the full optimization loop.

Short version:

1. Create about 20 realistic trigger eval queries.
2. Include both should-trigger and near-miss should-not-trigger prompts.
3. Let the user review the eval set with `assets/eval_review.html` when possible.
4. Run `scripts/run_loop.py` if the required CLI dependencies are available.
5. Inspect `selection_reason` and prompt regressions; only after confirmation, apply an accepted `best_description` through the change-control allowlist and report before/after scores.

## Environment Adaptation

Use `references/environment-adaptation.md` when the environment is limited, headless, remote, or when packaging/updating installed skills.

Key rules:

1. In limited environments, run test prompts yourself and use inline review.
2. In headless environments, prefer static artifacts or conversation review over local browser servers.
3. Preserve the existing skill name when updating a skill.
4. Package with `scripts/package_skill.py` when ready.

## Improvement Heuristics

When revising a skill after feedback:

1. Generalize from feedback rather than overfitting to one prompt.
2. Remove instructions that cause wasted work or excessive token use.
3. Split repeated helper code into `scripts/` if multiple evals recreate it.
4. Move long background material to `references/`.
5. Strengthen trigger boundaries when a skill steals work from a neighboring skill.
6. Add near-miss evals for every boundary bug you fix.

## Packaging

When the skill is ready:

```bash
python scripts/package_skill.py <path/to/skill-folder> [output-directory] --confirm
```

The packager validates the skill and excludes local build artifacts such as `__pycache__` and `.pyc` files.
It packages only `SKILL.md`, license/readme files, and the standard `agents/`, `assets/`, `references/`, and `scripts/` trees. It rejects symlinks, secret-bearing files/content, raw capture or evaluation artifacts, output paths inside the source skill, and collisions with an existing `.skill` archive, then atomically publishes a completed temporary archive.

## Reference Files

1. `references/evaluation-workflow.md`: full eval, benchmark, grading, and review loop.
2. `references/description-optimization.md`: trigger eval generation and description optimization loop.
3. `references/environment-adaptation.md`: limited/headless environment handling and packaging notes.
4. `references/trigger-eval-quickcheck.md`: lightweight trigger eval coverage review.
5. `references/schemas.md`: JSON schemas for eval and benchmark artifacts.
6. `agents/grader.md`: grading assertions against outputs.
7. `agents/analyzer.md`: analyzing benchmark results.
8. `agents/comparator.md`: blind A/B comparison.
9. `scripts/change_control.py`: path/ledger allowlist, Git state guard, zero-write read-only fingerprint, post-edit check, and explicit rollback.
10. `scripts/test_safety.py`: local regression tests for rollback scope, subprocess isolation, package scanning/path safety, holdout separation, and selection bounds.

## Troubleshooting And Recovery

| Problem | Recovery |
|---------|----------|
| Eval script crashes (`run_eval.py`, `run_loop.py`) | Check Python 3 is available: `python --version`. Verify `evals/evals.json` is valid JSON. Run with `--verbose` if supported. Fall back to manual dry-run evaluation. |
| Frontmatter not parsed by OpenCode | Ensure file uses `---\n` delimiters (not malformed YAML). Check `name` and `description` are present and `description` is ≤1024 chars. Keep environment-specific fields such as `compatibility` and `argument-hint` only when the current OpenCode setup uses them. |
| Skill overlap with another skill is unresolvable | Present a comparison table to the user: both descriptions, both trigger scenarios, and 3 near-miss prompts. Offer options: merge into one skill, split by explicit boundary, or keep both with tightened anti-triggers. Require explicit user choice. |
| Benchmark shows regression after edit | Do not discard the data. Record the failed attempt in `results.tsv`. Revert the edit. Diagnose why: over-specificity, conflicting instructions, or wrong dimension targeted. Try a different dimension next round. |
| `package_skill.py` fails | Check the skill folder has valid `SKILL.md`, contains no symlinks, secrets, or raw capture/result artifacts, and the output archive does not already exist. Build artifacts are excluded automatically. |
| No test-prompts.json exists for a skill | In `eval-only`, draft 2-3 prompts in memory and report the gap without writing. Persist `test-prompts.json` only after the user confirms that exact path through change control. |
| User wants to undo the current edit | Run `check` with the retained `manifest_sha256`, then use `restore --confirm --manifest-sha256 <digest> --expected-state <current_state_sha256>`. For a missing-target transaction this deletes only confirmed new files and empty parent-chain directories; any non-allowlisted file blocks restore. Validate and report restored paths. Use Git history only for an explicitly requested repository-level rollback. |
