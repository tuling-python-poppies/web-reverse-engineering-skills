# Template Project Regression Fixtures

This directory is reserved for small local regression samples used while extending the Decode Action template project.

Keep fixtures small and focused. A fixture should exercise one visitor or one family route, not an entire production bundle.

Recommended fixture classes:

1. `directive-negative.js`: a leading sequence string that must not become a directive.
2. `empty-body-negative.js`: empty loop or branch bodies that must remain attached.
3. `sojson-shadow-negative.js`: a shadowed decrypt identifier that must not be replaced.
4. `literal-fold.js`: finite literal folding plus non-finite and negative-zero exclusions.
5. `state-machine-negative.js`: dynamic state mutation that must remain untouched.

When adding a new visitor:

1. Add or update the smallest fixture that demonstrates the pattern.
2. Compare original and transformed completion value, side-effect trace, selected globals, and thrown error.
3. Run `npm run test` and confirm the output still parses.
4. If the transform cannot pass a negative case, keep it outside the bundled pipeline.

Do not store large real-world target scripts here. Keep those in the assigned project under `js_reverse_cache/source/` or `js_reverse_cache/ast/`.
