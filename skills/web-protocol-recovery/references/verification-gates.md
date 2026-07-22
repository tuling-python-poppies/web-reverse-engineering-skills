# Verification Gates

Use this checklist before marking a protocol recovery task complete. Apply only the gates relevant to the target family; explicitly mark skipped or blocked gates in the report.

## Core Gates

- startup gate completed and updated if the target classification changed
- request path confirmed
- moving parts classified
- target family classified and initial routing recorded
- canonical mutation point identified
- selected reconnaissance Provider and reason recorded
- on the Chromium route, ordinary first-pass evidence used `js-reverse-mcp` normal Chrome headless, or a visible Chrome DevTools baseline was explicitly approved and documented
- on direct Camoufox or WeChat routes, Provider ownership, target lifecycle, durable evidence, and cleanup recorded instead of claiming Chromium passes
- dual browser reconnaissance, when used, ran sequentially with isolated browser contexts/profiles, or explicit profile reuse and contamination risk were documented
- relevant MCP capabilities considered through `references/tool-playbook.md` before declaring a tooling blocker
- clean baseline captured before invasive tooling when the target is verifier-gated or behavior-sensitive; visible Chrome DevTools baseline requires explicit window/baseline approval
- normal-Chrome baseline captured before any CloakBrowser escalation on the Chromium route without upstream evidence, unless normal Chrome was unavailable and that blocker is documented
- normal `js-reverse-mcp` use, if any, was launched with `launch_browser({headless:true, cloakBinaryPath:""})` and no visible ordinary-browser window; otherwise the task records an explicit visible-browser approval or tooling blocker
- CloakBrowser use, if any, has explicit fingerprint, anti-bot, or environment-verification evidence and was done through `launch_browser({headless:false, cloakBinaryPath: "..."})` on `js-reverse-mcp` unless the user explicitly asked for hidden Cloak

## Replay And Helper Gates

- helper outputs verified on fixed inputs
- structured transport rules documented when the target is not plain JSON
- response decode steps are local and repeatable when the payload is not directly readable
- fixed-sample checks exist for local decoders when decode is part of the contract
- bootstrap artifact replay confirmed when public routes still require key, config, cookie, or wrapper seeding
- server-issued artifacts cataloged separately from locally computed or locally minted artifacts before local reimplementation
- cookie provenance proven when rotating cookies gate replay
- cookie provenance, slot placement, and session-chain integrity proven when they matter
- login or pairing bootstrap replay confirmed when the target needs a warm session before business traffic
- embedded runtime use, if any, proven by fixed inputs, explicit artifact extraction, Python-owned live egress, and a clear browser-free versus runtime-free handoff
- escalation-ladder reasoning recorded before any heavier runtime, broader patch surface, or transport exception was introduced

## Stateful, Transport, And Verifier Gates

- key schedule or session-secret derivation verified on captured samples when the stream is encrypted
- heartbeat, ack, counter, or message-tag rules documented when the stream is stateful
- raw frame parsing and business decode proven on at least one exact captured frame
- media-key derivation documented when file download or decryption uses separate secrets
- transport-gated route families documented with the narrow admission profile and route-local scope
- challenge-generated envelope families documented with framing, checksum, alphabet, state dependency, inner cipher, and payload anchor
- pagination route pivots and raw-source route metadata documented when later pages stop matching first-page arithmetic
- verifier-gated or challenge-bootstrap targets proved one fresh minimal live replay on one session chain before broad environment patching, runtime shrink, pagination scaling, or reuse generalization

## Delivery Gates

- `compact-replay` has one approved semantic live replay; `collector` repeats the minimal request or proves the next cursor/page before scale
- pagination or cursor advance confirmed when in scope
- account-bound constraints documented
- list-versus-detail permission boundaries documented when access levels differ
- page-specific exceptions documented
- final Python collector or local protocol client runs without browser automation or browser profiles
- final JS helper, if any, runs locally without browser automation or DOM dependence
- output saved in the requested format
