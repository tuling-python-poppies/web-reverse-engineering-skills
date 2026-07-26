# web-protocol-recovery Simple Project Layout

`web-protocol-recovery-simple/v1` is the only project layout used by web-protocol-recovery and all internal providers.

This layout is part of the architecture contract. Providers may not create or preserve a second layout for compatibility.

## Root Selection

Before the first filesystem write, use an explicit user-supplied folder. If none was supplied, ask once whether to use the current directory or a custom directory. Record the absolute `projectRoot` and reuse it for the entire task. Read-only reconnaissance may continue before this decision, but no trace, source, screenshot, request export, or generated code may be saved.

Never add a wrapper directory below the selected root. Never let a provider ask for a second landing directory.

Forbidden generated or required directories: `collector/`, `analysis/`, `input/`, `logs/`, provider-named project roots, and any second task root. Existing user files with those names may be read only when explicitly supplied as evidence; new delivery files still promote into `web-protocol-recovery-simple/v1` paths.

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
    akamai/
    samples/
    private/
  requirements.txt         # only when third-party dependencies exist
  README.md                # only for multi-file delivery or handoff
  .gitignore               # when local/private/cache/output files exist
```

Create only paths required by the current task. A valid delivery may contain only `main.py`.

**On-demand rule:** do not pre-create empty `js_reverse_cache/recon|source|ast|env|iv8|akamai|samples|private`, `tests/`, or `output/` just because they appear in the layout diagram. Create a subdirectory only when the first write for that namespace is about to happen (or the user/work order explicitly requests it via scaffold `--cache-namespace` / `--tests` / `--output`). Empty placeholder trees are forbidden.

## Ownership

- web-protocol-recovery owns `main.py` and final integration.
- Reconnaissance providers write only assigned `js_reverse_cache/recon/**` and `js_reverse_cache/source/**` paths.
- AST writes intermediate products under `js_reverse_cache/ast/`; promote only a callable, verified result to `main.js` or `utils/*.js`.
- env-patch writes probes under `js_reverse_cache/env/`; verified stable output may become `mod.js` and `main.js`.
- iv8 writes probes and net logs under `js_reverse_cache/iv8/`; stable Python helpers belong in `utils/` or the compact `main.py`. When the delivery imports iv8, `utils/iv8_silent.py` is an allowed stable helper for silent package import only.
- akamai writes transient collector, sensor, Pixel, cookie-transition, transport, and host-fingerprint evidence under `js_reverse_cache/akamai/`; accepted helper code promotes only through `utils/` or `main.py`.
- river-security writes challenge HTML/JS under `js_reverse_cache/source/`, env probes under `js_reverse_cache/env/`, iv8 runtime logs under `js_reverse_cache/iv8/`, and redacted fixed vectors under `js_reverse_cache/samples/`; accepted helper code promotes only through `utils/` or `main.py`.
- verifier keeps transient images under `js_reverse_cache/source/` and fixed redacted vectors under `js_reverse_cache/samples/` or stable `tests/`.
- douyin-abogus-native keeps fixed traces and redacted vectors under `js_reverse_cache/samples/` or stable `tests/`; accepted pure Python helpers promote only through `utils/` or `main.py`.
- python-collector owns stable HTTP, pagination, decode, and storage helpers assigned under `main.py` and `utils/`.

## Cache First, Promote After Proof

Downloaded HTML/JS/WASM/fonts/images, network exports, screenshots, browser state, traces, AST intermediates, env probes, and runtime logs stay in `js_reverse_cache/`. Promote code only after a fixed-vector or live semantic acceptance test passes.

`js_reverse_cache/private/` is never copied into the bundled skill or case library. Raw account/session artifacts require explicit field, path, and retention approval. Existing project files are never overwritten; choose a new approved path or leave the user-owned file unchanged.

## Absolute Path And Temp Policy

1. After `projectRoot` is recorded, every task-owned write must stay under that root. Preferred volatile tree: `js_reverse_cache/**` (and `output/**` only when the user asked for data files).
2. Forbidden as primary storage for task evidence: `%TEMP%`, `%TMP%`, `AppData\Local\Temp`, agent `opencode` temp roots, skill package directories, Desktop drop folders outside `projectRoot`, and any second cache root invented for convenience.
3. MCP tools that require an absolute file path must receive a path already under `projectRoot/js_reverse_cache/...` whenever the tool allows it.
4. If a tool refuses project paths and forces an external absolute path: (a) name that blocker, (b) copy the artifact into the matching `js_reverse_cache/` namespace immediately after the tool returns, (c) point subsequent work at the project copy only, (d) do not make `main.py` or stable helpers depend on the external path.
5. Do not delete `js_reverse_cache/` and leave the only copy of cookies/state in OS temp. Private state belongs in `js_reverse_cache/private/` with gitignore protection.
6. Scaffold creates cache dirs only under the absolute `projectRoot` passed to `scaffold_project.py`.

## Pre-Write Checklist (5 questions)

Before any new file/dir under a task project, answer yes to all applicable:

1. **projectRoot?** Absolute approved root is recorded and the path is inside it.
2. **Necessary namespace?** Creating `recon|source|ast|env|iv8|akamai|samples|private` only because the next write needs that folder (not "layout completeness").
3. **Not OS temp as primary?** Not writing primary evidence under `%TEMP%` / `AppData\Local\Temp` / agent temp roots.
4. **Logger?** iv8 or multi-step collector delivery has or will create `utils/logger.py` and uses it for progress.
5. **No empty tree?** No empty placeholder directories will remain after this step unless a file is written into them immediately.

## Scaffold (optional first write)

When the work order needs new empty layout paths under an absolute `projectRoot`, python-collector may call:

```text
python <skill-root>/scripts/providers/python-collector/scaffold_project.py <ABS_PROJECT_ROOT> --confirm [flags]
```

Create only requested missing files; never overwrite. See the python-collector Provider for flags and reject rules.

## Entry Points

The default user command is:

```text
python main.py
```

`main.js` and `mod.js` are local implementation helpers, not competing project entry points. Do not require `python -m collector.main` and do not create `collector/`, `analysis/`, `input/`, or `logs/` directories.
