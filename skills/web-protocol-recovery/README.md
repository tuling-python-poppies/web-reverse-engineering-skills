# Web Protocol Recovery

`web-protocol-recovery` is the single public entry for Web and miniapp protocol recovery. `SKILL.md` owns dispatch. Internal Providers are modules, not peer skills.

## Related Repositories

配套mcps仓库地址
https://gitee.com/tuling-python/web-reverse-mcps-tool

自研浏览器运行时框架代码仓库地址
https://gitee.com/tuling-python/nv8

## Route Index

- Start/dispatch: `SKILL.md`
- Architecture and ownership boundaries: `references/methodology/architecture.md`
- Default shape scripts and mandatory overlays: `references/methodology/success-shape-scripts.md`
- Authorization, scope, budget, execution, runtime, and cleanup contract: `references/methodology/provider-work-order.md`
- Project root and output layout: `references/methodology/project-layout.md`
- Reference and case read caps: `references/methodology/read-budget.md`
- Machine checkpoint contract: `references/schemas/checkpoint.schema.json`
- Case writeback and sanitization: `references/methodology/case-writeback.md`
- Symptom routing: `references/reference-router.md`
- Tool-family selection/escalation: `references/tool-playbook.md`
- Case selector: `references/cases/registry.json`
- Route regression metadata: `evals/route-regression.json`

## Provider Architecture

```text
references/providers/
  registry.json
  reconnaissance/
    chromium-recon/PROVIDER.md
    camoufox/PROVIDER.md
    camoufox/references/ops-ladder.md
    wechat-miniapp/PROVIDER.md
    wechat-miniapp/references/ops-playbook.md
    wmpf-address-adapter/PROVIDER.md
    wmpf-address-adapter/references/ops-playbook.md
  protocol-recovery/
    browser-hooks/PROVIDER.md
    ast/PROVIDER.md
    verifier/PROVIDER.md
    verifier/references/*.md
    verifier/scripts/*
    akamai/PROVIDER.md
    akamai/references/*.md
    akamai/scripts/*
    river-security/PROVIDER.md
    reese84/PROVIDER.md
    kasada/PROVIDER.md
  implementation/
    iv8/PROVIDER.md
    python-node/PROVIDER.md
    python-node/strategies/env-patch/STRATEGY.md
    nv8/PROVIDER.md
    pure-python/PROVIDER.md
    pure-python/profiles/douyin-abogus-native.md
  delivery/
    python-collector/PROVIDER.md
```

Internal skills are Providers under this tree (not peer top-level skills). Roles are explicit: reconnaissance locates evidence; protocol-recovery owns family rules and acceptance; implementation Providers generate one local artifact; delivery owns final browser-free Python egress. A typical Reese84 chain is `reese84 -> iv8/python-node -> python-collector`: Reese84 keeps protocol acceptance while the implementation Provider produces a narrow artifact. Akamai/Kasada sensor chains may use `nv8` as the implementation Provider when full browser-compatible local execution is required. `env-patch` is a `python-node` strategy, not a route. `douyin-abogus-native` is a `pure-python` profile, not a route. Providers receive `web-protocol-recovery-provider-work-order` and return `web-protocol-recovery-provider-result`; schemas live in `references/schemas/` and the explanatory contract is `references/methodology/provider-work-order.md`.

## Cases

The root registry indexes 25 hash-bound `web-protocol-recovery-case` manifests grouped by implementation runtime: 16 `iv8`, 6 `python-node`, and 3 `pure-python`. Template cases require fresh current-target verification. Each manifest declares its own `secretPolicy`; raw project-state persistence requires the hub's `raw-secret-handling` gate and never adds cookie/token values to the case library.

## Gates

`python scripts/gates/preflight.py --strict` runs every check below and is the single
entry point after any edit. Each one is fail-closed; none of them are advisory.

| Gate | Asserts |
|---|---|
| `verify_case_hashes.py` | Declared hashes match the bytes on disk for all 25 case manifests |
| `build_case_registry.py --check` | `registry.json` is exactly the generated projection |
| `validate_architecture.py` | Provider registry, route literals, hub and case-process contracts, read plans, case manifests, live-egress boundary, build residue, and LF-only line endings |
| `validate_schemas.py` | Work-order and result schemas |
| `validate_markdown.py` | Markdown contract |
| `validate_evals.py` | Offline route-regression metadata, provider route coverage, and the `test-prompts.json` fixture contract |
| case unit tests | Per-case offline behaviour |
| `test_preflight.py`, `test_architecture_contract.py`, `test_scaffold_project.py`, `test_line_endings.py` | The gates themselves fail in the failing direction |
| entry discipline scan | No import-time network, mkdir, or engine start in case entries |

Two invariants exist because both were violated silently for a long time. Every
hash-bound text surface is pinned to LF by `.gitattributes`, and
`validate_architecture.py` scans raw bytes for CRLF. Scripts that generate
checked-in hash-bound text must also write LF explicitly; `build_case_registry.py`
is covered by `test_line_endings.py` because that writer previously emitted
CRLF on Windows while its own `--check` read back with universal newlines.

## Runtime Helpers

Reverse-engineering helpers under `scripts/` are optional aids, not gates:

```cmd
python scripts\tools\check_reverse_env.py
python scripts\tools\crypto_fingerprint.py <sample>
python scripts\tools\protocol_diff.py <capture-a> <capture-b>
python scripts\providers\delivery\python-collector\scaffold_project.py <project-root> --entry --cache
```

`scripts/providers/cases/live_state.py` backs each case's `pull_live_state.py` for in-memory credential pulls. web-protocol-recovery-specific deposition and dedup rules live in `references/methodology/knowledge-maintenance.md`.

The gate runtime requires `jsonschema`. Case tests may have additional optional
dependencies declared by their manifest, including `pycryptodome`, `Pillow`,
`ddddocr`, `curl_cffi`, and `websocket-client`; preflight reports missing
optional modules and does not install them automatically. Node-based case
artifacts are executed only through an approved bounded process launcher with
current work-order hash, execution mode, and deadline evidence.
