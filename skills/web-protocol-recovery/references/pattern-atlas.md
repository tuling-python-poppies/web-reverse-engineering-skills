# Pattern Atlas

Use this file only when a recurring symptom is already visible and you need the shortest first move. It is an index, not a second playbook: load at most the named owner after selecting a row.

## Symptom Index

| Symptom | First move | Owner |
|---|---|---|
| `200` shell, empty hydration, or success flag without business payload | capture the first business-data request and validate response shape | `decoy-and-real-request-playbook.md` |
| Page code names one endpoint but wire traffic uses another | trust the network route and trace its initiator | `decoy-and-real-request-playbook.md` |
| Visible params differ from final query/body/header slots | diff business input against transport egress | `transport-wrapper-playbook.md` |
| Named `md5`/`btoa`/AES helper disagrees on fixed input | freeze browser/local intermediates before using the helper | `crypto-patterns.md` |
| First response is JS, `202`/`412` HTML, WASM/font, or linked challenge assets | freeze one coherent chain and derive/harvest state locally | `challenge-state-envelope-playbook.md` |
| Runtime getter, serializer, packer, or XHR/fetch egress already has the artifact | harvest that nearest stable boundary | `challenge-state-envelope-playbook.md` |
| Passive public key/config/nonce precedes a wrapped anonymous request | prove exact envelope build order | `public-bootstrap-envelope-playbook.md` |
| Entry HTML, cookie, URL/body/response fields share packet markers | separate state chain, framing, and inner crypto | `challenge-state-envelope-playbook.md` |
| Cookie blocks replay but writer/refresh path is unknown | attribute `Set-Cookie`, JS writes, and wire consumption | `cookie-provenance-playbook.md` |
| Session exists but business route rejects, redirects, or changes tenant/shop/org | separate identity, admission, and active context | `session-contract-playbook.md` |
| Anonymous flow fails only after logged-in state is added | rebuild one clean anonymous session chain | `session-contract-playbook.md` |
| Output shortens or branches on navigator/DOM/reflection/native surfaces | trace missing reads before patching | `environment-patch-playbook.md` |
| Full host semantics remain necessary after narrow environment proof | isolate one artifact in an embedded runtime | `embedded-browser-runtime-playbook.md` |
| TLS/ALPN/UA/HTTP-version failure occurs before meaningful application data | map a narrow admission matrix | `transport-pre-gate-playbook.md` |
| Normal HTTP status carries gibberish, compressed bytes, glyphs, or encoded strings | freeze raw payload and trace its first consumer | `response-decode-playbook.md` |
| GraphQL operation, WebSocket frames, protobuf/msgpack, or binary envelope owns the contract | separate transport envelope from business fields | `structured-transport-playbook.md` |
| One-shot captcha/verifier token gates the business request | preserve one coherent round and split protocol/compute/perception/behavior | `providers/implementation/verifier/references/replay-playbook.md` |
| Restored pixels look correct but submitted coordinates fail | map restored, displayed, and submitted coordinate spaces | `providers/implementation/verifier/references/replay-playbook.md` |
| Early pages work but later pages switch route family | capture cutoff and use raw pager targets | `pagination-route-pivot-playbook.md` |
| Only one page/request needs different headers, cookie refresh, or ordering | encode the exception narrowly | `page-specific-exception-playbook.md` |
| Parsed DOM attributes corrupt replay-critical query bytes | compare raw source, parsed value, and wire | `offline-inline-deob-playbook.md` |
| Real flow lives in iframe/worker/callback/mail/SMS/webhook | identify owning frame/channel and establish observation baseline | `tool-playbook.md` |
| Stateful stream needs pairing/login, keys, heartbeat, counters, or media derivation | freeze one full successful transcript | `stateful-stream-e2ee-playbook.md` |
| Tight pacing changes known failures into field/password-like errors | stop, cool down, and compare one bounded request | `troubleshooting-playbook.md` |
| Helper loads but fixed outputs still mismatch | return to fixed-input comparison; runtime health is not protocol proof | `troubleshooting-playbook.md` |
| A shortcut proposes browser-backed delivery, pasted live state, broad hooks, or rung skipping | run the direct self-check before editing | `anti-patterns-playbook.md` |

For broad invariants rather than a visible symptom, use `doctrine-index.md`. For exact routing paths, use `reference-router.md`.
