# pure-python Runtime Cases

This directory holds cases whose protocol artifact is produced by pure Python
with no JavaScript runtime. Current registered cases include `jd-h5st`, a
freshly verified Python-only implementation in the root registry.

Future browser-free algorithm cases (for example self-contained signers,
decoders, or checksums that port cleanly to Python) are written back here
through the root registry and `references/methodology/case-writeback.md`.

A case in this directory uses the same `web-protocol-recovery-case/v2` manifest
as every other runtime, with `runtime: pure-python`, `implementation.mode:
pure-python`, `secretPolicy: redacted-pull-live`, and a declared
`pull_live_state.py` only when the case actually consumes live cookie or storage
state.
