# AST Provider

## Select When

- Relevant bundle/source region is identified and structural restoration is the goal.
- Readable or callable local JS is needed without owning network replay.

## Do Not Select When

- Network entry is still unknown (recon first).
- Only a single reversible hook is needed (browser-hooks).
- Final collector ownership (python-collector owns delivery), unless structural recovery is a proved intermediate blocker in a sequential AST -> runtime/collector chain.

Use this provider for bounded whole-file or source-region structural restoration after web-protocol-recovery identifies the relevant bundle. It does not locate network entry points and does not own request replay.

Architecture boundary: web-protocol-recovery owns route choice, `projectRoot`, layout, acceptance, and final delivery. This provider only transforms assigned source into assigned cache/callable artifacts under `web-protocol-recovery-simple`, then returns hashes, proof, and unresolved blockers.

## Inputs And Outputs

Require a local source path/hash, target family evidence, desired readable or callable output, approved AST cache paths, and a semantic acceptance test. Preserve the original source. Write intermediate products only under `js_reverse_cache/ast/`; promote a callable verified result only to an explicitly assigned `main.js` or `utils/*.js` path.

Copy `scripts/template-project/` and the two AST scripts into the work order's `js_reverse_cache/ast/` path before use; never run them in the installed skill tree. `src/plugins/` owns family routing and `src/visitors/` one transform each. For a fast first pass, `scripts/decode_action_scaffold.js` is a single-file quick-start that runs `parse -> transform -> generate` with the bundled low-risk visitors and initial family plugins; copy it into the task cache before running. `scripts/string_table_recover.js` is a Babel-backed pass for obfuscator.io and jsjiami.v6/v7 string tables: it proves the array/decoder/rotation surfaces with scope-aware AST analysis, executes the extracted surface in a bounded worker only under explicit `--execute-target-code --trusted` flags, resolves aliases by binding identity, protects rotation/bootstrap code from rewriting, and rewrites only proved call sites; it ships a `--self-test` plus a regression file. Copy it into the task cache beside the pinned Babel dependencies before running; the same execution gate as bootstrap execution applies. Bundles may contain multiple independent tables; the default is fail-closed, then rerun with the reviewed pair explicitly selected, for example `--decoder Ki --array Ui`. The tool recognizes both `index = index - offset` and `index -= offset` forms.

Conservative normalization runs by default. Aggressive transforms — generic object merging (`merge-object`), dispatcher inlining (`inline-dispatcher`), while-switch unfolding (`while-switch-unpack`), and `awsc` block flattening — are bundled but gated behind the `--aggressive` flag because they cannot preserve semantics across arbitrary input. Enable `--aggressive` only in the task cache with negative fixtures and observable equivalence checks; keep intermediate products and reparse after each pass. Bootstrap execution requires both source review and explicit trust approval (`--execute-bootstrap --trusted-bootstrap`). Parsing and residue reduction are not semantic proof.

## Methodology References

Read at most one after a proved blocker, per the read budget:

- `references/decode-action-pipelines.md`: family detection order (obfuscator/sojson/awsc/common) and per-family pass pipelines behind the scaffold.
- `references/control-flow-patterns.md`: control-flow-flattening, dispatcher, and while-switch structural recovery patterns for the aggressive task-cache rewrites.
- `references/instrumentation-patterns.md`: when static rewriting must stop and switch to AST-level instrumentation for runtime-state-driven state machines.
- `references/template-usage.md`: when to use the single-file scaffold versus the directory template, and how to keep readable output separate from callable output.
- `references/residue-metrics.md`: how to interpret the bundled residue metric tools without treating lower counts as semantic proof.

Return input/output hashes, passes used, parse/reparse result, residue metrics, semantic fixture result, unresolved constructs, and whether output is readable-only or callable.
