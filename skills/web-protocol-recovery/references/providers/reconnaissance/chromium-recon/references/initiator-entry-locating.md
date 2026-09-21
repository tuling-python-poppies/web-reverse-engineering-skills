# Initiator And Entry Locating

## When To Read

Read this after the paired pass captured a real request and its initiator/paused stack, but the true business frame that writes or builds the target value is not yet proven. It turns the js-reverse half's "first mutation hypotheses" and the Exit "initiator/source evidence" into a repeatable method. It stays inside recon scope: prove the write boundary and entry, then hand off. It does not own hook injection (browser-hooks), structural recovery (ast), or algorithm restoration.

## Locate Model

Work backward from the sink, keeping four layers separate:

```text
writer <- builder <- entry <- source
```

- `writer`: the final write into URL, header, query, body, cookie, storage, or message envelope.
- `builder`: the logic that assembles, transforms, signs, encrypts, or packages the value.
- `entry`: the action, event, callback, or response that starts the builder path.
- `source`: the true inputs of the builder — upstream responses, cookies, storage, memory state, environment facts, time, randomness, or user input.

Observe the sink first, then walk backward. Expand upstream immediately when a source depends on a prior response, `Set-Cookie`, challenge result, or session bootstrap.

## Preferred Path

Use this order whenever a live request already exists:

```text
request -> request detail -> initiator stack -> candidate frame -> argument proof
```

1. **Start from the request.** Capture the exact request carrying the target, where the target sits (URL/header/body/message), and one normal-state sample before probing risk state.
2. **Pull the initiator or paused stack.** Prefer the request's own initiator over broad source search; find the first business-relevant frame still close to the final write.
3. **Triage the stack** with this table. Do not stop at the first frame that merely forwards the request.

| Frame class | Typical signal | Action |
|---|---|---|
| Framework noise | transport client, UI framework, bundle runtime | skip |
| Security SDK shell | auth, security, fingerprint, risk SDK wrapper | inspect |
| Business frame | project source, request builder, field assembler | prioritize |

4. **Prove the candidate frame.** A frame is valid only when it proves at least one of: it receives the target value directly; it assembles the target from stable local inputs; it calls the final writer with the target argument. Proof uses arguments, local variables, or writer-side observation — never name similarity.

## Fallback Path

Use when the initiator is missing or unhelpful:

```text
target field text -> narrow assignment search -> targeted breakpoint -> hook confirmation
```

- Search for the write pattern before searching generic crypto names (`md5`, `aes`, `sign`).
- Place breakpoints only where local variables or branch conditions must be proven.
- Confirmation hooks are browser-hooks work and only apply once the sink or near-sink writer is known; broad hooks before a clean baseline are an anti-pattern.

## Completion Standard

Entry locating is complete only when all hold:

- the request carrying the target is identified from a real sample;
- one candidate frame is proven business-relevant by argument or writer-side observation;
- the relation between candidate frame and final writer is clear;
- `source` categories are separated into local computation, upstream response/state, environment fact, or mixed dependency, so the next stage knows whether the value is pure-compute or state-dependent;
- normal-state and risk-state chains are separated when both appear.

Hand off with what is proven, what remains open, and the next narrow blocker. This provider does not restructure the shell or restore the algorithm; that is the next Provider's work.

## Common Missteps

- searching `md5` / `aes` / `sign` before the writer is proven;
- stopping at a framework transport frame;
- treating a security SDK wrapper as the final entry without argument proof;
- drifting into algorithm restoration before the write chain is closed.
