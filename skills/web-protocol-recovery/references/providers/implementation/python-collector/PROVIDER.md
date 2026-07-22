# Python Collector Provider

## Select When

- Real endpoint and moving protocol state are already proved.
- Desired result is `compact-replay` or `collector` under `web-protocol-recovery-simple/v1`.
- Final live egress must be browser-free Python.

## Do Not Select When

- Protocol is still unproved (recon or another implementation Provider first).
- User only wants evidence, a hook snippet, or offline local-proof.
- Scaffold would overwrite existing `main.py` or create wrapper trees (reject).
- Live replay / request budget / action class are still denied or empty.

Use this provider after web-protocol-recovery has proved the real endpoint and moving protocol state. It owns the stable browser-free live-egress implementation assigned under `main.py` and `utils/`.

Architecture boundary: web-protocol-recovery owns route choice, `projectRoot`, layout, acceptance, and final delivery. This provider is the only implementation Provider that may own final live egress, and only inside assigned `web-protocol-recovery-simple/v1` paths.

Python owns live egress, session/cookie handling, request budgets, retries, pagination, parsing, decode, persistence, and output. JavaScript, WASM, or iv8 helpers remain narrow local artifact generators. The final path never drives a browser.

## Scaffold

First write may use the skill-root scaffold (absolute `projectRoot` required, never overwrite):

```text
python <skill-root>/scripts/providers/python-collector/scaffold_project.py <ABS_PROJECT_ROOT> --confirm \
  [--entry] [--utils] [--iv8-silent] [--tests] [--cache] [--cache-namespace recon|source|ast|env|iv8|samples|private] \
  [--output] [--requirements] [--readme] [--gitignore]
```

Rules:

1. Refuse without `--confirm` and without an absolute root.
2. Reject symlink, Windows junction/reparse, and hard-linked destinations.
3. Create only requested missing paths; never overwrite an existing file.
4. Cache/output require `--gitignore` so `js_reverse_cache/**` and `output/**` stay untracked.
5. Do not generate `collector/`, `analysis/`, package frameworks, or a second landing root.
6. When the final collector will import iv8, pass `--iv8-silent` so scaffold creates `utils/iv8_silent.py` (and `utils/` if needed). The delivered `main.py` must still call `import_iv8_silent()`.

Layout details: `references/methodology/project-layout.md`. Delivery gate checklist: `references/delivery-gate-playbook.md`.

## Layout Ownership

| Path | Owner role |
|---|---|
| `main.py` | Final live-egress entry; compact; no browser driving |
| `utils/sign.py`, `utils/runtime.py`, `utils/decode.py`, `utils/client.py` | Narrow stable helpers only when a distinct responsibility exists |
| `utils/iv8_silent.py` | Required when the final collector depends on iv8; silent import only; template from the iv8 Provider `script-writing-rules.md` |
| `main.js` / `mod.js` | Optional local artifact generators from other Providers; not the live-egress owner |
| `js_reverse_cache/**` | Volatile evidence/probes; never the steady-state collector |
| `tests/**` or `js_reverse_cache/samples/**` | Fixed vectors and regression fixtures |
| `output/**` | User-requested data only after bounds are set |

Keep `main.py` short. Move only proven stable pieces into `utils/`. Do not import helpers whose import side effects open network, patch globals, or require a live browser. When the final collector needs iv8, create or reuse `utils/iv8_silent.py` and load it with `iv8 = import_iv8_silent()`; do not top-level `import iv8` in the delivered `main.py`.

## Acceptance (all required before scale)

1. Fixed-input / named checkpoint parity against captured truth.
2. One approved minimal live replay on a coherent session succeeds.
3. Content type, challenge markers, business result, and data shape pass.
4. Signatures, cookies, headers, and wrapped bodies regenerate at the canonical request boundary—not from a leftover browser jar.
5. Delivery gate: final path is browser-free; host-like values (UA, screen, etc.) are explicit config when they are only signer inputs.
6. `200` or a non-empty signature alone is not semantic success.

## Bounds

Honor the work-order `requestBudget` and never invent a larger budget:

- redirects, retries, response-byte caps, page count, concurrency, min delay
- output overwrite policy
- cookie domain/path scope and exact serialization
- response bytes preserved before decode

Scale pagination/retry/concurrency only after a repeatable first request and explicit confirmation.

## Exit

Return: absolute paths created or updated, fixed-vector and live acceptance state, budget remaining, cleanup state, residual limits, and any helper artifact paths/hashes. Do not claim `complete` while task-owned runtimes remain live or cleanup is incomplete.

## Failure Recovery

| Trigger | First fix | Still fails → stop |
|---|---|---|
| Endpoint or moving state still unproved | Return blocker to hub for recon/implementation | Do not scaffold |
| Scaffold path exists or reparse/hardlink | Choose new approved path or leave user file | Reject overwrite |
| Fixed vectors fail | Diff first divergence; fix helper/serialization | No live egress |
| Live `200` but wrong body/shape/challenge | Treat as fail; capture semantic mismatch | Do not scale |
| Import has network/browser side effects | Make import-safe; move I/O behind explicit call | Reject helper |
| Budget remaining 0 | Offline vectors only | No live egress until user raises budget |
