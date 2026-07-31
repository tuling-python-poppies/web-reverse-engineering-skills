# Recovery Acceptance Status

This file records the current standing of recovery-success evaluation. Trigger
selection is not the same as protocol recovery success.

## Current Standing

| Surface | Status | Evidence |
|---|---|---|
| Trigger routing | Bounded-recovery accepted; first-pass stability not accepted | 22 query aggregates and 66/66 final attempts after declared retries; first pass was 54/66, with 54/60 semantic correctness and 6/66 runtime errors |
| Offline implementation cases | Current local proof only | `preflight.py --strict` runs the four checked case unit-test suites |
| Historical cases | Template/process evidence only | 18 `historical-user-attested` case manifests require fresh target proof |
| Live current-target recovery | Not claimed | No authorized live target, current cookies/tokens, request budget, or business success predicate is present in this repo |

## Offline Audit Notes

- `selectableAs=proof` means freshly-verified offline artifact proof from current
  checked-in vectors/tests. It does not mean live-current target acceptance.
- Four migrated python-node historical cases carry a structured
  `sourceReference=95be929~1` with
  `sourceReferenceResolution.status=unresolvable-in-current-repository`. The
  verifier rejects treating that reference as a full commit or current proof.
- Provider manuals and playbooks are structurally checked by markdown, route,
  schema, line-ending, and live-egress scans; their domain rules still require
  authorized target evidence before live success can be claimed.

## Requirements For Live Recovery Acceptance

To convert live recovery from `not claimed` to accepted, a future run must provide
all of the following in a task project, not in the installed skill directory:

1. Explicit authorization, exact host/route scope, and request budget.
2. Current request/response/cookie/token/challenge evidence for the target.
3. Fixed vectors or replay samples binding local artifact output to captured wire
   bytes.
4. A semantic business success predicate, not only HTTP 200 or non-empty output.
5. Redacted artifacts and hashes that can be verified without persisted secrets.
