# Positive Sample Hygiene Playbook

Use this when verifier-gated recovery depends on human/browser oracles, especially behavior-sensitive sliders, click orders, risk-scored transcripts, or telemetry sidecars.

Browser tooling is evidence only. Final delivery remains browser-free and Python-owned.

## Why It Matters

A real human action inside an automation-owned browser can still fail because the environment is already contaminated. Common contaminants:

- CDP or remote-debugging ownership
- broad hooks, global function patches, stringify interceptors, or breakpoint side effects
- brand-new empty profiles with no ordinary browsing age
- consecutive rejects on one exit IP or session chain
- mixed success and failure rounds in one capture dump

Contaminated failures are useful environment evidence. They are weak proof that a trajectory, answer, coordinate map, or proof algorithm is wrong.

## Sample Grades

| Grade | Meaning | Authority |
|---|---|---|
| `clean-success` | Ordinary browser or non-instrumented path accepted by verifier and first downstream consumer | highest positive oracle |
| `clean-failure` | Ordinary path failed with no automation ownership | strong negative for protocol or risk policy |
| `contaminated-failure` | Automation, hooks, debug ports, poisoned profile, or exit reputation likely involved | environment evidence first |
| `partial` | Missing sidecars, final verify body, semantic success body, or downstream consumer | incomplete |

Never promote `contaminated-failure` into "trajectory family rejected" without a clean contrast sample.

## Capture Preference

From strongest to weakest positive oracle:

1. operator's ordinary browser, no automation attachment, redacted export of the full verifier round plus first successful business response
2. non-instrumented listen-only capture with no page hooks
3. automation browser used only to open the page, accepted only when ordinary capture is impossible and contamination is recorded
4. hooked automation capture for initiator and field discovery only

When protocol replay is stuck and a clean success sample is needed, ask only for the missing sample: exact URLs/actions, a redacted Network export of the verifier round, and the first downstream consumer response. If raw token/cookie values must be exported or persisted, stop with `nextAsk: raw-secret-handling` and record the exact fields, absolute allowlisted private path, repository exclusion, and retention deadline. User-supplied state may be inspected in memory without silently granting raw persistence.

## Minimum Usable Success Sample

- ordered requests with elapsed offsets
- init/load response family
- required sidecar requests and acknowledgements
- final verify/check request and semantic success response
- answer or track payload when behavior-sensitive
- first downstream consumer request and pass body
- active helper/script hashes when dynamic assets are involved
- environment notes: ordinary versus automation, hooks on/off, exit changed or not

## Use Rules

- diff `clean-success` against protocol replay before tuning behavior
- use `contaminated-failure` to identify environment risk, not as algorithm rejection
- rebuild fixed vectors from clean success boundaries when possible
- if only contaminated samples exist, limit claims and keep live acceptance blocked

## Hard Bans

- do not tune tracks solely against automation hand-slide failures
- do not inject broad hooks on the only positive path just to make capture easier
- do not mix grants from a success round into a later failed round
- do not call a sample complete when the downstream consumer is missing

## Exit Notes

Report sample grade, capture path, whether environment risk is implicated, and which clean boundaries were promoted into fixed vectors.
