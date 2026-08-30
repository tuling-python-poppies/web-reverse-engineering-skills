# Geetest GT4 文字点选流程

本文件只处理 GT4 文字点选（`risk_type=word`）。它与滑块、九宫格、图标点选和字序点选是不同的 subtype；公共的 lot、PoW、GCT、bundle 和 `w` 外壳规则可以复用，但感知结果和 `userresponse` wire shape 不能混用。

## 选择条件

必须同时具备以下独立信号：

1. `/load` 请求使用 `risk_type=word`。
2. `/load` 响应使用 `captcha_type=word`。
3. 响应包含候选主图 `imgs` 和目标提示图数组 `ques`。

仅有 Geetest host、`/load`、`/verify`、`w`、泛称“点选”、九个视觉区域或用户猜测不足以选择本流程。出现 `risk_type=nine`、`captcha_type=nine`、`nine_nums` 时选择九宫格流程；出现 `risk_type=slide`、`bg`、`slice` 时选择滑块流程。

## 同轮证据

冻结一轮完整状态：

- `/load` JSONP、callback、captcha id、客户端 `challenge`（当前 Web Demo 会发送 UUID）、`lot_number`、`payload`、`process_token`、`payload_protocol`、`pt` 和 `pow_detail`。
- 同轮 `imgs` 候选主图、全部 `ques` 目标图、raw GCT 和当前 raw `gcaptcha4.js` bundle。
- 主图原始宽高、候选框、目标文字、OCR 结果、匹配方法、像素坐标和转换后的 wire 坐标。
- 最终 `/verify` 查询键集合和完整语义响应。

禁止混用不同 lot 的 token、图片、提示图、callback、GCT、bundle、Cookie、答案或 `process_token`。答案识别失败后创建 fresh lot；不得在同一 lot 上枚举坐标或排列。

## 请求链

当前公开 GT4 Web Demo 的 word `/load` 最小形态为：

```text
callback=<dynamic>
captcha_id=<configured>
challenge=<client-generated UUID>
client_type=web
risk_type=word
lang=zh
```

如果当前真实请求证明还需要其他字段，按当前证据更新，不从 slide、nine 或历史版本推断。word `/verify` 的当前公共外层字段为：

```text
callback, captcha_id, client_type, lot_number, risk_type,
payload, process_token, payload_protocol, pt, w
```

文字点选默认不附加滑块专用的 `td` 或 `td_sign`。只有当前 bundle 和真实 wire 样本明确证明需要时，才加入额外字段。

## 感知流程

### 目标提示图

`ques[]` 常见为透明 RGBA 文字图，字形可能只存在于 alpha 通道。送 OCR 前必须把 alpha 图合成白底 RGB 图，再做灰度、自适应对比度和放大。直接把 RGB 全黑的透明图送给 OCR 会得到空结果或错误字符。

### 候选主图

`imgs` 是带纹理和复杂背景的候选文字图，不是九宫格切片。候选定位和文字识别必须分开：

1. 使用 `ddddocr` detection API 或等价文字检测器取得候选框。
2. 对候选框扩大少量边界后，使用 ddddocr beta/classic OCR 和多角度旋转识别。
3. 对 OCR 不确定的候选，使用当前提示图与候选图的 SIFT/局部特征比较或字体字形左部结构比较。
4. 只有候选唯一、点位在图片边界内且顺序与 `ques[]` 一致时，才形成答案。
5. 低置信、重复匹配或检测框不足时 fail closed；在预算内换 fresh lot，不提交猜测答案。

OCR 是感知证据，不是服务器验收。`--answers-file` 之类的人工/外部确认坐标只能绑定当前 lot，不能跨轮复用。

## userresponse Wire Shape

文字点选提交的是主图中的点击坐标，坐标不是原始像素、不是九宫格行列，也不是 `0..100` 百分比。当前 GT4 word adapter 使用主图宽高归一化到 `0..10000`：

```python
wire_x = round(pixel_x / image_width * 10000)
wire_y = round(pixel_y / image_height * 10000)
userresponse = [[wire_x, wire_y], ...]
```

点击顺序必须与 `ques[]` 目标顺序一致。图片尺寸、CSS 缩放和 device pixel ratio 发生变化时，以当前主图原始像素尺寸和当前正样本确认转换，不把一个 Demo 尺寸当作通用常量。

## w 组装和 iv8 边界

word `wPayload` 至少需要根据当前 bundle 重新确认：

```text
passtime, userresponse, device_id, lot_number,
pow_msg, pow_sign, geetest, lang, ep, biht,
gee_guard, bundle fixed fields, lot-derived fields, em
```

公共 GT4 shell 规则：

- PoW 明文使用当前同轮 `pow_detail`、captcha id 和 lot number。
- raw GCT 计算 `biht`，保持原始函数文本、JS int32 和 UTF-16 code unit 语义。
- `_lib` 固定字段和 `lib._abo` lot rule 从当前完整 bundle 提取。
- `pt=1` 的 AES IV 和 RSA 封装按当前 bundle/正样本确认。

当 bundle 需要浏览器式 JavaScript host 时，使用 `iv8` 作为窄工件生成器：

1. 先做 iv8 API gate 和离线成员探针。
2. work-order 绑定精确 bundle SHA-256、adapter SHA-256、未过期 approval deadline 和 capability-denied adapter。
3. 通过 registry 存在性和目标 export callable 检查确认导出特征。
4. 模块编号只是当前 bundle 证据，不能把任意 `require(31)` 或 `require(32)` 当作长期 API。
5. iv8 只返回 `w`，不提供 HTTP、WebSocket、文件系统或 Cookie 持久化桥。
6. Python 负责 `/load`、静态资源、预算账本、`/verify` 和语义结果。

## Live 交付

最终 collector 必须由 Python 发出所有 live HTTP。默认入口可以使用已批准的默认 work-order 直接运行；自定义 work-order 需要显式确认。实现应具备：

- 默认 bundle、work-order 和 cache 路径，不要求用户手工填写参数。
- `/load`、每张图片、GCT 和 `/verify` 的 scope 检查。
- response byte cap、不可变 request budget、最小请求间隔和并发限制。
- lot cache create-only，动态证据只进入 `<projectRoot>/js_reverse_cache/**`。
- 每次 OCR 歧义或 verifier semantic failure 在预算内最多有限次换 fresh lot；不能重置账本。
- 等待当前实现和真实样本证明的最小 verifier 延迟，当前公开实现至少等待约 1.5 秒。

`/verify` 返回裸 JSON 错误时仍要解析并记录错误 code；解析器不能只接受 JSONP。只有以下条件同时成立才算成功：

```text
status == "success"
data.result == "success"
data.fail_count == 0
```

## 失败分流

| 现象 | 首要检查 | 处理 |
| --- | --- | --- |
| `/load` 返回 slide/nine/icon | subtype 或请求参数错误 | 回到 verifier family router，不能混用答案规则 |
| 目标透明图 OCR 为空 | alpha 未合成到白底 | 先修预处理，不提交答案 |
| 候选框缺失或 OCR 多匹配 | 感知不确定 | 使用旋转 OCR/SIFT/字形回退；仍不唯一则 fresh lot |
| `-50004 jsonp xss` | callback 格式不符合当前服务端约束 | 使用当前正样本的动态毫秒 callback |
| `status=success, result=fail, fail_count=1` | `w` 已解密，答案或坐标 wire 语义错误 | 检查目标顺序、候选中心、`0..10000` 变换和同轮状态 |
| `-50002 param decrypt error` | bundle/export/AES/RSA 外壳不一致 | 检查 bundle hash、export callable、`pt` 和加密封装，不先改 OCR |
| `-50306 process_token Error` | lot 已消费、过期或混轮 | 创建 fresh lot，不能复用旧 token |
| `result=forbidden, fail_count=0` | bundle/GCT/版本字段不一致 | 刷新当前 bundle、GCT 和 work-order hash |

同一失败 lot 不扫描大量坐标。先保存脱敏 evidence，再创建 fresh lot；预算用尽时停止 live，不能自动恢复或扩大预算。

## 验收

1. `/load` 明确确认 `risk_type=word` 和 `captcha_type=word`，且 `imgs/ques`、tokens、GCT、bundle 同轮。
2. 离线测试覆盖透明提示图预处理、候选点边界、目标顺序、`0..10000` 坐标变换、PoW/GCT 和 `w` 形状。
3. iv8 export 经过 hash 绑定和 callable 检查，且没有 JS 网络/文件桥。
4. 至少一轮 fresh challenge 由自动识别路径完成语义成功；正式交付前最好再用独立 fresh lot 重复一次。
5. 每轮确认 `status=success`、`data.result=success`、`fail_count=0`。
6. 最终 live egress 由 Python 完成，浏览器只用于证据，不作为 collector 运行时依赖。
