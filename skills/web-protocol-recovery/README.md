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
    douyin-abogus-native/PROVIDER.md
    akamai/PROVIDER.md
    akamai/references/*.md
    akamai/scripts/*
    verifier/PROVIDER.md
    verifier/references/*.md
    verifier/scripts/*
    python-collector/PROVIDER.md
```

Internal skills are Providers under this tree (not peer top-level skills). `douyin-abogus-native` owns already-proved Douyin Web BDMS pure-Python `a_bogus` maintenance and request adaptation. `verifier` owns captcha protocol workflows and proof criteria. `akamai` owns Akamai Bot Manager workflow, cookie state machine, transport rules, iv8 collector route, and T'way field case. Providers receive `web-protocol-recovery-provider-work-order/v1` and return `web-protocol-recovery-provider-result/v1` (schema in `references/methodology/provider-work-order.md`). web-protocol-recovery remains the owner of methodology, scope, project root, layout, acceptance, and browser-free delivery.

## Cases

The root registry indexes 21 hash-bound `web-protocol-recovery-case/v1` manifests grouped by runtime: 16 `iv8`, one `pure-python`, and four `python-node` evidence cases. All historical cases require fresh current-target verification. `secretPolicy=redacted-pull-live` preserves state names and structure but no cookie/token values.

## Runtime Helpers

Reverse-engineering helpers under `scripts/` are optional aids, not gates:

```cmd
python scripts\check_reverse_env.py
python scripts\crypto_fingerprint.py <sample>
python scripts\protocol_diff.py <capture-a> <capture-b>
python scripts\providers\python-collector\scaffold_project.py <project-root> --entry --cache
```

`scripts/providers/cases/live_state.py` backs each case's `pull_live_state.py` for in-memory credential pulls. web-protocol-recovery-specific deposition and dedup rules live in `references/methodology/knowledge-maintenance.md`.
