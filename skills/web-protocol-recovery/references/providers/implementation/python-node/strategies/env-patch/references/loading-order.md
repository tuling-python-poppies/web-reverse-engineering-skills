# 环境模块加载顺序

## 标准加载顺序

```text
core/proxy-access-monitor.js           ← vm-browser-gap-diagnose.js 始终自动加载
core/profile-seed-manager.js           ← 传入 --profile/--profile-file 时自动加载
core/minimal-proxy-browser-env.js      ← 始终自动加载；后续模块可替换对应根对象
───────────────────────────── ↑ 自动 / ↓ 手动指定
bom/window-global-apis.js
bom/navigator-fingerprint.js
bom/location-url-state.js
bom/history-state.js                  ← 按需，依赖 location-url-state.js
bom/screen-fingerprint.js
bom/web-storage.js
bom/web-crypto.js
bom/performance-timing.js
bom/console-log-buffer.js             ← 可选
bom/observer-constructors.js          ← 可选
dom/event-constructors.js
dom/document-dom-runtime.js
dom/html-element-constructors.js      ← 必须在 document-dom-runtime.js 之后
webapi/fetch-request-response.js      ← 按需
webapi/xml-http-request.js            ← 按需
webapi/blob-file-formdata.js          ← 按需
webapi/url-search-params.js           ← 按需
webapi/network-mock-recorder.js       ← 按需，需在 XHR/fetch 之后
webapi/web-audio-fingerprint.js       ← 按需，AudioContext 指纹
webapi/webrtc-peerconnection.js       ← 按需，RTCPeerConnection 探测
webapi/worker-messaging.js            ← 按需，覆盖 window-global-apis.js 基础 Worker stub
encoding/base64-codec.js              ← vm-browser-gap-diagnose.js 已内置
encoding/text-codec.js                ← 按需
timer/timeout-interval-scheduler.js   ← vm-browser-gap-diagnose.js 已有确定性调度器；仅需活动 timer 清单时追加
js_reverse_cache/env/ai-generated/*   ← 项目本地补丁最后加载
```

## 分类内部顺序

### BOM 内部顺序

```text
window-global-apis → navigator-fingerprint → location-url-state → history-state → screen-fingerprint → web-storage → web-crypto → performance-timing
```

- `window-global-apis.js` 先提供宽泛构造器和窗口 API；专用 navigator、location、screen 和 storage 模块随后覆盖对应根对象或子属性。
- `location-url-state.js` 必须在 `history-state.js` 前：history 依赖它更新 URL。
- `screen-fingerprint.js` 放在宽泛窗口 API 后，避免基础 `screen.orientation` 覆盖 profile 值。
- `web-crypto.js` 和 `performance-timing.js` 可以放在 BOM 最后。`web-crypto.js` 使用真实 host WebCrypto，不接受固定伪随机 seed。

### DOM 内部顺序

```text
event-constructors → document-dom-runtime → html-element-constructors
```

- `event-constructors.js` 定义事件类，`document-dom-runtime.js` 可能用到。
- `html-element-constructors.js` 强依赖 `document-dom-runtime.js` 提供的 `Element` 基类，必须在之后。

### WebAPI 内部顺序

```text
fetch-request-response → xml-http-request → blob-file-formdata → url-search-params → network-mock-recorder
web-audio-fingerprint / webrtc-peerconnection / worker-messaging 可按缺口独立追加
```

- `network-mock-recorder.js` 增强 XMLHttpRequest 和 fetch，必须最后。
- `worker-messaging.js` 会覆盖 `bom/window-global-apis.js` 的基础 Worker/BroadcastChannel stub，建议放在 `window-global-apis.js` 之后。
- `web-audio-fingerprint.js`、`webrtc-peerconnection.js` 无强依赖；若使用 profile，`profile-seed-manager.js` 由诊断器自动提前加载。

## 最小加载集

根据目标脚本需求，只加载实际需要的模块。常见最小集：

### 简单指纹脚本

```text
bom/window-global-apis.js, bom/navigator-fingerprint.js, bom/location-url-state.js, bom/screen-fingerprint.js
```

### JSVMP 类签名

```text
bom/window-global-apis.js, bom/navigator-fingerprint.js, bom/location-url-state.js, bom/screen-fingerprint.js,
bom/web-storage.js, bom/web-crypto.js, bom/performance-timing.js,
dom/event-constructors.js, dom/document-dom-runtime.js, dom/html-element-constructors.js,
webapi/xml-http-request.js, webapi/url-search-params.js, encoding/text-codec.js
```

### 指纹探测较重脚本

```text
--profile default
bom/window-global-apis.js, bom/navigator-fingerprint.js, bom/location-url-state.js, bom/screen-fingerprint.js,
bom/web-crypto.js, bom/performance-timing.js,
webapi/web-audio-fingerprint.js, webapi/webrtc-peerconnection.js, webapi/worker-messaging.js
```

### 完整浏览器环境

加载所有模块（少见，一般不需要）。

## 通用约束

1. 只加载目标实际读取的模块；模块存在不等于输出正确。
2. 环境模块必须在目标初始化之前加载，且加载顺序属于可验证的运行时契约。
3. 需要 XHR/fetch 语义时走完整标准调用边界，不通过私有快捷字段绕过 wrapper。
4. 指纹与状态字段必须来自一个同源、同会话 baseline，不得混用多个采样来源。
5. `web-crypto.js` 提供真实 WebCrypto，但随机值本身不适合作为固定向量；验证应比较标准算法向量或捕获的确定性中间值。

## 按 undefinedPaths 前缀选择模块的算法

```text
1. 收集所有 undefinedPaths
2. 提取前缀集合（第一个 . 之前的部分）
3. 前缀 → 模块映射（见 env-modules.md）
4. 按标准顺序手动排列要加载的模块
5. 手动补充依赖（如 html-element-constructors.js 需要 document-dom-runtime.js，document-dom-runtime.js 前建议加载 event-constructors.js）
6. 如需真实指纹 seed，先生成 profile，再加 `--profile-file js_reverse_cache/env/profile.json`
7. 重新执行诊断
```

注意：`vm-browser-gap-diagnose.js` 会按 `--env` 参数给出的顺序逐个加载模块，不会自动排序或补依赖。把这段算法当作人工选择 `--env` 列表的规则。
内置前缀始终从 Provider 的 `env/` 解析，不读取当前目录下的同名文件。项目相对模块只接受 `js_reverse_cache/env/...`；其他已审查模块必须传入绝对路径。
