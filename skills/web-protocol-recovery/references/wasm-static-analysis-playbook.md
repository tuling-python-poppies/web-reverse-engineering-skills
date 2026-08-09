# WASM Static Analysis Playbook

Use this reference when a `.wasm` module (or an inline `WebAssembly.instantiate`
buffer) carries part of the protocol contract: a signer, a token builder, a
checksum, an encoder, or a decoder. It covers how to locate the relevant export
without over-committing to full disassembly.

## Core rule

Prefer executing one export for a narrow artifact over recovering the module.
Static structure inspection is cheap and always safe; instruction-level
disassembly is expensive and only justified in two cases named below.

## Layer 1: structure inspection (default, offline, no dependencies)

`scripts/wasm_module_inspect.py` reads the preamble, section table, import
table, export table, and function/memory/table/global counts. It does not
disassemble function bodies. Use it to answer:

- which functions are exported, and which export name looks like the signer
- what host capabilities the module imports (env functions, memory, table)
- whether the module declares its own memory or expects an imported one
- how many functions exist, to gauge whether the logic is small or large

This is enough to pick the export to call and to know what host surface the
execution sidecar must provide.

## Layer 2: execute the export (default delivery path)

Once the export is located, produce the artifact by executing it, not by
reading it:

- `route: python-node` with `strategy: wasm-sidecar` — Python drives a bounded
  Node/WASM helper that instantiates the module, provides the required imports,
  calls the export, and returns one artifact (sign, token, encoded frame,
  decoded payload).
- `route: iv8` — when the surrounding bundle needs browser-like host semantics
  before the export is reachable.

Executing a target-supplied `.wasm` is target-code execution: it still requires
the `executionPolicy` confirmation, reviewed bytes, and a SHA-256-approved
sandbox with network/file/process denied unless separately authorized.

## Layer 3: disassembly / decompilation (only when justified)

Reach for `wasm2wat`, `wasm-decompile`, or an equivalent only when one of these
holds:

1. **Porting to pure Python.** The algorithm must become a dependency-free
   Python signer (`route: pure-python`), so the exact operations have to be read
   out of the module.
2. **The module cannot be executed locally.** Instantiation is blocked (missing
   host imports that cannot be faithfully stubbed, threads/SharedArrayBuffer the
   sidecar cannot provide), so structure alone is insufficient.

These tools are optional and user-provided. They are not auto-installed and not
part of any bootstrap. If they are absent, report the blocker rather than
inventing a decode.

## executionPolicy boundary

- Reading module bytes with `scripts/wasm_module_inspect.py` is a read
  operation. It does not instantiate the module and does not trigger the
  target-code execution gate.
- `WebAssembly.instantiate`, running an export, or executing disassembled logic
  is target-code execution and keeps its `executionPolicy` confirmation.

## Verification gates

- a located export name is a hypothesis until calling it reproduces a captured
  artifact on fixed inputs
- compare the export output against a captured wire value, not only against
  "it returned something"
- when porting to Python, keep at least one deterministic parity vector between
  the WASM output and the Python port
- a non-empty return, a successful instantiation, or an HTTP `200` is not
  semantic success

## Acceptable handoff

The final collector stays local protocol code:

- Python plus a bounded WASM sidecar that returns one artifact, or
- pure Python once the algorithm is ported and parity-checked.

Final live egress stays browser-free and Python-owned; the WASM module is only a
narrow artifact generator.
