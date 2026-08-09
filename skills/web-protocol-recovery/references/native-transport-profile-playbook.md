# Native Transport Profile Playbook

Use this playbook only after `transport-pre-gate-playbook.md` proves that a route is transport-gated and the closest maintained impersonation backend cannot express the admitted browser profile.

## Entry Gate

All conditions must hold:

1. a clean browser baseline reaches meaningful application semantics
2. a plain client and a closer impersonation backend reach a different branch before those semantics
3. cookies, signer state, and payload bytes have been ruled out as the first difference
4. packet or runtime evidence identifies a TLS, ALPN, HTTP version, HTTP/2, or connection-reuse field the current backend cannot express
5. a route-local adapter remains smaller than browser-backed delivery

## Capture Contract

Record browser family/build, operating system, CPU, target host/route, capture time, proxy behavior, cold/reused/resumed connection state, negotiated TLS/ALPN/HTTP version, raw capture path and SHA-256, and whether GREASE, ECH, extension permutation, or experiments were active.

Capture at least three clean cold connections from the same build. Classify each field as exact, membership-stable/order-variable, connection-dependent, route-dependent, or unknown.

## Canonical Profile

Store structured observations, not only JA3/JA4 strings.

TLS fields:

- offered protocol versions
- cipher-suite membership and order
- extension membership and order
- supported groups and key-share order
- signature algorithms
- ALPN offerings
- GREASE slots and values
- ECH behavior when observed
- session ticket, PSK, and resumption-dependent changes

HTTP/2 fields:

- SETTINGS identifiers, values, and wire order
- connection and stream window behavior
- pseudo-header order
- priority behavior or explicit absence
- first request and early follow-up ordering when admission depends on it

Connection fields:

- pooling and origin coalescing
- redirect reuse
- proxy tunnel reuse
- resumption behavior

## Backend Ladder

Choose the nearest implementation that expresses the proved profile:

1. maintained browser-family impersonation profile
2. route-local options on that backend
3. maintained native TLS/H2 backend with explicit controls
4. small patched native backend for one proved missing field
5. blocker when the required behavior cannot be reproduced safely

Do not implement a TLS stack or HTTP/2 stack from scratch. Python owns application HTTP semantics; the adapter owns only the route-local transport behavior.

## Structured Diff

Compare an observed profile and candidate profile with:

```text
python scripts/tools/transport_profile_diff.py observed.json candidate.json --json
```

Use `--ignore-grease-values` only when repeated captures prove the GREASE slots are stable while values rotate. The tool preserves list and SETTINGS order.

## Verification Gates

Require:

1. three-capture field classification
2. structured profile validation
3. candidate packet capture, not only library configuration
4. normalized diff with every remaining mismatch explained
5. repeated route admission
6. session reuse and pagination checks
7. route-local containment
8. dependency build/hash and clean-install proof when custom binaries are delivered
9. final collector remains browser-free
