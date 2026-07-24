# Geetest GT4 Workflow

用于极验 GT4 滑块 `/load -> 图片识别 -> pow -> w -> /verify` 的纯协议复现，以及客户端 bundle 更新后从连续 `forbidden` 中恢复。

## 识别信号

- `/load` 返回 `lot_number`、`pow_detail`、`payload`、`process_token`、`payload_protocol`、`pt`、`bg`、`slice`。
- `/verify` 使用同轮 `lot_number/payload/process_token` 和动态 `w`。
- `wPayload` 常见字段包含 `setLeft`、`passtime`、`userresponse`、`pow_msg`、`pow_sign`、`gee_guard`、`em` 和由 bundle 注入的动态字段。

## 标准流程

1. 请求 `/load`，保存完整 JSONP 响应、Cookie 和图片地址。
2. 下载 `slice/bg`，校验真实图片后用 `ddddocr.slide_match(..., simple_target=True)` 得到原图缺口 `gap_x`，不要直接把它当成 `setLeft`。
3. 按 `pow_detail` 生成 `pow_msg/pow_sign`；当前格式是 `version|bits|hashfunc|datetime|captcha_id|lot_number||nonce`，其中 `lot_number` 和 `pow_detail` 必须来自本轮 `/load`。
4. 把原图坐标映射为页面提交坐标，再计算 `userresponse`。当前 300px 背景图验证公式为 `scale = 0.8876 * min(bg_width, 340) / bg_width`、`setLeft = round((gap_x - 2) * scale)`、`userresponse = setLeft / scale + 2`。
5. 从本轮 `gct_path` 原始源码计算 `biht`，并生成 `gee_guard`、`em`；不要把格式化后的 GCT 当作原始输入。
6. 组装当前 bundle 要求的 `wPayload`。
7. 对 `pt=1`，常见 `w` 是 `AES-CBC-PKCS7(compact_json, random16, iv='0000000000000000') + RSA-PKCS1-v1_5(random16)` 的 hex 拼接。这里的 `random16` 是 16 字节 ASCII hex 字符串，例如 `secrets.token_hex(8)`。
8. 用同轮外层参数请求 `/verify`，仅当 `status == "success"` 且 `data.result == "success"` 时算通过。

## 有 Bundle 时的快速路径

用户同时给出当前 `gcaptcha4.js`/`1.js` 和请求样本时，优先走下面的浏览器无关路径。已经有源码时不要先启动浏览器、做全量 AST 解混淆或手写 AES/RSA：

1. 先尝试最小首轮 `/load`：只传动态 JSONP `callback`、`captcha_id`、`client_type=web`、`risk_type=slide`、`pt=1`、`lang=zho`。很多公开 GT4 配置不要求预先提供 `lot_number/payload/process_token`。
2. 如果样本中的 `/load` 请求已经带 `lot_number/payload/process_token`，先区分请求输入和响应输出。后续 `/verify` 应使用 `/load` 响应返回的新值；两阶段 token 不同通常是正常刷新，不是断轮。
3. 离线暴露 webpack require，只执行 PoW 和 `w` 模块；同时从源码运行时读取 `_lib`、`lib._abo`。不要执行入口 UI 模块。
4. 下载同轮图片并识别坐标，从原图坐标映射到 `setLeft/userresponse`。
5. 下载并原样执行本轮 GCT，读取其写入的 `biht`。当前 GCT 写入的是十进制字符串，不要强制转成整数。
6. 组装 `wPayload`，调用 bundle 的 `w` 模块，真实等待 `passtime` 后提交同轮 `/verify`。
7. 连续创建三轮新 challenge 验证，不能在同一个失败 lot 上扫描大量坐标。

可直接复用：

- `scripts/gt4_bundle_helper.js`：读取当前 bundle，动态提取元数据、PoW、GCT 和 `w`。
- `scripts/gt4_replay.py`：同轮 `/load -> 图片 -> helper -> sleep -> /verify` 模板。
- `scripts/gt4_pure_replay.py`：不执行 JavaScript 的纯 Python `/load -> OCR -> PoW/GCT/AES/RSA -> sleep -> /verify` 模板。

运行模板：

```bash
python scripts/gt4_replay.py \
  --captcha-id <captcha_id> \
  --bundle <当前 gcaptcha4.js> \
  --helper scripts/gt4_bundle_helper.js
```

## 纯 Python 极速路径

用户明确要求“纯 Python / 纯算”且已提供当前 bundle 时，按下面顺序执行，避免先做一轮 Node/vm 再返工：

1. 先在工作区搜索 `gt4_pure.py`、`gt4_protocol.py`、`RSA_N_HEX`、`PKCS1_v1_5`。已有实现只作为算法和公钥来源，必须用当前 bundle 与新 challenge 重新验证。
2. 直接复制或改造 `scripts/gt4_pure_replay.py`，依赖仅为 `requests`、`ddddocr`、`Pillow`、`pycryptodome`。运行路径不得导入 `subprocess`，不得调用 Node、iv8、ExecJS、jsdom 或浏览器。
3. 用完整 bundle 文本解出顶部 XOR 字符串表，再解析 `_lib/lib._abo` 初始化段。大字符串表可能占据源码前数十万字符，不要用 `source[:20000]` 查元数据；先定位明文 `n[...]` lot rule，再向前截取小窗口查 `_lib` 对象。
4. Python 的 `decodeURI` 兼容实现必须保留 URI reserved 字符的 `%XX` 形式；不能无条件使用 `urllib.parse.unquote()`，否则 XOR 输入长度可能变化，导致后半段字符串表错位。
5. PoW 明文固定核对为 `version|bits|hashfunc|datetime|captcha_id|lot_number||nonce`。当前 bundle 调 PoW 模块的最后一个参数是空字符串，不能误传 `/load` 返回的长 `payload`。
6. 下载同轮原始 GCT，以 `=5381;` 定位哈希函数：向前找最近的 `function ` 并按花括号提取完整函数，再取紧随其后的 guard 函数。按 JavaScript int32、UTF-16 code unit 和 `Function.prototype.toString()` 原文语义计算 `biht`；不要要求 `var e=5381` 紧跟函数左花括号。
7. 图片识别后必须应用当前坐标映射公式；不要把 `gap_x` 直接作为 `setLeft`。`ddddocr` 返回 `target_x=0` 时优先取有效的 `target[0]`。
8. 生成轨迹并按轨迹时间真实等待，但不要擅自把逐点轨迹加入 `wPayload`。当前滑块组件提交的是 `setLeft/passtime/userresponse`，轨迹用于时序证据和本地归档。
9. 用 Python 生成随机 16 字节 ASCII hex AES key，执行 AES-CBC-PKCS7；再用已验证 GT4 公钥做 RSA-PKCS1-v1_5，拼接两个 hex。RSA modulus 无法从当前字符串表稳定提取时，允许使用模板中的已验证公钥，但必须通过新 `/verify` 确认未轮换。
10. 首轮成功后再并行跑两轮新 lot。三轮均检查 `status == "success"`、`data.result == "success"`、`fail_count == 0`；不要以固定 `w` 长度作为正确性证据。

最短命令：

```bash
python scripts/gt4_pure_replay.py \
  --captcha-id <captcha_id> \
  --bundle <当前 gcaptcha4.js>
```

## Bundle 更新故障判定

出现以下组合时，优先判断为客户端 bundle 元数据轮换，而不是依赖、OCR 或网络问题：

- `/load` 成功，图片可识别。
- PoW 和 `w` 均能生成，`/verify` HTTP/JSONP 正常。
- 外层 `status` 是 `success`，但 `data.result` 连续为 `forbidden`，通常 `fail_count == 0`。
- 更换距离后仍稳定 `forbidden`。

如果用户已经提供最新 bundle，不必先启动浏览器。先离线对比旧、新 bundle 顶部预置字段和 webpack 模块结构。

## 动态字段来源

GT4 bundle 顶部会在进入主模块前写入两组元数据：

- `window._lib`：直接并入 `wPayload` 的固定字段，但字段名和值会随 bundle 轮换。
- `window.lib._abo`：根据 `lot_number` 生成附加字段的表达式映射。

已验证轮换样本（只能作版本证据，禁止写死）：

```text
更早 fixedFields: {"ZAhG":"MwHu"}
2026-07 中期 fixedFields: {"jCpk":"yZ7D"}
2026-07-23 fixedFields: {"YYhg":"BjI0"}  # static v1.9.6-1db46d

更早 lot rule:
  (n[17:18]+n[9:10])+.+(n[16:19])+.+(n[23:30]) -> n[10:15]
2026-07 中期 lot rule:
  n[20:20]+n[8:8]+n[11:11]+n[30:30] -> n[16:21]
2026-07-23 lot rule:
  n[1:4] -> n[24:27]
```

这些值只能作为版本样本，不应继续写死在 Node/vm 实现中。加载当前 bundle 后直接读取 `_lib` 和 `lib._abo`。纯 Python 从当前 `code.js` 文本解析同一组字段。

## 稳健暴露 Webpack Require

旧提取脚本把入口表达式中的字符串表索引写死为 `(20)`；新版索引变为 `(51)` 后，替换不再命中。应匹配整个 `i(i[...]=16)` 结构：

```js
function loadBundle(bundlePath) {
  let code = fs.readFileSync(bundlePath, 'utf8');
  code = code.replace(
    /i\(i\[[^\]]+\]\s*=\s*16\)/,
    '(globalThis.__req = i, {})'
  );

  const ctx = { console, setTimeout, clearTimeout };
  ctx.globalThis = ctx;
  ctx.global = ctx;
  ctx.self = ctx;
  ctx.window = ctx;
  ctx.navigator = {};
  ctx.document = {};
  vm.createContext(ctx);
  vm.runInContext(code, ctx, { timeout: 10000, filename: bundlePath });

  return {
    req: ctx.__req,
    fixedFields: ctx._lib || {},
    lotRules: (ctx.lib && ctx.lib._abo) || {},
  };
}
```

本次新旧 bundle 的模块数均为 61，已确认的 helper 为：

- `req(25).default(...)`：PoW。
- `req(27).default.load({type: 'gt4'})`：`gee_guard`。
- `req(31).default(compactJson, {options: {pt: '1'}})`：`w` 加密。
- `req(60).default([], em)`：填充 `em`。

当前 PoW 模块的实测参数顺序不能按字段名猜测：

```js
const pow = req(25).default(
  data.lot_number,
  captchaId,
  data.pow_detail.hashfunc,
  data.pow_detail.version,
  Number(data.pow_detail.bits),
  data.pow_detail.datetime,
  ''
);
```

当前 `gee_guard` 输出为 `{"roe":{"aup":"3","sep":"3","egp":"3","auh":"3","rew":"3","snh":"3","res":"3","cdc":"3"}}`，`em` 输出为 `{"ph":0,"cp":0,"ek":"11","wd":1,"nt":0,"si":0,"sc":0}`。这些模块编号和结果只是当前版本证据；后续升级仍应检查导出类型和函数特征，不能无条件假设。

## GCT 与 `biht`

`/load` 返回的 `gct_path` 必须按本轮地址下载。GCT 会导出 `_gct`，对 `{geetest:'captcha', lang:'zh', ep:'123'}` 增加 `biht`。当前实测 `typeof payload.biht === 'string'`，值形如 `"1426265548"`；保留 GCT 写入的原始类型。

当前 GCT 的 `biht` 不是普通静态配置，而是对两个函数的 `Function.prototype.toString()` 原文做 5381 风格哈希后得到。格式化、beautify 或改写 GCT 会改变函数原文，从而生成不同的 `biht`；本次原始 minified GCT 计算结果是 `1426265548`，格式化副本曾计算出不同值。

纯 Python 路径可以不执行 GCT：从原始源码中提取包含 `var e=5381` 的哈希函数及紧随其后的 guard 函数，按 JavaScript `int32`、左移和 UTF-16 code unit 语义复现哈希。不要把 `1426265548` 长期写死为跨版本常量。

## 通用 Lot Rule 解析

规则中的 `n[a:b]` 是零基、包含末端的切片。`+` 表示字符串拼接，解析结果中的 `.` 表示嵌套对象路径。

```js
function resolveLotExpression(expression, lotNumber) {
  return expression
    .replace(/n\[(\d+):(\d+)\]/g, (_, start, end) =>
      lotNumber.slice(Number(start), Number(end) + 1)
    )
    .replace(/\+/g, '');
}

function lotExtra(lotNumber, rules) {
  const result = {};
  for (const [keyExpression, valueExpression] of Object.entries(rules)) {
    const path = resolveLotExpression(keyExpression, lotNumber).split('.');
    const value = resolveLotExpression(valueExpression, lotNumber);
    let target = result;
    path.forEach((key, index) => {
      if (index === path.length - 1) target[key] = value;
      else target = target[key] || (target[key] = {});
    });
  }
  return result;
}
```

组装时使用：

```js
const wPayload = {
  setLeft,
  passtime,
  userresponse,
  device_id: '',
  lot_number: data.lot_number,
  pow_msg: pow.pow_msg,
  pow_sign: pow.pow_sign,
  geetest: 'captcha',
  lang: 'zh',
  ep: '123',
  biht,
  gee_guard,
  ...fixedFields,
  ...lotExtra(data.lot_number, lotRules),
  em,
};
```

## 纯 Python 路径

纯 Python 不需要 iv8、Node、ExecJS 或浏览器环境。`code.js` 可以只作为文本数据源，不执行其中的 JavaScript：

1. 提取顶部 `decodeURI(...)` 字符串和循环 XOR key，解出字符串表。
2. 从 `_lib/lib._abo` 初始化段读取字段名、字符串表索引和 lot rule。
3. 从字符串表选择当前 RSA modulus；找不到时才使用已验证公钥兜底。
4. 从本轮原始 GCT 源码计算 `biht`。
5. Python 生成 PoW、`gee_guard`、`em`、AES key、AES ciphertext 和 RSA encrypted key。

实现时优先直接使用 `scripts/gt4_pure_replay.py`，下面内容用于理解和排错，不要每个目标重新手写一次。

当前规则必须从 bundle 解析，不要手写。2026-07-23 样本对应：

```python
# fixedFields: {"YYhg": "BjI0"}
# lotRules: {"n[1:4]": "n[24:27]"}  -> key=lot[1:5], value=lot[24:28]
w_payload['YYhg'] = 'BjI0'
w_payload[lot_number[1:5]] = lot_number[24:28]
```

当前图片识别要兼容 `ddddocr` 同时返回占位 `target_x=0` 和有效 `target=[x1,y1,x2,y2]` 的情况：

```python
result = detector.slide_match(slice_bytes, bg_bytes, simple_target=True)
target = result.get('target')
gap_x = int(target[0]) if target and int(target[0]) > 0 else int(result['target_x'])
```

当前纯 Python `w` 核心：

```python
aes_key = secrets.token_hex(8).encode()
compact = json.dumps(w_payload, ensure_ascii=False, separators=(',', ':')).encode()
aes_hex = AES.new(aes_key, AES.MODE_CBC, iv=b'0000000000000000').encrypt(
    pad(compact, AES.block_size)
).hex()
rsa_hex = PKCS1_v1_5.new(public_key).encrypt(aes_key).hex()
w = aes_hex + rsa_hex
```

本次验证中 RSA 公钥、AES-CBC 方式、PoW 算法和 `userresponse` 生成方式未发生变化。仍需以服务端结果为准，不要仅凭静态 diff 宣称兼容。

## 高频排查

1. 只替换了 bundle 文件，但 loader 仍读取旧文件名：运行的仍是旧算法。
2. require 暴露正则写死字符串表索引：`ctx.__req` 不存在或仍执行入口模块。
3. 只替换加密模块，不更新 `_lib/lib._abo`：`w` 长度正常但 `/verify` 返回 `forbidden`。
4. 把动态字段长期硬编码：下一次小版本轮换会再次失效；Node/vm 应运行时提取。
5. 官方 Demo 可能按风控分配 `svg_seed` 点选，不等于直接请求 `risk_type=slide` 的协议发生变化；不要用 Demo 出现点选来否定滑块 `/load` 样本。
6. `ddddocr` 的 `target_x=0` 可能只是占位值；若 `target[0] > 0`，应优先使用 `target[0]`，否则会提交 `setLeft=0` 并得到 `result=fail, fail_count=1`。
7. GCT 下载后先 beautify 再计算 `biht`：函数 `toString()` 原文已变化，结果不可信；保留 raw 和 formatted 两份时只能用 raw 参与计算。
8. `status == "success"` 只表示请求被处理，不表示验证通过；必须检查 `data.result`。
9. 最终至少连续验证 Node/vm/iv8 路径 3 次；纯 Python 路径若存在，也至少验证 1 次真实 `/verify` 成功。
10. Python `requests` 在 `/load` 成功后下载 `static.geetest.com` 图片报 `ProxyError/RemoteDisconnected`：先检查环境代理；协议脚本可按环境使用 `session.trust_env = False`，不要误判为图片 URL 或 token 失效。
11. Node 22 的 `globalThis.navigator` 可能是只读 getter；不要直接 `Object.assign(globalThis, {navigator:{}})`，应使用独立 `vm.createContext()`。
12. `w` 长度会随紧凑 JSON 长度变化，不要把某次的 `1472` 或其他长度作为正确性判据；只检查十六进制格式、RSA 尾段长度和最终服务端结果。
13. `passtime` 不只是 payload 字段。生成参数后必须真实 `sleep(passtime / 1000)` 再请求 `/verify`，避免声明时间超过真实请求时序。
14. PoW 使用 `/load` 的长 `payload` 参与明文：当前版本会生成错误的 `pow_msg`；应确认 lot number 后是两个连续分隔符 `||`。
15. 用固定字符窗口读取 bundle 开头：混淆字符串表本身可能超过窗口，导致 `_lib/lib._abo` 明明存在却解析失败；按 lot rule 的明文位置反向定位初始化段。
16. GCT 正则只匹配 `function x(t){var e=5381`：当前 GCT 在 `5381` 前还有控制流变量，会误报找不到；先搜索 `=5381;` 再做函数边界提取。

## 本次验证证据

- 修复前：连续 5 次 `status=success, result=forbidden`。
- 修复后：模块复用的 iv8 流程连续 3 次 `result=success, fail_count=0`。
- 不执行任何 JavaScript 的纯 Python 流程真实返回 `result=success, fail_count=0`。
- 2026-07 浏览器无关 Python + Node VM 路径连续三轮成功：原图 `gap_x=182/197/209`，映射 `setLeft=160/173/184`，三轮均为 `status=success, result=success, fail_count=0`。
- 2026-07 纯 Python 路径连续三轮成功，全程未调用 Node/JS 引擎/浏览器：原图 `gap_x=219/100/215`，映射 `setLeft=193/87/189`，动态 `biht="1426265548"`，三轮均为 `status=success, result=success, fail_count=0`。
- 2026-07-23 bundle 轮换（`v1.9.6-1db46d`，`fixedFields={"YYhg":"BjI0"}`，`lotRules={"n[1:4]":"n[24:27]"}`）后连续 `forbidden`；替换最新 `gcaptcha4.js` 后 Node helper 与纯 Python 均恢复：`result=success, fail_count=0`（helper 1 轮 + pure 3 轮）。
