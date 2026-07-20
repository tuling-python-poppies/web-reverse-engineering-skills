# Environment Patch Provider

## Select When

- Target JS and entry (or `script-load-only`) are known.
- Smallest path is Node/vm/jsdom with minimal missing browser surfaces.
- Fixed-vector signer/cookie/header behavior must be verified after runtime success.

## Do Not Select When

- Browser-like host, XHR/netLog, or registry runtime case needs a fuller embedded runtime (prefer iv8).
- Entry is unknown (recon first).
- Runtime load alone is treated as proof (always require fixed vectors).

**vs iv8:** env-patch = minimal Node gaps for a known entry; iv8 = browser-like local host when that is the smallest faithful runtime.

Use this provider only with known target JS and a known entry or `script-load-only` runtime goal. It iterates run -> diagnose missing environment -> add the smallest module -> verify the target behavior.

## Trust Gate

`node:vm` is not a security boundary. Before executing target JS or custom environment modules, record source path, SHA-256, provenance, static review of Node capabilities/dynamic evaluation, and explicit execution approval. Untrusted material remains static-only.

## Workflow

1. From the approved project root, run `<provider-dir>/scripts/vm-browser-gap-diagnose.js --trusted-code` without env modules. The current directory is the project path boundary, not the Provider directory.
2. Select and order the smallest modules from `env/` using `references/env-modules.md`. Read `references/loading-order.md` instead, in a later iteration, only when a multi-module dependency or replacement order remains the current blocker.
3. Repeat diagnosis while preserving proxy/gap monitoring with selected modules.
4. Keep generated patches and probes under `js_reverse_cache/env/` and load them through that explicit path. Built-in module names always resolve from the Provider and cannot be shadowed by the project. Relative project modules reject symlink, junction, traversal, and real-path escape.
5. After runtime success, trigger the known signer/cookie/header behavior and compare fixed vectors or browser intermediates.
6. Promote only verified stable output to assigned `mod.js` and `main.js`; web-protocol-recovery owns final `main.py` integration.

`success:true` only means the observable runtime path did not throw. It is not signer or replay proof. Return module load errors, unresolved paths, input/output hashes, functional result, first divergence, and residual environment assumptions.

## Optional References

- `references/env-modules.md`: map observed undefined paths to active modules and apply the compact default order.
- `references/loading-order.md`: diagnose a proven multi-module dependency or replacement-order blocker in a separate iteration.
- `references/node-detection.md`: repair Node/VM identity and reflected-shape leaks.
- `references/webpack.md`: expose only the webpack runtime boundary needed by the target.
- `references/limitations.md`: recognize opcode-level or real-engine gaps that environment modules cannot close.
