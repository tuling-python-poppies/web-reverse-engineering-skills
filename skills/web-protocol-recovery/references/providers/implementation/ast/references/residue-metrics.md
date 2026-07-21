# Residue Metrics

Use this reference after an AST output parses successfully and the next blocker is deciding which visitor or instrumentation step should come next. Metrics are direction signals, not semantic proof.

## Tools

The directory template contains two optional tools:

1. `../scripts/template-project/src/tools/collect-residue-metrics.js`
2. `../scripts/template-project/src/tools/compare-with-reference.js`

Copy `../scripts/template-project/` into the task cache, install dependencies there, and run the tools only on task-owned files.

## collect-residue-metrics

```bash
node src/tools/collect-residue-metrics.js output.js metrics.json
```

It counts common residual structures:

```json
{
  "lineCount": 1200,
  "splitPipeCount": 3,
  "loopSwitchCount": 2,
  "opcodeIfChainCount": 16,
  "dispatcherWrapperCount": 8,
  "hexIdentifierCount": 140
}
```

Interpretation rules:

1. Stable `loopSwitchCount` or `opcodeIfChainCount` means control-flow visitor or instrumentation is likely the next step.
2. High `dispatcherWrapperCount` points to object merge or dispatcher inlining, subject to the aggressive-transform gate.
3. High `hexIdentifierCount` with already-readable structure usually means renaming should wait until last.
4. Fewer lines are not automatically better; parse stability and observable semantic equivalence outrank count reduction.

## compare-with-reference

```bash
node src/tools/compare-with-reference.js output.js reference.js compare.json case-id
```

Use it only when a reference output, earlier verified output, or human-cleaned target exists. Read `status`, `gaps`, and the `ours` versus `reference` metrics. A smaller gap does not prove semantic parity; it only helps choose the next pass.

## Safety Boundary

These tools parse, generate, and count AST structures. They do not execute target code. Treat them as low-risk analysis aids, then rely on reparsing, fixtures, fixed vectors, and Provider acceptance tests for proof.
