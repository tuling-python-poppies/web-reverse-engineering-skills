# Case Writeback Mode

Case writeback turns a verified web-protocol-recovery project into a small, sanitized, reusable case. It is a web-protocol-recovery governance mode, not an implementation provider and not an automatic consequence of project write permission.

## Eligibility

Offer writeback only when the final acceptance test passed, the stable entry runs, evidence provenance is known, and at least one fixed vector, repeated live proof, or semantic business success proves the implementation. Python code must compile and must not perform network traffic or create files on import. Unresolved guesses, one lucky response, browser-backed final delivery, and duplicate one-off debugging sessions are not eligible.

## Completion Prompt

After an eligible task, web-protocol-recovery presents a read-only candidate summary with proposed `caseId`, family, reusable pattern, implementation mode/strategy/profile, source stage, required current Provider chain, verification, files, minimal frozen assets, excluded sensitive material, and whether this is a new case or an update. Ask whether to write back. A positive answer authorizes candidate preparation only.

Before writing, show the exact allowlist and sanitized asset list and obtain a second explicit confirmation. Then create a change-control snapshot for only those paths.

## Case Layout

```text
references/cases/<runtime>/<case-id>/
  case.json
  PROCESS.md
  entry.py               # implementation case; .js/.mjs/.cjs/.wasm also allowed
  pull_live_state.py     # case-scoped selector backed by the shared parser
  fixtures/
    vectors.json         # optional deterministic/redacted vectors
    request.sample.json  # optional redacted shape
    response.sample.json # optional redacted shape
  assets/                # optional minimal public frozen JS/HTML/images
  tests/
    test_vectors.py      # optional offline test
```

Runtime directories are `iv8`, `pure-python`, and `python-node`. Families remain `signer`, `challenge`, `verifier`, `decode`, `session`, and `transport`; they describe the protocol gate and remain manifest metadata rather than directory owners. Miniapp is recorded as a platform/runtime tag, never as a gate family.

## Metadata

Every `case.json` uses `web-protocol-recovery-case` and records a stable lowercase `caseId`, revision, status, family, runtime, `caseKind`, protocol patterns, vendor/product/version/subtype, optional structured `exactScopes`, positive and negative match signals, minimum independent signals, verification class, dependencies, `secretPolicy=redacted-pull-live`, and structured Provider provenance. Implementation cases declare `implementation.mode` as `iv8`, `python-node`, or `pure-python`, with optional `strategy` or `profile`. Evidence cases set `implementation: null`. `sourceStage`, `historicalProviderChain`, and `requiredCurrentProviderChain` are arrays/objects of Provider stages with `provider`, `role`, and optional `purpose`, `strategy`, or `profile`; do not write old string provider-chain fields. `artifacts.process`, optional `artifacts.entry`, `artifacts.pullLiveState`, and every supplemental asset are `{path, sha256}` objects. Process is exactly `PROCESS.md`; an implementation entry is executable rather than fixture/test/evidence; an evidence case must not invent an entry. Every file under the case directory is declared and hash-bound, except the tool-residue exemptions `.pytest_cache/` and `__pycache__/` directories and the `.DS_Store` and `Thumbs.db` files, which `scripts/verify_case_hashes.py` ignores and which must never be declared or hash-bound.

A `freshly-verified` case binds distinct `verification.testArtifact` executable code and JSON `verification.evidenceArtifact` to matching declared assets; the test command names the test artifact, while evidence records `passed=true` and `executed=true`. When `verification.proof.activeScope=offline-only`, the proof also binds the current entry and test hashes. Any preserved live summary must be explicitly classified as historical provenance with `currentAcceptance=false`; it cannot serve as the active evidence artifact. A `historical-user-attested` case records provenance and `requiresFreshVerification=true`; it is selectable template evidence but never current-target proof. `python scripts/verify_case_hashes.py` enforces these verificationClass contracts offline.

An evidence case may declare `historicalReferences` only for a file already listed in `references/case-live-reference-archive/MANIFEST.json`. Copy the manifest path, archive path, SHA-256, byte size, full source commit, and `readPolicy=study-only` exactly. Historical dependencies belong under `historicalDependencies`; they are descriptive and must not be installed during case reuse. Archive code is immutable provenance: never import or execute it, add it as `artifacts.entry`, copy it into delivery, or promote an old live result to current acceptance. The archive verifier checks each byte against the exact Git source blob and requires an explicit manifest review for every detected non-empty sensitive literal.

`registry.json` is the machine-readable source of truth. Future tasks read only the registry first and select only `status=verified` rows, then honor `verificationClass` + `selectableAs` (`proof` for freshly-verified, `template` for historical-user-attested). A site case requires one matching `exactScopes` object (`scheme`, canonical host, explicit port, absolute route prefix) or at least two independent high-confidence signals. Alias signals such as `alias:*` normalize historical naming and do not count as independent high-confidence signals. A generic parameter name, `_0x`, `412`, or one SDK string never selects a case alone. When two verified cases share an exact scope or both satisfy the minimum signal set, registry order is not a tiebreaker; case reuse must stop until runtime, algorithm, product subtype, or negative-signal evidence selects exactly one case.

Hash cascade is mandatory after any hash-bound edit: recompute SHA-256 of the changed target file, update the corresponding `case.json` field (`artifacts.process` / `entry` / `pullLiveState` / `assets[]` / `preRead[]` / `verification.testArtifact` / `verification.evidenceArtifact`), then recompute that `case.json` and update `registry.json` `manifest.sha256` plus keep registry `verificationClass`/`selectableAs` aligned with the case. Shared `preRead` targets require every referencing case to be updated. Before commit, run `python scripts/verify_case_hashes.py` from the skill root and require exit 0; it must also reject undeclared case files, unregistered `case.json` files, absolute or escaping declared paths, and verificationClass contract failures.

Any commit that changes a hash-bound case file, a `minimumIndependentSignals` threshold, `exactScopes`, `negativeSignals`, or case-selection semantics must carry a commit body stating what changed, why, and the verification result (for example the `verify_case_hashes.py` and `preflight.py --strict` outcome). A one-line subject alone is not enough for these high-impact edits, because the threshold or hash change is otherwise invisible in the log. In a Git worktree, `scripts/preflight.py` enforces this for HEAD commits that touch hash-bound case files or registry threshold/scope/exclusion keys.

Historical note: commit `5b37aef` mixed provider-tree migration with the first case schema cascade and used a subject-only message. That history is retained without rewrite; new high-impact case commits must still carry a body, and acceptance is judged on current HEAD plus preflight rather than rewriting that commit.

Historical user attestation does not replace fresh current-target acceptance and never authorizes embedded live requests, dependencies, verifier submission, account state, or raw persistence. New work must use `freshly-verified`; restored historical manifests are read-only except for credential removal, path migration, or integrity repairs explicitly approved by the user. A migration that changes an active case's kind, entry boundary, verification classification, or historical reference must increment `revision`, refresh `verification.metadataMigratedAt`, and rebuild the registry hash cascade even when no test was executed.

## PROCESS.md

Record the goal and success predicate, match and exclusion signals, reconnaissance choice, request/state chain, canonical mutation point, false leads, provider order, minimal implementation, fixed-vector/live proof, dependencies, invalidation signals, and sensitive materials intentionally excluded.

## Sanitization

Never write back `js_reverse_cache/private/`, cookie/token values, Authorization, sessions, personal identifiers, full browser state, HAR files, complete private responses, or one-time telemetry. Preserve names, shapes, provenance, and field placement. When current state is necessary, declare its names in `liveState`, obtain it from one approved browser session at reproduction time, select it through `pull_live_state.py`, keep it in memory, and do not persist it. Prefer synthetic inputs and expected hashes. Bundle only minimal public assets required for offline verification, with source, capture time, and SHA-256. Case code must contain no local absolute paths and no live traffic on import.

## Update Rules

Update an existing case only when vendor, product generation, protocol family, and subtype still match. Increment revision and verification time. Apply the hash cascade above for every touched process/entry/asset/preRead/verification.* /manifest. A changed product generation, verifier subtype, incompatible wire shape, or different state model creates a new case. Mark obsolete cases `stale` or `deprecated`; do not silently rewrite their identity.

Promote a lesson into generic web-protocol-recovery methodology only when it applies across sites and the user separately approves that methodology path. Default writeback changes only the case directory and registry.

## Commit Hygiene

1. Prefer a **case-only commit** for `references/cases/**` + `registry.json` hash cascade. Do not mix darwin score rows (`skills/darwin-skill/results.tsv`) into the same commit when avoidable.
2. Prefer a **methodology-only commit** for SKILL/layout/anti-pattern/scaffold changes.
3. Prefer a **chore commit** for `.gitattributes`, score TSV, and pure formatting.
4. After case edits, run from skill root: `python scripts/preflight.py` (hashes + all discovered case unittests + `scripts/test_preflight.py` + entry discipline scan). `--skip-tests` skips only discovered case unittests; it still runs `scripts/test_preflight.py` and fails closed if that file is missing. Default ignores warnings; `python scripts/preflight.py --strict` fails on WARN and LEGACY_WARN. LEGACY_WARN is derived from `verificationClass=historical-user-attested`, not a hardcoded path list. Entry scan covers import head **and** AST module-level side effects (`with`, `requests.*` aliases/`from requests import`, `curl_cffi.requests`, `_iv8()`/`JSContext`, `mkdir`, unguarded side-effect helpers); keep live work under `main()` / `if __name__ == "__main__"`.
