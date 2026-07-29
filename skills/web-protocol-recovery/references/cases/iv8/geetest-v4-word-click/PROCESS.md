# Geetest v4 文字点选逆向过程

本文仅作为历史过程证据。本案例不包含活跃实现；
`case.json.historicalReferences` 声明的归档代码仅供研究，针对当前目标重新构建并验证前不得用于交付。

## 案例身份

验证码不能只按厂商名选择案例。本案例四字段固定为：

| 字段 | 值 |
| --- | --- |
| Provider | Geetest |
| Product version | v4 |
| CAPTCHA type | 文字点选 |
| Protocol value | `word` |
| Bootstrap page | `https://gt4.geetest.com/` |
| Load endpoint | `https://gcaptcha4.geetest.com/load` |
| Verify endpoint | `https://gcaptcha4.geetest.com/verify` |

它不是 Geetest v4 滑块、图标点选、九宫格、无感或一次验证的精确案例，也不适用于 Geetest v3。普通“点选”描述只有在 `/load` 请求的 `risk_type=word` 且响应 `captcha_type=word` 时，才能归到本案例的“文字点选”。

## 目标与实测结果

运行时完全脱离浏览器：Python 负责 HTTP、提示字和背景图片识别；iv8 只执行当前官方 Geetest JavaScript，生成 verifier 所需的加密 `w`。所有网络请求属于同一个 `curl_cffi.requests.Session(impersonate="chrome")`。

最终公开 demo proof 使用提示字“龙、井、茶”，三个目标均由 `ocr-exact` 唯一匹配。结果为：

```text
status=success
data.result=success
data.fail_count=0
data.score=2
requests_used=10
```

HTTP 200 或顶层 `status=success` 单独都不算成功。必须同时检查 `data.result=success`，本案例还记录 `fail_count` 和 `score`。

用户确认打印完整 API 信息后，另一轮公开 demo proof 使用提示字“鲜、豆、苗”，同样三个 `ocr-exact`，共 10 个请求，返回 `result=success`、`fail_count=0`、`score=1`。成功响应在控制台保留为 `verify_response`，实测结构为：

```json
{
  "status": "success",
  "data": {
    "lot_number": "<dynamic>",
    "result": "success",
    "fail_count": 0,
    "seccode": {
      "captcha_id": "<captcha-id>",
      "lot_number": "<dynamic>",
      "pass_token": "<dynamic>",
      "gen_time": "<dynamic>",
      "captcha_output": "<dynamic>"
    },
    "score": "1",
    "payload": "<dynamic>",
    "process_token": "<dynamic>",
    "payload_protocol": 1
  }
}
```

文档只记录字段形状和占位符；案例运行时按用户确认打印真实响应，但不会把这些动态值保存为 frozen 素材或缓存文件。

## 快速匹配指纹

满足以下条件时可直接从本案例起步：

- Geetest v4 页面或兼容的 v4 endpoint。
- `/load` 请求参数包含 `risk_type=word`。
- `/load` 响应 `data.captcha_type` 等于 `word`。
- 响应包含 `lot_number`、`payload`、`process_token` 和 `payload_protocol`。
- 背景字段是 `imgs`，有序提示图片字段是 `ques`。
- 响应同时给出 `static_path`、`js` 和 `gct_path`。
- 官方 runtime 仍是 `gt4.js`、`gcaptcha4.js`、GCT 和语言脚本的组合。
- 当前 `gcaptcha4.js` 仍能定位 `$_BBFs:function` verifier 锚点。

若网络形状相同但 webpack module ID 变化，只重定位 `$_BBFs` 和 `$_BEP`；不要重新做整站入口发现。若 `captcha_type` 不是 `word`，停止精确复用。

## Intake 与边界

本次验证使用：

- Artifact：公开 demo URL、浏览器网络证据、当前官方脚本和公开验证码图片。
- Target type：`Geetest / v4 / 文字点选(word)`。
- Baseline：同一次浏览器证据采样得到的 Windows Chrome 风格环境，`navigator.webdriver=false`。
- Verification：固定样本 OCR/坐标回归、iv8 非空 `w`、受限真实 verifier proof。
- Nearest case：`captcha/geetest-v4-slider.py`，仅复用 v4 官方 runtime、`$_BBFs` 和 same-session replay；不复用滑块位移公式。

浏览器证据、HTTP session 和 iv8 环境不能混拼不同运行的 UA、Cookie、screen、storage 或 TLS 线索。若任务由其它 owner 移交，消费其批准的同源 artifact；不要跨 MCP 调用已经 stale 的 source ID。

## 网络链路发现

### 1. `/load` 请求

公开 demo 的关键请求形状是：

```text
GET https://gcaptcha4.geetest.com/load
callback=geetest_<timestamp>
captcha_id=<public demo id>
challenge=<fresh uuid>
client_type=web
risk_type=word
lang=zh
```

响应是 JSONP。先解析最外层，再检查 `data.captcha_type`，不要根据页面文案猜类型。

### 2. 图片字段

文字点选和滑块的图片区分很明确：

| 类型 | 背景 | 提示/目标 |
| --- | --- | --- |
| 文字点选 `word` | `data.imgs` | `data.ques[]`，顺序就是点击顺序 |
| 滑块 `slide` | `data.bg` | `data.slice` |

`ques` 是透明底单字小图，不能把它当文本 URL 参数。下载后先保留 RGBA alpha，再进行提示字 OCR。

### 3. 官方脚本

同一挑战代次下载：

- `https://static.geetest.com/v4/gt4.js`
- `static_server + static_path + js`
- `static_server + gct_path`
- `static_server + static_path + /i18n/zho.js`

不要用历史 `gcaptcha4.js` 配当前 GCT，也不要把另一个挑战的 `lot_number`、`payload` 或 `process_token` 拼到新挑战。

### 4. `/verify` 请求

浏览器成功请求确认 verifier URL 包含：

- `captcha_id`
- `client_type`
- `lot_number`
- `risk_type=word`
- `payload`
- `process_token`
- `payload_protocol`
- `pt`
- `w`

这些字段由官方 runtime 结合 fresh `/load` 数据生成。Python 不手写 `w`，只捕获官方 runtime 产生的完整 verify URL。

## `answer` 明文定位

在分析环境中，于 `$_BBFs` 入口前观察第一个参数。文字点选的最小业务答案为：

```json
{
  "passtime": 1250,
  "userresponse": [[3383, 3825], [5100, 2950], [4233, 7450]]
}
```

其中：

- `passtime` 是从 challenge 加载到提交的毫秒级时间字段。
- `userresponse` 是与 `ques[]` 相同顺序的点坐标数组。
- 每个点不是原图像素，而是映射到 `0..10000` 的二维坐标。
- 本 flow 没有滑块的 `setLeft`，也不使用 `target_x - target_width / 2`。

固定样本“浆、水、汤”用于验证该结构，期望坐标为：

```text
[[3383,3825],[5100,2950],[4233,7450]]
```

固定输入只证明坐标和 iv8 verifier 重建正确，不代表新的 live challenge 一定识别正确。

## 坐标公式

`ddddocr` 背景检测返回 `[x1, y1, x2, y2]`。点击点取候选框中心，然后分别按背景原图宽高归一化：

```python
point_x = round((x1 + x2) / 2 / image.width * 10000)
point_y = round((y1 + y2) / 2 / image.height * 10000)
```

注意：

- 必须使用下载背景的原始尺寸，不是网页 CSS 显示尺寸。
- 顺序必须跟 `ques[]` 一致，不能按候选框在背景上的位置排序。
- 一个候选只能使用一次。
- 不要沿用 Geetest v4 滑块的显示比例、slice 半宽或 `setLeft`。

## 图像识别链

文字点选不是一次 OCR 调用，必须分别记录提示、候选和匹配决策。

### 1. 提示字 OCR

对每个 RGBA 提示图：

1. 合成到白底。
2. 转灰度并 autocontrast。
3. 缩放到 128x128。
4. 用 `ddddocr` beta OCR 识别。
5. 只取第一个 CJK 字符；没有汉字就停止，不猜答案。

### 2. 背景候选框

使用 `ddddocr.DdddOcr(ocr=False, det=True)` 检测所有字框。候选数少于提示数时立即停止。每个框四边扩 4 像素，保留旋转文字边缘。

### 3. 候选 OCR

背景字有颜色、旋转和纹理干扰。每个 crop 同时走两组输入：

- 原 RGB crop。
- 高色差 mask：像素 `max(channel)-min(channel)>80` 视作前景。

每组输入以 `-40..40` 度、步长 10 度旋转，缩放到 96x96，并同时跑 beta/classic OCR。收集所有识别到的 CJK 字符形成候选 label set。

如果某提示字只在一个未使用候选的 label set 中出现，记为 `ocr-exact`。唯一 exact 的优先级高于任何特征匹配。

### 4. SIFT 回退

未 exact 的提示字使用 alpha 轮廓与候选灰度图做 SIFT：

- 提示 alpha 取反并缩放到 128x128。
- 候选 crop 转灰度并缩放到 128x128。
- BFMatcher `knnMatch(k=2)`。
- Lowe ratio 使用 `0.8`。
- 分数是通过 ratio test 的匹配点数。

只有分数明显可用时才选择最高分，并记录为 `sift-N`。

### 5. 低分偏旁回退与拒绝

当所有剩余 SIFT 分数都不超过 1 时，直接取最高分容易把相似字体噪声当证据。本案例改为：

1. 使用候选 OCR label set 中的字符。
2. 用微软雅黑生成标准字形。
3. 只比较提示字和标准字形左侧约 45% 区域。
4. 再用 SIFT 计算偏旁相似分数。
5. 只有唯一最高且分数大于 0 才选择，记录为 `radical-N`。
6. 零分或并列最高时抛出 `low-confidence point selection`，不调用 `/verify`。

`FONT_PATH` 默认是 Windows 的 `C:\Windows\Fonts\msyh.ttc`，可用环境变量 `GEETEST_CJK_FONT` 覆盖。非 Windows 环境要指向可用的中文字体，否则低分样本会按设计停止。

## 误判诊断与修正

### 第一轮：彩色旋转字漏识别

提示为“踵、鱼、翅”时，原 crop OCR 没有稳定识别“踵”，SIFT fallback 选错候选，verifier 返回 semantic fail。把高色差 mask 加入旋转 OCR 后，离线恢复到正确点：

```text
[[3650,2675],[6350,4150],[2617,7225]]
```

这证明失败点是视觉候选标签，不是 `w`、坐标公式或 session。

### 第二轮：一分 SIFT 假阳性

提示为“珍、珠、汤”时，“珍”和“珠”精确命中，“汤”只得到 `sift-1`，却落到错误候选。正确第三点是中部候选，坐标为：

```text
[[7517,2275],[3333,5300],[5550,5800]]
```

加入低分偏旁比较后，第三字由 `radical-3` 唯一选中。该修正同时保留历史样本：

```text
浆、水、汤 -> [[3383,3825],[5100,2950],[4233,7450]]
铜、锣、烧 -> [[3017,2750],[6550,2175],[1700,6975]]
鲜、橙、多 -> [[8017,1875],[3217,1800],[1200,2150]]
```

不要用 verifier failure 进行自动重试或在线试错。每次失败先回到保存的公开图片做离线诊断，修正后跑完整回归，再决定是否执行新的受限 proof。

## iv8 verifier 重建

官方 loader 依赖动态 `<script>` 和 `<link>`。最小 iv8 环境执行以下步骤：

1. 创建 `head`、`body` 和 `#captcha`。
2. 缺失时用 `__iv8__.wrapNative` 补 `document.createElementNS`。
3. 包装 `document.head.appendChild`。
4. 遇到 `/load?` 时，把 Python 已获得的 fresh `loadData` 交给对应 JSONP callback。
5. 遇到 `gcaptcha4.js`、GCT、语言脚本时，eval 同一 challenge 代次的源码。
6. CSS 只回调 `onload`，不做真实下载；CSS 不参与 verifier。
7. `initGeetest4` 使用 `riskType: 'word'`、`product: 'float'`、`language: 'zho'`。
8. drain/sleep 让初始化完成。
9. 通过 registry 获取当前 backend 并调用 `$_BBFs(answer, callback, true)`。
10. append verify JSONP script 时先保存 URL，再调用本地 fake failure callback 关闭 SDK pending 状态。
11. iv8 不发真实 verify 请求；Python 用同一 session 请求捕获的 URL。

`gcaptcha4.js` 只做两处分析/运行 patch：

```text
loadCss:function(){...} -> loadCss:function(){return Promise.resolve()}
}return i[              -> }window.__gtRequire=i;return i[
```

当前已验证 bundle 的 backend 路径是：

```javascript
var backend = window.__gtRequire(17).default.$_BEP(window.captchaObj.$_BAGF);
backend.$_BBFs(answer, callback, true);
```

`17` 是版本证据，不是永久 API。若失效：

1. 搜索 webpack module source 中的 `$_BBFs:function`。
2. 检查对应 export/prototype。
3. 搜索暴露 `$_BEP` 的 registry。
4. 用 `window.captchaObj.$_BAGF` 解析 backend。
5. 确认返回对象具有 `$_BBFs` 后再继续。

## 环境字段

最小环境包含：

- `location` 指向 Geetest v4 demo origin。
- 与 HTTP header 一致的 `navigator.userAgent`。
- `platform`、`language(s)`、CPU、memory、touch 和 `webdriver=false`。
- `screen` 宽高、可用区域和色深。
- `window` 内外宽高与 `devicePixelRatio`。
- timezone `Asia/Shanghai`。

新目标有 browser baseline 时，从同一个 evidence owner 的同源 snapshot 更新这些字段。不要从不同浏览器运行挑值拼成“更像”的环境。

## 受限真实重放

1. 创建一个 Chrome impersonated session。
2. 设置 UA、语言和 referer。
3. fresh UUID 请求 `/load`，记录 `loaded_at`。
4. 检查 `captcha_type == 'word'`。
5. 同 session 下载背景、提示图和四类官方脚本。
6. 离线识别提示、候选和有序 points；低置信时停止。
7. 构造 `answer={passtime,userresponse}`。
8. iv8 生成带非空 `w` 的 verify URL。
9. 保证从 `/load` 到 `/verify` 至少 1.5 秒。
10. 同 session GET verify URL。
11. 同时验证 transport 与 semantic success。
12. 在原摘要中增加 `verify_response`，打印 `/verify` JSONP 解析后的完整对象；不把它写入缓存。

案例设置 `REQUEST_LIMIT=20`、并发 1、禁止重定向、响应上限 8 MiB，并限制 host 到 `gcaptcha4.geetest.com` 与 `static.geetest.com`。一次典型成功 proof 使用 10 个请求。不要添加自动 retry、批量或并发。

## 固定输入与验收

执行 live proof 前至少做三层检查：

1. `python -m py_compile` 通过。
2. 保存的公开样本产生预期点，且低分样本不回归。
3. iv8 初始化完成、没有 resource error、verify URL host/path 正确且 query 存在非空 `w`。

live 成功必须满足：

```text
HTTP 200
status=success
data.result=success
data.fail_count=0
```

停止于第一个成功 proof。按本案例的显式输出约定，完整 `/verify` 解析对象只在控制台的 `verify_response` 中打印；不要保存 `w`、lot number、payload、process token、完整 verify URL 或完整响应，且不要打印请求 URL 或 `w`。

## 失败矩阵

| 症状 | 可能原因 | 有界检查 |
| --- | --- | --- |
| `/load` 返回非 `word` | 类型或 demo 配置变化 | 停止并按真实 `captcha_type` 重新分类 |
| 提示 OCR 为空 | alpha/白底归一化失败 | 检查 RGBA 合成和 CJK 提取，不猜字 |
| 候选框少于提示数 | detector 漏框或图片格式变化 | 保存当前公开图片，离线检查 detection |
| 彩色旋转字 exact 缺失 | 原 crop OCR 受纹理/颜色影响 | 检查色差 mask 和旋转 OCR label set |
| 仅有 `sift-0/1` | 特征证据不足 | 走偏旁比较；零分或并列时停止 |
| 点位正确但顺序错 | 按背景位置排序了候选 | 必须按 `ques[]` 顺序组装 `userresponse` |
| 坐标整体偏移 | 使用 CSS 尺寸或滑块公式 | 按背景原图宽高归一到 10000 |
| `window.__gtRequire` 缺失 | webpack marker 改变 | 重新定位 loader return marker |
| module 17 没有 backend | module ID 更新 | 搜索 `$_BBFs:function` 和 `$_BEP` |
| verify URL 没有 `w` | 初始化、GCT、answer 或 resource chain 不完整 | 检查 init flag、resource error 和同代脚本 |
| HTTP 200 但 `result=fail` | 视觉误判、旧 challenge、环境或 timing | 先离线检查 points，再查 session freshness 和延时 |

## 复用决策

使用最短路径：

1. `Geetest + v4 + 文字点选 + word` 和字段锚点均匹配：直接适配本案例。
2. 网络结构匹配但 module ID 变化：只重定位 `$_BBFs`/`$_BEP`。
3. 图片风格变化但协议仍是 `word`：保留 iv8 和 HTTP 链，只替换并回归视觉 solver。
4. `captcha_type` 是 `click`、`icon`、`slide` 或其它值：不是精确匹配，选择独立案例。
5. 缺少可信入口或同源环境 artifact：返回明确缺失证据，不在 iv8 中猜。

## 历史实现与素材策略

历史来源实现曾在运行时下载当时的官方脚本和公开 challenge 图片到调用方工作目录 `js_reverse_cache/`。该实现不再作为活跃案例代码；其哈希绑定归档仅供研究，在针对当前目标重新恢复并验证前不得导入、执行或复制到交付代码。

skill 不冻结 Geetest bundle、现场图片或响应，原因是：

- 官方脚本 hash 和 module ID 会变。
- 图片只是一次性公开 challenge，不是运行依赖。
- lot、payload、process token、`w` 和 verify URL 都是瞬态值。
- 已验证代码和坐标回归证据足以表达可复用模式。

公开 demo CAPTCHA ID 和 endpoint 被保留；没有账号 Cookie、Authorization、个人 token 或完整响应作为 frozen 素材写入案例。运行时完整 verify 解析对象只按用户确认打印到控制台。
