# Geetest GT4 文字点选实现案例

## 身份与边界

本案例适用于 Geetest GT4 文字点选，不适用于滑块、九宫格、图标点选、字序点选或 GT3。选择必须同时看到：

1. 请求 `risk_type=word`。
2. `/load` 响应 `captcha_type=word`。
3. 响应包含 `imgs` 候选主图和有序 `ques[]` 目标提示图。

共享 Geetest host、`/load`、`/verify`、`w` 或页面上的“点选”文案不足以选择本案例。

## 已验证协议形状

同一轮 `/load` 使用动态 callback、captcha id、客户端 `challenge` UUID、`client_type=web`、`risk_type=word` 和语言。响应需要冻结 `lot_number`、`payload`、`process_token`、`payload_protocol`、`pt`、`pow_detail`、`imgs`、`ques[]`、raw GCT 和当前 bundle；只看到响应 `captcha_type=word` 而没有请求侧 `risk_type=word` 时不得选择本案例。

文字点选 `/verify` 的公共外层字段为：

```text
callback, captcha_id, client_type, lot_number, risk_type=word,
payload, process_token, payload_protocol, pt, w
```

默认不附加滑块 `td/td_sign`，也不使用九宫格 `[row, col]`。

## 答案与坐标

`ques[]` 顺序就是点击顺序。透明 RGBA 提示图必须先合成白底再 OCR；候选主图需要文字检测、旋转 OCR 和特征/字形回退。低置信、重复匹配或漏框时停止并换 fresh lot，不能在同一 lot 上枚举坐标。

输入点使用 `imgs` 原始像素坐标，提交前转换为 GT4 的 `0..10000` wire 坐标：

```python
wire_x = round(pixel_x / image_width * 10000)
wire_y = round(pixel_y / image_height * 10000)
userresponse = [[wire_x, wire_y], ...]
```

不要使用 CSS 显示尺寸、滑块 `gap_x - 44` 或九宫格行列公式。

## iv8 与 Python 边界

当前实现由 Python 获取 `/load`、图片、GCT 并提交 `/verify`；iv8 只在本地 `JSContext` 中加载 hash-bound bundle 生成窄 `w`。iv8 不得访问网络、文件系统、浏览器 Cookie 或页面 UI。work-order 必须绑定 bundle/adapter SHA-256、approval deadline 和 capability-denied adapter，并检查 registry/export 特征。

模块编号属于当前 bundle 证据，不是长期 API。bundle 更新后必须重新定位 callable export、更新 hash binding，并重新执行离线测试和 fresh live proof。

## 验证记录

当前公开 Demo 的独立 fresh rounds 已通过：

- 一轮使用当前轮人工确认坐标，经 iv8 生成 `w` 后语义成功。
- 一轮由自动 OCR、候选框和回退逻辑生成坐标，经 iv8 生成 `w` 后语义成功。
- 其他默认入口回归也达到 `status=success`、`data.result=success`、`fail_count=0`。

这些 live 记录只保留在脱敏 proof summary 中；不保存 Cookie、token、lot、图片、`w`、完整 URL 或完整响应。

## 复用限制

本案例是窄 implementation artifact，不是最终 collector。当前目标仍需由 verifier owner 重新确认 subtype 和语义 acceptance，再由 Python collector 绑定当前 session、scope、预算和动态资源。只要 `captcha_type`、图片布局、答案数量、坐标 wire shape、bundle export 或 GCT 规则变化，就停止复用并回到 fresh evidence。
