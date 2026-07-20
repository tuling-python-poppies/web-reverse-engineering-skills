# Trigger Eval Quickcheck

Use this checklist when reviewing `evals/trigger-evals.json` without running the full automated optimization loop.

## File Shape

Each item should use this shape:

```json
{
  "query": "realistic user prompt",
  "should_trigger": true
}
```

## Minimum Coverage

For each skill, aim for:

1. 6-10 should-trigger prompts.
2. 6-10 should-not-trigger prompts.
3. At least 3 near-miss negatives from neighboring skills.
4. At least 2 casual or typo-tolerant prompts.
5. At least 1 prompt that describes the workflow without naming the skill.

## Manual Review Questions

For each query, ask:

1. Would a normal user actually write this?
2. Is it specific enough that a skill would help?
3. Does the expected trigger label match the skill description, not just keywords?
4. If it is negative, which neighboring skill should win instead?
5. If no skill should trigger, is that explicit in the prompt?

## Boundary Matrix

For JS reverse skills, keep these boundaries covered:

1. Browser hook snippet vs entry tracing.
2. Entry tracing vs Node.js env patching.
3. Env patching vs AST deobfuscation.
4. AST deobfuscation vs browser runtime debugging.
5. Skill creation/optimization vs using a domain skill.

## Full Quantitative Loop

When the needed CLI is available and the user wants measured trigger accuracy, switch to `references/description-optimization.md` and run `scripts/run_loop.py`.
