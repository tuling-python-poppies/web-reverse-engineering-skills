# Verifier Provider

## Select When

- Target is verifier-gated: a distinct proof round authorizes the business request.
- One coherent verifier round is frozen (assets, tokens, coordinate space, success predicate).
- Work order allows the `verifier` action class; live verify additionally needs `liveReplayAllowed`.

## Do Not Select When

- The gate is still unclassified or no coherent verifier round has been frozen; classify and capture one round first.
- Mixing tokens/images/proof fields across adjacent rounds.
- Live verify without work-order permission for live replay and verifier action class.
- User only wants evidence of “there is a captcha” (return blocker; do not solve).

Use this provider after web-protocol-recovery classifies the target as verifier-gated and freezes one coherent verifier round. It implements perception and proof-input preparation; web-protocol-recovery retains protocol ownership and iv8 may implement the official browser runtime proof builder.

Architecture boundary: web-protocol-recovery owns route choice, `projectRoot`, layout, acceptance, and final delivery. This provider only writes assigned verifier assets/fixtures under `web-protocol-recovery-simple/v1`, then returns candidate proof inputs, confidence, and semantic verifier evidence.

## Inputs

Required: provider/product/version/subtype, get/load and verify request shapes, one-round state, asset dimensions, coordinate spaces, proof-builder evidence, authorization, and an objective success predicate.

Family-specific round binding, perception, coordinate normalization, and proof-input procedures: `references/replay-playbook.md` (read only when this work order names it).

## Workflow

1. Freeze one round: challenge id/token, image/asset bytes or paths, coordinate space, and success predicate. Discard any field from a previous round.
2. Perceive locally: prefer `ddddocr` for OCR, detection, slider matching, and comparison; use Pillow/OpenCV for bounded preprocessing, contour, template, and difference fallbacks.
3. Normalize library-version result shapes before applying target formulas. Missing confidence, coordinates, or unsupported field types fail closed and require independent corroboration.
4. Build proof inputs only; do not own the final business HTTP unless the work order explicitly assigns a python-collector handoff of those fields.
5. Live verify only when both live replay and the `verifier` action class are approved. Stop before live verify when confidence is zero, tied, or below the case threshold.

OCR, boxes, and offsets are candidates only. Success requires the verifier's semantic response and, when relevant, the linked business request.

## Artifacts

| Kind | Path |
|---|---|
| Transient challenge images | `js_reverse_cache/source/` |
| Sanitized deterministic fixtures | `js_reverse_cache/samples/` or stable `tests/` |
| Proof-input samples (redacted) | work-order allowed paths only |

Promote only sanitized deterministic fixtures. Never store raw account secrets in the skill or case library.

## Acceptance

1. One-round binding: no mixed tokens/images/proof fields.
2. Perception output includes confidence (or explicit fail-closed reason).
3. Offline fixture/vector check when available.
4. Live verify (if approved): verifier semantic success, not only HTTP `200`.
5. Linked business request (if in scope) succeeds with regenerated proof fields.

## Exit

Return: product/version/subtype, proof-input shape, confidence, fixture paths/hashes, live verify state (or offline-only), and the next hub action (python-collector integration, another Provider, or stop).

## Failure Recovery

| Trigger | First fix | Still fails → stop |
|---|---|---|
| Round not frozen / fields mixed | Recapture one coherent round | Blocker: round binding |
| Confidence zero/tied/low | Retry perception or independent corroboration | No live verify |
| Library shape mismatch | Normalize result schema; pin versions | Fail closed |
| Live verify denied | Stay offline with fixtures | Do not submit |
| Semantic fail after live | Diff challenge markers / coordinate space / token age | Do not scale or re-submit blindly |
