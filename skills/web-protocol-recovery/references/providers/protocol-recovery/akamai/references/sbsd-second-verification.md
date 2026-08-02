# SBSD Second Verification

Use this reference when an Akamai target exposes a CPR marker, a randomized
collector script, or a sensor POST whose body may be wrapped in an encrypted
`body` field. This file owns the SBSD-specific observation and verification
method. General Akamai state ownership remains in the Provider and cookie
state-machine references.

## Scope And Terminology

Separate these objects during analysis:

- **Challenge page**: a privacy or soft-challenge response returned to a
  business request.
- **Collector**: the randomized JavaScript asset that gathers browser and page
  signals.
- **Verification POST**: the collector-owned request that carries either a
  visible signal object or an encrypted `body` envelope.
- **Pass state**: the server-issued Cookie and business response state after
  the verification chain. A Cookie shape alone is not acceptance.

## Entry Evidence

Record one coherent chain:

```text
landing document
  -> server seed cookies
  -> randomized collector GET with v and optional t
  -> collector-owned verification POST
  -> response Set-Cookie transition
  -> next sensor or business request
```

Useful markers include `cpr_chlge`, a CPR parameter request, `bm_so`, `bm_s`,
`bm_sc`, `sbsd_o`, or `sbsd_c`. A marker must be paired with an independent
network, script, Cookie, or business-consumer observation before family
selection.

The collector GET may carry `v`, while the verification POST may omit `v` and
may omit the query string entirely. Record both request shapes. The absence of
`v` from the final URL does not prove that the value was unused during body
construction.

## Body Variants

Treat the wire body as a versioned variant, not a universal format.

### Visible JSON variant

The POST body can expose a JSON object containing `signals` directly. Count
the keys at the wire boundary and record the stage. The count is `N`, not a
fixed protocol constant; deployments can produce different counts at landing
and route stages.

### Encrypted envelope variant

The POST body can expose a JSON object whose top-level field is `body`, with a
string value containing the protected payload. The plaintext may contain fields
such as `ver`, `signals`, `perf`, `s`, and `tid` before wrapping, but this must
be confirmed by a same-run fixed vector.

A valid structural observation requires all of:

1. the collector GET URL and its `v`/`t` query-key shape;
2. the exact POST body length and a redacted digest;
3. the top-level JSON keys at the wire boundary;
4. the response status and Cookie names;
5. the next request's outbound Cookie names.

Do not infer the character table, shuffle seed, LCG constants, or plaintext
field order from body length alone.

## Dynamic Signals And Integrity

Dynamic key names are an obfuscation layer. Build a per-version mapping from
the observed key to a stable semantic label. Never hardcode a key name from a
single run.

The integrity candidate is often appended after the ordinary signal fields and
can therefore appear outside an otherwise sorted key sequence. This is a
candidate-identification clue, not proof of the field meaning.

Use this analysis order:

1. identify the timestamp candidate and its unit;
2. identify the seed-cookie input and its writer;
3. separate ordinary fields from the integrity candidate;
4. compare two same-version runs while keeping one runtime profile coherent;
5. derive the formula only from recorded intermediate checkpoints;
6. validate the result against a fixed vector and the wire body.

Do not treat a fixed count such as 115, a fixed split such as 114 plus 1, or
fixed `setCv` indexes as protocol invariants. All counts and indexes are
version- and stage-dependent until proved otherwise.

## VMP Instrumentation Map

For a current collector source, locate structures before inserting probes.

| Area | Observation | Rule |
|---|---|---|
| IIFE entry | trace buffer and bounded export | keep logs in memory until redaction |
| Context object | seed, timestamp, accumulator getters/setters | map current variables, not old indexes |
| Main dispatch loop | PC, opcode, stack depth | use coarse timing and bounded entries |
| Nested loop | inner opcode and top stack values | correlate with accumulator writes |
| Arithmetic handlers | `+`, `-`, `*`, `%`, `<<` operands/results | preserve JavaScript evaluation order |

When rewriting `POP()` calls into locals, keep the original left-to-right
evaluation order. For non-commutative operations, changing the order changes
the result and can produce invalid intermediate values.

Correlate seed, timestamp, accumulator writes, body generation, and response
Cookie state from the same execution. Do not combine fragments from separate
runs.

## Verification Levels

| Level | Required evidence | Result |
|---|---|---|
| Structure | collector URL, body shape, Cookie names, request order | variant identified |
| Algorithm | fixed input decrypts, unshuffles, and restores expected JSON | local-proof |
| Protocol | verification response and Cookie transition are accepted | protocol proof |
| Business | fresh business request returns expected application data | delivery acceptance |

`200`, a non-empty `body`, a long Cookie, or a generated signal count is not
semantic success. A `405`, privacy shell, or empty application response remains
a failed protocol checkpoint even when local body generation completed.

## Artifact Discipline

Store only redacted metadata, fixed vectors, digests, and bounded traces under
the assigned project `js_reverse_cache/akamai/` path. Do not store raw Cookie
values, raw verification bodies, full fingerprint values, or full collector
source in Provider notes or the case library.
