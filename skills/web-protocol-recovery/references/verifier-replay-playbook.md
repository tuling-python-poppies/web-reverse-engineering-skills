# Verifier Replay Playbook

Thin entry only. Do not treat this file as the full method.

## When

- business traffic waits on captcha, one-shot verification, or click-order challenges
- there is no meaningful business signer, but requests fail until a verifier passes
- UI clicks appear to unlock the next request

## Rule

Verifier output is the real dynamic parameter. Final delivery is protocol replay, not UI automation.

## Next read (exactly one)

`references/providers/implementation/verifier/references/replay-playbook.md` for family binding, freeze-one-round, JSONP framing, coordinate/proof packaging, and local solver notes.

Implementation work order: `references/providers/implementation/verifier/PROVIDER.md`.
