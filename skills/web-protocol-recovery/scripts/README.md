# scripts/ layout

Scripts are grouped by role. New scripts must be placed in the matching
category, never at the `scripts/` root.

## Categories

### tools/ — reverse-work diagnostics
Analysis helpers you or the agent run during a protocol task. Each is
offline, bounded, dependency-light, and carries `--self-test`.

- `check_reverse_env.py` — probe local node/curl/protoc/iv8/protobuf, etc.
- `crypto_fingerprint.py` — classify suspicious digest/alphabet output
- `protocol_diff.py` — compare two captured protocol samples
- `transcript_diff.py` — first structural diff between normalized chains
- `transform_trace_diff.py` — first divergence in runtime transform traces
- `transport_profile_diff.py` — validate/compare TLS/H2/connection profiles
- `grpc_frame_inspector.py` — bounded gRPC/grpc-web frame structure
- `protobuf_inspect.py` — schema-free protobuf wire decode (fallback)
- `wasm_module_inspect.py` — WASM section/import/export structure
- `evidence_normalizer.py` — normalize HAR/transcript into secret-free proof
- `practice_lab.py` — deterministic offline protocol controls

### gates/ — skill validation gates
Run when editing the skill, not during protocol tasks. `preflight.py`
orchestrates the rest.

- `preflight.py` — top-level gate orchestrator
- `validate_architecture.py` — provider/route/read-plan/residue/EOL contracts
- `validate_schemas.py` — JSON Schema contract fixtures
- `validate_markdown.py` — local Markdown links and anchors
- `validate_evals.py` — route-regression and test-prompt fixture metadata
- `read_budget.py` — read-plan/read-budget accounting contract
- `verify_case_hashes.py` — hash-bound case + registry integrity
- `build_case_registry.py` — generate/verify the case registry projection
- `forward_test_report.py` — validate external fresh-agent forward-test reports

### tests/ — unit tests for the gates
- `test_preflight.py`, `test_architecture_contract.py`,
  `test_scaffold_project.py`, `test_line_endings.py`,
  `test_read_budget.py`, `test_validate_evals.py`

### providers/ — provider-scoped helpers
Helpers owned by one Provider live under its own subtree, e.g.
`providers/delivery/python-collector/scaffold_project.py`. Provider docs cite
these as `scripts/...` relative to that Provider's own directory.

## Rules for adding a script

1. Place it by role: a task diagnostic goes in `tools/`, a skill gate in
   `gates/`, a gate unit test in `tests/`, a Provider helper under
   `providers/`.
2. A script at the `scripts/` root is a placement defect.
3. `tools/*` diagnostics and gate-side diagnostics that must stay green carry
   `--self-test` and are registered in `gates/preflight.py`
   `DIAGNOSTIC_SELF_TESTS` using their full `scripts/<category>/<name>.py` path.
4. Scripts resolve the skill root with `Path(__file__).resolve().parents[2]`
   (root is two levels above `scripts/<category>/`).
5. Keep scripts offline and dependency-light; final live egress belongs to the
   `python-collector` delivery Provider.

## Enforcement (not just convention)

`gates/validate_architecture.py` (run by `gates/preflight.py`) fails closed when:

1. any `.py` file sits directly under `scripts/` (must be categorized), or
2. a `scripts/tools/*.py` exposing `--self-test` is missing from
   `gates/preflight.py` `DIAGNOSTIC_SELF_TESTS`.

So a scattered or unregistered script breaks preflight instead of drifting
silently. Tests: `tests/test_architecture_contract.py`
(`ScriptPlacementContractTests`).
