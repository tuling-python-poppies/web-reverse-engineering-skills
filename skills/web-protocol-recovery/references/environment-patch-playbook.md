# Environment Patch Playbook

Use this file when extracted logic runs in a local runtime but outputs still differ from the page.

## Common mismatch sources

- missing globals
- different user agent branches
- DOM-derived constants
- text encoding assumptions
- `Date.now()` or randomness precision
- scheduler, timer, or microtask differences
- load-order mistakes between env surfaces, polyfills, hooks, init, and trigger
- helper functions patched by side scripts
- instance-level hooks bypassed by prototype rewrites, rebinding, or wrapper replacement
- async bootstrap state that is only consumed later from cookie, storage, or one cached object
- unimplemented native surfaces such as `canvas`, WebGL, layout metrics, or style computation that quietly collapse fingerprint or verifier payloads
- host-object contract mismatches such as descriptors, prototype chains, constructor identity, enumeration, or native-looking function surfaces
- structurally shortened outputs caused by null-returning host APIs rather than wrong business logic

## Working method

Separate four layers before patching:

1. transport and redirect admission
2. request-wrapper and serialization mutation
3. algorithm/helper behavior on fixed inputs
4. host environment and runtime scheduling

Prove the first divergent layer. A redirect shell, wrong final URL, or missing request usually belongs above environment emulation; a helper mismatch on frozen inputs belongs below it.

1. classify the gap first: missing surface, load-order contract, or host-object contract mismatch
2. compare helper outputs on the same fixed inputs
3. compare structural metrics such as length, repeated blocks, and field presence before chasing semantics
4. identify the first diverging intermediate value
5. if cookie, storage, script, or resource injection barely changes the output, inspect which host APIs are actually probed
6. if the right names exist but probes branch on descriptors, `ownKeys`, `instanceof`, constructor checks, or native-looking functions, patch the contract before adding more globals
7. if hooks vanish, the artifact stays empty, or behavior changes only after bundle load, prove whether env surfaces, polyfills, hooks, init, and trigger were loaded in the wrong order
8. patch only the smallest missing environment surface or authoritative boundary that downstream code cannot bypass
9. if the runtime later only reads a server-issued cookie, storage value, token, or cached blob, test whether injecting a verified sample removes the async bootstrap from the hot path
10. allow structural failures to propagate; suppress only the exact recoverable error class you can justify
11. keep the patch local to the helper runtime, not a whole browser dependency

Before widening the environment, verify final URL, response content type, redirect history, proxy ownership, decompression, and whether the compared browser/local samples came from the same request and session.

## Verification rule

Loading success is only a milestone.
A helper that no longer throws can still emit an empty, downgraded, or structurally wrong artifact.

Before live replay:

1. rerun the decisive artifact in the same patched environment, hook placement, and load order you plan to ship
2. compare fixed-input browser and local outputs by structure first: length, prefix, segment count, field presence, encoding, or emitted headers and body
3. for hook-driven runtimes, treat order as part of the contract:
   - environment surfaces or fake transport primitive
   - target bundle
   - capture hook or observation boundary
   - init or config
   - trigger
4. if a target polyfill or wrapper replaces your early hook, move the hook after that replacement or upward to a stable boundary every call must cross

## Boundary-selection rule

Patch the nearest stable boundary, not the prettiest one.

Prefer these boundaries over one-off instance patching when the target keeps rebinding helpers:

- prototype methods such as `XMLHttpRequest.prototype.open` or `.send`
- constructor-time wrappers
- transport-wrapper ingress before mutation
- request egress after mutation but before final live egress

If the runtime can replace one instance method and skip your patch, that patch surface is too low.

## Common traps

- patching the entire DOM when only one global value was needed
- patching one object instance when the runtime clones, rebinds, or replaces the method upstream
- fixing every undefined while ignoring load order between env surfaces, polyfills, hooks, init, and trigger
- replaying an entire async bootstrap when the signer only reads an already-issued cookie, storage slot, or token
- copying cookie, storage, script, or resource snapshots when the runtime actually branches on `canvas`, WebGL, layout, style, or native descriptors
- adding more globals when the real divergence is descriptor, prototype, constructor, or native-surface shape
- treating a much shorter verifier sidecar as an answer-quality problem instead of environment evidence
- calling the job done because the helper loads without throwing
- swallowing every runtime error and hiding recursion, stack overflow, or corrupted VM state
- blaming crypto before checking environment-sensitive branches

## Delivery rule

Prefer tiny local patches and explicit state injection over browser-backed execution.
