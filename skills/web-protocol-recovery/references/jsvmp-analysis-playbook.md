# JSVMP Analysis Playbook

Use this file when the target wraps logic inside a custom VM or bytecode interpreter. It owns transferable JSVMP technique; concrete tool invocation belongs to the selected reconnaissance Provider and the connected MCP schema.

## Recognition signals

Structural markers of a JSVMP interpreter:

| Signal | Detail |
|---|---|
| File size | one 200KB+ file, often 500KB–2MB |
| Naming | meaningless single letters (`a`,`b`,`c`) or `_0x` prefixes |
| Large array | thousands of numeric elements (the bytecode program) |
| Dispatch loop | `while (true) { switch (opcode) { case 0: ... } }` |
| Stack ops | frequent `push` / `pop` / `shift` |
| API hijack | rewrites `XMLHttpRequest`, `fetch`, `document.cookie` |

Typical interpreter shape:

```javascript
var program = [3, 15, 7, 22, ...]; // bytecode
var stack = [];                     // operand stack
var ip = 0;                         // instruction pointer
function run() {
  while (true) {
    switch (program[ip++]) {
      case 0: stack.push(program[ip++]); break;   // PUSH
      case 1: { const a = stack.pop(), b = stack.pop(); stack.push(a + b); break; } // ADD
      // dozens to hundreds of cases
    }
  }
}
```

Core principle: **do not decompile the bytecode.** Bound the signature from both I/O ends plus middle-layer observation, and prefer executing the VM over recovering it.

## Interpreter shape appendix

Use this appendix only to **recognise and locate** the interpreter, not to devirtualise it. Recognition and export location are cheap; full opcode recovery is not, and it is rarely on the shortest path to the artifact.

### Entry and constant mapping

```javascript
// IIFE entry with single-letter constants standing in for numbers
!function () {
  var U = void 0, y = parseInt, E0 = Function, AN = Uint8Array;
  var E = 15, l = 10, m = 12, x = 16, S = 13, $ = 11; // number->name aliases
}
```

- Grep the first ~2KB for `var <name>=<number>` pairs; these alias numeric opcodes/table indexes behind letters.
- A large numeric array elsewhere in the file is the bytecode program, not data.

### Dispatch loop

```javascript
function DG(C, d) {
  for (d[7] = x; d[7] !== U;) {
    var op  = d[7] & 31;        // low 5 bits  = opcode
    var sub = d[7] >> 5 & 31;   // next 5 bits = sub-operation
    switch (op) {
      case 0: d[7] = 612; break;      // BRANCH
      case 1: /* W(C[Y], null, ...) */ break; // CALL
      // dozens to hundreds of cases
    }
  }
}
```

### Opcode bit-encoding

A common 32-bit instruction packs three fields:

```
bit 0-4    opcode          (op  = word & 31)
bit 5-9    sub-operation   (sub = word >> 5 & 31)
bit 10-31  operand/immediate (word >> 10)
```

Extract the **current** interpreter's shift/mask from its own dispatch line. Never copy PC, stack, opcode, or accumulator indexes from another version or another site; they drift per build.

### Constant table

- Calls route through an indexed table such as `C[9][idx]`: strings, function indexes, and parameter descriptors all live behind one index space.
- `W = Function.prototype.call.bind(call)` style shims mean every builtin call looks like `W(C[idx], null, ...)`.
- Enumerate distinct `C[9][n]` indexes and read ~50 chars of context per index to label string vs function-index vs descriptor.

### Opcode classification hints

| Class | Body markers |
|---|---|
| BRANCH | rewrites the PC word (`d[7]=...`), or `d[7]=cond?a:b` |
| CALL | `W(C[idx], null, ...)`, `.apply` / `.call` |
| ARITH | `d[a]=d[b]-d[c]`, comparisons, bit ops |
| STORE | `P[d[i]]=...`, `d[a][C[k]]=d[b]`, `in` checks |
| ALLOC | `d[i]=[]`, local var declaration, arg-frame setup |
| STRING | `new fh(...)` regex, `+` concat, `join('')` finalisation |
| RETURN | `return ...`, `throw ...` |
| EXCEPTION | `try {...} catch (...) {}` around a state transition |

### Export location

The exported signer name is usually absent from the source because it is encoded in the table. Find it through the registration path, not by text search:

1. Locate the module registration call (a `register(name, module, factory)` shape).
2. Follow the factory's returned object to the exposed method.
3. That method dispatches into the interpreter via `W(C[funcIdx], null, ...)`.

Once the export is located, prefer executing it for one artifact (`route: python-node` wasm/vm sidecar or `route: iv8`) over reconstructing the opcode table. Final live egress stays browser-free and Python-owned.

## Pre-classification: which anti-bot type

Observe the redirect/status behaviour before any hook, then branch:

- repeated `412`/challenge before `200` → **signature-type JSVMP** (Ruishu/Akamai family): the four techniques below apply, but I/O hooks may disturb the challenge — prefer source-level instrumentation first.
- direct `200` but the business request carries a signature parameter → **behaviour-type JSVMP**: standard four-technique flow.
- direct `200`, no signature parameter → likely not JSVMP; return to ordinary obfuscation analysis.

## Four-technique methodology

Recover the signature by combining, not by full devirtualization. Each technique is a generic capability; the selected Provider maps it to concrete tools.

1. **Hook the I/O boundary.** Ignore VM internals; capture only what enters and what leaves. Intercept request egress (XHR/fetch), cookie writes, and crypto primitives (`btoa`/`atob`/hash/HMAC), plus `String.fromCharCode` (high-frequency in JSVMP string building). Extract: signature parameter name, value shape (length/charset/encoding), and its wire position (query/body/header/cookie).
2. **Instrument the interpreter.** When I/O alone cannot be correlated (e.g. a self-implemented MD5), trace the dispatch function coarse→medium→fine: dispatcher-level call trace → hot sub-functions → string primitives (`charAt`/`charCodeAt`/`substring`/`concat`/`join`). `join('')` is often the final concatenation point. For accumulator-based challenge formulas, add bounded arithmetic-handler traces and correlate them with seed, timestamp, and wire-body checkpoints.
3. **Analyse the logs.** From hundreds of trace records, isolate the signature chain by keyword (signature prefix), time window (1–2s before the request), type (string args over numeric VM scheduling), length (>8 chars), and cross-request variance. Use **reverse-tracing** (from the signature value back to its input plaintext, hop by hop) and **multi-request diffing** (fixed factors = keys, changing factors = timestamp/nonce/business params).
4. **Source-level instrumentation.** For self-contained VMs (Ruishu 5/6, Akamai sensor_data, webmssdk, obfuscator.io) where the algorithm lives entirely inside `switch/case`, rewrite the VMP source at the transport layer to tap every `obj[key]` read and `fn(args)` call, exposing the hottest environment keys, methods, and functions the VM actually touches. This is the general weapon when the first three techniques are blocked or too noisy.

### Technique selection matrix

| VM characteristic | Preferred techniques |
|---|---|
| Signature via hookable API (CryptoJS/atob/MD5) | 1 + 3 (hot-API hook + log reverse-trace) |
| VM calls sub-functions via `Function.apply/call` | 2 + 3 (multi-path interpreter trace + logs) |
| Self-contained, algorithm inside `switch/case` | 4 first, with 1 for the I/O boundary |
| Deeply environment-bound (fingerprint-driven signature) | 4 to locate the fingerprint set, then env emulation |

## Algorithm fingerprint table

Infer the algorithm from output shape before rebuilding:

| Output | Likely algorithm |
|---|---|
| 32 hex | MD5 |
| 40 hex | SHA-1 |
| 64 hex | SHA-256 |
| 44 Base64 with `=` padding | HMAC-SHA256 + Base64 |
| 24/32/44 Base64 | AES (CBC/ECB) |
| length varies with input | non-fixed hash: encryption or custom encoding |
| contains separators | custom concatenation format |

## Common JSVMP variants

- **VM hijacks XHR/fetch** (request completes inside the VM, outer hook misses it): hook a lower primitive (`XMLHttpRequest.prototype.send`) captured before the VM rewrites it, or capture at the network/protocol layer instead of the JS layer.
- **VM dynamically builds the crypto function** (`eval`/`new Function`): hook the code-generation boundary and extract the generated source.
- **Nested VMs** (outer VM decrypts inner bytecode): do not model the nesting; hook the final egress and the initial entry, widen trace capture, and filter by timestamp.
- **VM + WASM** (VM drives control flow, WASM does the crypto): hook the WASM exports for I/O, then load the `.wasm` locally and call the export directly.

## Restoration decision

Drive every decision from the environment/method evidence gathered above (especially technique 4's hot-key/hot-method output):

1. Hot methods are standard crypto (CryptoJS/SubtleCrypto/HMAC/btoa) and plaintext order is recoverable → pure algorithm reimplementation (Python `hashlib`/`pycryptodome`, or a tiny Node helper).
2. Plaintext comes from inside the VM but an independent signer function is extractable → sandbox-execute that function with a minimal environment aligned to the observed hot keys.
3. VM hijacks the whole request chain and reads many environment properties → jsdom/Node environment emulation; the hot-key set tells you exactly which properties to align (see `environment-patch-playbook.md` and the Camoufox Provider's `jsdom-env-patches.md`).
4. Cannot detach from the browser at all → browser automation is the last resort, never the protocol-first delivery.

Prefer isolating the one helper output the request needs over heroic full recovery. A tiny wrapper around the VM output that Python can call is a valid delivery; a retained browser is not.

## Common traps

- devirtualizing the whole VM when only one result matters
- missing side inputs passed into the VM entry point
- treating failure under Node, jsdom, or a thin shim as proof the VM cannot run locally
- installing broad hooks on a signature-type challenge before a clean baseline (observer effect can change the challenge)
- hoisting `POP()` calls without preserving JavaScript's left-to-right evaluation order; subtraction, remainder, and shift results can diverge
- copying VM array indexes from another version instead of extracting the current PC, stack, opcode, and accumulator locations

## Delivery rule

If a tiny helper wrapper around the VM output is enough for protocol replay, use that instead of full recovery. Final live egress stays browser-free and Python-owned.
