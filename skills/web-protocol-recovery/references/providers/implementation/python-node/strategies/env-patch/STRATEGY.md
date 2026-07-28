# Environment Patch Strategy

## Select When

- Target JS and entry (or `script-load-only`) are known.
- Smallest path is Node/vm/jsdom with minimal missing browser surfaces.
- Fixed-vector signer/cookie/header behavior must be verified after runtime success.

## Do Not Select When

- Browser-like host, XHR/netLog, or registry runtime case needs a fuller embedded runtime (prefer iv8).
- Entry is unknown (recon first).
- Runtime load alone is treated as proof (always require fixed vectors).

**vs iv8:** env-patch = minimal Node gaps for a known entry; iv8 = browser-like local host when that is the smallest faithful runtime.

Use this `python-node` strategy only with known target JS and a known entry or `script-load-only` runtime goal. It iterates run -> diagnose missing environment -> add the smallest module -> verify the target behavior.

Architecture boundary: web-protocol-recovery owns route choice, `projectRoot`, layout, acceptance, and final delivery. The active Provider is `python-node` with `strategy: env-patch`; this strategy only writes assigned env probes or verified JS helpers under `web-protocol-recovery-simple`, then returns fixed-vector proof or a blocker.

## Trust Gate

`node:vm` is not a security boundary. Before executing target JS or custom environment modules, record source path, SHA-256, provenance, static review of Node capabilities/dynamic evaluation, and explicit execution approval. Untrusted material remains static-only.

## Workflow

1. From the approved project root, run `<strategy-dir>/scripts/vm-browser-gap-diagnose.js --trusted-code` without env modules. The current directory is the project path boundary, not the installed strategy directory.
2. Select and order the smallest modules from `env/` using `references/env-modules.md`. When a Proxy/diagnostic gap log already exists, run `scripts/gap-log-module-advisor.js <gap-log.json>` first; treat `recommendedModules` as path candidates relative to `env/`, then confirm each against `env-modules.md` before loading.
3. Repeat diagnosis while preserving proxy/gap monitoring with selected modules.
4. Keep generated patches and probes under `js_reverse_cache/env/` and load them through that explicit path. Built-in module names always resolve from the strategy directory and cannot be shadowed by the project. Relative project modules reject symlink, junction, traversal, and real-path escape.
5. When diagnosis needs real browser seed values (UA, screen, storage, fingerprint samples) and no approved seed artifact exists, use `scripts/browser-seed-collector.js` as a DevTools Console/Snippets paste. It only reads local page state and prints JSON; save the redacted result under `js_reverse_cache/env/` or feed it via `--profile-file`. Do not start or switch a browser from this strategy solely to collect seeds; request recon evidence or reuse an already-open authorized page.
6. **Optional advanced branch** (not default): if modular rounds already ran (or evidence is native-only), and you need `setFuncNative` / constructor shape / targeted `monitor` / cache-area hand-written verification before promoting `mod.js`/`main.js`, read `references/advanced-env-path.md`, copy `scripts/advanced-env-engine.js` into `js_reverse_cache/env/`, and verify there. Take only needed shells from `references/browser-stubs.md`. Do not open advanced on the first turn without the gate in that doc.
7. After runtime success, read `references/verification-and-replay.md` before claiming functional success; trigger the known signer/cookie/header behavior and compare fixed vectors or browser intermediates.
8. Promote only verified stable output to assigned `mod.js` and `main.js`; use `templates/` only as project-local skeletons, and web-protocol-recovery owns final `main.py` integration.

`success:true` only means the observable runtime path did not throw. It is not signer or replay proof. Return module load errors, unresolved paths, input/output hashes, functional result, first divergence, and residual environment assumptions.

## Optional Scripts

| Script | When | Output |
|---|---|---|
| `scripts/vm-browser-gap-diagnose.js` | Default diagnose loop | gap / undefined paths |
| `scripts/gap-log-module-advisor.js` | Gap log exists; need module shortlist | `recommendedModules` under `env/` |
| `scripts/browser-seed-collector.js` | Need real browser seed for profile | Console JSON (no network) |
| `scripts/webpack-module-runtime.js` | Webpack runtime boundary only | load/expose helpers |
| `scripts/advanced-env-engine.js` | Gate met: native disguise, targeted monitor, cache-area hand-written verify | copy into `js_reverse_cache/env/`, then import |

## Runtime Boundary

Default architecture is `env/core/*` monitors, the `env/` module tree, project-local `js_reverse_cache/env/ai-generated/*.js` patches, and the diagnose/advisor/seed scripts. `advanced-env-engine.js` is an **optional branch inside this strategy** for native shape and targeted monitoring after the advanced gate is met, not a second default and not a replacement for iv8 when browser-host semantics are required. Do not run modular spray and advanced as two competing ungoverned defaults in the same loop. If host semantics remain the first divergence after modular and (when gated) advanced work, return a blocker or escalate to iv8 per `references/path-upgrade-checklist.md`.

## Optional References

- `references/env-modules.md`: map observed undefined paths to active modules and apply the compact default order.
- `references/loading-order.md`: diagnose a proven multi-module dependency or replacement-order blocker in a separate iteration.
- `references/node-detection.md`: repair Node/VM identity and reflected-shape leaks.
- `references/advanced-env-path.md`: optional advanced engine gate, cache layout, and promote rules.
- `references/browser-stubs.md`: optional document/navigator/XHR shell snippets for the advanced path only; take the minimum.
- `references/webpack.md`: expose only the webpack runtime boundary needed by the target.
- `references/limitations.md`: recognize opcode-level or real-engine gaps that environment modules cannot close.
- `references/path-upgrade-checklist.md`: decide whether to keep shrinking env-patch, use advanced, move to iv8, or stop for WASM/engine blockers.
- `references/delivery-templates.md`: use the bundled `templates/main.py`, `templates/main.js`, and `templates/mod.js` without turning load success into replay proof.
