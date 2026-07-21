# Web Protocol Recovery

`web-protocol-recovery` is the single public entry for Web and miniapp protocol recovery. `SKILL.md` owns dispatch. Internal Providers are modules, not peer skills.

## Route Index

- Start/dispatch: `SKILL.md`
- Architecture and ownership boundaries: `references/methodology/architecture.md`
- Default shape scripts and mandatory overlays: `references/methodology/success-shape-scripts.md`
- Authorization, scope, budget, execution, runtime, and cleanup contract: `references/methodology/provider-work-order.md`
- Project root and output layout: `references/methodology/project-layout.md`
- Reference and case read caps: `references/methodology/read-budget.md`
- Case writeback and sanitization: `references/methodology/case-writeback.md`
- Symptom routing: `references/reference-router.md`
- Tool-family selection/escalation: `references/tool-playbook.md`
- Case selector: `references/cases/registry.json`

## Provider Architecture

```text
references/providers/
  reconnaissance/
    chromium-recon/PROVIDER.md
    camoufox/PROVIDER.md
    camoufox/references/ops-ladder.md
    wechat-miniapp/PROVIDER.md
    wechat-miniapp/references/ops-playbook.md
  implementation/
    browser-hooks/PROVIDER.md
    ast/PROVIDER.md
    env-patch/PROVIDER.md
    iv8/PROVIDER.md
    verifier/PROVIDER.md
    python-collector/PROVIDER.md
```

Internal skills are Providers under this tree (not peer top-level skills). Providers receive `web-protocol-recovery-provider-work-order/v1` and return `web-protocol-recovery-provider-result/v1` (schema in `references/methodology/provider-work-order.md`). web-protocol-recovery remains the owner of methodology, scope, project root, layout, acceptance, and browser-free delivery.

## Cases

The root registry indexes 18 hash-bound `web-protocol-recovery-case/v1` manifests grouped by runtime: 14 `iv8`, zero current `pure-python`, and four `python-node` evidence cases. All historical cases require fresh current-target verification. `secretPolicy=redacted-pull-live` preserves state names and structure but no cookie/token values.

## Runtime Helpers

Reverse-engineering helpers under `scripts/` are optional aids, not gates:

```cmd
python scripts\check_reverse_env.py
python scripts\crypto_fingerprint.py <sample>
python scripts\protocol_diff.py <capture-a> <capture-b>
python scripts\providers\python-collector\scaffold_project.py <project-root> --entry --cache
```

`scripts/providers/cases/live_state.py` backs each case's `pull_live_state.py` for in-memory credential pulls. web-protocol-recovery-specific deposition and dedup rules live in `references/methodology/knowledge-maintenance.md`.
