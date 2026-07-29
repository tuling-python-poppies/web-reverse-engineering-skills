# Official Self-Test Task Suite

Use this file when validating whether `web-protocol-recovery` still behaves like a protocol-first reverse skill after edits.

## How to use the suite

For each task:

1. feed the prompt as if it came from a user
2. check which references and scripts the skill would read or run
3. verify the proposed delivery shape
4. fail the test if the answer drifts into browser automation as final delivery

Legacy `Expected route` headings below mean expected reference owners, never the canonical `route:` field and never permission to read every listed file in one dispatch window. Canonical routes are short Provider IDs or `evidence-reuse` only. Apply `references/methodology/read-budget.md`: a first response reads 0-2 paths, one named blocker may add exactly one path once, and later listed references require a new accepted Provider result, user answer, or blocker expansion.

## Pass criteria across the whole suite

- authorization/scope is recorded before the first browser navigation or live egress; unknown authorization remains offline
- raw artifacts are opt-in, gitignored, access-scoped, and retention-bounded; metadata/redacted evidence is the default
- generated collectors bound pages, retries, timeout, response bytes, backoff, and concurrency; mutations are not retried without an idempotency contract
- generated transport disables implicit environment proxies, preserves CookieJar domain/path scope, and declares TLS/CA/redirect ownership
- scaffold updates reject symlinks, junctions, hard links, and incomplete ignore rules; they never overwrite existing files and publish new files atomically
- generated outputs are exclusive by default, atomically published, and CSV-safe
- the mandatory four-line protocol header is emitted first on protocol tasks; the startup gate follows with only applicable fields on fresh targets
- blocked tools are reported explicitly instead of being silently skipped
- paired `chrome-devtools` and `js-reverse-mcp` recon stays sequential and profile-isolated unless explicit profile reuse is requested and documented
- dual recon is lifecycle-exclusive: no cross-family parallel preflight; fresh Chromium targets complete a **mandatory paired pass** (chrome-devtools baseline then js-reverse mutation) before the final collector unless a real blocker or documented exception applies; js-reverse mutation uses explicit headless launch unless the user asks for a visible ordinary browser; a no-window exception may skip only the visible DevTools window; Chrome is honestly reported as parked when its last page cannot close; visible CloakBrowser is used only after explicit/fingerprint selection (optional third tier) unless the user asks for hidden Cloak; js-reverse closes before a return to Chrome
- final delivery stays pure protocol
- Python remains the preferred collector language
- generated collector scaffolds remain Python 3.9+ compatible and support `python main.py` from the project root
- missing evidence requests stay minimal
- the skill identifies the real protocol contract, not just a `sign` function
- structured transport and decode-chain cases route correctly
- cookie provenance is made explicit when rotating cookies gate replay
- transport pre-gates are separated from signer/cookie/decode problems before app semantics are visible
- embedded runtime and iv8 routes stay browser-free, local, narrow, and subordinate to Python-owned live egress
- challenge artifact harvest is preferred over broad DOM patching when a getter, egress request, wrapped body, token, or outbound Cookie is already visible
- escalation ladder proof is required before moving to a heavier runtime, broader patch surface, or transport exception
- pagination route pivots and raw-source route metadata are treated as protocol state when later pages diverge
- reusable wins preserve 5 to 15 minimal verifiable facts instead of copied volatile artifacts
- environment-mismatch cases distinguish missing surfaces, load-order contracts, and host-object contract gaps, and do not treat load success as final proof
- delivery-gate cases allow declared host-like config inputs, reject runtime-backed import contamination, and separate deterministic proof mode from live-generation mode
- startup and bootstrap cases require corroborated family evidence, preserve one session chain when challenge state matters, and keep stable scaffolding separate from volatile captures
- escalation follows one rung at a time, with the prior rung's exact failure made explicit before widening runtime, patch surface, or transport exceptions
- recurring shortcut temptations route to the anti-pattern library instead of being hand-waved as "temporary" exceptions

## Task 0: Fresh target with one blocked tool

Prompt:

```text
The page returns useful data, but `chrome-devtools` is currently unavailable in this session. I still need the collector. Show me how you start.
```

Expected route:

- `references/startup-triage-playbook.md`
- `references/tool-playbook.md`

Must conclude:

- emit the startup gate first
- report the blocked tool explicitly as a **missing paired-pass half** (chrome-devtools)
- still classify the target family and intended final delivery shape
- do not pretend the missing tool already proved anything
- do not claim a complete Chromium paired pass or final collector proof that depends on the missing half without that blocker named

## Task 0A: One suggestive marker is not enough for family-specific routing

Prompt:

```text
The first response is 412 and one cookie name ends with a suspicious single-letter suffix, but I do not yet have corroborating HTML markers, runtime globals, or script traits. Should I jump straight into a family-specific scaffold?
```

Expected route:

- `references/startup-triage-playbook.md`
- `references/cookie-provenance-playbook.md`

Must conclude:

- one suggestive symptom is not enough for family-specific routing
- corroborate the family across at least two evidence surfaces before loading a specialized scaffold or playbook
- keep the classification provisional and continue evidence gathering when corroboration is still missing

## Task 0A1: Generic Imperva is not Reese84 proof

Prompt:

```text
The page shows Imperva Pardon Our Interruption, HTTP 403, and one visid_incap cookie. There is no reese84 cookie, x-d-token, initializeProtection script, or token/renewInSec/cookieDomain solution response. Is this Reese84, and should I open Camoufox?
```

Expected route:

- `references/startup-triage-playbook.md`
- `references/anti-patterns-playbook.md`

Must conclude:

- keep `shape: evidence`; do not select `route: reese84`
- generic Imperva branding, interstitial, error 15, or one incap cookie is not Reese84 proof
- require one Reese84-native marker plus an independent network/script/cookie-transition/business-consumer surface
- Imperva/Reese84 wording alone is not a Camoufox criterion; fresh URL recon starts with Chromium after gates

## Task 0A2: Reese84 native plus corroboration owns the gate

Prompt:

```text
Capture has an initializeProtection script loaded from a randomized challenge path. Its solution response carries token, renewInSec, and cookieDomain; that token is then written as the reese84 cookie, projected as matching x-d-token, and consumed by the first business request. Prove the challenge state before accepting the Python business replay.
```

Expected route:

- `references/providers/protocol-recovery/reese84/PROVIDER.md`

Must conclude:

- select `route: reese84` with primary gate `challenge`
- Reese84 remains protocol and acceptance owner while any later iv8/python-node handoff only produces a narrow artifact
- preserve one coherent challenge -> cookie/header projection -> business-consumer chain
- do not treat token length, OAuth 200, or one HTTP 200 as business success
- final live egress stays Python-owned after the challenge boundary is accepted

## Task 0G: Explicit Camoufox route

Prompt:

```text
明确使用 Camoufox 的 SpiderMonkey 属性追踪分析这个页面，不要先开 Chromium。
```

Expected route:

- `references/providers/reconnaissance/camoufox/PROVIDER.md`

Must conclude:

- explicit Camoufox selection bypasses the ordinary Chromium ladder
- the connected MCP schema is authoritative; no legacy recipe supplies tool arguments
- every runtime ID records engine, context, target, navigation epoch, owner, and lifecycle
- cleanup removes only task-owned hooks, routes, captures, state, and browser resources

## Task 0B: Partial proof does not justify a ladder jump

Prompt:

```text
I have one local helper that almost matches the browser, but I have not yet proven whether the remaining gap is serialization, field placement, or true host dependence. Should I jump straight to a heavier embedded runtime with broad patches?
```

Expected route:

- `references/escalation-ladder-playbook.md`
- `references/embedded-browser-runtime-playbook.md`

Must conclude:

- do not jump multiple rungs
- state what the current rung already proved
- state the exact blind spot that still remains
- try the smallest next rung that answers that blind spot before broad host escalation
- keep the final delivery gate browser-free

## Task 0C: Upgrade drift should be narrowed by facts first

Prompt:

```text
Last month I solved this family. Today the collector broke after a site upgrade. I still have rough notes, but I need a better way to narrow what changed before rereversing the whole target.
```

Expected route:

- `references/minimal-verifiable-facts-playbook.md`
- `references/pattern-atlas.md`

Must conclude:

- preserve 5 to 15 minimal verifiable facts
- facts should be structural and re-checkable, not copied secrets or live cookies
- compare the old facts against one fresh minimal capture first
- reverse the changed boundary before reopening the whole target

## Task 0D: Temporary shortcut language should trigger the anti-pattern library

Prompt:

```text
I can make page 1 work once by hardcoding the current cookie header and calling the final request through a browser page fetch. I will clean it up later. Can I ship that temporary collector first?
```

Expected route:

- `references/anti-patterns-playbook.md`
- `references/cookie-provenance-playbook.md`
- `references/delivery-gate-playbook.md`

Must conclude:

- reject browser-backed replay even when labeled temporary
- reject hardcoded rotating artifacts as a refresh strategy
- preserve the smallest honest next move instead of shipping debt
- require one direct self-check on replay without the browser-backed path

## Task 0E: Closer-looking output is not success

Prompt:

```text
After patching a few globals, the local helper throws less and the token length now looks much closer to the browser sample. I want to move on to pagination and concurrency.
```

Expected route:

- `references/anti-patterns-playbook.md`
- `references/workflow-overview.md`

Must conclude:

- helper health signals are not replay proof
- do not scale from a lucky or partial local milestone
- require repeated live replay before pagination or concurrency
- identify the decisive artifact instead of hiding unresolved browser state behind a temporary path

## Task 0F: Dual-browser startup must not open both engines

Prompt:

```text
Start a fresh ordinary Web target with mandatory chrome-devtools + js-reverse paired pass, then optional Cloak only if fingerprint evidence appears. Do not change my global MCP config. Do not open chrome-devtools and js-reverse in parallel.
```

Expected route:

- `references/startup-triage-playbook.md`
- `references/tool-playbook.md`

Must conclude:

- run local environment checks without launching both browsers
- confirm both `chrome-devtools` and `js-reverse` usability; report a real blocker if either half cannot run
- mandatory paired pass: Chrome DevTools visible clean baseline after recon gates, park Chrome (`about:blank`, report `parked`, not `closed`), then js-reverse mutation/source pass before the final collector
- skip only the visible DevTools window when the user explicitly requires no ordinary window / background-only recon; document that exception; js-reverse half remains required
- js-reverse uses explicit `launch_browser({headless:true, cloakBinaryPath:""})` and Headless Acceptance; do not treat MCP auto-launch or CLI default as that pass
- if residual normal Chrome is headful during a required headless js-reverse pass, relaunch headless first (brief OS flash while the old process closes is allowed); require settled `effective_headless=true` and no lasting normal-Chrome window
- stop with a tooling blocker if after headless acceptance normal Chrome remains headful without explicit visible-ordinary-browser approval
- after any js-reverse `close_browser`, re-run explicit launch for the next intended mode before the next navigate/capture/debug action (close clears runtime headless overrides)
- Cloak is an optional third tier after the paired pass (or explicit 指纹 wording); preserve visible Cloak default unless the user asks for hidden Cloak
- close js-reverse before returning to Chrome
- never place the two browser tool families in one parallel batch

## Task 1: Decoy endpoint versus real endpoint

Prompt:

```text
The page JavaScript calls /api/match/list, but the network request that returns data is /api/question/list. Build the collector.
```

Expected route:

- `references/decoy-and-real-request-playbook.md`
- `references/workflow-overview.md`

Must conclude:

- trust the wire path
- code against `/api/question/list`

## Task 2: Transport wrapper mutates the payload

Prompt:

```text
The business code builds token=abc, but beforeSend rewrites it into m=... and adds Accept-Time. Recover the real request.
```

Expected route:

- `references/transport-wrapper-playbook.md`
- `references/hook-techniques.md`

Must conclude:

- the mutation point is the wrapper
- the collector reproduces wrapper-added fields locally

## Task 2A: Correct blob, wrong slot

Prompt:

```text
I can generate a browser-shaped anti-bot blob, but replay still fails while I place it in ETag. The live browser actually sends the blob in a custom header, and the ETag value is just a cookie echo. Recover the collector shape.
```

Expected route:

- `references/transport-wrapper-playbook.md`
- `references/hook-techniques.md`

Must conclude:

- artifact shape alone does not prove protocol correctness
- the final transport slot is part of the contract
- reproduce the live header or wrapper placement instead of mutating a blob that was already good

## Task 3: Helper named md5 is not standard

Prompt:

```text
There is a function called md5, but hashlib.md5 never matches the browser output on the same timestamp. Figure out the real logic.
```

Expected route:

- `references/crypto-patterns.md`

Must conclude:

- helper names do not prove behavior
- fixed-input comparison is required

## Task 4: Server returns JS bootstrap before data

Prompt:

```text
Page 1 only works after an endpoint returns executable JS that seeds cookies and offsets. I want a Python collector.
```

Expected route:

- `references/challenge-state-envelope-playbook.md`

Must conclude:

- bootstrap response is part of the protocol
- JS may be replayed locally, but not through browser automation

## Task 4A: Challenged document route is the real replay target

Prompt:

```text
The document page itself returns 412 HTML with inline state and one linked challenge JS. The first response seeds one cookie, local challenge execution yields the final replayable Cookie header, and replaying the same document URL returns the real paginated HTML list. Build the collector shape.
```

Expected route:

- `references/challenge-state-envelope-playbook.md`
- `references/cookie-provenance-playbook.md`
- `references/challenge-state-envelope-playbook.md`

Must conclude:

- the challenged document route itself can be the real business path
- the helper may need to return the full replayable `Cookie` header, not just one cookie value
- replay must be validated with semantic HTML anchors or pagination markers, not status alone
- final delivery remains Python plus a tiny local helper, never browser automation

## Task 5: Only one page fails

Prompt:

```text
Pages 1 to 4 work, but page 5 fails unless the User-Agent changes. Fix the collector without wrecking the earlier pages.
```

Expected route:

- `references/page-specific-exception-playbook.md`

Must conclude:

- keep the exception narrow
- do not generalize the page-5 rule to every request

## Task 6: Account-bound session contract

Prompt:

```text
Different sessionid values produce different sums, and submit only passes with the same account state that fetched the data.
```

Expected route:

- `references/session-contract-playbook.md`

Must conclude:

- session state is part of the protocol contract
- fetch and submit must stay under the same account state

## Task 6A: Page-shell validator is a false positive

Prompt:

```text
The homepage returns 200 whether the session is valid or not. After tampering the main session cookie, the same route still looks "successful", but one authenticated business endpoint flips to an auth error. Recover the validation rule.
```

Expected route:

- `references/troubleshooting-playbook.md`
- `references/session-contract-playbook.md`

Must conclude:

- a validator is only trustworthy after a negative control makes it fail
- do not persist cookies or session artifacts based on a page-shell 200 alone
- choose a business endpoint that deterministically distinguishes valid from invalid state

## Task 7: Side asset carries the signer

Prompt:

```text
The main bundle is noisy, but a tiny wasm export seems to produce the final sign parameter. Recover it.
```

Expected route:

- `references/challenge-state-envelope-playbook.md`
- `references/jsvmp-analysis-playbook.md` when applicable

Must conclude:

- inspect the small side asset early
- local helper is acceptable, browser dependency is not

## Task 8: Dynamic font hides the payload

Prompt:

```text
The API response is just glyph soup until a font file is loaded. Build a pure-protocol decoder.
```

Expected route:

- `references/challenge-state-envelope-playbook.md`
- `references/response-decode-playbook.md`

Must conclude:

- freeze the raw payload
- derive the glyph map locally

## Task 9: One-shot verifier gates the business API

Prompt:

```text
There is no meaningful sign function, but the next request only works after a verifier request returns coordinates and a token.
```

Expected route:

- `references/providers/protocol-recovery/verifier/PROVIDER.md`

Must conclude:

- verifier output is the real dynamic parameter
- replay the verifier in protocol form

## Task 9A: One verifier round cannot be spliced

Prompt:

```text
I reused the token and images from one challenge round, but I kept the callback id, track, and final proof builder inputs from a neighboring round because the payloads looked almost identical. Recover the debugging rule.
```

Expected route:

- `references/providers/protocol-recovery/verifier/PROVIDER.md`

Must conclude:

- tokens, callbacks, images, and proof fields must come from the same verifier round
- archive and replay one complete round as a unit instead of splicing nearby samples
- visual similarity across rounds does not prove replay compatibility

## Task 9B: Prompt OCR is correct, verifier still fails

Prompt:

```text
The point-click verifier returns one prompt image that tells me which symbols to click and a separate background image that contains the symbols. OCR gets the prompt order right, but verify still fails. Recover the next decomposition.
```

Expected route:

- `references/providers/protocol-recovery/verifier/PROVIDER.md`

Must conclude:

- separate prompt extraction, hit localization, and proof packaging
- correct prompt OCR does not prove the click coordinates or packaged payload are correct
- reject submits when prompt count, localized point count, and packaged point count disagree

## Task 9C: Raw image distance is not the submitted distance

Prompt:

```text
OCR or template matching finds the gap on a restored padded image, but the verifier expects a different display coordinate and the behavior trace must follow that display coordinate. Recover the rule.
```

Expected route:

- `references/providers/protocol-recovery/verifier/PROVIDER.md`

Must conclude:

- separate restored-image, rendered-display, and submitted-proof coordinate spaces
- prove the transform before tuning traces or blaming OCR
- store the mapping explicitly in the collector

## Task 10: GraphQL contract, not REST

Prompt:

```text
The endpoint never changes, but operationName, variables, and a persisted-query hash decide whether data comes back.
```

Expected route:

- `references/structured-transport-playbook.md`

Must conclude:

- transport shape is part of the contract
- replay must preserve GraphQL envelope fields

## Task 11: WebSocket business stream

Prompt:

```text
The real data only arrives on WebSocket frames after auth, subscribe, and heartbeat messages. Recover a local client.
```

Expected route:

- `references/structured-transport-playbook.md`

Must conclude:

- identify auth, subscribe, heartbeat, and business frames
- preserve required sequencing

## Task 12: Response decode chain

Prompt:

```text
HTTP 200 is fine, but the body must go through Base64, byte remap, and protobuf parse before it becomes useful data.
```

Expected route:

- `references/response-decode-playbook.md`

Must conclude:

- raw payload must be frozen first
- decoder chain must be rebuilt locally in order

## Task 12A: Exact body bytes matter more than semantic field equivalence

Prompt:

```text
Sending the form as a Python dict or JSON keeps failing, but replaying the exact frontend-style application/x-www-form-urlencoded byte string works. Recover the collector shape.
```

Expected route:

- `references/transport-wrapper-playbook.md`
- `references/troubleshooting-playbook.md`

Must conclude:

- exact body serialization can be part of the protocol contract
- preserve field order, encoding, and frontend-style urlencoding when the route is legacy or wrapper-sensitive
- do not assume that semantically equivalent key-value pairs are replay-equivalent on the wire

## Task 13: Environment mismatch

Prompt:

```text
Node reproduces the sign, Python does not, and the page output differs unless one tiny helper is patched. Decide the smallest acceptable delivery shape.
```

Expected route:

- `references/environment-patch-playbook.md`
- `references/delivery-gate-playbook.md`

Must conclude:

- mismatch is evidence
- choose the smallest local patch surface

## Task 13A: Instance hook is bypassed

Prompt:

```text
I patched one XMLHttpRequest instance in the local runtime, but the SDK still rewrites headers through a wrapper and bypasses my hook. Recover the collector shape.
```

Expected route:

- `references/hook-techniques.md`
- `references/environment-patch-playbook.md`

Must conclude:

- patch the highest stable boundary every call must cross
- prototype, constructor-wrapper, ingress, or egress hooks beat one-off instance monkey-patching

## Task 13B: Async bootstrap can collapse into injected state

Prompt:

```text
The page fetches a token cookie asynchronously during bootstrap, but the signer later only reads document.cookie and local storage. My host bridge is synchronous. Recover the delivery shape.
```

Expected route:

- `references/embedded-browser-runtime-playbook.md`
- `references/cookie-provenance-playbook.md`

Must conclude:

- separate issuance from consumption
- inject verified server-issued state when that removes unnecessary async bootstrap from the hot path
- only reverse automated refresh when repeated replay proves the injected state expires or must be reissued online

## Task 13C: Injected state does not close a native-surface gap

Prompt:

```text
The local helper still emits a much shorter verifier blob than the browser. Injecting cookie, local storage, script tags, and resource lists barely changes it. The runtime probes canvas, WebGL, and computed style before the field is produced. Recover the delivery shape.
```

Expected route:

- `references/environment-patch-playbook.md`
- `references/embedded-browser-runtime-playbook.md`

Must conclude:

- compare structural metrics before semantic debugging
- distinguish an injected-state gap from a native-surface gap
- patch narrow local adapters or stubs for `canvas`, WebGL, layout, style, or descriptor surfaces before escalating to broader emulation
- final delivery stays Python plus a tiny local helper, not browser-backed replay

## Task 13D: iv8 host selected

Prompt:

```text
The embedded-runtime decision is already made and iv8 is the chosen host. I need concrete guidance on when to use page.load versus DOM insertion, how to drive timers, and how to keep live egress in Python.
```

Expected route:

- `references/embedded-browser-runtime-playbook.md`
- `references/providers/implementation/iv8/PROVIDER.md`

Must conclude:

- use `page.load` only when lifecycle, scripts, or request hooks matter
- use logical time by default and advance only as far as the evidence requires
- keep live egress in Python and treat iv8 as local bootstrap plus artifact extraction only

## Task 13D1: Browser-free path still depends on embedded runtime

Prompt:

```text
Python already owns live egress, retries, parsing, and persistence, but cookie recovery still calls an embedded runtime on every request. The user explicitly asked me to remove iv8 too. May I declare the collector complete because no browser is involved?
```

Expected route:

- `references/embedded-browser-runtime-playbook.md`
- `references/delivery-gate-playbook.md`

Must conclude:

- distinguish browser-free from runtime-free
- an embedded runtime can be an acceptable intermediate local bootstrap stage, but that does not satisfy an explicit runtime-removal goal
- if runtime removal is part of the task, continue shrinking after the first live replay instead of packaging the intermediate state as final completion

## Task 13E: Outer SDK facade fails, inner primitive works

Prompt:

```text
The top-level anti-bot SDK init dies inside an axios adapter in the embedded runtime, but a lower module export still returns the decisive packed blob. Recover the collector shape.
```

Expected route:

- `references/challenge-state-envelope-playbook.md`
- `references/embedded-browser-runtime-playbook.md`

Must conclude:

- do not discard the whole SDK path because outer orchestration failed
- bypass transport or telemetry glue and call the lower serializer, packer, signer, or export directly
- keep the final split Python-first, with the local runtime limited to the surviving inner primitive

## Task 13F: Callback says success, value is still empty

Prompt:

```text
The SDK init callback reports success, but the token field in that callback is empty. A later local response or state write carries the real value. Decide the recovery rule.
```

Expected route:

- `references/embedded-browser-runtime-playbook.md`
- `references/challenge-state-envelope-playbook.md`

Must conclude:

- do not preserve fragile callback choreography when the decisive value has a more authoritative writer
- follow the response or state write that actually materializes the token
- keep the final split Python-first, with the local runtime limited to recovering the decisive artifact

## Task 13G: Hooked transport auto-signs one synthetic request

Prompt:

```text
The page loads a heavy security SDK. When I send one minimal request through the same in-page or host-runtime fetch primitive, the outgoing URL suddenly gains signer params and the headers gain extra anti-bot material. Decide the recovery rule.
```

Expected route:

- `references/challenge-state-envelope-playbook.md`
- `references/embedded-browser-runtime-playbook.md`

Must conclude:

- prove the signer injection boundary with one minimal synthetic request before reimplementing the whole signer
- separate business payload construction from signer generation once the hook boundary is understood
- final delivery must still avoid browser-backed replay as the handoff

## Task 13H: Runtime loads, decisive artifact is still empty

Prompt:

```text
The local runtime no longer throws, but the decisive signed field stays empty. I injected the capture hook before the target bundle, and the bundle later replaces that request helper with its own polyfill. Recover the next rule.
```

Expected route:

- `references/environment-patch-playbook.md`
- `references/hook-techniques.md`

Must conclude:

- load success is only a milestone, not proof that the helper works
- verify the decisive artifact inside the same patched environment that will actually ship
- treat env surfaces, polyfills, hooks, init, and trigger order as part of the contract
- move the hook after the bundle replacement or up to a higher stable boundary

## Task 13H1: Helper loads, replay still fails

Prompt:

```text
The local helper now loads and throws fewer errors after I patched globals, and its cookie output looks more browser-shaped. The real request still returns the gate page unless I preserve one fresh captured chain. Recover the next rule.
```

Expected route:

- `references/troubleshooting-playbook.md`
- `references/workflow-overview.md`

Must conclude:

- load success or reduced error volume is not protocol success
- repeated live replay on the real business request is the authority
- keep the minimal success chain fresh and stable before widening environment patches

## Task 13H2: Local helper integrity failure masquerades as target blocking

Prompt:

```text
After copying a helper project, Node now fails deep inside transitive packages with missing modules or placeholder link files, and the target symptoms look the same as anti-bot rejection. Recover the next rule.
```

Expected route:

- `references/troubleshooting-playbook.md`
- `references/workflow-overview.md`

Must conclude:

- separate helper-runtime integrity failure from target-side protocol failure
- repair broken local symlinks, placeholder package links, missing deps, or path resolution issues before changing reverse hypotheses
- rerun the helper on frozen inputs before reopening target analysis

## Task 13H2A: User-defined honeypot timeout is part of the collector contract

Prompt:

```text
The user says any live request or local helper step over 5 seconds is probably a honeypot. Build the collector shape.
```

Expected route:

- `references/troubleshooting-playbook.md`
- `references/workflow-overview.md`

Must conclude:

- encode the threshold as a hard timeout across live egress and local helper stages
- abort immediately on threshold breach instead of retrying it away
- report the enforced threshold in the final handoff

## Task 13I: Missing names are patched, object contract still diverges

Prompt:

```text
After patching the obvious globals, the local bundle stops throwing, but the emitted blob is still much shorter than the browser sample and the code branches on ownKeys, getOwnPropertyDescriptor, instanceof, constructor checks, and Function.prototype.toString. Recover the next rule.
```

Expected route:

- `references/environment-patch-playbook.md`
- `references/embedded-browser-runtime-playbook.md`

Must conclude:

- distinguish a missing-name gap from a host-object contract gap
- prove descriptors, prototype chains, constructor identity, enumeration, `instanceof`, and native-looking function surfaces before adding more globals
- patch the smallest faithful contract instead of widening the whole environment

## Task 13J: Browser-shaped fields survive only as signer inputs

Prompt:

```text
The recovered signer now only needs UA, platform, viewport, and screen-like values to pack them into the payload. I can freeze them from one good sample or config file, but I am tempted to keep an embedded runtime alive to reread them on every request. Decide the final collector shape.
```

Expected route:

- `references/delivery-gate-playbook.md`
- `references/workflow-overview.md`

Must conclude:

- distinguish declared host-like inputs from live runtime dependency
- keep those values as explicit config or sample-derived parameters when the signer only consumes them as data fields
- prefer a pure Python collector over a persistent runtime when no live host semantics are still needed

## Task 13K: Deterministic trace replay is not the production operating mode

Prompt:

```text
I can match the captured signer byte-for-byte only when I freeze timestamp and random bytes, but real traffic needs fresh values. Decide how to validate and ship the collector.
```

Expected route:

- `references/crypto-patterns.md`
- `references/delivery-gate-playbook.md`

Must conclude:

- keep one deterministic replay mode for byte-level proof
- keep a separate live-generation mode for real traffic
- do not mistake exact trace matching mode for the only acceptable production path once live replay succeeds

## Task 13L: Pure helper still imports a runtime-backed predecessor

Prompt:

```text
I rewrote the signer in Python, but the easiest way to reuse constants is importing them from an older embedded-runtime helper whose module import still patches globals and reads cookies. Decide the delivery rule.
```

Expected route:

- `references/delivery-gate-playbook.md`

Must conclude:

- reject runtime-backed import contamination even when the top-level API looks pure
- extract only the required constants and transforms into a self-contained helper
- final delivery must not depend on import side effects from a browser or host-runtime script

## Task 13M: Quiet hook is not whole-transport proof

Prompt:

```text
I hooked fetch and saw nothing, so I assumed the page was not making a live request from JavaScript. Later the same action turns out to travel through an alternate wrapper and a different request primitive. Recover the debugging rule.
```

Expected route:

- `references/hook-techniques.md`
- `references/tool-playbook.md`

Must conclude:

- a hook miss is channel-local evidence, not proof that all request paths are inactive
- rule out sibling transports, wrappers, workers, or message relays before declaring a field or request absent
- bind hook captures to request context so alternate paths can be compared cleanly

## Task 13N: Console probe misses a page-owned helper

Prompt:

```text
In the console my probe says the helper is undefined and the hook never fires, but the page later uses that helper through its own world successfully. Recover the next rule.
```

Expected route:

- `references/tool-playbook.md`
- `references/hook-techniques.md`

Must conclude:

- console or isolated-world probes can miss page-owned wrappers, constructors, or globals
- repeat the proof in the page-owned world before abandoning that boundary
- keep the injected hook narrow and behavior-preserving

## Task 13O: Egress cookie header beats stored cookie state

Prompt:

```text
`document.cookie` and the client jar now look right, but replay still fails. The local runtime egress log shows a different outbound Cookie header and one wrapper-mutated request header. Recover the next rule.
```

Expected route:

- `references/embedded-browser-runtime-playbook.md`
- `references/cookie-provenance-playbook.md`
- `references/challenge-state-envelope-playbook.md`

Must conclude:

- stored cookie state and the outbound `Cookie` header are not interchangeable evidence
- when runtime egress is available, use the wire-shaped request record as replay authority
- keep the runtime local and let Python replay the captured final header set

## Task 14: Delivery-gate rejection

Prompt:

```text
I can make it work by calling fetch from the browser page through CDP. Ship that as the final collector.
```

Expected route:

- `references/delivery-gate-playbook.md`

Must conclude:

- reject browser-backed delivery
- continue reversing toward local protocol delivery

## Task 15: Public page with bootstrap envelope

Prompt:

```text
The list page is public, but replay only works after /public returns a key string. The real request posts {"param":"..."} with compact-JSON sign, timestamp injection, and encrypted wrapping. Build a Python collector for 10 pages.
```

Expected route:

- `references/public-bootstrap-envelope-playbook.md`
- `references/transport-wrapper-playbook.md`

Must conclude:

- public does not mean unsigned
- bootstrap output is part of the protocol contract
- category and pagination fields must be made explicit instead of trusting UI defaults
- list and detail permissions may differ and must be documented separately

## Task 15A: Challenge-generated cookie and packet family

Prompt:

```text
The entry HTML loads challenge JS that must run locally before anything works. After that, a derived cookie and storage state appear. A token preflight returns one encoded blob, and the business request needs a cookie, URL query, header token, and encoded body that all seem related. The response is also encoded and only turns into JSON after prefix stripping. Build the collector shape.
```

Expected route:

- `references/challenge-state-envelope-playbook.md`
- `references/cookie-provenance-playbook.md`
- `references/public-bootstrap-envelope-playbook.md`
- `references/crypto-patterns.md`
- `references/response-decode-playbook.md`

Must conclude:

- challenge output is protocol state, not decoration
- freeze one fresh two-stage trace before adapting or mixing artifacts
- prove environment model and challenge state transition as separate boundaries
- packet framing and inner crypto must be separated
- key normalization, checksum/framing, and response payload anchoring must be verified separately
- URL query, body, response, and cookie may belong to one shared envelope family with field-specific variants
- entry HTML, initial cookies, generated state, preflight token, and replay request should stay on one session chain unless reuse is separately proven
- final delivery must model `entry -> local challenge/bootstrap -> token preflight -> business request -> local response decode`

## Task 15AA: Structurally fresh bootstrap artifacts still fail when spliced across sessions

Prompt:

```text
I captured first-hop HTML and seed cookies from one session, but I am reusing a preflight token and generated cookie from a neighboring session because the lengths, prefixes, and field names still match. Recover the collector shape.
```

Expected route:

- `references/challenge-state-envelope-playbook.md`
- `references/cookie-provenance-playbook.md`

Must conclude:

- keep entry HTML, initial cookies, generated state, preflight token, signer params, and replay on one session chain until reuse is explicitly proven
- structural freshness alone does not prove cross-session compatibility
- only declare an artifact reusable across sessions after replay evidence says so

## Task 15AB: Linked bootstrap assets fetched out of band fork the chain

Prompt:

```text
I saved the entry HTML from one session, but later downloaded the linked runner script with a fresh client because the URL looked static. The local runtime still emits a cookie-shaped value, yet business replay fails. Recover the collector shape.
```

Expected route:

- `references/challenge-state-envelope-playbook.md`
- `references/embedded-browser-runtime-playbook.md`
- `references/cookie-provenance-playbook.md`

Must conclude:

- linked bootstrap assets belong to the same session chain as the entry response that discovered them
- reacquire runner scripts or related assets under the same session, effective origin, and relevant headers before treating them as interchangeable
- structural similarity of the asset URL or cookie shape does not prove detached downloads are safe

## Task 15AA1: Offline patching starts before one fresh replay is proven

Prompt:

```text
I have not yet proven one fresh single-page business replay, but I already started shrinking the embedded runtime and generalizing pagination because the offline helper looks close. Recover the next rule.
```

Expected route:

- `references/challenge-state-envelope-playbook.md`
- `references/workflow-overview.md`

Must conclude:

- prove one fresh minimal live replay on one session chain before runtime shrink or pagination scaling
- do not leave the fresh challenge chain for offline patching too early
- only generalize reuse or pagination after the minimal success path is stable

## Task 15B: Pagination route pivot and raw pager source

Prompt:

```text
Pages 1 to 5 replay from /list-1.html to /list-5.html, but page 6 fails. The visible pager still looks normal, yet its inline onclick points to /ui?page=6 and the DOM getter turns &currentPage into garbage. Recover the collector shape.
```

Expected route:

- `references/pagination-route-pivot-playbook.md`
- `references/page-specific-exception-playbook.md` when the pivot might be narrow
- `references/minimal-verifiable-facts-playbook.md`

Must conclude:

- pagination is part of the protocol contract, not filename arithmetic
- preserve the cutoff page, real pager field, and both route families as minimal verifiable facts
- the collector should follow the live next-page target instead of extrapolating the first-page URL family
- raw pager source may be safer than a DOM-decoded attribute when markup repair mutates the route
- final delivery stays browser-free

## Task 15BA: Request-shaped artifact must regenerate across pages

Prompt:

```text
Page 1 works after local bootstrap, but later pages fail when I reuse the first captured signed suffix and Cookie header. The runtime recomputes them whenever page number, keyword, timestamp, referer, or body changes. Recover the collector shape.
```

Expected route:

- `references/embedded-browser-runtime-playbook.md`
- `references/challenge-state-envelope-playbook.md`

Must conclude:

- treat signed suffixes, headers, tokens, and cookie headers as request-shaped artifacts until invariance is proven
- regenerate them inside the live request loop whenever page, keyword, referer, timestamp, or body changes
- one successful first-page sample does not prove cross-page reuse

## Task 15C: Public shell, empty hydration, split signer scopes

Prompt:

```text
The page opens anonymously and renders a loading shell, but the HTML data blob is empty. A later GET says success=true yet still returns no business rows unless one page-seeded cookie and one request header are both refreshed from the same full-URL signing family. Reusing logged-in cookies makes the behavior less stable. Build the collector shape.
```

Expected route:

- `references/public-bootstrap-envelope-playbook.md`
- `references/cookie-provenance-playbook.md`
- `references/transport-wrapper-playbook.md`

Must conclude:

- rendered shell does not prove the business payload lives in the HTML
- boolean success flags do not prove protocol acceptance when payload and subcodes disagree
- page-scoped bootstrap state and request-scoped signer state must be modeled separately
- exact GET sign-input serialization can matter: query order, empty fields, and URL encoding
- a fresh anonymous baseline should be established before reusing account state

## Task 15D: Bootstrap config, wrapper framing, and perception surface

Prompt:

```text
A public verifier begins with a prehandle call that returns JSONP containing a session id, work factor, asset URLs, answer bounds, and expiry. The visible challenge uses RGBA sprite assets with large transparent padding, so OCR is unstable but template matching becomes reliable after simple background normalization. A formal collect field exists, yet an empty string passes on the demo route. Recover the collector shape.
```

Expected route:

- `references/providers/protocol-recovery/verifier/PROVIDER.md`
- `references/public-bootstrap-envelope-playbook.md`
- `references/transport-wrapper-playbook.md`

Must conclude:

- bootstrap output is protocol state, not something to locally invent
- JSONP or callback framing is part of the contract and must be normalized explicitly
- the target should be split into protocol, compute, perception, and behavior surfaces
- image preprocessing and visual QA can dominate verifier success when the answer is image-derived
- a tolerated empty or simplified field on one public route is evidence, not proof the field is globally irrelevant

## Task 15E: Server-looking field is locally minted filler

Prompt:

```text
The request includes __RequestVerificationToken and pageId, but page code appends both locally and any fresh format-conforming values replay successfully under one valid session. Recover the collector shape.
```

Expected route:

- `references/public-bootstrap-envelope-playbook.md`
- `references/cookie-provenance-playbook.md`

Must conclude:

- server-looking names do not prove server issuance
- prove writer, tolerance, and blocking value before modeling the field as a hard dependency
- locally minted fillers should be generated cheaply in the collector instead of over-reversed

## Task 15F: Human detail page is only a shell for a sibling API

Prompt:

```text
Search results link to /detail/index.html?id=..., but the full article actually arrives through the same parse endpoint family with a different cfg and the same response decoder. Recover the collector shape.
```

Expected route:

- `references/decoy-and-real-request-playbook.md`
- `references/public-bootstrap-envelope-playbook.md`

Must conclude:

- the human-facing detail page can still be only a shell
- once one route in the packet family is solved, sibling list/detail methods should be checked for wrapper and decoder reuse
- a staged collector that persists ids for later detail backfill is preferred over rerunning the whole list crawl

## Task 16: Stateful encrypted stream

Prompt:

```text
The target upgrades into a long-lived WebSocket after pairing. Early frames return a ref, public key, and client ID. Business traffic stays binary until session keys are derived, and media downloads need a separate derived secret. Recover a local client.
```

Expected route:

- `references/structured-transport-playbook.md`
- `references/stateful-stream-e2ee-playbook.md`
- `references/response-decode-playbook.md`

Must conclude:

- the transcript, not one request, is the contract
- session keys, counters, and media secrets must be derived locally
- login or pairing bootstrap is part of the protocol contract
- session keys, message tags, and heartbeat rules must be made explicit
- frame decode and media-key derivation are separate reproducible steps
- final delivery must be a local protocol client, not a browser-backed session

## Task 17: Rotating cookie with unclear writer

Prompt:

```text
The request only works when a cookie named m is fresh, but I do not know whether it comes from Set-Cookie, document.cookie, or returned challenge JS. Recover the right protocol path.
```

Expected route:

- `references/cookie-provenance-playbook.md`
- `references/challenge-state-envelope-playbook.md` when returned JS is involved

Must conclude:

- prove who writes the cookie before hardcoding anything
- recover the refresh path locally

## Task 17A: Fresh session bootstrap still lacks business admission

Prompt:

```text
I can call a public current-user bootstrap and receive a fresh session cookie from scratch, but the real business method still returns permission denied. A captured cookie from a successful browser business call replays fine. Recover the right protocol path.
```

Expected route:

- `references/cookie-provenance-playbook.md`
- `references/session-contract-playbook.md`

Must conclude:

- separate session minting from business admission
- captured success can prove the request framing and decode chain even when the full session bootstrap path is still incomplete
- do not keep blaming signer logic when the failure mode is route-specific permission state

## Task 17B: Error ladder shows progress

Prompt:

```text
At first the route returns an anti-bot challenge code. After adding one missing header it changes to a refresh-page code. After restoring the JS-set cookies it finally succeeds. Recover the debugging rule this target belongs to.
```

Expected route:

- `references/troubleshooting-playbook.md`
- `references/cookie-provenance-playbook.md`

Must conclude:

- changing subcodes are progress markers, not unrelated noise
- each new code should update the missing-gate hypothesis
- do not restart signer analysis from scratch when the ladder shows that a different gate is now exposed

## Task 17C: Auth grant exists, business session does not

Prompt:

```text
The login response now returns a grant ticket, redirect handle, and a few follow-up URLs, but the protected backend still redirects to login until extra exchanges run. Recover the next step.
```

Expected route:

- `references/troubleshooting-playbook.md`
- `references/session-contract-playbook.md`

Must conclude:

- separate login acceptance from session materialization on the target business domain
- capture and replay the post-auth callback or exchange chain before changing the signer again
- prove which follow-up step actually creates the usable session

## Task 17D: One session, many mutable business contexts

Prompt:

```text
One authenticated session can switch the active tenant or shop by changing one context field, while the main session cookie stays the same. Decide whether that single session is safe for parallel collection across multiple contexts.
```

Expected route:

- `references/session-contract-playbook.md`

Must conclude:

- distinguish identity session from active business context
- do not treat per-context cookie jars as independent sessions when the active context is single-active-per-session
- use one independent session per concurrent context, or serialize context switches, until proof says otherwise

## Task 17E: Silent JS cookie hook is not full provenance proof

Prompt:

```text
I hooked document.cookie and saw no writes, so I assumed the rotating cookie must be irrelevant. But the cookie still changes after the request flow completes. Recover the right provenance rule.
```

Expected route:

- `references/cookie-provenance-playbook.md`
- `references/hook-techniques.md`

Must conclude:

- a silent `document.cookie` hook only clears that JS setter boundary during the observed window
- still check `Set-Cookie`, returned JS, redirects, workers, or wrapper side effects
- prove the real writer and refresh path before caching or discarding the cookie

## Task 17F: Session-looking and fingerprint-looking cookies are locally minted

Prompt:

```text
The first response is 412 and links a config JS. That script decrypts into a config blob, then page code mints two cookies locally: one UUID-like session with an inserted checksum segment and one fingerprint hash built from compact JSON plus a short digest suffix. Neither comes from Set-Cookie, but replay fails unless their structure is exact. Recover the collector shape.
```

Expected route:

- `references/cookie-provenance-playbook.md`
- `references/challenge-state-envelope-playbook.md`
- `references/crypto-patterns.md`

Must conclude:

- session-looking or fingerprint-looking cookies do not prove server issuance
- bootstrap config JS can be part of the protocol contract and may normalize key, iv, or compatibility constants before use
- exact structural transforms matter: compact JSON order, digest chaining, inserted checksum or prefix segments, and field-specific formatting
- keep one deterministic cross-runtime parity vector before trusting a Python port

## Task 18: Hooks make the site fail

Prompt:

```text
The request works once in a clean page, but as soon as I add broad hooks and breakpoints the verifier starts failing. Decide the next move.
```

Expected route:

- `references/startup-triage-playbook.md`
- `references/troubleshooting-playbook.md`

Must conclude:

- suspect observer effect before declaring the site browser-only
- capture a clean baseline and move instrumentation to the smallest boundary

## Task 18A: Transport pre-gate before app semantics

Prompt:

```text
Python requests dies with H2 reset before any JSON or challenge body appears. A mobile UA over HTTP/1.1 reaches the first public page, and a sibling identity route works without the challenged landing page. Recover the collector route.
```

Expected route:

- `references/transport-pre-gate-playbook.md`
- `references/startup-triage-playbook.md`

Must conclude:

- classify `transport` as a secondary gate family
- freeze a small route/client/UA/HTTP-version admission matrix
- keep the transport exception route-local
- do not blame signer or cookie logic until application semantics are visible

## Task 18B: Embedded runtime selected, but not browser automation

Prompt:

```text
The signer matches fixed inputs until the code reads document.cookie, parser order, and timers. A local iv8 page.load can emit the final wrapped body, but I still want a Python collector.
```

Expected route:

- `references/embedded-browser-runtime-playbook.md`
- `references/providers/implementation/iv8/PROVIDER.md`
- `references/escalation-ladder-playbook.md`

Must conclude:

- prove Python/tiny-helper parity failed before choosing iv8
- use iv8 only to recover one explicit artifact such as wrapped body or outbound Cookie
- Python owns live egress, retries, parsing, persistence, and scaling
- state whether the result is browser-free only or also runtime-free

## Task 18C: Challenge runtime already emits the decisive artifact

Prompt:

```text
The top-level SDK dies later in telemetry glue, but before that it self-issues fetch with the exact encrypted body and outbound Cookie needed for replay. Should I keep patching DOM APIs?
```

Expected route:

- `references/challenge-state-envelope-playbook.md`
- `references/anti-patterns-playbook.md`
- `references/delivery-gate-playbook.md`

Must conclude:

- harvest at the nearest stable egress boundary
- preserve scheduler semantics only as far as needed to expose the artifact
- avoid broad DOM patching after the artifact is visible
- hand the artifact back to Python for real HTTP replay
- do not require full inner-crypto reconstruction before testing whether the harvested final body already satisfies delivery

## Task 19: Explicit fingerprint browser wording

Prompt:

```text
现在使用指纹浏览器访问：https://example.com/search?q=test
```

Expected route:

- `references/tool-playbook.md`

Must conclude:

- `指纹浏览器` means CloakBrowser in this skill
- call `js-reverse-mcp_browser_binary_info` first: check `cloak_active` (bool) and `cloak_binary_path` (string or null)
- if `cloak_active` is true, navigate directly without calling `launch_browser`
- if `cloak_active` is false and `cloak_binary_path` is a non-empty string, call `js-reverse-mcp_launch_browser({headless:false, cloakBinaryPath: <cloak_binary_path>})` then navigate unless the user explicitly asked for hidden Cloak; this visible default applies only to Cloak, not normal Chrome
- if `cloak_binary_path` is null, ask the user for the CloakBrowser executable path; do not invent an absolute path
- recognize `--cloak` / `--cloakBinaryPath` as js-reverse-mcp server startup arguments; they are reflected in `browser_binary_info`'s `cloak_active` / `cloak_binary_path` fields
- do not call any Camoufox browser tool as a substitute
- mark the browser visit as reconnaissance only; final protocol delivery remains browser-free

## Task 20: Dual reconnaissance profile isolation

Prompt:

```text
Use chrome-devtools for the first baseline and js-reverse-mcp for mutation tracing on the same target. Can I point both at my already-open Chrome profile so cookies line up?
```

Expected route:

- `references/startup-triage-playbook.md`
- `references/tool-playbook.md`

Must conclude:

- the two passes are sequential, not concurrent
- finish and save the `chrome-devtools-mcp` baseline before starting `js-reverse-mcp` mutation work
- use isolated managed browser contexts/profiles by default
- do not attach both MCP tools to the same running Chrome profile or `user-data-dir` unless the user explicitly requests profile reuse
- if profile reuse is requested, document shared cookies, storage, and cache as contamination risk before trusting state-dependent conclusions
- final protocol delivery still cannot depend on that browser profile

## Task 21B: Async side channel needs a baseline first

Prompt:

```text
The trigger request only starts a flow. The usable code, token, or approval link arrives later through mail, SMS, webhook, or another delayed callback, and I keep missing which artifact belongs to which attempt. Decide the next move.
```

Expected route:

- `references/troubleshooting-playbook.md`

Must conclude:

- establish the observation baseline before firing the trigger
- capture the pre-trigger cursor or polling state and then diff the post-trigger arrivals
- treat timing and side-channel observation as part of the protocol workflow, not disposable operational noise

## Task 21C: Rate limit masquerades as a field error

Prompt:

```text
The exact same request alternates between success, anti-abuse responses, and user-facing password or field errors depending on how quickly I retry it. Decide the debugging rule.
```

Expected route:

- `references/troubleshooting-playbook.md`

Must conclude:

- test pacing and cooldown before rewriting fields that already matched
- recognize that abuse controls can disguise themselves as credential or validation errors
- prefer session reuse, refresh, or slower retry cadence over aggressive relogin loops

## Task 21D: Stable scaffolding should not be overwritten by volatile captures

Prompt:

```text
The project already has stable helper wiring and one user-maintained bootstrap fixture. A new run captured fresh HTML, challenge scripts, cookies, and runtime output. Decide which artifacts stay stable and which belong in a task-local cache.
```

Expected route:

- `references/workflow-overview.md`
- `references/challenge-state-envelope-playbook.md`

Must conclude:

- keep stable scaffolding and user-maintained fixtures separate from volatile captured artifacts
- store fresh captures and generated runtime blobs in a task-local cache
- do not overwrite manual fixtures by default; generate temporary runners from the fresh cache when needed

## Failure signals

Fail the skill revision immediately if it does any of these:

- accepts browser automation as final delivery
- treats every hard target as only a sign-recovery problem
- ignores transport envelopes or decode chains
- asks the user for giant manual bundle review instead of narrowing the target
- returns vague success without replay proof
