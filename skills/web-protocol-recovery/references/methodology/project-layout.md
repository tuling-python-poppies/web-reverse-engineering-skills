# WPR Simple Project Layout

`web-protocol-recovery-simple/v1` is the only project layout used by WPR and all internal providers.

## Root Selection

Before the first filesystem write, use an explicit user-supplied folder. If none was supplied, ask once whether to use the current directory or a custom directory. Record the absolute `projectRoot` and reuse it for the entire task. Read-only reconnaissance may continue before this decision, but no trace, source, screenshot, request export, or generated code may be saved.

Never add a wrapper directory below the selected root. Never let a provider ask for a second landing directory.

Reject a selected root or output path when any existing component is a symlink, Windows junction, mount-point reparse path, or hard-linked file. Resolve containment without following those aliases. Create new files by exclusive atomic publication and never overwrite an existing path.

## Minimal Shape

```text
<project-root>/
  main.py                  # default final entry, created only when implementation exists
  main.js                  # optional callable JS entry
  mod.js                   # optional verified Node environment
  config.local.json        # optional private local config; always ignored
  utils/                   # optional stable helpers
  tests/                   # optional fixed-vector or regression tests
  output/                  # optional user-requested data output
  js_reverse_cache/        # volatile evidence and intermediate work
    recon/
      chrome/
      js-reverse/
      cloak/
      camoufox/
      miniapp/
    source/
    ast/
    env/
    iv8/
    samples/
    private/
  requirements.txt         # only when third-party dependencies exist
  README.md                # only for multi-file delivery or handoff
  .gitignore               # when local/private/cache/output files exist
```

Create only paths required by the current task. A valid delivery may contain only `main.py`.

## Ownership

- WPR owns `main.py` and final integration.
- Reconnaissance providers write only assigned `js_reverse_cache/recon/**` and `js_reverse_cache/source/**` paths.
- AST writes intermediate products under `js_reverse_cache/ast/`; promote only a callable, verified result to `main.js` or `utils/*.js`.
- env-patch writes probes under `js_reverse_cache/env/`; verified stable output may become `mod.js` and `main.js`.
- iv8 writes probes and net logs under `js_reverse_cache/iv8/`; stable Python helpers belong in `utils/` or the compact `main.py`.
- verifier keeps transient images under `js_reverse_cache/source/` and fixed redacted vectors under `js_reverse_cache/samples/` or stable `tests/`.
- python-collector owns stable HTTP, pagination, decode, and storage helpers assigned under `main.py` and `utils/`.

## Cache First, Promote After Proof

Downloaded HTML/JS/WASM/fonts/images, network exports, screenshots, browser state, traces, AST intermediates, env probes, and runtime logs stay in `js_reverse_cache/`. Promote code only after a fixed-vector or live semantic acceptance test passes.

`js_reverse_cache/private/` is never copied into the bundled skill or case library. Raw account/session artifacts require explicit field, path, and retention approval. Existing project files are never overwritten; choose a new approved path or leave the user-owned file unchanged.

## Entry Points

The default user command is:

```text
python main.py
```

`main.js` and `mod.js` are local implementation helpers, not competing project entry points. Do not require `python -m collector.main` and do not create mandatory `collector/`, `analysis/`, `input/`, or `logs/` directories.
