# Public Project Triage

## Evaluation checklist

For each repository record:

- last substantive code commit, not README update
- license
- advertised Akamai version
- actual exported primitives
- sensor schema completeness
- challenge parser/solver completeness
- HTTP/session integration
- fixtures and live tests
- hard-coded UA, target URLs, screen, keys, or collector paths

## Reusable conclusions from the field case

1. A repository containing captured `akamai2.0.js` or `akamai3.0.js` may hold a full browser collector but still lack a standalone generator API.
2. A parser library can decode challenge descriptors without building sensor sections.
3. Legacy 1.7/1.75 generators commonly contain stale Chrome profiles and obsolete interaction models.
4. Shuffle, printable-character transforms, SHA-256, modular reduction, and cookie parsing are narrow reusable primitives.
5. Claims of v3 support or high pass rate require current live replay evidence.
6. Missing license means inspect for facts only; do not copy implementation.
7. Current targets may rotate collector paths/config while retaining protocol roles.

## Decision rule

Prefer a live downloaded collector plus narrow local host when:

- the target collector is large and frequently rotated
- a pure port lacks fixed-input parity
- the live collector already succeeds in a browser-free local runtime
- the Python HTTP boundary remains fully controlled

Prefer a pure Python port only after fixtures prove the complete current schema and challenge path.
