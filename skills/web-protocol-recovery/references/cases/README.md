# Web Protocol Recovery Case Registry

`registry.json` is the only selector. Read it first, select one `status=verified` entry, verify its manifest hash, then load the declared `case.json`. If multiple verified entries match the same exact scope or minimum signal set, stop and require a discriminator (runtime, algorithm, product subtype, or negative signal) instead of choosing by registry order. The manifest is the complete source of metadata and hash-binds every file in that case directory.

Cases are grouped by delivery runtime:

- `iv8/`: Python owns live egress while iv8 executes the browser-dependent artifact generator.
- `pure-python/`: Python-only protocol or algorithm implementations; currently reserved for future cases.
- `python-node/`: Python owns live egress while Node.js/jsdom constructs protocol artifacts. Restored documents without a standalone verified helper use `caseKind=evidence` and do not pretend to provide an implementation entry.

All cases use `web-protocol-recovery-case/v1`. Historical restorations use `verificationClass=historical-user-attested` and always require fresh target verification. New writeback uses `verificationClass=freshly-verified` with executable test and JSON evidence artifacts.

Every case uses `secretPolicy=redacted-pull-live`: retain cookie/token names, shapes, provenance, and transport positions, but never persisted values. When current state is required, web-protocol-recovery obtains it from one explicitly authorized browser session, runs the case's `pull_live_state.py`, passes the selected JSON in memory, and does not write it back to the case library.
