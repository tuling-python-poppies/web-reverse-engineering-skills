# Web Protocol Recovery Case Registry

`registry.json` is the only selector. Read it first, select one `status=verified` entry, verify its manifest hash, then load the declared `case.json`. Each registry row also carries:

- `verificationClass`: `freshly-verified` or `historical-user-attested` (must match the case manifest)
- `selectableAs`: `proof` (freshly-verified current-target proof after offline vectors) or `template` (historical shape/process evidence only)

If multiple verified entries match the same exact scope or minimum signal set, stop and require a discriminator (runtime, algorithm, product subtype, or negative signal) instead of choosing by registry order. The manifest is the complete source of metadata and hash-binds every file in that case directory.

Cases are grouped by implementation runtime:

- `iv8/`: Python owns live egress while iv8 executes the browser-dependent artifact generator.
- `pure-python/`: Python-only protocol or algorithm implementations.
- `python-node/`: Python owns live egress while Node.js/jsdom constructs protocol artifacts. Restored documents without a standalone verified helper use `caseKind=evidence` and do not pretend to provide an implementation entry.

All cases use `web-protocol-recovery-case`. Historical restorations use `verificationClass=historical-user-attested`, `caseKind=evidence` where no executable implementation is claimed, and always require fresh target verification. New writeback uses `verificationClass=freshly-verified`, `caseKind=implementation`, structured `implementation`, `sourceStage`, `historicalProviderChain`, and `requiredCurrentProviderChain` fields, with executable tests and JSON evidence artifacts when applicable.

Every case uses `secretPolicy=redacted-pull-live`: retain cookie/token names, shapes, provenance, and transport positions, but never persisted values. When current state is required, web-protocol-recovery obtains it from one explicitly authorized browser session, runs the case's `pull_live_state.py`, passes the selected JSON in memory, and does not write it back to the case library.
