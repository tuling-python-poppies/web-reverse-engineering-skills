# Patched Helper Playbook

Thin entry only.

## When

- helpers named `md5`, `btoa`, `atob`, `sha1`, or similar disagree with standard libraries on fixed inputs

## Rule

Names do not prove behavior. Fixed-input validation does. Ship fixed-input self-checks with the collector.

## Minimum loop

1. freeze input (e.g. `"abc"` or captured timestamp)
2. record live helper output
3. run local candidate
4. compare intermediates and final
5. classify standard / patched / custom

## Next read (exactly one)

`references/crypto-patterns.md` for algorithm families. Broader env triage: `environment-patch-playbook.md`.
