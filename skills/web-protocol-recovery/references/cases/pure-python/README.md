# pure-python Runtime Cases

This directory is reserved for cases whose protocol artifact is produced by
pure Python with no JavaScript runtime. It currently holds zero cases, which is
expected: cases eligible for the iv8 and Camoufox corpora inherently needed a
JS runtime, so none of them belong here.

Keep this directory as a forward-looking slot. A future browser-free algorithm
case (for example a self-contained signer, decoder, or checksum that ports
cleanly to Python) is written back here through the root registry and
`references/methodology/case-writeback.md`.

A case in this directory uses the same `web-protocol-recovery-case/v1` manifest
as every other runtime, with `runtime: pure-python`, `secretPolicy:
redacted-pull-live`, and a declared `pull_live_state.py` only when the case
actually consumes live cookie or storage state.
