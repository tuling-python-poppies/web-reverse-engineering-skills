# Verifier Provider

## Select When

- Target is verifier-gated: a distinct proof round authorizes the business request.
- One coherent verifier round is frozen (assets, tokens, coordinate space, success predicate).

## Do Not Select When

- The gate is still unclassified or no coherent verifier round has been frozen; classify and capture one round first.
- Mixing tokens/images/proof fields across adjacent rounds.
- Live verify without work-order permission for live replay and verifier action class.

Use this provider after web-protocol-recovery classifies the target as verifier-gated and freezes one coherent verifier round. It implements perception and proof-input preparation; web-protocol-recovery retains protocol ownership and iv8 may implement the official browser runtime proof builder.

Read `references/replay-playbook.md` for family-specific round binding, perception, coordinate normalization, and proof-input procedures.

Required inputs are provider/product/version/subtype, get/load and verify request shapes, one-round state, asset dimensions, coordinate spaces, proof-builder evidence, authorization, and an objective success predicate.

Prefer local `ddddocr` for OCR, detection, slider matching, and comparison. Use Pillow/OpenCV for bounded preprocessing, contour, template, and difference fallbacks. Normalize library-version result shapes before applying target formulas; missing confidence, coordinates, or unsupported field types fail closed and require independent corroboration. OCR, boxes, and offsets are candidates only; success requires the verifier's semantic response and, when relevant, the linked business request.

Transient challenge images remain under `js_reverse_cache/source/`. Promote only sanitized deterministic fixtures. Stop before live verify when confidence is zero, tied, or below the case threshold. Never mix tokens, callbacks, images, or proof fields from adjacent rounds.
