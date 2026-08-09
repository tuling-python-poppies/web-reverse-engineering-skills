# x-kpsdk-cd: Bounded Problem (Solvable)

`x-kpsdk-ct` (the fingerprint credential from `/tl`) and `x-kpsdk-cd` (a per-request proof-of-work) are different problems. This reference states what is tractable, the concrete solution paths, and scoping guidance.

## What is tractable

- Minting `x-kpsdk-ct` browser-free: reproduce the bootstrap, run the collector in a VM sandbox, fill the environment surfaces, submit `/tl`, mint `ct` on a coherent egress. This is the main path and is the Provider's primary acceptance target.
- Minting `x-kpsdk-cd` browser-free: **solvable** via the full-lifecycle sandbox approach (see below).

## The cd mechanism

- `x-kpsdk-cd` is a per-request proof-of-work. Observed mechanics: a SHA-256-based work loop over a seeded input, a small number of rounds, and a difficulty threshold.
- The PoW seed mixes a value computed parent-side inside `p.js`'s VM, never sent on the wire. This is why a ct-only sandbox (running only `ips.js`) cannot produce `cd` — it lacks the parent context.

## Solution paths

### Path A: Full-lifecycle sandbox (recommended)

Run **both** `p.js` and `ips.js` in the same Node VM sandbox:

1. Load `p.js` → `KPSDK.configure(...)` executes naturally → the cd seed computation runs as part of the standard lifecycle.
2. `ips.js` loads inside the `/fp` context as normal → mints ct.
3. When `p.js` wraps a business request, it calls the cd generator internally → the PoW seed is available because `p.js` is running.
4. Hook or intercept the cd output at the point `p.js` attaches it to the outbound request header.

This approach makes cd a **natural byproduct** of running the full Kasada lifecycle, not a separate extraction problem. The sandbox already runs `ips.js`; extending it to also run `p.js` is an architectural expansion, not a new unknown.

### Path B: AST extraction (targeted)

If full-lifecycle is too heavy:

1. Locate the `cd` producer in `p.js` via the export/registration path, not text search (see `references/jsvmp-analysis-playbook.md`).
2. Identify the seed inputs, isolating the parent-side value.
3. Lift only that computation into a standalone function.
4. Verify the PoW loop (hash, rounds, threshold) against captured `cd` samples on frozen inputs before trusting it live.

### Path C: Same-sandbox interception

If `p.js` uses `KPSDK.cd()` or similar internal API to generate cd on demand:

1. In the sandbox, after `p.js` boots, hook `KPSDK.cd` (or the internal function it calls).
2. Call it with the business URL/params → get cd.
3. Attach to the Python HTTP request alongside ct.

## How to scope it in a work order

- If the target's business path does not require `cd`, state that and proceed on `ct` only.
- If `cd` is required, use Path A (full-lifecycle sandbox) as the default approach — it avoids the need to reverse the seed computation separately.
- Never fabricate or hardcode a `cd`. A frozen or guessed proof-of-work fails per request and is not a delivery.
- Gate acceptance on same-session business replay, not on a locally plausible `cd`.
