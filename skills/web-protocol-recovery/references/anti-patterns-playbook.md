# Anti-Patterns Playbook

Use this file before or during execution when a tempting shortcut is about to replace the next proof. For an already-observed failure after one bounded replay, use `troubleshooting-playbook.md` instead.

This file exists because soft principles are easy to agree with and easy to ignore.
Counterexamples constrain better when they answer four questions:

1. what tempting move is showing up
2. why it is false progress
3. what the smallest honest next move is
4. what one self-check can stop the slide

## How to use it

When you notice yourself thinking:

- "I can just ship this temporary browser-backed collector"
- "the cookie looks fresh enough"
- "the helper loads now, good enough"
- "I should jump to a heavier runtime"
- "I already got page 1 once, let's scale"

stop and match the temptation below before editing more code.

## Anti-pattern 1: Browser-backed replay dressed up as a temporary collector

Temptation:

- call page `fetch`
- drive CDP or Playwright for the final request
- keep a browser profile around as a hidden dependency

Why it is false progress:

- the unresolved protocol state stays unexplained
- replay proof depends on a page world, not local artifacts
- the handoff becomes impossible to reason about or maintain

Smallest honest next move:

- identify the decisive artifact the browser is adding
- harvest that artifact at the nearest stable boundary
- hand it back to Python for the real HTTP replay

Self-check:

- if the browser process disappears, does the collector still work?

## Anti-pattern 2: Hardcode the current rotating cookie, token, or header because it works once

Temptation:

- paste the current cookie header into config
- freeze one token or sidecar that still happens to pass
- treat a current sample as a refresh strategy

Why it is false progress:

- it proves only one snapshot, not writer or refresh path
- expiry, slot placement, or session binding remain unknown
- later failures get misdiagnosed as signer bugs

Smallest honest next move:

- prove who writes the artifact
- prove where it is consumed on the wire
- rebuild or refresh only the authoritative artifact that replay actually needs

Self-check:

- can the collector recover the artifact again without manual recapture?

## Anti-pattern 3: Scale after one lucky success

Temptation:

- start pagination after one good page
- add concurrency before one stable replay path exists
- shrink runtimes before a fresh chain is proven twice

Why it is false progress:

- one lucky pass can hide stale state, session-chain coupling, or page-specific tolerance
- failures later get mixed together with scale effects

Smallest honest next move:

- replay the same minimal request at least twice
- prove page 2 or one next cursor with the same collector path
- only then widen scope

Self-check:

- does the same single-page request still succeed on a fresh repeat?

## Anti-pattern 4: Jump multiple rungs because the current one is frustrating

Temptation:

- Python mismatch -> broad embedded runtime
- local runtime loads -> broad host patching
- one blocked route -> route-wide transport cargo cult

Why it is false progress:

- the real blind spot stays unnamed
- comparison baselines get destroyed
- heavier layers hide simpler unresolved mistakes such as slot placement or serialization

Smallest honest next move:

- write the ladder log
- prove the exact failure at the current rung
- move up one rung only

Self-check:

- can you name the exact blind spot the heavier layer is supposed to answer?

See `references/escalation-ladder-playbook.md` for the rung model.

## Anti-pattern 5: Install broad hooks before a clean baseline

Temptation:

- inject global hooks immediately because the target looks hard
- set broad breakpoints before one clean request is captured
- treat hook-induced failure as evidence the site is browser-only

Why it is false progress:

- observer effect can change timing, identity, or verifier behavior
- the clean contract gets lost before it is frozen

Smallest honest next move:

- capture one untouched baseline request and response pair
- move hooks outward toward the narrowest stable boundary
- compare hooked and clean behavior explicitly

Self-check:

- did the failure mode change only after your instrumentation landed?

## Anti-pattern 6: Reverse the visible helper or visible param instead of the wire mutation point

Temptation:

- chase a page-level `sign` because it looks named
- code against the visible endpoint instead of the live route
- trust the business payload before wrapper rewrite

Why it is false progress:

- the real contract may live in a wrapper, interceptor, or egress mutation
- a correct blob in the wrong slot still fails

Smallest honest next move:

- trace the canonical mutation point
- capture the final wire-shaped request
- rebuild what actually crosses the boundary

Self-check:

- does the thing you are reversing exactly match what the wire sends?

## Anti-pattern 7: Treat helper load success, fewer exceptions, or browser-shaped output as protocol success

Temptation:

- token length looks closer
- the runtime throws less
- cookie shape looks more realistic

Why it is false progress:

- these are only local health signals
- they do not prove the real request replays

Smallest honest next move:

- run the real business request
- validate response semantics, not just status or shape
- repeat the replay

Self-check:

- does the actual target request now succeed repeatedly?

## Anti-pattern 8: Overwrite stable scaffolding with volatile captures

Temptation:

- replace user-maintained fixtures with fresh target blobs
- edit stable helpers directly with run-specific artifacts
- blur reusable code and volatile capture state

Why it is false progress:

- later diffs become unreadable
- the stable path gets contaminated by one run
- upgrade analysis loses its clean baseline

Smallest honest next move:

- keep fresh captures in task-local cache
- generate temporary runners from volatile artifacts
- update stable scaffolding only after the lesson is proven reusable

Self-check:

- could you rerun the diff from a clean stable base tomorrow?

## Anti-pattern: Dump evidence into OS temp instead of project `js_reverse_cache/`

Temptation:

- write recon/MCP exports under `%TEMP%`, `AppData\Local\Temp`, or an agent `opencode` temp folder
- hardcode that temp path in `main.py` after delivery
- wipe project `js_reverse_cache/` while keeping the only working cookie/state in temp

Why it is false progress:

- violates `web-protocol-recovery-simple` ownership of volatile evidence
- delivery cannot be re-run from the project root alone
- secrets and large dumps leak outside the gitignored project cache contract

Smallest honest next move:

- create or reuse `<projectRoot>/js_reverse_cache/<namespace>/`
- save or copy all evidence there
- read only project-relative cache paths from stable code

Self-check:

- if `%TEMP%` is wiped, can the project still locate its evidence and private state?

## Anti-pattern: Ship iv8/collector progress with only bare `print` and no `utils/logger.py`

Temptation:

- paste `print("...")` through the main script
- omit `utils/logger.py` even though iv8 delivery rules require the shared logger helper
- re-implement ad-hoc loguru try/except in every `main.py`

Why it is false progress:

- drifts from the old iv8-web-reverse and current iv8 `script-writing-rules` template
- loses optional `loguru` without a single fallback helper
- makes progress logs inconsistent and harder to redacted-bound

Smallest honest next move:

- create `utils/logger.py` from the iv8 template (optional loguru + PrintLogger)
- `from utils.logger import logger` and use `logger.info` for progress
- keep final console tables only when the user explicitly wants console-only results

Self-check:

- does a re-runnable iv8/collector delivery include `utils/logger.py` without duplicating fallback code in `main.py`?

## Anti-pattern: Treat non-empty sign/token as success

Temptation:

- celebrate a long `h5st` / cookie / token string
- skip business body parse because HTTP tooling "looks fine"

Why it is false progress:

- frozen or stale signers can still emit long tokens while the business API returns 403 empty body
- delivery needs product/data shape, not token aesthetics

Smallest honest next move:

- define the semantic payload fields up front
- require HTTP status + content-type + parsed business rows
- when token exists but business fails, prefer live bundle/env refresh over more token printing

Self-check:

- if the token were replaced by random bytes of the same length, would your acceptance still fail?

## Anti-pattern: Expired cookie/session export as a stable solution

Temptation:

- reuse yesterday's `browser_state.json` / `reese84` / risk cookies forever
- delete project cache and keep the only state in OS temp

Why it is false progress:

- TTL and rotation make one-shot exports decay
- private state outside `js_reverse_cache/private/` breaks project-local reproduction

Smallest honest next move:

- store state under `js_reverse_cache/private/` (gitignored)
- document refresh path (browser export or challenge regenerate)
- fail closed with a clear "state expired" when business gate returns challenge HTML

Self-check:

- can a cold machine reproduce after wiping OS temp, with only project files + documented refresh steps?

## Anti-pattern: Generic Imperva or intermediate success as Reese84 proof

Temptation:

- route an Imperva interstitial, error 15, or one incap cookie directly to Reese84
- treat a fresh `reese84`, OAuth `200`, or a non-empty token as business acceptance
- import or execute a template's archived challenge implementation to skip reconstruction

Why it is false progress:

- generic Imperva surfaces do not identify the Reese84 product family
- challenge and OAuth success can coexist with a rejected business request
- archived code is provenance tied to an old target state, not a current implementation asset

Smallest honest next move:

- require one Reese84-native marker plus an independent network, script, cookie-transition, or business-consumer surface
- preserve one challenge -> cookie/header -> business-consumer chain and validate parsed business fields
- use archived references only to name a bounded implementation fact, then reconstruct it under a current work order

Self-check:

- would the route and acceptance still hold if the vendor label, OAuth status, and archived code were removed from the evidence?

## Anti-pattern: Pre-create empty layout trees

Temptation:

- mkdir every diagram folder under `js_reverse_cache/` up front
- leave empty `assets/` / `samples/` / `recon/` after cleanup

Why it is false progress:

- violates on-demand layout
- confuses "structure exists" with "evidence exists"

Smallest honest next move:

- create a namespace only when writing the first file into it
- delete empty leftover dirs after tasks

Self-check:

- would `dir /s` show any empty evidence folder that never received a file?

## Entry format for new anti-patterns

When a shortcut recurs across more than one job, add it in this shape:

```markdown
## Anti-pattern N: <short name>

Temptation:
- ...

Why it is false progress:
- ...

Smallest honest next move:
- ...

Self-check:
- ...
```

Keep it generic.
Do not copy live cookies, secrets, or one-off values here.

## Final rule

If a shortcut cannot survive one direct self-check, it is not a shortcut.
It is debt disguised as progress.
