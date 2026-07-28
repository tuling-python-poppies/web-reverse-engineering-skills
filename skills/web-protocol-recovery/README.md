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
  registry.json
  reconnaissance/
    chromium-recon/PROVIDER.md
    camoufox/PROVIDER.md
    camoufox/references/ops-ladder.md
    wechat-miniapp/PROVIDER.md
    wechat-miniapp/references/ops-playbook.md
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
  implementation/
    iv8/PROVIDER.md
    python-node/PROVIDER.md
    python-node/strategies/env-patch/STRATEGY.md
    pure-python/PROVIDER.md
    pure-python/profiles/douyin-abogus-native.md
  delivery/
    python-collector/PROVIDER.md
```

Internal skills are Providers under this tree (not peer top-level skills). Roles are explicit: reconnaissance locates evidence; protocol-recovery owns family rules and acceptance; implementation Providers generate one local artifact; delivery owns final browser-free Python egress. `env-patch` is a `python-node` strategy, not a route. `douyin-abogus-native` is a `pure-python` profile, not a route. Providers receive `web-protocol-recovery-provider-work-order/v2` and return `web-protocol-recovery-provider-result/v2`; schemas live in `references/schemas/` and the explanatory contract is `references/methodology/provider-work-order.md`.

## Cases

The root registry indexes 22 hash-bound `web-protocol-recovery-case/v2` manifests grouped by implementation runtime: 16 `iv8`, 5 `python-node`, and 1 `pure-python`. All historical cases require fresh current-target verification. `secretPolicy=redacted-pull-live` preserves state names and structure but no cookie/token values.

## Runtime Helpers

Reverse-engineering helpers under `scripts/` are optional aids, not gates:

```cmd
python scripts\check_reverse_env.py
python scripts\crypto_fingerprint.py <sample>
python scripts\protocol_diff.py <capture-a> <capture-b>
python scripts\providers\delivery\python-collector\scaffold_project.py <project-root> --entry --cache
```

`scripts/providers/cases/live_state.py` backs each case's `pull_live_state.py` for in-memory credential pulls. web-protocol-recovery-specific deposition and dedup rules live in `references/methodology/knowledge-maintenance.md`.
