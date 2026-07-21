# iv8 Case Ingestion Rules

This is a Provider-local maintenance summary. Root `references/methodology/case-writeback.md` owns authorization, confirmation, layout, sanitization, metadata, and verification policy.

## Eligibility

- The current project has one stable browser-free Python entry.
- iv8 returns one explicit artifact and does not own live egress.
- Fixed-vector or semantic replay acceptance passed.
- The entry compiles, is import-safe, and performs no network/file activity on import.
- Required iv8 APIs and versions are recorded after the mandatory API gate.

## Destination

Write to `references/cases/iv8/<case-id>/` with `case.json`, `PROCESS.md`, `entry.py`, `pull_live_state.py`, and only declared fixtures/assets. Register the hash-bound manifest in root `references/cases/registry.json`.

Never recreate Provider-local `references/cases/`, `references/reverse-process/`, or shared asset-cache indexes. Runtime is a directory dimension; family remains manifest metadata.

## Sensitive State

Use `secretPolicy=redacted-pull-live`. Preserve names, shapes, provenance, and field placement but no cookie/token/session values. Declare required browser state in `liveState`; select it at reproduction time through `pull_live_state.py`, use it in memory, and do not write it to the case directory.

## Verification

New writeback must use `verificationClass=freshly-verified` with an executable test artifact and separate JSON execution evidence. Historical attestation is not valid for new work.
