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

Chat/final summary may still use the compact machine fields below. Project delivery additionally requires root file `分析报告.md`.

```markdown
shape: <compact-replay|collector>
route: <final Provider ID>
gateFamily: <one primary gate family>
providerStages: <ordered {provider, role, strategy?, profile?, purpose?} stages>
projectRoot: <absolute path>
layout: web-protocol-recovery-simple
stableFiles: <bounded paths>
report: 分析报告.md
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

## 分析报告.md

Required at `<projectRoot>/分析报告.md` for Full completion of `compact-replay` or `collector` after stable delivery files are written. Not required for pure read-only `evidence`. Never place under `js_reverse_cache/`.

```markdown
# 分析报告

## 任务摘要
- 目标站点/接口：
- 成功形态：compact-replay | collector
- 结论一句话：

## 目标与范围
- scheme/host/port/route：
- 授权与预算边界：

## 证据与入口
- 关键请求/入口函数：
- 状态来源（cookie/header/body/sign）：

## 协议/门控
- 主 gate family：
- 次要门控：
- 规范突变点：

## 实现路径
- Provider 顺序：
- 本地工件（iv8/python-node/pure-python 等）：
- 最终 live egress：python-collector / main.py

## 验收结果
- 固定向量/检查点：
- 最小 live 复放：
- 业务语义/数据形状：

## 稳定文件
- main.py / utils / tests：
- 分析报告.md：本文件

## 风险与限制
- residual risks：
- 不该扩展的范围：

## 复现步骤
1.
2.
3.
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
