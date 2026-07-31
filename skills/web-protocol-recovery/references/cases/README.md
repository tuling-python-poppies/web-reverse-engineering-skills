# Web Protocol Recovery Case Registry

`registry.json` is the only selector. Read it first, select one `status=verified` entry, verify its manifest hash, then load the declared `case.json`. Each registry row also carries:

- `verificationClass`: `freshly-verified` or `historical-user-attested` (must match the case manifest)
- `selectableAs`: `proof` (freshly-verified offline artifact proof from current checked-in vectors/tests, not live-current target acceptance) or `template` (historical shape/process evidence only)

If a row declares `match.requiredSignalGroups`, non-scope selection must match at least one observed signal from every disjoint group in addition to the minimum signal count. If multiple verified entries match the same exact scope or minimum signal set, stop and require a discriminator (runtime, algorithm, product subtype, or negative signal) instead of choosing by registry order. The manifest is the complete source of metadata and hash-binds every file in that case directory.

Cases are grouped by the runtime needed to reproduce or rebuild the protocol artifact:

- `iv8/`: Active implementation cases expose offline iv8 artifact generation only; task-project Python owns any freshly authorized live egress. Evidence cases may describe an iv8 reconstruction without shipping an active entry.
- `pure-python/`: Python-only protocol or algorithm implementations.
- `python-node/`: Python owns live egress while Node.js/jsdom constructs protocol artifacts. Restored documents without a standalone verified helper use `caseKind=evidence` and do not pretend to provide an implementation entry.

All cases use `web-protocol-recovery-case`. Historical restorations use `verificationClass=historical-user-attested`, `caseKind=evidence` where no executable implementation is claimed, and always require fresh target verification. New writeback uses `verificationClass=freshly-verified`, `caseKind=implementation`, structured `implementation`, `sourceStage`, `historicalProviderChain`, and `requiredCurrentProviderChain` fields, with executable tests and JSON evidence artifacts when applicable.

Some cases declare `historicalReferences` into `../case-live-reference-archive/MANIFEST.json`. These hash-bound files preserve implementation provenance from an exact Git commit. They may be opened one at a time only after the selected active case identifies a concrete blocker; they are study-only and must never be imported, executed, installed from, copied into delivery, or accepted as current live proof.

`verification.sourceCommit` always means a resolvable full 40-character commit id. If retained provenance text cannot resolve in this repository, record it as `sourceReference` plus `sourceReferenceResolution.status=unresolvable-in-current-repository`; it remains descriptive evidence and cannot satisfy current proof or writeback eligibility.

Every case uses `secretPolicy=redacted-pull-live`: retain cookie/token names, shapes, provenance, and transport positions, but never persisted values. When current state is required, web-protocol-recovery obtains it from one explicitly authorized browser session, runs the case's `pull_live_state.py`, passes the selected JSON in memory, and does not write it back to the case library.
