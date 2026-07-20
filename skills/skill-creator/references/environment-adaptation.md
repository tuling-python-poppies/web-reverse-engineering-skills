# Environment Adaptation

Use this reference when evaluating, reviewing, or packaging skills in limited, headless, or remote environments.

## Limited Tooling

If subagents or the full local toolchain are unavailable, keep the same loop but simplify mechanics:

1. Read the skill's `SKILL.md`.
2. Run each test prompt yourself using the skill instructions.
3. Skip baseline runs if independent comparison is not meaningful.
4. Present outputs directly in the conversation.
5. Focus on qualitative feedback rather than benchmark statistics.

This is less rigorous than subagent-based testing, but still catches structural problems and unclear instructions.

## Headless Or Remote Environment

If no browser/display is available:

1. Prefer inline review or static review artifacts over local servers.
2. Generate benchmark files on disk when possible.
3. If a review page downloads `feedback.json`, ask the user to make it available and then read it.
4. Avoid commands that assume Unix job control, such as `nohup`, `&`, or `kill $PID`, unless the current shell supports them.

## Updating Existing Skills

When modifying an installed or existing skill:

1. Preserve the directory name and frontmatter `name`.
2. If the source is read-only, copy it to a writable temp directory first.
3. Before editing, use `scripts/change_control.py snapshot` with an explicit confirmed path allowlist; use its baseline archive for old-vs-new comparison and rollback.
4. Do not rename the packaged `.skill` unless the user explicitly wants a new skill.

## Packaging

Use:

```bash
python scripts/package_skill.py <path/to/skill-folder> [output-directory] --confirm
```

The packager validates the skill, includes only standard skill files/trees, excludes local eval/build artifacts, scans included files for secrets and raw capture/result artifacts, rejects symlinks and output paths inside the source skill, refuses archive collisions, and atomically publishes a completed temporary archive.

If direct output writes fail, stop and ask the user for a different output directory. Do not bypass collision or path-scope checks with a manual copy.

If a `present_files` tool exists, use it to present the `.skill` package. Otherwise, report the output path.

## Blind Comparison

Use blind comparison only when the user asks whether one skill version is truly better or when ordinary benchmark results are inconclusive.

Read:

1. `agents/comparator.md`
2. `agents/analyzer.md`

The core idea is to compare two outputs without revealing which skill version produced each, then analyze why one wins.
