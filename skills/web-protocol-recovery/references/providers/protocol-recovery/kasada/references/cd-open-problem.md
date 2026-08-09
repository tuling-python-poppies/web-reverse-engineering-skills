# x-kpsdk-cd: Open Problem

`x-kpsdk-ct` (the fingerprint credential from `/tl`) and `x-kpsdk-cd` (a per-request proof-of-work) are different problems. This reference states honestly what is tractable and what is not, so scope is set before committing.

## What is tractable

- Minting `x-kpsdk-ct` browser-free: reproduce the bootstrap, run the collector in a VM sandbox, fill the environment surfaces, submit `/tl`, mint `ct` on a coherent egress. This is the main path and is the Provider's primary acceptance target.

## What is the open problem

- `x-kpsdk-cd` is a per-request proof-of-work. Observed mechanics are roughly: a SHA-256-based work loop over a seeded input, a small number of rounds, and a difficulty threshold. The blocker is that the PoW seed mixes a value that is never sent on the wire, computed parent-side inside the VM. Without lifting that parent-side computation out of the script, the `cd` cannot be reproduced from captured traffic alone.

## How to scope it in a work order

- If the target's business path does not require `cd`, state that and proceed on `ct` only.
- If `cd` is required, treat it as a bounded blocker: report the seed-gap explicitly, note that recovery needs the parent-side VM computation lifted (an `ast` / interpreter-shape effort against the specific build), and do not claim a solved `cd` from a partial mapping.
- Never fabricate or hardcode a `cd`. A frozen or guessed proof-of-work fails per request and is not a delivery.

## Recovery direction (if in scope)

1. Locate the `cd` producer in the build via the export/registration path, not text search (see `references/jsvmp-analysis-playbook.md`).
2. Identify the seed inputs, isolating the parent-side value that never hits the wire.
3. Lift only that computation, verify the PoW loop (hash, rounds, threshold) against captured `cd` samples on frozen inputs before trusting it live.
4. Gate acceptance on same-session business replay, not on a locally plausible `cd`.
