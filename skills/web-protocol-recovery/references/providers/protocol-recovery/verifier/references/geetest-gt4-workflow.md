# Geetest GT4 Active Workflow

用于 Geetest GT4 滑块协议恢复：`/load -> image pair -> proof fields -> w/td -> /verify`。
本文件描述当前协议边界和可验证的适配器，不把单一站点布局参数提升为通用 GT4 规则。

## Select When

选择本流程需要同时看到以下证据：

- `/load` 返回 `lot_number`、`pow_detail`、`payload`、`process_token`、`payload_protocol`、`pt`、`bg`、`slice`。
- `captcha_type=slide` 或请求 `risk_type=slide`。
- `/verify` 使用同轮 `lot_number`、`payload`、`process_token` 和动态 `w`。
- 当前 bundle 能定位到滑块提交和加密导出。

只有通用图片识别、缺口检测或浏览器 UI 自动化时，不选择本流程。

## Evidence Contract

冻结一轮完整状态：

1. `/load` JSONP、同轮图片、`gct_path`、`static_path`、bundle 版本和 cookie 状态。
2. 图片原始宽高、OCR 两种模式的结果、候选置信度和坐标适配方式。
3. `wPayload` 的字段名、值类型、插入顺序和最终删除/追加动作。
4. `/verify` 的完整查询键集合和语义响应。

不同 `lot_number`、图片、GCT、bundle、轨迹、cookie 或 `process_token` 不得拼接。

## Request Chain

首轮 `/load` 只发送当前目标授权的最小查询参数。当前 GT4 Web Demo 的已验证形态为：

```text
callback=<dynamic>
captcha_id=<configured>
client_type=web
risk_type=slide
pt=1
lang=zh
```

如果当前 `/load` 响应或真实请求证明需要 `challenge` 或其他字段，按当前轮证据加入；不得从其他产品或版本推断。

`/verify` 使用同一轮的：

```text
callback, captcha_id, client_type, lot_number, risk_type,
payload, process_token, payload_protocol, pt, w, td
```

最终成功必须同时满足：

```text
status == "success"
data.result == "success"
data.fail_count == 0
```

HTTP 200、非空 `w`、外层 `status=success` 或固定 `w` 长度都不是成功。

## Image Adapter

`ddddocr` 的输出必须先归一化为“背景原始坐标中的缺口中心”：

1. 优先执行 `simple_target=False`，兼容 `target=[center_x, center_y]` 和 `target=[x1,y1,x2,y2]`。
2. 若结果异常、无有效框或置信度偏低，再执行 `simple_target=True`。
3. 两个结果接近时取均值；差异较大时使用有效的 simple 候选，并把候选来源记录到本轮 metadata。
4. 低置信度是候选状态，不是自动拒绝条件；最终授权来自新 challenge 的语义成功。

当前 80px 拼块 Web Demo 的坐标适配为：

```python
set_left = round(gap_x - 44)
userresponse = set_left + 1 + random.random()
```

`44` 是当前布局中缺口中心到滑块左边缘的偏移。它是目标/布局 adapter，必须用当前图片尺寸和至少一轮正向语义结果确认；不得作为所有 GT4 目标的通用公式。

当前 Demo 不应默认使用以下推导替代上述 adapter：

```python
set_left = round((gap_x - 2) * scale)
userresponse = set_left / scale + 2
```

该公式只在当前 bundle 明确证明其实际 client/natural 尺寸和提交分支时才可使用。

## Behavior Sidecar

当前滑块提交将行为轨迹放在 `/verify` 查询参数 `td`，而不是最终 `wPayload` 的 `new_track` 字段：

```text
td == new_track
td = gzip(track_json) -> URL-safe Base64 without padding
```

当前 Web Demo 的轨迹 JSON 形态为：

```json
{
  "m": 1,
  "w": 300.03125,
  "h": 261.53125,
  "s": 0,
  "e": 0,
  "p": [[time, x_normalized, y_normalized, type]]
}
```

已验证的当前 adapter 使用约 54 个点、独立的 `track_duration`、起点/移动/抖动/结束类型、停顿和小幅回撤。压缩边界为 raw deflate level 9，gzip header 使用当前 Unix 秒时间、OS=3，尾部包含 CRC32 和 ISIZE，再做 Base64URL 无 padding 编码。

`passtime` 和 `track_duration` 是两个独立字段。轨迹时间必须在发送 `/verify` 前真实等待，且 `td` 与 `td_sign` 必须由同一轮重新生成。

## Proof Fields

### PoW

当前 sha256 PoW 明文为：

```text
version|bits|hashfunc|datetime|captcha_id|lot_number||nonce
```

`pow_detail`、`lot_number`、`captcha_id` 必须来自同一轮。最后一个模块参数按当前 bundle 证据确定为空字符串，不得传入长 `payload`。

### GCT

按本轮 `gct_path` 读取原始源码。不要 beautify、格式化或改写后再计算 `biht`。从 `=5381;` 定位哈希函数和紧随其后的 guard 函数，保持 JavaScript int32、UTF-16 code unit 和原始函数文本语义。`biht` 的字符串类型必须保留。

### Bundle Metadata

从当前 bundle 运行时或纯文本解析得到：

- `window._lib` 的固定字段。
- `window.lib._abo` 的 lot-number 派生规则。
- 当前加密导出、`gee_guard`、`em` 和轨迹打包器。

`n[a:b]` 是零基包含末端切片；`+` 表示拼接；`.` 表示嵌套对象路径。固定字段、lot rule、`gee_guard` 和 `em` 必须按当前 bundle 或当前正样本刷新，不得跨版本硬编码。

### td_sign

当前 bundle 的滑块签名规则为：

```python
td_sign = HMAC-SHA256(
    key=lot_number.encode("utf-8"),
    message=td.encode("utf-8"),
).hexdigest()
```

`td_sign` 进入加密前的 `wPayload`；`td` 进入最终 `/verify` 查询。最终 `wPayload` 不保留已经删除的 `new_track` 字段。

## iv8 Artifact Boundary

当当前 bundle 需要浏览器式运行时，使用 `route: iv8`：

1. API gate 记录实际 iv8 版本、`JSContext` 成员和离线成员探针。
2. work-order 必须绑定当前 bundle SHA-256、adapter SHA-256、有效 approval、执行期限和能力隔离说明。
3. iv8 只读取同轮 bundle，生成 `w` 或其他明确窄工件。
4. iv8 不提供 HTTP、WebSocket、文件系统或 cookie 持久化桥。
5. Python 负责 `/load`、图片/GCT 资源、账本、`/verify` 和最终响应判断。
6. bundle 模块 ID 只是当前证据；使用导出特征和 hash 绑定，不能把单个模块 ID 当作长期 API。

如果没有可验证的能力隔离 adapter，停止在静态证据或纯 Python 路径；不要用 `node:vm`、自报 sandbox 标签或任意命令替代隔离证明。

## w Assembly

当前滑块 `wPayload` 至少需要验证以下字段：

```text
setLeft, passtime, userresponse, device_id, lot_number,
pow_msg, pow_sign, geetest, lang, ep, biht,
gee_guard, _lib fields, lot-rule fields, em, td_sign
```

`td` 不重复放入 `wPayload`，除非当前 bundle 明确证明该版本需要重复字段。最终加密必须发生在所有动态字段完成之后。

## Acceptance

按以下顺序验收：

1. 离线验证 PoW、GCT、lot rule、`td` 解码、`td_sign` HMAC 和 w 工件形状。
2. 在新 `lot_number` 上执行至少三轮同一 collector 路径。
3. 每轮确认 `status=success`、`data.result=success`、`fail_count=0`。
4. 确认最终请求由 Python 发出，iv8 只返回窄工件。
5. 记录 OCR 候选、坐标 adapter、bundle hash、iv8 版本、请求预算和清理状态。

## Failure Triage

| 现象 | 首要检查 |
| --- | --- |
| `/load` 失败 | scope、captcha_id、参数语言和当前轮响应类型 |
| `result=fail, fail_count=1` | 缺口中心、44px adapter、`userresponse`、轨迹形态、`td_sign`、同轮 token |
| `result=forbidden, fail_count=0` | bundle hash、`_lib`、lot rule、加密导出和版本元数据 |
| w 长度变化 | 只作为线索，检查 JSON 内容和最终服务端结果，不把长度当判据 |
| iv8 加载异常 | API 成员、bundle hash、DOM/环境最小适配和能力隔离；不把页面 UI 自动化当最终交付 |

同一失败 lot 不扫描大量坐标。先保存脱敏证据，再创建新 challenge；请求预算和同轮一致性不可重置。
