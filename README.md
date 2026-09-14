# Web Reverse Engineering Skills

这是一个面向兼容型 AI 编程代理的 Web 协议逆向 Skill 仓库。仓库把协议恢复、浏览器取证、验证码协议、JavaScript 运行时适配、Python 无浏览器交付，以及 Skill 自身的质量评估拆成可组合的工作能力。

仓库当前包含两个主要 Skill：

- `web-protocol-recovery`：协议恢复的公开入口和统一调度中心。
- `darwin-skill`：对 Skill 进行结构评估、效果验证、迭代优化和变更记录。

## 核心定位

`web-protocol-recovery` 只处理用户明确提出的 Web 或小程序协议工作，例如：

- 定位或恢复 `sign`、`token`、请求头、Cookie、challenge、验证码字段。
- 分析请求签名、请求包装、响应解码和会话状态机。
- 处理 JSVMP、WASM、浏览器环境差异和 JavaScript 混淆运行时。
- 恢复 Akamai、Kasada、River Security（瑞数）、Reese84 等挑战协议。
- 恢复 Geetest、阿里云、腾讯、字节跳动、网易易盾等验证码协议。
- 把已经证明的协议转换成 browser-free Python collector。
- 用固定向量、同轮状态和语义响应验证协议实现。

它不是通用的浏览器自动化 Skill，也不是普通 REST/GraphQL 客户端生成器。浏览器、JavaScript、WASM 和 iv8 只用于取证或生成窄工件；最终 live HTTP、WebSocket handshake 和 sent frame 必须由 Python 协议客户端或 collector 发出。



## 配套mcps仓库地址

https://gitee.com/tuling-python/web-reverse-mcps-tool

自研浏览器运行时框架代码仓库地址

https://gitee.com/tuling-python/nv8



## 什么时候触发

### 应触发

用户明确要求以下动作时触发：

- 恢复、定位、验证、实现、交付或复现 Web 协议。
- 分析真实请求中的签名、token、Cookie、challenge 或加密字段。
- 还原验证码的 `/load`、`/verify`、`/check` 等协议链。
- 分析 WebSocket、protobuf、WASM 或 JSVMP 在请求协议中的作用。
- 交付浏览器无关的 Python 签名器、解码器或采集器。

### 不应触发

以下任务应返回边界说明，不应强行进入协议恢复流程：

- 普通页面 QA、截图、点击、填表和回归测试。
- 单纯的 Camoufox、CloakBrowser 或浏览器使用问题。
- 普通 REST/GraphQL 客户端生成。
- 普通 AST 格式化、重命名或代码整理。
- 前端、CSS、UI 和营销页面工作。
- OpenCode/MCP/插件配置，除非用户明确修改的是 Skill 定义。
- 原生 ELF、PE、DLL、SO、APK、IPA、桌面程序或固件逆向。
- 没有 Web/小程序表面的纯 TCP/UDP、PCAP 或原生 OLLVM/虚拟机逆向。

仅出现“验证码”“403”“GraphQL”“WebSocket”“protobuf”“AST”或“浏览器”等词，并不足以选择某个 Provider；必须根据真实协议意图和证据路由。

## `web-protocol-recovery` 工作模型

这个 Skill 是唯一的公开协议入口，也是决策中心。内部 Provider 不是并列的公开 Skill，而是由它按工作单调度的能力模块。

每个协议任务按照以下顺序收敛：

```text
明确意图
  -> 选择交付形态
  -> 选择主要阻塞族
  -> 选择 route / Provider
  -> 固定证据和同轮状态
  -> 生成窄工件
  -> 固定向量或离线证明
  -> Python collector 交付
  -> 语义 live 验收
  -> 在不可变预算内扩展
```

### 四种交付形态

| 形态 | 用途 | 最小交付 |
|---|---|---|
| `evidence` | 只定位问题，不实现 collector | 真实请求、入口、状态来源或精确阻塞点 |
| `local-proof` | 固定样本或离线向量验证 | 可复现的转换、解码、还原 helper 或固定输出 |
| `compact-replay` | 小范围协议重放 | 简短的根目录 `main.py` 和窄 runtime/helper |
| `collector` | 稳定的浏览器无关交付 | 有边界、有预算、有语义验收的 Python collector |

没有明确说明时，静态证据任务默认从 `evidence` 开始；用户明确要求实现完整代码时，默认选择 `collector`，但仍先完成证据和离线证明。

### 四行协议头

协议任务的首次回复和后续 gated turn 使用四行机器头，便于在上下文压缩后恢复任务状态：

```text
shape: <evidence|local-proof|compact-replay|collector>
route: <Provider ID 或 evidence-reuse>
nextAsk: <none 或唯一的立即阻塞/治理决策>
nextRead: <本轮允许读取的精确路径>
```

其中：

- `shape` 是交付深度，不是协议类型。
- `route` 只能是 Provider ID 或 `evidence-reuse`，不能写 gate、strategy、profile 或文件路径。
- `nextAsk` 只保留眼前的执行硬阻塞或治理决策，不重复询问已经覆盖的常规动作。
- `nextRead` 遵守读取预算，避免无关地加载整个 Provider 树。

### 六类主要阻塞族

每个任务选择一个主要 gate family，其余问题记录为 secondary gate：

- `signer`：签名、摘要、请求头或参数计算。
- `challenge`：Akamai、Kasada、River Security、Reese84 等挑战状态。
- `verifier`：验证码、一次性验证和 WAF captcha gateway。
- `decode`：响应、字体、protobuf、压缩或加密数据解码。
- `session`：Cookie、token、设备状态和同轮会话绑定。
- `transport`：TLS、HTTP/2、WebSocket、代理或请求发送方式。

平台名不是 gate family。例如 `miniapp` 是 route 信号，GT4 是 verifier 家族，Akamai 通常属于 `challenge`。

## Provider 能力

Provider 注册表位于 [`skills/web-protocol-recovery/references/providers/registry.json`](skills/web-protocol-recovery/references/providers/registry.json)。当前能力分为四种角色。

### 取证与侦察

| Provider | 功能 |
|---|---|
| `chromium-recon` | 普通 Web 取证、页面状态、重定向、网络请求、initiator、脚本和运行时证据；指纹浏览器/CloakBrowser 也从此路线进入。新目标要求 DevTools clean baseline 与 js-reverse mutation 的配对流程。 |
| `camoufox` | 用户明确要求 Camoufox、SpiderMonkey 或引擎级属性追踪时进行取证；不负责最终 live egress。 |
| `wechat-miniapp` | 连接 WeChat miniapp WebView、WMPF、AppService 和 WMPFDebugger，定位小程序请求、脚本、目标线程和状态。 |

### 协议恢复与协议所有权

| Provider | 功能 |
|---|---|
| `browser-hooks` | 在已知边界上做可逆的 XHR、fetch、WebSocket、Cookie、crypto 或函数 hook。 |
| `ast` | 进行整文件结构恢复、AST 分析、源码改写和安全的调用/成员访问定位。 |
| `verifier` | 负责验证码家族选择、同轮状态、感知与 proof 构造、verify/check 语义验收。支持 GT3/GT4、阿里云、腾讯、字节、易盾、携程、百度、数美、云片、360 天御等流程。 |
| `akamai` | 负责 Bot Manager sensor、Cookie 状态机、业务 admission 和状态刷新。 |
| `river-security` | 负责瑞数/River Security 的 `412`、`$_ts`、S/T Cookie、URL/header challenge 和状态机。 |
| `reese84` | 负责 Reese84 challenge、随机解题路径、`reese84` Cookie、`x-d-token` 和业务 admission。 |
| `kasada` | 负责 `x-kpsdk-*`、`KP_UIDz`、KPSDK bootstrap、`/tl` sensor 和业务 admission。 |

协议 owner 在实现 Provider 工作期间继续拥有 acceptance，避免只验证 runtime 输出而忽略真正的服务器语义。

### 本地实现 runtime

| Provider | 功能 |
|---|---|
| `iv8` | 在浏览器式 JavaScript runtime 中生成窄工件，例如签名、challenge 字段、Cookie、wrapped body 或 GT4 `w`；禁止通过 JS 发请求、访问文件或持久化 Cookie。 |
| `python-node` | 对已知 JavaScript 入口提供 Node/vm/jsdom 或 Node/WASM 适配；支持 `direct-node`、`env-patch` 和 `wasm-sidecar` strategy。 |
| `nv8` | 为 Akamai/Kasada 等需要 Edge/浏览器式 host 的传感器提供完整本地 runtime 能力；它是 Provider，不是第四种 implementation mode。 |
| `pure-python` | 将已经证明的签名、解码、校验和序列化逻辑移植为 Python；Douyin BDMS 维护使用 `profile: douyin-abogus-native`。 |

严格的 implementation mode 只有 `iv8`、`python-node` 和 `pure-python`；`env-patch` 是 `python-node` strategy，`nv8` 是实现 Provider。

### 最终交付

| Provider | 功能 |
|---|---|
| `python-collector` | 维护根目录 `main.py`、Python live egress、HTTP/WebSocket、Cookie/session、预算、重试、分页、解析、解码、落盘和最终语义输出。它是唯一可以拥有最终 live egress 的 delivery Provider。 |

典型链路如下：

```text
chromium-recon -> browser-hooks/ast -> iv8/python-node/pure-python -> python-collector
verifier -> iv8/python-node/pure-python -> python-collector
akamai -> nv8/python-node/iv8 -> python-collector
river-security -> python-node(env-patch)/iv8 -> python-collector
reese84 -> iv8/python-node -> python-collector
kasada -> nv8/python-node -> python-collector
```

## 验证码协议能力

`verifier` Provider 会先按版本和供应商信号选择最小 family reference，不会因为一个通用字段或 HTTP 状态就猜测协议。

当前覆盖的重点家族包括：

- Geetest GT3：`register-slide`、`gettype.php`、`fullpage`、`slide`、`ajax.php`。
- Geetest GT4：`/load`、`lot_number`、`pow_detail`、`payload`、`w`、`/verify`。
- Geetest GT4 nine-grid：`risk_type=nine`、`captcha_type=nine`、`imgs`、`ques`、`nine_nums`。
- Aliyun Captcha V2/V3：`InitCaptchaV2/V3`、`VerifyCaptchaV2/V3`、`sg.xxx`、`pe.xxx`、`T001/F001`。
- Tencent TCaptcha/TDC：`cap_union_prehandle`、`tdc.js`、`TDC.getData(true)`、`cap_union_new_verify`。
- ByteDance VerifyCenter：`/captcha/get`、`/captcha/verify`、`captchaBody`、`cyfreso`、BDMS/mssdk slider。
- Netease Yidun：`NECaptcha`、`api/v3/get`、`api/v3/check`、`cb`、`data`。
- Ctrip：`captcha/v4`、`risk_inspect`、`verify_jigsaw`、`verify_icon`。
- Baidu Passport spin/rotate V2。
- Shumei、Yunpian、360 Tianyu 和其他 generic slider family。

验证码验收不以 OCR 置信度、滑块距离、非空 `w` 或 HTTP 200 为准，必须检查平台的语义成功字段。例如：

```text
GT4:    status == "success" && data.result == "success" && data.fail_count == 0
Aliyun: VerifyCode == "T001" && VerifyResult == true
Tencent: errorCode == "0" 且返回 ticket/randstr
```

同一轮的 token、图片、Cookie、callback、动态脚本、轨迹、sidecar 和 verify 请求不能跨轮拼接。

## GT4 当前实现边界

仓库中的 GT4 workflow 特别强调以下边界：

```text
/load -> image pair -> PoW/GCT/proof fields -> w/td -> /verify
```

- Python 获取同轮 `/load`、图片和 GCT 资源。
- `ddddocr` 结果先统一为背景原始坐标中的缺口中心。
- `setLeft`、`userresponse`、轨迹、`td` 和 `td_sign` 由 verifier workflow 负责。
- iv8 只加载当前 hash 绑定的 bundle，生成窄 `w` 工件。
- iv8 必须确认 webpack registry 存在且目标 export 可调用。
- Python 负责 budget ledger、缓存、`/verify` 和最终语义结果。
- response body 读取遵守 work-order 的 byte cap。
- bundle hash、adapter hash、ISO-8601 approval deadline 和 capability-denied adapter 都必须纳入 work-order。

项目侧的 GT4 交付应保留：

- `utils/iv8_silent.py`：抑制 iv8 import banner 的安全 helper。
- `utils/logger.py`：统一日志接口，支持可选 `loguru` 和 fallback logger。
- 根目录 `main.py`：Python-only live egress 入口。
- `js_reverse_cache/**`：同轮证据、图片、响应、向量和 checkpoint。
- 根目录 `分析报告.md`：完整 collector 交付报告。

## 安全与治理边界

### 默认允许的常规动作

在已选择的 shape 内，以下动作通常按 standing approval 执行并内部记账：

- 隔离浏览器 recon。
- 只读 live 请求和协议所需的 verifier submit。
- 在用户项目根目录下写入脱敏证据。
- 使用用户已经提供的 Cookie/session。
- 在初始不可变 request budget 内做合理规模的重放。

### 必须明确确认的动作

以下动作是 hard stop，不能由 Skill 自行推断授权：

- 安装依赖，例如 `pip install`、`npm install`。
- 在本地 runtime 主动执行目标站提供的 JS/WASM/HTML。
- 业务 mutation，例如表单提交、下单、支付、账号变更。
- 扩大 success shape 或提高 request budget。
- 持久化或导出 raw secret、Cookie、token、账号状态。
- 向 case library 写回新的案例。

### 文件和缓存规则

- 一个任务只使用一个绝对 `projectRoot`。
- 统一布局为 `web-protocol-recovery-simple`。
- 动态证据只能写入 `<projectRoot>/js_reverse_cache/**`。
- 不把 OS temp、AppData temp、Skill 目录作为主存储。
- case library 只保存脱敏、离线、hash-bound 的案例材料。
- 不覆盖现有 `main.py` 或其他稳定文件，除非工作单明确允许 exact path。
- 不创建 `collector/`、`analysis/` 或第二个项目根目录。

### 浏览器生命周期

- 一次只激活一个浏览器家族。
- 普通 Web fresh recon 先完成 DevTools clean baseline，再进行 js-reverse mutation。
- Camoufox 只在明确的 Camoufox/SpiderMonkey/engine-level 条件下选择。
- 浏览器 ID、session、profile 和 worker ID 不能跨引擎复用。
- 任务完成前必须关闭或明确记录 retained 的 runtime 资源。
- 不能在单个浏览器引擎失败三次后才宣布浏览器不可用；按 fallback 链切换并记录工具阻塞。

## 证据、案例与预算

### Evidence first

先固定以下信息，再写实现：

1. 真实 endpoint 和请求方法。
2. initiator、调用入口或最终 wire mutation point。
3. 会变化的状态来源，例如 token、Cookie、nonce、时间、设备字段或轨迹。
4. 一轮完整的请求/响应和客观 acceptance test。

如果用户已经提供 HAR、源码、固定向量或响应样本，优先使用 `evidence-reuse` 或 `local-proof`，能不开浏览器就不开。

### Case library

案例只通过 `references/cases/registry.json` 选择：

- 只有 `status=verified` 的 entry 可选择。
- `freshly-verified` 代表当前固定向量/测试证明，不自动代表目标线上状态仍有效。
- `historical-user-attested` 只提供历史流程证据，必须重新做当前目标验证。
- 案例必须匹配 exact scope 或多个独立高置信信号。
- 一个案例失败后不能直接选择 sibling case 规避失败。
- historical reference 只能作为 study-only 证据，不能直接复制进交付代码。

### Request budget

预算是跨 Provider、跨进程、跨 route 的不可变任务状态：

- 每次 navigation、HTTP request、retry、WebSocket handshake 或 sent frame 都要在 egress 前预留一个单位。
- 传输失败也消耗已预留单位，不退款。
- `total` 不能自动提高，`remaining` 不能通过重新启动进程恢复。
- Provider 必须遵守 `minDelayMs`、`concurrency`、redirect、retry 和 response byte cap。
- 预算耗尽时只能继续离线分析；增加预算必须使用 `nextAsk: scope-expansion`。

## 验收标准

以下条件共同决定完成状态：

1. 固定向量、命名 checkpoint 或源码 hash 证明通过。
2. 同轮状态完整，没有跨轮 token、Cookie、轨迹或动态脚本混用。
3. 请求字段在 canonical mutation point 生成，而不是只生成了一个看起来相似的 helper 输出。
4. response content type、challenge marker、业务字段和数据形状正确。
5. 最终请求由 Python 发出，浏览器/JS/WASM/iv8 没有承担 live egress。
6. collector 至少通过可重复的最小 live replay；不能只凭一次 HTTP 200 扩大规模。
7. `status=complete` 时所有 task-owned runtime 已清理，或者每个 retained resource 都有完整批准记录。
8. 根目录存在 `分析报告.md`，报告中记录证据、路径、hash、预算、验收和残余风险。

## 仓库结构

```text
.
├── README.md
├── .gitattributes
├── .gitignore
└── skills/
    ├── darwin-skill/
    │   ├── SKILL.md
    │   ├── references/
    │   ├── scripts/
    │   └── results.tsv
    └── web-protocol-recovery/
        ├── SKILL.md
        ├── references/
        │   ├── cases/
        │   ├── methodology/
        │   └── providers/
        ├── scripts/
        │   ├── gates/
        │   ├── providers/
        │   ├── tests/
        │   └── tools/
        └── test-prompts.json
```

### 重要文件

| 文件 | 作用 |
|---|---|
| `skills/web-protocol-recovery/SKILL.md` | 触发边界、统一调度、阶段规则和安全约束。 |
| `references/providers/registry.json` | Provider、角色、implementation mode 和 route 注册表。 |
| `references/methodology/architecture.md` | 决策中心、Provider 所有权、布局和 acceptance 架构契约。 |
| `references/methodology/provider-work-order.md` | work-order schema、scope、预算、执行权限和结果契约。 |
| `references/methodology/success-shape-scripts.md` | 四种 shape 的默认执行脚本和 overlay。 |
| `references/cases/registry.json` | hash-bound、可验证案例的唯一选择入口。 |
| `scripts/gates/preflight.py` | Skill 提交前的综合离线检查入口。 |
| `scripts/gates/validate_architecture.py` | 架构、路由、live egress、残留物和脚本布局检查。 |
| `scripts/gates/verify_case_hashes.py` | 案例 hash 和来源一致性检查。 |
| `scripts/gates/validate_evals.py` | route regression metadata 检查。 |
| `scripts/providers/delivery/python-collector/scaffold_project.py` | 在绝对 project root 下创建最小 collector 布局，拒绝覆盖。 |

## 内置工具箱

`web-protocol-recovery/scripts/` 下的工具用于离线分析、质量门禁和 Provider 辅助：

- `check_reverse_env.py`：检查 Python、Node、iv8、nv8、浏览器工具和 lockfile 环境。
- `crypto_fingerprint.py`：分析可疑字符串的编码、熵、字符集和可能类型。
- `protocol_diff.py`：对比两个 JSON/text 协议样本，支持路径过滤和脱敏。
- `evidence_normalizer.py`：规范化证据记录和敏感字段。
- `transcript_diff.py`：比较请求/响应 transcript。
- `transform_trace_diff.py`：比较转换链和中间值。
- `transport_profile_diff.py`：比较 transport profile 和网络层差异。
- `grpc_frame_inspector.py`：解析 gRPC frame 并执行负例检查。
- `protobuf_inspect.py`：离线识别 protobuf 字段和 wire type。
- `wasm_module_inspect.py`：检查 WASM exports/imports 和模块边界。
- `practice_lab.py`：运行 scope、session、wire mutation、状态和上下文隔离练习题。
- `forward_test_report.py`：生成 forward-testing 报告，验证路由和行为声明。
- `aliyun_v2_profile_diff.py`：比较 Aliyun V2 DeviceConfig、Log2、token 和 profile。
- `path_safety.py`：拒绝 symlink、junction、reparse point、hard link 和越界路径。

大多数诊断工具支持 `--self-test`，综合门禁会在 preflight 中执行已注册的 self-test。

## 快速使用

### 1. 让代理加载协议 Skill

在支持 Skill 的代理环境中，将本仓库的 `skills/` 目录作为 Skill 根目录，并确保代理可以读取：

```text
skills/web-protocol-recovery/SKILL.md
skills/darwin-skill/SKILL.md
```

不要把 `web-protocol-recovery` 的 Provider 文件当作独立顶层 Skill 安装；它们由公开入口按 work-order 加载。

### 2. 协议恢复任务示例

```text
请恢复这个站点 /verify 请求中的 w 和 td，先分析我提供的请求样本，最后交付 browser-free Python collector。
```

预期行为是：先选择 `collector`，识别 verifier gate，固定同轮证据和 scope，完成离线证明，再进入有限 live acceptance。不能直接把浏览器页面请求当作最终交付。

### 3. 离线证明任务示例

```text
我只想用固定向量验证这个签名函数，不需要浏览器和网络。
```

预期行为是：选择 `local-proof`，保持离线，不询问 live replay、账号、预算或项目目录；输出 `acceptanceTest` 和 `result`。

### 4. 运行 Skill 预检

在 `skills/web-protocol-recovery` 目录执行：

```bash
python scripts/gates/preflight.py --strict
```

常用的独立检查：

```bash
python scripts/gates/verify_case_hashes.py
python scripts/gates/build_case_registry.py --check
python scripts/gates/validate_architecture.py
python scripts/gates/validate_schemas.py
python scripts/gates/validate_markdown.py
python scripts/gates/validate_evals.py
```

`preflight --strict` 会检查案例 hash、registry projection、架构和文档契约、schema、route eval、案例单测、Skill 自测、诊断工具、Provider guard、live egress 和 entry discipline。

### 5. 检查指定提交的 commit body

历史提交默认不参与 commit-body gate，避免旧提交阻塞当前工作。需要审计某个提交时显式指定 ref：

```bash
python scripts/gates/preflight.py --strict --commit-body-ref HEAD
```

## `darwin-skill` 功能

`darwin-skill` 是 Skill 的质量优化器，不负责目标网站协议恢复。它提供：

- 9 维质量评分：frontmatter、工作流、失败模式、检查点、可执行性、资源整合、架构、实测表现、反例黑名单。
- 静态评估：检查 Skill 描述、路径、章节、边界和资源引用。
- 效果评估：使用典型 prompt 做 with-skill 与 baseline 对比。
- 独立 judge：通过子 agent 降低“自己修改、自己评分”的偏差。
- validation-gated 优化：只有验证后质量提高才保留。
- 棘轮式 Git 流程：记录修改、评估、保留或回滚。
- runtime neutrality 检查：避免把某个特定代理写死成唯一运行环境。
- 结果记录：使用 `results.tsv` 记录 score、模式、验证状态和残余风险。
- 成果卡片和评估报告生成。

它的典型流程是：

```text
读取 Skill
  -> 设计测试 prompt
  -> 建立 baseline
  -> 9 维评分
  -> 提出单点改进
  -> 静态与行为验证
  -> 人工确认
  -> 保留或回滚
  -> 记录 results.tsv
```

`dry_run` 可以用于资源受限的预评估，但不能被当作完整行为验证；重要质量声明应以 `full_test` 或明确人工确认作为依据。

## 设计原则总结

1. 证据优先：先证明真实请求、动态状态和 wire mutation point，再写实现。
2. 最小路径：优先使用 supplied artifact、固定向量和最小 Provider，不无理由升级 runtime。
3. 同轮一致：token、Cookie、图片、脚本、轨迹、sidecar 和响应必须来自同一轮。
4. Python 出网：本地 JS/WASM/iv8 只生成窄工件，最终 HTTP/WebSocket 由 Python 负责。
5. 语义验收：非空 sign、HTTP 200、runtime load 成功和一次 lucky replay 都不足以证明完成。
6. 明确边界：mutation、依赖安装、目标代码执行、预算扩展、raw secret 和 case writeback 都需要单独治理。
7. 可恢复：每个阶段记录 checkpoint、artifact path、hash、预算、runtime lifecycle 和 blocker。
8. 可维护：全局方法写入 methodology，能力实现写入 Provider，避免产生平行 Skill 和重复项目布局。

## 许可证与使用边界

本仓库中的 Skill 是协议分析和软件工程工作流定义。使用者应确保目标、账号、请求、样本和自动化行为具有合法授权。Skill 默认拒绝未授权的业务 mutation、敏感凭据导出、越界文件写入和未批准的目标代码执行。
