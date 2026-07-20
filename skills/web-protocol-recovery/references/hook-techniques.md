# Hook Techniques

Use this file when runtime proof is faster than static reading.

## Highest-value hook targets

- `fetch`
- `XMLHttpRequest.prototype.open`
- `XMLHttpRequest.prototype.send`
- transport wrapper functions
- bootstrap helpers
- signer helpers
- storage reads and writes when session state is changing

## Hook goals

- capture pre-sign strings
- capture final payloads after wrapper mutation
- capture response-side refresh fields
- capture cookies or globals that change between requests

## Evidence interpretation

- a silent hook only disproves that exact boundary
- a quiet `document.cookie` hook does not clear `Set-Cookie`, returned JS, redirect wrappers, workers, or other writers
- a quiet storage setter hook does not clear direct property assignment or sibling state writers
- a quiet `fetch` hook does not clear XHR, wrapper, worker, or message-based transport
- if a console or isolated-world probe misses a page-owned helper, repeat the proof in the page-owned world before abandoning the lead

## Logging shape

- bind captures to target, event, method, URL, field, and a short caller hint when possible
- one request-bound log line is worth more than a dump of naked values

## Hooking order

1. wire-level hooks
2. wrapper-level hooks
3. helper-level hooks
4. local-variable breakpoints only if hooks still leave ambiguity

Rule:

- if instance-level hooks get replaced or skipped, move upward to the shared boundary that every call must cross such as the prototype, constructor wrapper, or transport egress

## Behavior safety

- default hooks to observe only
- forward original args, preserve `this`, and return the original result or promise
- if a hook changes behavior, treat the new failure mode as possible observer effect until proven otherwise

## Common traps

- hooking business-layer functions while missing the transport wrapper
- hooking one convenient object instance when the runtime keeps rebinding or cloning the real caller
- pausing too early with breakpoints and drowning in noise
- capturing only final hashes without the input string that produced them
