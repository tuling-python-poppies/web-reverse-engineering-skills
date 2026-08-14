# NV8 操作说明书

本地 Edge V8 JavaScript Sandbox，基于 Node.js vm 隔离，提供完整浏览器 API 兼容层。

**说明：** 本文档中 `<nv8-root>` 指 NV8 安装目录。npm 包名：`nv8`。

当前基线：

- Node.js `24.11.0`
- 默认浏览器 profile：Edge 150
- 可选 profile：Edge 151
- 默认执行后端：`child-process`
- 测试：`15/15` 通过（公开 API + 协议层）

## 目录

1. [运行前提](#1-运行前提)
2. [安装到项目](#2-安装到项目)
3. [公共 API 一览](#3-公共-api-一览)
4. [createSandbox 快捷 API](#4-createsandbox-快捷-api)
5. [NV8 完整 API](#5-nv8-完整-api)
6. [指纹 profile](#6-指纹-profile)
7. [时钟和调度 profile](#7-时钟和调度-profile)
8. [执行后端](#8-执行后端)
9. [页面、Realm 和 Worker](#9-页面realm-和-worker)
10. [离线网络 replay](#10-离线网络-replay)
11. [请求采集和 API Trace](#11-请求采集和-api-trace)
12. [性能优化说明](#12-性能优化说明)
13. [生命周期和资源限制](#13-生命周期和资源限制)
14. [调试子进程](#14-调试子进程)
15. [安全边界](#15-安全边界)
16. [常见问题](#16-常见问题)

---

## 1. 运行前提

### 1.1 Node 版本

必须使用 Node 24.x。Python 宿主脚本通过 `NVM_HOME` 自动定位，无需手动切换：

```powershell
node --version   # 期望: v24.x
```

Node 版本错误时会出现 `module.hasTopLevelAwait is not a function` 等报错，这不是项目问题，先修正 Node 版本。

### 1.2 实验性标志

所有使用 nv8 的脚本都需要加 `--experimental-vm-modules`：

```powershell
node --experimental-vm-modules your-script.js
```

### 1.3 依赖

```powershell
cd <nv8-root>
npm install --ignore-scripts
```

---

## 2. 安装到项目

### 2.1 在你的项目里安装本地包

```powershell
# 在你的项目目录执行（使用绝对路径指向 NV8 安装目录）
npm install <nv8-root>
```

安装后 `package.json` 会写入：

```json
"nv8": "file:<nv8-root>"
```

### 2.2 禁止全局 link 作为默认方案

不要用全局 `npm link` 作为默认安装方式。每个协议恢复项目都应在自己的 `package.json` 中声明 `nv8`，并在项目目录执行 `npm install`，这样 `node_modules/nv8/package.json` 可以作为运行前检查点。

### 2.3 在脚本里导入

```js
import { createSandbox, edge151Fingerprint } from 'nv8';
```

---

## 3. 公共 API 一览

| 导出 | 类型 | 说明 |
|------|------|------|
| `createSandbox` | 函数 | 简洁 API，推荐入口 |
| `EdgeSandbox` | 类 | 完整底层 API |
| `edge150Fingerprint` | 对象 | Edge 150 冻结指纹 |
| `edge151Fingerprint` | 对象 | Edge 151 冻结指纹 |
| `drainWorkerThreadPool` | 函数 | 关闭全局 Worker 线程池 |

---

## 4. createSandbox 快捷 API

### 4.1 基础用法

```js
import { createSandbox, edge151Fingerprint } from 'nv8';

const sb = await createSandbox('https://example.com', {
  fingerprint: edge151Fingerprint,
  backend: 'worker-thread',   // 或 'child-process'
  timeout: 5000,
  heap: 512,                  // MB
});

// 执行 JS，直接返回值（不是 {type, value}）
const ua = await sb.run('navigator.userAgent');
console.log(ua);

// 导航到新页面
await sb.navigate('https://example.com/next');

// 读取请求记录
const requests = await sb.requests();

// 关闭
await sb.close();

// 进程退出前清理线程池
createSandbox.drain();
```

### 4.2 `createSandbox(url, options)` 参数

| 参数 | 说明 |
|------|------|
| `url` | 页面 URL 字符串 |
| `options.fingerprint` | 指纹对象，默认 Edge 150 |
| `options.backend` | `'child-process'`（默认）或 `'worker-thread'` |
| `options.timeout` | 执行超时，毫秒，默认 1000 |
| `options.heap` | 最大堆内存，MB，默认 512 |
| `options.replay` | 网络 replay 数组 |

### 4.3 Sandbox 实例方法

| 方法 | 说明 |
|------|------|
| `sb.run(code)` | 执行脚本，直接返回值 |
| `sb.eval(code)` | 执行脚本，返回 `{type, value}` |
| `sb.runAll(sources[])` | 批量执行，返回值数组 |
| `sb.runModule(source, url)` | 执行 ES module |
| `sb.navigate(url)` | 导航到新页面（字符串快捷方式） |
| `sb.navigate({url, html, referrer})` | 导航带完整配置 |
| `sb.requests()` | 读取网络请求记录 |
| `sb.clearRequests()` | 清空请求记录 |
| `sb.enableTrace()` | 开启 API trace |
| `sb.disableTrace()` | 关闭 API trace |
| `sb.trace()` | 读取 trace 记录 |
| `sb.clearTrace()` | 清空 trace |
| `sb.close()` | 关闭沙箱 |
| `sb.raw` | 访问底层 `EdgeSandbox` 实例 |

### 4.4 `Symbol.asyncDispose` 支持

```js
// Node 24+ 显式资源管理
await using sb = await createSandbox('https://example.com');
const result = await sb.run('1 + 2');
// 离开 using 块时自动 close()
```

### 4.5 退出清理

```js
// 进程结束前调用，确保 Worker Thread 干净退出
createSandbox.drain();
```

---

## 5. NV8 完整 API

### 5.1 创建

```js
import { EdgeSandbox, edge151Fingerprint } from 'nv8';

const sandbox = await EdgeSandbox.create({
  page: {
    url: 'https://example.com/',
    html: '<!doctype html><body></body>',
    referrer: '',
    contentType: 'text/html',
  },
  fingerprint: edge151Fingerprint,
  execution: { backend: 'child-process' },
  limits: {
    timeoutMs: 5000,
    maxHeapBytes: 512 * 1024 * 1024,
  },
  proxyTrace: { enabled: false },
  networkCapture: { enabled: true, maxEntries: 1000 },
  replay: [],
});
```

### 5.2 执行

```js
// 脚本（返回 {type, value}）
const result = await sandbox.evaluate(source);

// ES module
const result = await sandbox.evaluateModule(source, 'https://example.com/main.mjs');

// 批量执行（单次 IPC 往返，性能最优）
const results = await sandbox.batchEvaluate([code1, code2, code3]);
```

### 5.3 页面管理

```js
// 替换页面（保留 Cookie/Storage 持久化状态）
await sandbox.setPage({
  url: 'https://example.com/next',
  html: '<!doctype html><body>Next</body>',
});
```

### 5.4 请求和 Trace

```js
const requests = await sandbox.networkRequests();
sandbox.clearNetworkRequests();

await sandbox.enableTrace();
const entries = await sandbox.trace();
await sandbox.disableTrace();
await sandbox.clearTrace();
```

### 5.5 关闭

```js
await sandbox.close();
// 可重复调用，无副作用
```

---

## 6. 指纹 profile

### 6.1 选择 profile

```js
import { edge150Fingerprint, edge151Fingerprint } from 'nv8';

// Edge 150（默认）
const sb = await createSandbox(url, { fingerprint: edge150Fingerprint });

// Edge 151
const sb = await createSandbox(url, { fingerprint: edge151Fingerprint });
```

Edge 151 相比 150 的新增 surface：
- `FontFaceSet` 相关表面
- `WheelEvent.prototype.momentum`
- `PerformanceNavigationTiming.navigationId`
- `Intl.v8BreakIterator` 兼容 adapter
- `Error.stackTraceLimit` descriptor 更新
- `queryLocalFonts()` 全局暴露

### 6.2 自定义 profile（不要直接修改冻结对象）

```js
const myFingerprint = {
  ...edge151Fingerprint,
  navigator: {
    ...edge151Fingerprint.navigator,
    language: 'en-US',
    languages: ['en-US', 'en'],
    hardwareConcurrency: 8,
  },
  screen: {
    ...edge151Fingerprint.screen,
    width: 2560,
    height: 1440,
    availWidth: 2560,
    availHeight: 1400,
    devicePixelRatio: 1.25,
  },
  timing: {
    ...edge151Fingerprint.timing,
    jitterSeed: 0xdeadbeef,   // 控制 memory/audio/canvas 噪声种子
  },
};
```

### 6.3 指纹结构总览

```
fingerprint
├── browserMajorVersion        // 150 或 151
├── locale                     // 'zh-CN'
├── timezone                   // 'Asia/Shanghai'
├── navigator
│   ├── userAgent
│   ├── platform
│   ├── languages / language
│   ├── hardwareConcurrency
│   ├── deviceMemory
│   ├── webdriver              // 保持 false
│   ├── plugins[]
│   ├── mimeTypes[]
│   └── userAgentData          // UA-CH 高熵值
├── screen
│   ├── width / height
│   ├── availWidth / availHeight
│   ├── colorDepth / pixelDepth
│   ├── devicePixelRatio
│   └── availLeft / availTop / isExtended
├── rendering
│   ├── webglVendor            // 'Google Inc. (NVIDIA)'
│   ├── webglRenderer          // ANGLE 渲染器字符串
│   └── webgpu                 // WebGPU 配置
├── timing
│   ├── wallClockOffsetMs
│   ├── dateNowResolutionMs
│   ├── performanceResolutionMs
│   ├── performanceJitterMs
│   ├── jitterSeed             // 控制 memory/audio/canvas 噪声
│   ├── minimumTimerDelayMs
│   └── animationFrameIntervalMs
└── capabilities
    ├── network                // online / effectiveType / rtt / downlink
    ├── serviceWorker          // enabled
    ├── media                  // audioCodecs / videoCodecs / devices
    ├── sensors                // 各传感器配置
    └── externalDevices        // bluetooth / hid / serial / usb
```

### 6.4 反检测特征（已内置）

以下特征已通过通用方式内置，无需手动配置：

| 特征 | 实现 |
|------|------|
| `document.hasFocus()` | 始终返回 `true` |
| `outerHeight - innerHeight` | 固定 57px（模拟工具栏） |
| `navigator.userAgentData.brands` | `Not A;Brand / Chromium / Microsoft Edge` |
| `uaFullVersion` | `150.0.7718.1` / `151.0.7849.46` |
| `navigator.plugins` | 5 个 PDF Viewer 插件 |
| `navigator.mimeTypes` | `application/pdf` + `text/pdf` |
| `connection.type` | `wifi` |
| `connection.rtt` | `50` ms |
| `Notification.permission` | `default` |
| `webkitAudioContext` | `AudioContext` 别名 |
| `chrome.runtime` | 完整 stub |
| `WebGL VENDOR` | `Google Inc. (NVIDIA)` |
| `performance.memory` | 基于 jitterSeed 的随机值 |
| Audio analyser 噪声 | 基于 jitterSeed，session 唯一 |
| Canvas getImageData 噪声 | 基于 jitterSeed，session 唯一 |

### 6.5 关于 jitterSeed

`timing.jitterSeed` 同时控制三个 session 唯一指纹：

- `performance.memory.totalJSHeapSize` / `usedJSHeapSize`（±8% 偏移）
- `AnalyserNode.getFloatFrequencyData` / `getByteFrequencyData` 等音频数据
- `getImageData` 返回的像素数据（约 1/64 字节 ±1 扰动）

不同 jitterSeed → 不同 session 指纹，相同 jitterSeed → 可复现。

### 6.6 站点特定配置

以下内容**因目标站点而异**，逆向时按需配置而非写死：

- `screen.width/height`、`screenX/screenY` — 取决于要模拟的用户画像
- `battery.level/charging` — 部分站点读取充电状态
- `navigator.language/languages` — 语言环境
- `capabilities.network` — 网络类型/速度
- `capabilities.media.devices` — 枚举的音视频设备

---

## 7. 时钟和调度 profile

```js
timing: {
  wallClockOffsetMs: 0,         // Date.now() 偏移
  dateNowResolutionMs: 0,       // Date 量化精度（0=不量化）
  performanceResolutionMs: 0,   // performance.now() 量化
  performanceJitterMs: 0,       // performance.now() 抖动振幅
  jitterSeed: 0x4e5638,         // 确定性噪声种子
  minimumTimerDelayMs: 0,       // setTimeout 最小延迟
  animationFrameIntervalMs: 16, // rAF 帧间隔
}
```

---

## 8. 执行后端

| 后端 | 隔离级别 | 启动速度 | 适用场景 |
|------|---------|---------|---------|
| `child-process` | 进程隔离（默认） | 较慢，约 400ms 热启动 | 不受信任代码、生产环境 |
| `worker-thread` | V8 Isolate 隔离 | 快，约 160ms 热启动 | 受信任代码、高频调用 |

Worker Thread 池在模块加载时预热，第一次 `createSandbox` 无额外等待。

不要在不受信任代码场景使用 `worker-thread`，它不是进程级安全边界。

---

## 9. 页面、Realm 和 Worker

### 9.1 iframe

同源 iframe 创建独立的完整 Realm，各自有独立的 `Array`、`JSON`、DOM 构造器：

```js
await sb.run(`
  const iframe = document.createElement('iframe');
  document.body.appendChild(iframe);
  iframe.contentWindow.Array !== Array; // true
`);
```

### 9.2 DedicatedWorker

Worker 脚本必须来自 replay、Blob URL 或 `data:` URL：

```js
const sb = await createSandbox('https://example.com', {
  replay: [{
    method: 'GET',
    url: 'https://example.com/worker.js',
    body: 'self.onmessage = e => self.postMessage(e.data * 2);',
  }],
});

const result = await sb.run(`
  new Promise(resolve => {
    const w = new Worker('https://example.com/worker.js');
    w.onmessage = e => resolve(e.data);
    w.postMessage(21);
  })
`);
// result === 42
```

---

## 10. 离线网络 replay

### 10.1 配置

```js
const sb = await createSandbox('https://api.example.com', {
  replay: [
    {
      method: 'GET',
      url: 'https://api.example.com/data',
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: 'value' }),
    },
    {
      method: 'POST',
      url: 'https://api.example.com/submit',
      status: 200,
      body: '{"ok":true}',
    },
  ],
});
```

未匹配 replay 的请求不会真实发送，直接返回 `TypeError`。

### 10.2 读取捕获的请求

```js
const requests = await sb.requests();
for (const req of requests) {
  console.log(req.method, req.url);
  console.log(req.headers);
  console.log(req.bodyText);    // UTF-8 视图
  console.log(req.bodyBase64);  // Base64 无损视图
}
```

---

## 11. 请求采集和 API Trace

```js
// 开启 trace（默认关闭）
await sb.enableTrace();
await sb.run('navigator.userAgent; document.body');

const entries = await sb.trace();
// entries[0] = { sequence, operation, api, receiver, arguments, result }

await sb.disableTrace();
await sb.clearTrace();
```

Trace 观察兼容层 API 调用，不是真实 Chromium DevTools 调用栈。

---

## 12. 性能优化说明

以下优化已内置，无需手动配置：

| 优化 | 效果 |
|------|------|
| Worker Thread 线程池（最多2个，30s TTL） | 热启动 ~160ms（原 ~1300ms） |
| Module bundle（3990 模块预打包） | 冷加载 ~300ms（原 ~1012ms） |
| Script LRU cache（256条 vm.Script） | evaluate ~0.025ms/call（原 ~0.3ms） |
| Pre-warm realm shell | setPage ~160ms（原 ~330ms） |
| RESET_REALM opcode | 页面切换复用 source cache |
| BATCH_EVALUATE opcode | 批量执行单次 IPC 往返 |
| Ring buffer / Buffer list | 零拷贝帧编码 |

### 12.1 重建 module bundle

修改了 `src/` 里的 realm 模块后必须重建：

```powershell
cd <nv8-root>
node tools/build-module-bundle.mjs
```

### 12.2 批量执行

```js
// 一次 IPC 往返执行多个表达式，性能最优
const [ua, lang, mem] = await sb.runAll([
  'navigator.userAgent',
  'navigator.language',
  'performance.memory.usedJSHeapSize',
]);
```

---

## 13. 生命周期和资源限制

### 13.1 默认限制

| 字段 | 默认值 |
|------|--------|
| `timeoutMs` | 1000 ms |
| `maxHeapBytes` | 512 MB |
| `maxSourceBytes` | 1 MB |
| `maxHtmlBytes` | 4 MB |
| `maxOutputBytes` | 1 MB |
| `maxPayloadBytes` | 8 MB |
| `maxRealms` | 12 |

### 13.2 推荐模板

```js
const sb = await createSandbox(url, options);
try {
  const result = await sb.run(source);
  console.log(result);
} finally {
  await sb.close();
}
```

### 13.3 进程退出清理

```js
process.on('exit', () => createSandbox.drain());
```

---

## 14. 调试子进程

```powershell
$env:EDGE_SANDBOX_CHILD_INSPECT_BRK = "9230"
$env:EDGE_SANDBOX_DISABLE_TIMEOUT = "1"
$env:EDGE_SANDBOX_CHILD_STDERR = "1"
node --experimental-vm-modules your-script.js
```

然后打开 `edge://inspect` 或 `chrome://inspect`，配置 `localhost:9230`，点击 inspect。

调试完毕后清除变量：

```powershell
Remove-Item Env:EDGE_SANDBOX_CHILD_INSPECT_BRK -ErrorAction SilentlyContinue
Remove-Item Env:EDGE_SANDBOX_DISABLE_TIMEOUT   -ErrorAction SilentlyContinue
Remove-Item Env:EDGE_SANDBOX_CHILD_STDERR      -ErrorAction SilentlyContinue
```

---

## 15. 安全边界

### 15.1 child-process 隔离

- 用户代码不能访问宿主 Node global
- 超时后杀进程，后续任务使用全新进程
- IPC 有大小限制

### 15.2 沙箱内无法访问

- 外部 HTTP/WebSocket/TCP
- 本地文件系统
- Node 内置模块（`fs`、`process`、`child_process` 等）
- 真实 GPU、摄像头、麦克风

### 15.3 适用场景

适合：执行浏览器 JS bundle（签名、Cookie、token 生成）、离线协议调试和 replay、指纹读取测试、Worker/iframe Realm 关系验证。

不适合：不等于真实 Chromium 通过、不提供 TLS/JA3/HTTP2 指纹、不提供真实渲染和 GPU 行为。

---

## 16. 常见问题

### Q: `module.hasTopLevelAwait is not a function`
Node 版本不对，必须是 24.x。

### Q: `fingerprint userAgent must describe Chrome ...`
UA 必须包含 `Chrome/150.` 或 `Chrome/151.`，不能包含 `Edg/`。

### Q: `fetch()` 返回 `TypeError`
没有匹配的 replay 记录。检查 method、URL（含协议/路径/query）是否完全一致。

### Q: 返回值是 `{ type: "other" }`（使用底层 `EdgeSandbox` API 时）
复杂对象不能跨 IPC 传输，在沙箱内用 `JSON.stringify()` 序列化后再返回。

### Q: `createSandbox` 的 `sb.run()` 返回 undefined
复杂值会返回 `undefined`（`run` 省略了 type 信息）。如果需要 type，改用 `sb.eval()`。

### Q: Worker 无法加载
Worker URL 必须在 replay 中有对应的 GET 记录，或是当前沙箱创建的 Blob URL。

### Q: 运行很慢
- 检查 `timeout` 是否太小
- 首次启动 Worker Thread 需要预热，后续会快很多
- 复杂 HTML 或超大 source 会增加 IPC 开销
