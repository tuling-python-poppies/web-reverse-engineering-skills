# Troubleshooting Playbook

Use this file after one bounded replay exists and an observed response/runtime symptom still blocks acceptance. It owns diagnosis by evidence. For preemptive checks against browser-backed delivery, stale-state hardcoding, broad hooks, rung skipping, or shape-only success, use `anti-patterns-playbook.md`.

## Symptom routing

### `403`, `412`, `429`

- compare headers
- compare cookies
- compare pacing
- compare sign freshness
- compare whether the challenged document URL itself succeeds after local bootstrap instead of after a guessed API pivot
- if failures start only after hooks or breakpoints, suspect observer effect and recapture a clean baseline

### `200` with business error

- compare query and body serialization
- compare timestamp precision
- compare transport wrapper outputs
- compare whether a verifier or cookie refresh step is now missing
- if subcodes change across attempts, map the ladder instead of treating each failure as unrelated noise

### `200` with gibberish or strings

- check decrypt path
- check fonts
- check hint arrays for page-specific header clues
- if raw bytes decode cleanly but saved files or terminal output still look garbled, separate local encoding or render issues from target-side decode gates before changing the protocol hypothesis

### the chosen login or session validator always looks valid

- tamper one decisive cookie, token, or session field and rerun the validator as a negative control
- if empty or tampered state still returns `200` or a page shell, treat that route as a false validator rather than proof of login
- find one stricter authenticated business endpoint that fails deterministically on bad state before persisting cookies or session artifacts

### first request works, replay fails

- check rotating cookies
- check in-memory refresh fields
- check whether bootstrap must run before each request
- prove cookie provenance before blaming the signer
- keep first-hop HTML, linked bootstrap assets, seed cookies, and generated state on one fresh session chain before widening environment patches
- if runtime egress exposes a full outbound `Cookie` header, compare that against the jar before blaming one cookie name or one refresh helper

### login looks accepted, but the target business route still redirects or rejects

- treat grant tickets, redirect handles, async follow-up URLs, and auth acks as authentication artifacts, not finished session proof
- capture post-auth callbacks, redirect exchanges, or session-establishing follow-up requests before changing the signer again
- diff cookie state before and after each post-auth hop so you know which step actually materializes the usable session

### local helper fails in a way that looks like target blocking

- check local runtime integrity first: broken symlinks, placeholder link files from copied `node_modules`, missing transitive deps, bad paths, and encoding-induced path resolution failures
- rerun the helper on frozen inputs and separate helper bootstrap failure from protocol failure before changing the signer hypothesis
- if the helper cannot load its own dependency tree, repair the local runtime before reopening target-side reverse work

### async artifact never appears or cannot be matched to one attempt

- establish the observation baseline first: mailbox cursor, webhook receiver, queue offset, or polling window
- trigger the flow only after the baseline is live
- diff pre-trigger and post-trigger artifacts so the attempt-to-artifact mapping is explicit
- treat timing, cursor state, and delayed delivery as part of the protocol workflow, not just operational noise

### user-defined latency threshold or honeypot budget

- if the user says a request or helper step that crosses `N` seconds should be treated as suspicious, encode that as a hard timeout in the collector
- abort immediately when that threshold is crossed instead of silently retrying it away
- report where the threshold is enforced so the handoff reflects the real safety contract

### the same request degrades into password-like or field-like errors after tight pacing

- repeat one previously understood request after a sufficient cooldown before changing fields that already matched
- compare the failure text or subcodes across slow and fast pacing, not just across code edits
- suspect punitive disguise or abuse cooldown when a field-looking error appears only after repeated attempts
- prefer cookie refresh or existing-session reuse over aggressive relogin loops when the target is rate-sensitive

### error or subcode shifts as each patch lands

- treat the changing sequence as evidence that one gate has been cleared and the next gate is now exposed
- distinguish "same failure again" from "different failure after progress"
- update the missing-gate hypothesis before rewriting the signer, wrapper, or bootstrap from scratch
- use the new code to decide whether the next move is cookie provenance, session admission, wrapper slot placement, verifier state, or simple pacing backoff

## Final rule

When a replay fails, route by the observed symptom and change one hypothesis at a time. If no replay exists yet, return to triage rather than treating setup uncertainty as troubleshooting.
