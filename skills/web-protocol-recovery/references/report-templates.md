# Report Templates

Use these headings to keep progress crisp and comparable across investigations.

## Report depth by success shape

| Shape | Use |
|---|---|
| `evidence` / `local-proof` | Light status only (below). Skip full recon/implementation/final templates unless the user expands scope. |
| `compact-replay` / `collector` | Recon -> dynamic validation -> implementation decision -> final delivery as phases complete. |
| Any shape at a pause | Escalation ladder report when changing rungs; minimal verifiable facts when handing off a solved fragment. |

### Light status (evidence / local-proof)

```markdown
shape: <evidence|local-proof>
route: <Provider ID|evidence-reuse>
status: <complete|blocked|failed>
decisiveEvidence: <bounded evidence>
artifactPath: <path, only if produced>
artifactSha256: <SHA-256, only if produced>
acceptanceTest: <required for local-proof>
result: <required for local-proof>
blockerOrNextStep: <one smallest move>
browserLifecycle: <state or none>
nextRead: <0-1 path>
```

## Recon report

```markdown
shape: <compact-replay|collector>
route: <chromium-recon|camoufox|wechat-miniapp>

## Recon
- Target URL:
- Final landing URL:
- Selected recon Provider and reason:
- Evidence mode: fresh browser baseline / evidence reuse / blocked-tool limited path
- Provider result: proved / skipped / blocked and why
- Chromium paired pass, when selected: chrome-devtools baseline result; js-reverse-mcp mutation result; any missing-half blocker; optional Cloak tier if used
- Direct route, when selected: Camoufox or WeChat ownership/lifecycle/cleanup result
- Recon isolation: separate profiles / explicit profile reuse with contamination risk / not applicable
- Page type: SSR / CSR / SPA / MPA / hybrid
- Useful data source: HTML / XHR / Fetch / GraphQL / WebSocket / asset / binary / other

Real request candidates
- Request 1:
  - URL:
  - Method:
  - Purpose:
  - Transport kind:
  - Paging fields:
  - Key headers:
  - Key cookies:
  - Decode needed:

Misleading signals
- 1.
- 2.

Next hypothesis
- 1.
- 2.
```

## Dynamic validation report

```markdown
shape: <evidence|local-proof|compact-replay|collector>
route: <Provider ID|evidence-reuse>

## Dynamic Validation
- Target function or request:
- Validation method: hook / diff / replay / fixed-input helper test
- Inputs:
- Observed outputs:
- Raw payload: hash/length/redacted sample by default; approved raw path only under artifactPolicy:

What changed on the wire
- Query:
- Body:
- Headers:
- Cookies:

Conclusion
- Verified helper or protocol rule:
- Verified decode or parser rule:
- Remaining unknowns:
```

## Implementation decision report

```markdown
shape: <compact-replay|collector>
route: <implementation Provider ID>

## Implementation Decision
- Implementation form: Python HTTP client / Python WebSocket client / Python + JS helper / Python + WASM helper / Python + bootstrap helper
- Why this form:
  1.
  2.
  3.
- Browser-free status: no browser runtime in final live-egress path
- Runtime-free status: no local embedded runtime / embedded runtime remains only for explicit artifact extraction

Protocol contract
- Required session state:
- Required headers:
- Required cookies:
- Required helper outputs:
- Required transport envelope:
- Required decode chain:
- Required local runtime artifact, if any:
- Transport admission exception, if any:

Known risks
- 1.
- 2.
```

## Escalation ladder report

```markdown
shape: <evidence|local-proof|compact-replay|collector>
route: <current Provider ID|evidence-reuse>

## Escalation Ladder
- Current rung:
- Last proved artifact:
- Exact failure at this rung:
- Why the next rung is the smallest honest move:
- Browser-free delivery still preserved as:
```

## Final delivery report

```markdown
shape: <compact-replay|collector>
route: <final Provider ID>
gateFamily: <one primary gate family>
providerChain: <ordered Provider IDs>
projectRoot: <absolute path>
layout: web-protocol-recovery-simple
stableFiles: <bounded paths>
endpoint: <scheme/host/port/route>
movingState: <signatures/cookies/headers/body fields>
transportKind: <HTTP/WebSocket/GraphQL/etc.>
decodeChain: <ordered steps or none>
verification: <fixed parity + approved live-egress replay + semantic/data-shape checks>
browserLifecycle: <engines opened/parked/closed and ID disposition>
limits: <page/retry/concurrency/rate/duration bounds>
caseWriteback: <not-eligible|offer-pending|declined|accepted>
residualRisks: <bounded list or none>
```

## Minimal verifiable facts

```markdown
shape: <evidence|local-proof|compact-replay|collector>
route: <Provider ID|evidence-reuse>

## Minimal Verifiable Facts
- Gate family:
- Fact 1:
- Fact 2:
- Fact 3:
- Fact 4:
- Fact 5:
```

## Project layout

Project layout has one owner: `references/methodology/project-layout.md`. Reports may name the selected root, layout id, stable files, and cache paths, but must not redefine the tree.
