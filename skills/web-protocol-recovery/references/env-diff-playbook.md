# Environment-Diff Playbook

Thin entry only. Prefer the canonical environment playbook on first load.

## When

- redirect/wrapper page may rewrite path/headers/body/cookies
- browser vs local outputs disagree on fixed inputs
- Node/Python still differs after obvious patches

## Next read (exactly one)

`references/environment-patch-playbook.md` — start at **Triage before patching**. Helper name looks standard but fixed inputs disagree → `patched-helper-playbook.md` then `crypto-patterns.md` only as a later expansion. Implementation: `providers/implementation/env-patch/PROVIDER.md`.
