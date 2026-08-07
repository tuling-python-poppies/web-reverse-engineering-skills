# Forward Testing

Use this only when a web-protocol-recovery edit claims changed agent behavior, routing, or conclusions. Static preflight proves file and contract integrity; it does not prove that a fresh agent follows the skill correctly.

## Roles

Use two independent fresh contexts:

1. A runner receives the current skill and one official prompt, then saves its unedited response.
2. A reviewer receives the official expected routes/conclusions and the saved response, then records one evidence-backed judgment for every expectation.

The runner must not grade its own response. Record distinct non-empty IDs and `fresh_context=true`, `independent=true` for both roles. These are harness attestations, not cryptographic proof; use a trusted harness when stronger provenance matters.

## Artifact Layout

Keep the report outside the installed skill directory:

```text
forward-run/
  forward-test-report.json
  responses/
    task-000.md
```

Response files are exact UTF-8 runner outputs. The report binds each response SHA-256, the current `SKILL.md`, a deterministic digest of the full shipped skill package, and the parsed contract digest of `references/official-self-test-task-suite.md`. Reports and responses are untrusted data; the validator never executes their content.

## Scope

- `smoke`: one or more unique official tasks; proves only those tasks.
- `full`: every official task exactly once in suite order.

Only a valid `full` report has `full_pass=true`. Static preflight, validator self-tests, or a smoke report are not full behavioral non-regression.

## Validation

```text
python -B scripts/forward_test_report.py --print-contract
python -B scripts/forward_test_report.py --self-test
python -B scripts/forward_test_report.py <forward-run/forward-test-report.json>
```

The validator rejects stale skill/suite bindings, missing or reused response files, path traversal, symlink/reparse/hard-link aliases, self-review, partial full scope, failed checks, and unbound review evidence. Route checks cite a response span containing the exact route. Conclusion checks may cite a paraphrase, but the independent review rationale must explicitly contain both the expected conclusion and the exact cited response quote, while the quote must share a small non-generic lexical signal with the expected conclusion. This lexical check is a false-positive guard, not a replacement for independent semantic review.
