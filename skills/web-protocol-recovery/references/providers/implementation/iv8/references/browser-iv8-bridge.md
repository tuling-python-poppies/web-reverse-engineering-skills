# 浏览器环境到 iv8 兼容桥接

本文件用于把单一浏览器页面上下文、调试工具快照或用户样本接入 `iv8` 复现链路。目标不是把浏览器整体载入 iv8，而是把可用来源的采样结果归一成 iv8 可承接的 `environment`、`config`、`page.load`、`netLog`、`wrapNative`、storage/cookie 和 Python 请求重放材料。

本文件只说明 evidence owner 应采什么，以及 iv8 receiver 如何消费 artifact。它不授权 iv8 receiver 启动、切换或调用浏览器工具；`SKILL.md` 的 Packet Permission 与 Side-Effect Gate 始终优先。`browserReconAllowed != yes` 时不导航，`liveReplayAllowed != yes` 时不下载页面/脚本/图片或发目标 HTTP，账号/session 范围未批准时不导入相应 Cookie/storage。

## 四层流程

1. 采样层：使用一个当前可用页面上下文、调试工具快照或用户样本采集网络、脚本线索、Cookie、storage、headers 和 JS 可见环境值。
2. 归一层：默认只保存脱敏 baseline 摘要，再生成最终 `browser_env.json`。只有用户确认字段、路径和保留期限后才保存原始结果；其它抓包、日志或历史样本只做对照，不混入最终请求链。
3. 注入层：用 `iv8.JSContext(environment=..., config=...)` 承接 JS 可见环境，用 `page.load` 承接 HTML/外链资源和生命周期，用最小 `wrapNative` patch 承接目标实际检测的缺口。
4. 重放层：Python `requests.Session` 只沿用 baseline 的 UA、headers、cookies、storage 派生值和每次循环内新生成的 sign/token/suffix。TLS/HTTP2 指纹不属于 iv8，必要时改用 `curl_cffi.requests` 或回到浏览器请求。

## 来源选择

按以下顺序选择一个 baseline 来源：

1. 已有 web-protocol-recovery evidence Provider 结果：先查 bundled case 和 reverse-process，再复用该 Provider 已经记录的同一 engine/session/target。原浏览器仍 live 时由该 evidence Provider 调用 source ID 并导出当前环境；iv8 只消费批准的 `browser_env.json`/artifact，不跨 MCP 调用 ID。
2. 没有上游浏览器证据的新 standalone 任务：若已知入口仍需要 fresh browser baseline，iv8 Provider 在 `browserReconAllowed=yes` 后向 web-protocol-recovery 返回 blocker，由 web-protocol-recovery 选择 reconnaissance Provider 并发出 bounded work order；iv8 receiver 不直接调用 `js-reverse-mcp`、CloakBrowser 或其它 browser MCP。
3. 用户提供的抓包、HTML、JS、Cookie、headers 或环境快照：用于无法直接打开目标页但仍要完成 iv8 复现的场景。
4. iv8 默认 environment：仅用于目标不依赖真实浏览器环境，或用户接受残余风险的场景。

被目标站风控拦截（412/403/验证码）时，由 web-protocol-recovery 选定的 evidence Provider 在批准范围内复核会话、headers、cookie、freshness 和页面状态；iv8 只接收结果 artifact。需要引擎级指纹/属性追踪时，由 web-protocol-recovery 向 `camoufox` Provider 发出 bounded work order，不由 iv8 自行切 engine。

每条真实请求链路只能选择一个 `BROWSER_BASELINE`，可取值：`browser`、`devtools`、`manual`、`default`。

## Baseline 选择

- `browser`：来自 evidence/discover owner bounded sidecar 导出的单一真实页面 artifact；具体 engine 由该 owner 选择并记录 provenance，iv8 receiver 不直接操作。适合目标依赖 Cookie、storage、UA、headers、canvas/WebGL 或页面生命周期时使用。
- `devtools`：来自手工 Console/Snippets 或降级调试工具快照，适合只需要少量 JS 可见环境值或请求样本时使用。
- `manual`：来自用户提供的抓包、HTML、JS、Cookie、headers 或环境 JSON，适合无法直接访问目标页时使用。
- `default`：使用 iv8 默认环境和脚本内常量，适合目标只依赖可控 URL、body、timestamp 或纯 JS 算法时使用。

## 缓存产物

- `js_reverse_cache/browser_env_raw.json`：可选原始环境快照；包含 Cookie、storage 或 token 时必须先确认，不得默认保存。
- `js_reverse_cache/browser_env.json`：最终单一 baseline 的归一化快照，主脚本只读取这个文件。
- `js_reverse_cache/browser_network.json`：baseline 网络请求/响应样本，仅在需要时保存。
- `js_reverse_cache/browser_scripts.json`：脚本 URL、源码片段或入口线索，仅在需要时保存。
- `js_reverse_cache/manual_sample.json`：用户样本归档，仅在用户明确要求保存时写入，并默认脱敏。

## browser_env.json Schema

推荐结构：

```json
{
  "baseline": "browser",
  "source": "browser-tool-or-manual-sample",
  "fallback_level": 0,
  "page_url": "https://example.com/page",
  "api_url": "https://example.com/api",
  "userAgent": "...",
  "timezone": "Asia/Shanghai",
  "headers": {"User-Agent": "..."},
  "cookies": [
    {"name": "name", "value": "...", "domain": ".example.com", "path": "/", "accountBound": false}
  ],
  "storage": {
    "accountBound": false,
    "local": {},
    "session": {}
  },
  "environment": {
    "location": {},
    "navigator": {},
    "window": {},
    "screen": {},
    "document": {},
    "media": {},
    "webgl": {},
    "webgl2": {},
    "webgpu": {},
    "audioContext": {},
    "visualViewport": {},
    "storage": {},
    "geolocation": {},
    "performance": {},
    "batteryManager": {},
    "history": {},
    "webrtc": {},
    "canvas": {}
  },
  "config": {
    "timezone": "Asia/Shanghai",
    "permissions": {},
    "time": {"mode": "logical"},
    "features": {}
  },
  "patches": {
    "canvas": {},
    "webgl": {},
    "nativeFunctions": []
  },
  "diagnostics": {
    "not_merged": true,
    "notes": []
  }
}
```

## iv8 API 映射

| 浏览器材料 | iv8 承接方式 |
| --- | --- |
| `navigator.userAgent/language/languages/platform/vendor/productSub/hardwareConcurrency/deviceMemory/maxTouchPoints/userAgentData/connection/plugins` | `environment.navigator` |
| `screen.width/height/availWidth/availHeight/colorDepth/pixelDepth/orientation` | `environment.screen` |
| `window.innerWidth/innerHeight/outerWidth/outerHeight/devicePixelRatio/screenX/screenY` | `environment.window` |
| `location.href/origin/protocol/host/path/search/hash` | `environment.location`，页面生命周期重要时同时用 `page.load({baseURL})` |
| `document.referrer/readyState/visibilityState/domain` | `environment.document` 或 `page.load(snapshot)` |
| HTML 与外链 JS/CSS | `__iv8__.page.load({html, resources, headers})` 或 `ctx.add_resource(...)` |
| Cookie | Python `requests.Session.cookies` + iv8 内 `document.cookie` 最小写入 |
| localStorage/sessionStorage | `ctx.eval` 在 context 创建后写入，不放进 `environment.storage` |
| WebGL/WebGL2/WebGPU 基础参数 | `environment.webgl`、`environment.webgl2`、`environment.webgpu` |
| canvas 指纹结果 | `environment.canvas`；目标检测具体函数时用最小 `wrapNative` patch |
| AudioContext latency/指纹值 | `environment.audioContext`；复杂音频渲染不能完整继承 |
| permissions/geolocation/media queries | `config.permissions`、`environment.geolocation`、`environment.media` |
| performance/time/timers | `environment.performance`、`config.time`、`time_mode`、`eventLoop.sleep/drain/advance` |
| XHR/fetch 被 SDK 改写后的 URL/header/body | iv8 内触发请求后读 `__iv8__.netLog.entries` |
| native 函数检测 | `__iv8__.wrapNative(fn, name)`，只 patch 目标实际读取的函数 |
| 可信 pointer/mouse 事件 | `__iv8__.input.dispatchPointerEvent` / `dispatchMouseEvent` |
| TLS/HTTP2/JA3/浏览器进程级指纹 | iv8 不能承接；用 `curl_cffi.requests`、浏览器侧请求或只作为风险说明 |

## 采集建议

开始采集前先查 root `references/cases/registry.json`。精确案例存在时，按其 `case.json` 和 `PROCESS.md` 列出的环境字段与锚点做最小补证，不要重复全量采集。厂商相同但产品版本或目标子类型不同，不得当作精确案例复用。

浏览器/调试上下文路径（由 bounded sidecar 的 evidence owner 执行；iv8 receiver 不直接执行）：

1. 打开目标页并完成与目标 API 同 session 的必要交互。
2. 采集网络请求/响应、目标脚本 URL、Cookie、localStorage、sessionStorage 和关键 headers。
3. 在同一页面上下文中采集 `navigator`、`screen`、`window`、`document`、`location`、WebGL/canvas 摘要和目标实际读取的字段。
4. 默认直接生成脱敏 `js_reverse_cache/browser_env.json`；只有用户确认后才把原始快照保存到 `browser_env_raw.json`。

手工样本路径：

1. 确认用户给出的 HTML、JS、Cookie、headers、请求体和响应样本属于同一 session 或同一次请求链路。
2. 仅在用户确认保存时，把脱敏样本写入 `js_reverse_cache/manual_sample.json` 或独立 HTML/JS 文件。
3. 只把 iv8 可承接字段写入 `browser_env.json`，其它字段放到 diagnostics 或报告中。

默认环境路径：

1. 只在目标不依赖真实浏览器环境，或用户接受残余风险时使用。
2. 在脚本顶部保留 UA、PAGE_URL、API_URL、timezone 等可编辑常量。
3. 请求失败且表现为环境分支或风控失败时，再回到浏览器环境桥接流程。

## 约束

- 一个主脚本默认只读取 `browser_env.json`，不要在运行时同时读多个快照拼字段。
- handoff 中浏览器仍 live 时，只有原 owner 能调用其 source ID；iv8 receiver 不启动另一 engine 去复取同一 ID。浏览器关闭后只消费 owner 已保存并标为 `artifact-only` 的同源快照。
- `cookies` 优先使用带 `domain`/`path` 的对象数组；旧字典格式只能绑定到 `page_url` 的精确 host，禁止用 `session.cookies.update()` 产生 domainless cookie。
- 每个 cookie artifact 同时记录 `accountBound: true|false|unknown`；`accountOrSessionUse=none` 只允许显式 `false`，`blocked|unknown` 不注入任何 cookie，`approved-identifiers-only` 只注入 packet 点名的 cookie。
- storage 同样记录顶层 `accountBound`；`approved-identifiers-only` 使用 `local:<key>` / `session:<key>` 精确点名。`none` 只注入显式 `false`，`blocked|unknown` 不写入 localStorage/sessionStorage。
- 切换 `BROWSER_BASELINE` 后必须重新采集同一套 UA、Cookie、headers、storage、页面 HTML、动态 JS 和签名输入。
- 使用 `manual` 或 `default` baseline 时，`browser_env.json` 的 `fallback_level` 必须大于 0，并在完成报告中说明缺失的真实浏览器证据。
- `browser_env.json` 顶层 `cookies` 只写入 Python `Session`，不要塞进 iv8 `config.cookies`；顶层 `storage.local/session` 只通过 `localStorage/sessionStorage.setItem` 写入，不要塞进 `environment.storage`。
- `environment.storage` 只表示 `navigator.storage.estimate()/persisted()` 这类配额指纹，不表示 localStorage 业务数据。
- storage 写入时机要与页面生命周期一致：默认先用 `page.load({baseURL, ...})` 或 `environment.location` 建立正确 origin，再写 `localStorage/sessionStorage`；如果目标内联脚本在 load 阶段读取 storage，必须把 storage prelude 插到目标脚本之前或手动控制脚本执行顺序。
- 环境桥接失败时优先查看页面报错、调用栈、目标实际读取字段和服务端响应差异，补目标实际读取的字段，不添加通用大 proxy。
- 生成 sign/header/token/suffix 时，如果 body、page、timestamp、nonce、cookie 或 storage 参与计算，必须在翻页循环内重建。
