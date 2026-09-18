# Template Usage

Use this reference when the AST work order has already selected the AST Provider and the current blocker is which bundled template to copy into the task cache. It is not a new route; `PROVIDER.md` remains the entry point.

## Delivery Modes

Choose the output mode before changing transforms:

1. **Readable output**: optimize for human analysis. Do not add `require`, `module.exports`, or callable wrappers by default. Prefer string recovery, low-risk normalization, deterministic aliases, and manual ordering of critical entries.
2. **Callable output**: optimize for local execution or integration. Add exports, wrappers, and entry calls only when the work order explicitly asks for a callable helper and provides a semantic acceptance test.

Do not mix the two modes in one artifact. A readable file can feed a later callable helper, but it is not itself replay proof.

## Choose The Template

Use Provider-local `../scripts/decode_action_scaffold.js` for a fast first pass when:

1. the sample is new and the family is still uncertain;
2. the user wants quick readable output before deeper custom passes;
3. one low-risk `parse -> transform -> generate` loop is enough to decide the next family.

Use Provider-local `../scripts/template-project/` when:

1. a second or later target-specific visitor is needed;
2. family logic and visitors must be maintained separately;
3. sojson, obfuscator, awsc, and common behavior need independent regression fixtures;
4. residue metrics or reference comparisons are part of the acceptance test.

Use Provider-local `../scripts/string_table_recover.js` with the pinned Babel dependencies when:

1. the bundle is a string-table family (obfuscator.io, jsjiami.v6/v7) and the first goal is a decoded string dump plus a call-site rewrite;
2. the structural plugins would select `common` or cannot recover the strings themselves;
3. execution of the extracted decoder and rotation surfaces is approved (`--execute-target-code --trusted`).

Copy either template into the work order's approved `js_reverse_cache/ast/` path before use. Never run or edit the installed skill tree.

## First Pass

For the single-file scaffold after copying it into the task cache:

```bash
node js_reverse_cache/ast/decode_action_scaffold.js -i js_reverse_cache/source/original.js -o js_reverse_cache/ast/output.readable.js
```

For the directory template after copying it into the task cache:

```bash
cd js_reverse_cache/ast/template-project
npm install
npm run decode
```

For the string-table pass after copying it into the task cache:

```bash
node js_reverse_cache/ast/string_table_recover.js -i js_reverse_cache/source/original.js -o js_reverse_cache/ast/strings.recovered.js --dump js_reverse_cache/ast/string-table.json --execute-target-code --trusted
```

The copied script must resolve its pinned `@babel/parser`, `@babel/traverse`, and `@babel/types` from the task project's `node_modules` (keep the script under that project or set the task-local Node module path). If inspection reports multiple decoder/array pairs, review the candidates and select the exact pair explicitly, for example `--decoder Ki --array Ui`; do not choose by name alone.

The first output should record the selected family/plugin and whether the result is readable-only or callable. The input and output paths must differ, and generated files must not overwrite the original source. When the selected plugin is `common` while the source still holds a large string table, treat it as a family miss, not as proof that the file is unobfuscated: run the string-table recovery flow in the skill-root `references/obfuscation-guide.md` before other passes.

## Continue Safely

1. Reparse after every generated output.
2. Keep intermediate files for each aggressive pass.
3. Add one visitor family at a time so failures can be attributed.
4. Use negative fixtures before enabling object merging, dispatcher inlining, while-switch unfolding, or awsc block flattening.
5. Stop static recovery and switch to instrumentation when state, VM dispatch, or runtime values control the remaining structure.

## Family Notes

1. `sojson` and `sojsonv7`: identify string array, bootstrap, and decrypt function; execute only the minimal trusted bootstrap when the work order approves it; replace only confirmed decrypt calls/member reads. jsjiami.v7 aliases one decoder under many local names and builds its rotation method names at runtime; the bundled plugin replaces only one name and its sandbox excludes the array function and rotation, so recover the string table first and never read a silent zero-replacement as "nothing to do".
2. `obfuscator`: recover the string table first (array + decoder + rotation + alias closure); then add dispatcher object handling, order table recognition, and loop tail cleanup before broad readability changes.
3. `awsc`: normalize expression-level control flow first, then handle nested blocks and sequence expressions under aggressive gating.
4. `common`: keep low-risk literal cleanup, member normalization, string merging, and conservative dead-code cleanup.

## Boundaries

Do not:

1. execute the whole mixed business bundle as a shortcut;
2. auto-inline complex dispatcher functions with `this`, `arguments`, closure reads, or assignment side effects;
3. force VM/VMP state machines into static output when runtime state controls dispatch;
4. convert readable output into callable output without an explicit callable acceptance test.
