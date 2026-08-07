# Reference Router

Read focused generic references when the symptom matches. First response loads 0-2 paths; one named blocker may add one path inside the current dispatch window. Hard window and whole-task caps: `references/methodology/read-budget.md`. Default paths: `references/methodology/success-shape-scripts.md`.

## First Load Rules

1. Name success shape or current blocker before opening any playbook.
2. Prefer the selected `PROVIDER.md` over generic essays.
3. First response: 0-2 paths; the initial dispatch window caps at 3 after one blocker expansion.
4. Never preload the whole tree, all cases, or sibling playbooks "just in case".
5. Do not open Camoufox for ordinary evidence-only work, but preserve a direct Camoufox route when the user explicitly requests Camoufox/SpiderMonkey or recorded second-engine criteria are already met. Do not open collector/layout docs with no write planned.
6. When escalating, add exactly one path and state why.

## Core (start / route / stop)

- `references/methodology/success-shape-scripts.md` for default first path by deliverable
- `references/methodology/architecture.md` when ownership, Provider boundaries, or project shape is unclear
- `references/methodology/read-budget.md` when tempted to load more files
- `references/startup-triage-playbook.md` when the target is fresh and the first question is "what kind of fight is this?"
- `references/workflow-overview.md` for the shortest end-to-end execution map
- `references/escalation-ladder-playbook.md` when a partial proof tempts a heavier layer
- `references/anti-patterns-playbook.md` when a shortcut feels faster than evidence
- `references/delivery-gate-playbook.md` when deciding handoff vs still cheating
- `references/tool-playbook.md` for tool choice and next-step routing
- `references/report-templates.md` for phase reporting (light vs full by success shape)
- `references/verification-gates.md` for acceptance checks

## Request Path And Wrapper Mutation

- `references/decoy-and-real-request-playbook.md` when the page and the wire disagree on the real endpoint
- `references/transport-wrapper-playbook.md` when transport wrappers rewrite params, headers, or payloads
- `references/multi-writer-field-playbook.md` when one field has disjoint value shapes, more than one writer path, or a locally proved writer never appears on accepted wire traffic
- `references/crypto-patterns.md` when signatures or standard-looking helper outputs do not match fixed inputs
- `references/obfuscation-guide.md` when packed code or string tables dominate the bundle

## Cookies, Bootstrap State, And Sessions

- `references/providers/protocol-recovery/akamai/PROVIDER.md` when Akamai-native markers such as `_abck`, `bm_sz`, `ak_bmsc`, `bm_s`, `bm_sc`, `sbsd_c`, `cpr_chlge`, `sensor_data`, `/akam/13/pixel_*`, or a confirmed random-path collector have independent corroboration. The Provider owns cookie transitions, sensor/Pixel separation, transport coherence, host-local fingerprint policy, and local collector execution acceptance.
- `references/providers/protocol-recovery/river-security/PROVIDER.md` when River Security / 瑞数 markers such as `$_ts.nsd`, `$_ts.cd`, `<script r="m">`, dynamic `_$...()` entry, HTTP `412` plus S/T cookies, or URL/header challenge-state mutation have independent corroboration. A vendor guess or `412` alone is not enough.
- `references/providers/protocol-recovery/reese84/PROVIDER.md` when one Reese84-native marker such as a `reese84` cookie, `x-d-token` projection, `initializeProtection` challenge script, or `token` + `renewInSec` + `cookieDomain` solution response has independent network/script/cookie-transition/business-consumer corroboration. Generic Imperva/interstitial/error-15 evidence is not enough.
- `references/cookie-provenance-playbook.md` when a cookie is blocking replay but the writer or refresh path is still unclear
- `references/session-contract-playbook.md` when results or submission are account-bound
- `references/public-bootstrap-envelope-playbook.md` when a public page needs passive keys, config, nonce, entry cookies, or an encrypted wrapper
- `references/challenge-state-envelope-playbook.md` for executable challenge, harvest boundary, server-JS cookie double-call, or tiny side assets (single canonical file for that family)

## Host-Bound Runtime And Local Execution

- `references/environment-patch-playbook.md` for browser-vs-local triage, redirect/wrapper layers, and minimal host patches
- `references/embedded-browser-runtime-playbook.md` when host-visible JavaScript semantics are needed without a full browser
- `references/providers/implementation/iv8/PROVIDER.md` after the embedded-runtime playbook selects `iv8`; the Provider routes to its runtime cheatsheet after API verification
- `references/hook-techniques.md` when runtime proof is faster than static reading
- `references/offline-inline-deob-playbook.md` when live inspection is unstable, anti-debug noise is high, or inline/eval-packed code must move offline
- `references/opaque-runtime-profile-playbook.md` when stage-level transforms require one coherent runtime profile, fragments from separate runs fail when combined, or delivery class must distinguish algorithmic/profile-driven/artifact-pool behavior

## Transport, Decode, And Structured Payloads

- `references/transport-pre-gate-playbook.md` when TLS, ALPN, UA, HTTP version, or route admission blocks semantics before signer/cookie analysis
- `references/native-transport-profile-playbook.md` only after the transport pre-gate proves the nearest maintained impersonation backend cannot express one observed TLS/H2/connection field
- `references/response-decode-playbook.md` when the payload needs local decode before it becomes usable data
- `references/structured-transport-playbook.md` when GraphQL, WebSocket, gRPC/grpc-web, protobuf, msgpack, or binary envelopes carry the real contract
- `references/jsvmp-analysis-playbook.md` when a custom VM or bytecode interpreter hides the logic

## Verifiers, Pagination, And Narrow Exceptions

- `references/providers/protocol-recovery/verifier/PROVIDER.md` when captcha or one-shot verification is the protocol gate. The Provider owns the captcha family router; after it is loaded, read exactly one selected family reference such as Geetest, Tencent TDC, Aliyun V2/V3, Ctrip, ByteDance VerifyCenter, Yidun, Shumei, Yunpian, 360 Tianyu, generic `replay-playbook.md`, or `positive-sample-hygiene-playbook.md` when automation ownership, hooks, debug ports, profile age, or exit reputation may contaminate the sample.
- `references/pagination-route-pivot-playbook.md` when later pages pivot route families or raw pager metadata beats parsed DOM
- `references/async-export-job-playbook.md` when create/poll/download is a task state machine and this run needs new-task proof plus file-completeness gates
- `references/page-specific-exception-playbook.md` when only one page or one request behaves differently
- `references/troubleshooting-playbook.md` when replay logic is almost correct but still unstable
- `references/stateful-stream-e2ee-playbook.md` when login, pairing, session keys, keepalive frames, or media decryption make the stream stateful

## Doctrine And Pattern Indexes (when still broad)

- `references/doctrine-index.md` for family-level invariants
- `references/pattern-atlas.md#symptom-index` for symptom -> first move
- `references/minimal-verifiable-facts-playbook.md` when durable facts must be recorded
- `references/reproducible-evidence-playbook.md` when captures must be normalized without reusable state, accepted/rejected chains need a first-divergence proof, or a deterministic negative control is required

## Maintaining This Skill (not ordinary protocol tasks)

- `references/methodology/knowledge-maintenance.md`
- `references/official-self-test-task-suite.md` — self-test only; never first-load on live recovery work
- `references/methodology/forward-testing.md` — fresh-runner and independent-reviewer evidence for behavioral claims after skill edits
- `references/methodology/provider-work-order.md`
- `references/methodology/project-layout.md`
- `references/methodology/case-writeback.md`
