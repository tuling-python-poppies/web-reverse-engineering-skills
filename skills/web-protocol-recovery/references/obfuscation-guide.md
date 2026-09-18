# Obfuscation Guide

Use this file when the page ships packed, flattened, or string-table-heavy JavaScript.

## Recognition signals

- giant string arrays, or an array-builder function that reassigns itself after the first call
- rotate-then-decode string tables: array definition + decoder + rotation/init IIFE
- two-argument decoder calls such as `decoder(850, "V5]P")` with a per-call key
- one decoder aliased under many local names (`var a = decoder`, `var b = decoder`, ...)
- `eval`, `Function`, or self-redefining wrappers
- control-flow flattening
- numeric array dispatch
- tiny side assets controlling the real logic

## Working order

1. search for the real API path first
2. search for transport wrappers before unpacking everything
3. extract only the smallest logic slice needed for the current request
4. save a clean snapshot before each major edit
5. move offline early when anti-debug noise is high

## String-table recovery (verified on real obfuscator.io and jsjiami.v7 bundles)

1. Save the raw source bytes first and work from a copy.
2. Locate three surfaces: the string-array definition, the decoder function, and the rotation/init IIFE. Extract them with quote-aware balanced scanning: decoder keys can contain `)` and `]` (for example `"C)"` and `")La4"`), so naive brace matching over-counts and truncates.
3. Run the three surfaces verbatim in a local Node `vm` sandbox before decoding anything. The rotation IIFE mutates array order; decoding before rotation returned garbage for every call site in both observed families. Executing target code still follows the work order's `executionPolicy` gate, and only these three surfaces belong in the sandbox - never the whole business bundle.
4. Do not hunt for rotation by tokens alone. obfuscator.io uses `array.push(array.shift())` inside a `for(;[];)` loop; jsjiami.v7 composes method names at runtime (`"tfi"+"hs"` then a transform function) and calls `array["un"+name]` / `array[name]`. If a `.push(`/`.shift()` scan finds nothing, find the IIFE that calls the array function inside a checksum loop and execute it as-is.
5. Enumerate every call site and resolve the decoder alias closure: follow assignments of the decoder name through intermediate names before rewriting. One observed bundle aliased a single decoder 42 times across 823 call sites; replacing only the canonical name leaves nearly every call encoded.
6. Evaluate the decoder per call site with the exact literal arguments from that site. Two-argument decoders use a per-call key, so there is no single key that dumps the whole table. The decoder subtracts an internal index offset, so dump the call-site literal, not the internal index.
7. Apply the dump: replace `alias(index[, key])` with the decoded literal, then reparse or run `node --check`. Do not beautify before the first useful rewrite pass.
8. Check family markers before choosing a pipeline: `var _0xodf="jsjiami.com.v7"` (jsjiami; the marker is also string-array element 0 and the decoder cache-key salt) versus no marker plus `for(;[];)` and self-defending strings such as `while (true) {}` or `(((.+)+)+)` (obfuscator.io).
9. Prefer the AST provider's Babel-backed `string_table_recover.js` (under `references/providers/protocol-recovery/ast/scripts/`, copied with the pinned AST dependencies into the task cache before use) to automate steps 2-7: it proves surfaces and aliases by scope, including nested IIFEs and compound index offsets such as `index -= 392`; replays the rotation in a bounded worker; protects rotation/bootstrap code and eval/string payloads; and reports parse status. It executes target code only under explicit `--execute-target-code --trusted` flags and ships a `--self-test` plus regression fixture. A bundle can contain multiple independent tables; fail closed, review the reported candidates, then select the exact pair with `--decoder NAME --array NAME` (for example `--decoder Ki --array Ui`). Do not select by short name alone.

## Family routing

Do not trust a single signal. `_0x` identifiers, `setInterval` anti-debug, ternaries, `void 0`, and dispatcher-shaped objects all appear across families. Route on the string-table shape first: array + decoder + rotation + alias calls. A scaffold that reports its selected plugin as `common` while the file still holds a large string table means the family was missed, not that the file is unobfuscated. Provider-local family scoring and pass pipelines live in the AST provider's `references/decode-action-pipelines.md`.

## Common traps

- beautifying the whole bundle before finding the real request, except when a one-line file makes search unusable
- ignoring inline scripts and side assets
- losing original variable names that are useful for diffing
- decoding before replaying the rotation IIFE
- rewriting only the canonical decoder name instead of the full alias closure
- trusting brace or token scans that ignore quoted strings and runtime-composed method names

## Delivery rule

Only deobfuscate as much as the protocol replay requires.
