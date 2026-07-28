# Startup Triage Playbook

Use this reference at the start of every fresh target.

The goal is to decide what kind of fight this is before you load giant bundles or poison the page with broad hooks.

Default first paths by deliverable: `references/methodology/success-shape-scripts.md`. Reference load caps: `references/methodology/read-budget.md`. Do not load this whole playbook when a success-shape script already names the next single action.

## Startup gate

Complete these four checks first:

1. reconnaissance route and tool sanity
    - select Chromium, Camoufox, or WeChat before launching; explicit Camoufox and WMPF requests bypass the Chromium ladder
    - on Chromium: confirm whether both `chrome-devtools` and `js-reverse` are usable; fresh targets require a **mandatory lightweight paired pass** (DevTools baseline then js-reverse mutation) before the final collector unless a real blocker or documented exception applies
    - run `scripts/check_reverse_env.py` when local execution is available
    - follow `references/tool-playbook.md` Browser Lifecycle for serialized Chromium phases, profile isolation, headful exceptions, Cloak tier, and cleanup
    - note local iv8 or transport-client availability only when host-bound bootstrap or transport admission is suspected
    - report blockers instead of warming multiple engines to test availability; do not skip a paired half silently
2. artifact directory discipline
    - complete `references/methodology/project-layout.md` before the first write; do not create a root or cache implicitly
    - save approved dynamic materials only under the selected project's `js_reverse_cache/`
    - keep stable collector code at root `main.py`, with optional helpers under `utils/`; do not create a mandatory `collector/` tree
3. family triage
    - choose the first family that explains the failure mode best
    - before loading a family-specific scaffold or playbook, corroborate the family across at least two evidence surfaces such as response shape, cookie behavior, runtime markers, script traits, or wire behavior
    - add the secondary tag `transport-gated` when TLS, ALPN, UA, HTTP version, or route-local admission blocks the clean baseline before application semantics are visible
    - if the family changes after new evidence, restate it explicitly
4. delivery intent
   - state the smallest acceptable final shape
    - reject browser-backed replay, profile-bound state, and automation-driven submission up front

## Escalation ladder before full browser dependence

Use the smallest faithful layer that explains the evidence:

1. simple decode or standard algorithm: handwrite in Python first
2. host-bound JavaScript without true interaction: route to `references/embedded-browser-runtime-playbook.md`
3. full interaction or rendering dependence: observe in browser, but keep the delivery gate strict and do not confuse observation with the final collector

For the full rung-by-rung rule, proof requirements, and "do not jump layers" contract, read `references/escalation-ladder-playbook.md`.

## Family triage

### `signer-gated`

Symptoms:

- one or more request fields change every time
- the server rejects stale `sign`, `m`, `token`, header, or wrapper output
- the request initiator points into wrapper or helper logic

First move:

- capture one good request
- trace the initiator
- locate the canonical mutation point
- if the field collapses to a standard digest, compact JSON, or obvious packet format, handwrite it in Python before touching any runtime
- if the code reads host objects, lifecycle state, timers, or XHR wrappers, route to `references/embedded-browser-runtime-playbook.md`

Primary references:

- `references/transport-wrapper-playbook.md`
- `references/crypto-patterns.md`
- `references/embedded-browser-runtime-playbook.md` when host semantics matter

### `challenge-gated`

Symptoms:

- the first meaningful response is challenge HTML/JS such as `202` or `412`
- server seed cookies plus client-derived cookies decide admission
- challenge JavaScript rewrites URL suffixes, headers, body fields, or replay state before business data is visible
- River Security markers appear: `$_ts.nsd` / `$_ts.cd`, `<script r="m">`, dynamic `_$...()` entry, or paired server `*S` + generated `*T` cookies

First move:

- freeze one coherent challenge chain: first response, headers, `Set-Cookie`, challenge HTML, linked scripts, generated state, and second request delta
- do not classify from `412` or a user hypothesis alone
- for River Security, read `references/providers/protocol-recovery/river-security/PROVIDER.md` before selecting a case or runtime
- for generic challenge bootstrap, read `references/challenge-state-envelope-playbook.md`
- use Chromium recon by default; River Security is not a Camoufox criterion

Primary references:

- `references/providers/protocol-recovery/river-security/PROVIDER.md` for confirmed River Security / 瑞数 markers
- `references/providers/protocol-recovery/akamai/PROVIDER.md` for confirmed Akamai markers
- `references/challenge-state-envelope-playbook.md` for unclassified executable challenge state
- `references/cookie-provenance-playbook.md` when the writer or refresh order is unknown

### `transport-gated` (secondary tag)

Symptoms:

- standard HTTP clients fail at H2 reset, TLS EOF, handshake timeout, or early disconnect before meaningful application data appears
- the same route behaves differently across UA families, HTTP versions, ALPN, or client stacks
- impersonated transport or mobile or app UA passes while default desktop or stdlib traffic fails
- a sibling auth, identity, or business route bypasses a challenged landing route

First move:

- freeze a small admission matrix across route, client stack, UA family, and HTTP version
- find one narrow profile that admits the baseline cleanly
- test route-local bypasses before loading giant bundles
- continue normal family triage only after application semantics become visible

Primary references:

- `references/transport-pre-gate-playbook.md`

### `verifier-gated`

Symptoms:

- the business request only works after a captcha/verifier, one-shot verification token, or warm-up step
- the page starts failing once hooks or breakpoints are installed
- there is no meaningful business signer, but a token, cookie, or coordinates appear after a separate request

First move:

- capture a clean untouched baseline before invasive instrumentation
- diff requests and verifier outputs first
- only then add the narrowest hook that proves the boundary
- if challenge HTML plus scripts appear to seed a cookie, URL suffix, or headers, route to `challenge-gated` first
- if a bootstrap runtime exposes a getter after init or self-issues the decisive request, route to `references/challenge-state-envelope-playbook.md`

Primary references (pick one first path):

- `references/providers/protocol-recovery/verifier/references/replay-playbook.md` when captcha/one-shot verification is the gate
- `references/challenge-state-envelope-playbook.md` when a bootstrap getter/egress already has the artifact
- `references/troubleshooting-playbook.md` when replay is close but unstable
- later only if needed: verifier PROVIDER, cookie-provenance, embedded-browser-runtime

### `decode-gated`

Symptoms:

- the request succeeds, but the payload stays unreadable
- the body needs glyph mapping, decompression, protobuf, Base64, or layered decode
- fonts, side assets, or tiny helper functions decide whether the response becomes usable

First move:

- freeze the raw payload first
- locate the first consumer of the unreadable data
- rebuild the decode chain locally before scaling collection

Primary references:

- `references/response-decode-playbook.md`
- `references/challenge-state-envelope-playbook.md`
- `references/structured-transport-playbook.md` when the payload sits inside a binary envelope

### `session-gated`

Symptoms:

- login, pairing, subscribe, heartbeat, or reconnect order decides success
- auth appears once, but later frames fail unless counters, tags, or keys stay in order
- media download or decryption needs secrets derived from prior traffic

First move:

- freeze one full successful transcript
- separate handshake, keepalive, and business frames before reading payload semantics
- rebuild one stable local session before adding scale

Primary references:

- `references/stateful-stream-e2ee-playbook.md`
- `references/structured-transport-playbook.md`
- `references/session-contract-playbook.md`

## Observer-effect rule

If hooks, breakpoints, or monkey patches make the target behave differently, assume your tooling may be changing the sample.

In that case:

1. revert to the cleanest possible capture
2. save one untouched request and response pair
3. move hooks outward toward the transport boundary
4. prefer initiator stacks and request diffs over broad global monkey patches

Do not call the target "browser-only" until you have ruled out your own instrumentation.

## CloakBrowser escalation rule

Do not switch merely because the target is a JS reverse task. Follow `references/tool-playbook.md#cloakbrowser-and-explicit-visibility-exceptions`; explicit fingerprint-browser wording selects CloakBrowser through js-reverse, never Camoufox, and persistent configuration remains a separately confirmed write.
