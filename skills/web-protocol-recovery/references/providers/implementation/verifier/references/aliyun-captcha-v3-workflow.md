# 阿里云 Captcha V3 协议恢复工作流

## 适用信号

看到以下任一组信号时使用本参考：

- `InitCaptchaV3`、`VerifyCaptchaV3`
- `5xyk05.captcha-open.aliyuncs.com` / `*-verify.captcha-open.aliyuncs.com`
- `CaptchaType == "PUZZLE"`
- `StaticPath` 形如 `3.28.0/pe.015.xxx` / `3.28.0/pe.032.xxx`
- FeiLin `DeviceConfig`、`deviceToken`、`Log2`、`Log3`
- 最终码 `T001`、`F001`、`F025`

与 V2 的关键区别：

| 项 | V2 | V3 |
|---|---|---|
| Init/Verify | `InitCaptchaV2` / `VerifyCaptchaV2` | `InitCaptchaV3` / `VerifyCaptchaV3` |
| 动态脚本 | `sg.xxx` | `pe.xxx`（`dynamicJS/3.28.0/pe.*`） |
| 设备日志域 | 常为 `device.captcha-open.aliyuncs.com` | 常见 `cloudauth-device-dualstack.cn-shanghai.aliyuncs.com` |
| 挑战类型 | `SLIDING` 等 | 本地页常见 `PUZZLE` 缺口滑块 |
| 主入口（已验证项目） | `run_t001.py` | **`run_v3_fast.py`**（基线 `run_v3.py`） |

普通阿里云 RPC 签名、`acw_sc__v2` WAF cookie 或非验证码接口不属于本分支。
阿里 V2 日更请走 `references/aliyun-captcha-v2-workflow.md`；**不要把 V2 项目文件改到 V3 目录，也不要用 V2 会话句柄覆盖 V3 画像。**

## 目标形态

最终交付应是：

- Python 拥有 HTTP、cookie、会话、真实等待和最终结果判断。
- AES、HMAC、MD5、Base64、zlib 等直接纯算。
- `arg`/`data` 的 pe VM 可纯 Python 或无 DOM 的本地 helper。
- 浏览器只用于取证与日更画像采集，不是运行依赖。
- 用户只做验证层时，停止在 `VerifyCaptchaV3`，不要回放业务接口。

已验证主入口（项目 `039-阿里v3`）：

```powershell
python run_v3_fast.py
python run_v3_fast.py --auto-update
```

## FeiLin 日更快速分支（昨日 T001，今日 F001/F025）

当用户明确描述“阿里 V3 每天更新”“昨天还能过、今天又挂”时，优先执行本分支。
**不要先改轨迹，也不要因为 `StaticPath`/`pe.xxx` 轮换就重提整套 VM。**

### 1. 固定边界

1. 工作目录固定为 V3 项目本身，例如 `E:\ai_project\039-阿里v3` 或 `039-阿里v3修复`。
2. V2 项目（如 `038-阿里v2`）与本 Provider 的 V2 日更逻辑**只作参考**，禁止改其它项目文件。
3. 取证页优先用项目本地页：`http://127.0.0.1:8765/ai_studio_code.html`。
4. 主运行入口是 `run_v3_fast.py`；`run_v3.py` 是被它 import 的协议基线。

### 2. 先判定是哪一层更新

按以下顺序核对：

```text
DeviceConfig.version          # FeiLin 版本，日更最常见
  -> full Log2 133 字段画像
  -> sparse token 模板 / field21
  -> FeiLin URL 与资源自证（field 117/118）
  -> UA / Client-Hints 与画像一致性
  -> pe StaticPath 的 arg key / data stream
  -> 轨迹 / 时钟
```

若 `DeviceConfig.version != profile.feilinVersion`，立即把本地 profile 判为过期。
不要继续发送混合版本 Verify 来调轨迹。

### 3. 已验证的 FeiLin field21 家族

field21 **常见 classic** 骨架（多代数只换 source/mask）：

```text
mixed[i] = 32 + ((ord(source[i]) - 32 + ord(session_suffix[i]) - 32) % 95)
field21  = Base64(mixed XOR mask)
session_suffix = session_id[-8:]   # 8 位小写 hex
```

已验证 classic 参数（示例）：

```text
FeiLin106:
  source = 68fded68
  mask   = 31f79ddc

FeiLin107:
  source = cccccccc
  mask   = 0000000000000000   # 8 个零字节，等价于只 Base64(mixed)

FeiLin108:
  source = ========
  mask   = 072e8290           # hex: 3037326538323930
```

FeiLin108 固定向量：

```text
58c88084 -> YmITMG1/bGE=
554f0616 -> YmVjQXVhd2M=
```

恢复方法（不要只靠一个样本猜常量）：

1. 连续抓至少 2～5 个当前版本 session 的 field21。
2. 先试 classic：对每个字节位枚举可打印 source，要求 mask 在多样本间恒定。
3. 先命中已知家族，再通用 classic 拟合。
4. classic 穷举无解 = 算法换代：停更新器硬拟合；profile 可写 `field21.algorithm`，实现落项目 `verifier`。
5. 新参数/算法必须同时用于 Log2 完整画像和 Verify 稀疏 token。

### 4. profile 必须整套更新

禁止只替换 `field21` 或 FeiLin URL。正确最小更新集：

```text
feilinVersion
field21.sourceKey / field21.xorMaskHex   # classic
  或 field21.algorithm                   # 非 classic
fullDeviceFields   # 133，来自当前浏览器 Log2 501
tokenFields        # 133 稀疏模板，索引与运行时覆盖规则保持
userAgent          # 与请求头 USER_AGENT / sec-ch-ua 一致
```

运行时仍会覆盖动态字段，例如：

- `21` field21
- `42` IP
- `43` stage timing（稀疏模板必须带 `92/93/94`，否则时钟 rebase 会 KeyError）
- `72/74/87` 时间
- `77` certifyId（token）
- `117/118` FeiLin URL 与 resource timing

### 5. 自动日更脚本（优先）

V3 项目已沉淀：

```powershell
# 只检查是否过期
python scripts/auto_update_feilin_profile.py

# 过期才更新
python scripts/auto_update_feilin_profile.py --apply

# 强制重抓
python scripts/auto_update_feilin_profile.py --force

# 主入口：过期则自动更新后再跑
python run_v3_fast.py --auto-update
```

脚本行为：

1. InitCaptchaV3 读取在线 `DeviceConfig.version`。
2. 与 `verifier/t001_profile.json` 的 `feilinVersion` 比较。
3. 版本一致：不抓包、不改文件。
4. 版本不一致且 `--apply`：
   Playwright Chromium 打开本地 `ai_studio_code.html`，监听页面网络拿到 Init + Log2（不是 Fiddler/mitmproxy 系统代理抓包）。
5. 解密 Log2 完整 133 字段，多样本恢复 field21。
6. 写回 profile，并同步 `run_v3.py` 的 UA / sec-ch-ua。
7. 备份旧 profile 到 `t001_profile.bak_*.json`，材料进 `js_reverse_cache/auto_feilin/`。

### 6. 手工取证最小集

若自动脚本不可用，至少保存同一轮：

- Init 请求/响应（含 `DeviceConfig`、`StaticPath`、`CertifyId`）
- 浏览器自动发出的 Log2 完整 form body
- 当前 FeiLin 脚本 URL（`g.alicdn.com/captcha-frontend/FeiLin/.../feilin108.xxx.js`）
- 一次可信 Verify（可选，用于 sparse token 对照）

解密 Log2：

```text
outer = AES_CBC_decrypt(Data, upload_key=a549a55c60a39aa0, iv=0123456789ABCDEF)
# outer: session_prefix#W#...#GatherCost#501#Base64(record)
record = Base64Decode(event)
# record: session_id#AES(payload)#...
full_133 = AES_CBC_decrypt(record[1], DeviceConfig.session_key).split("#")
```

### 7. pe / arg / data 不要和 FeiLin 混为一谈

`StaticPath` 从 `pe.015` 轮到 `pe.032` 不等于 FeiLin 画像过期。

- FeiLin 日更：动 `t001_profile.json` + field21。
- pe 轮换：动 arg key 表 / data stream codec。
- `run_v3_fast.py` 已支持 `3.28.0` 多 pe 的 arg key 映射；日更失败时先看 FeiLin 版本，不要先重写 pe VM。

data 侧已验证 stream key 可长期稳定为：

```text
3e627e1b4c63f913
```

路径变了仍应做固定输入输出回归；只有 VM 输出或 key 真变才更新 helper。

### 8. 错误码分层（V3 实战）

- `F025`：优先查 DeviceConfig / token envelope / checksum / 完整画像与稀疏增量一致性 / 版本混用。
- `F001`：结构过了以后的风险拒绝；**版本画像过期时也可能直接表现为 F001**，不要先当轨迹问题硬调。
- `T001` 且 `VerifyResult=true`：最终通过。

Log2/Log3 返回 `Code=200` 只能说明 sidecar 接收成功，不能当作 Verify 通过。

### 9. 日更完成标准

必须同时满足：

```text
当前 DeviceConfig.version == 本地 profile.feilinVersion
field21 多样本向量命中
Log2 == 200 / true
Log3 == 200 / true
VerifyCode == T001
VerifyResult == true
主入口：python run_v3_fast.py 退出码 0
```

### 10. 2026-07-17 已验证案例（FeiLin107 -> 108）

现象：

- 本地 profile 仍是 `feilin107...`
- 在线 Init 已发 `1.4.2/feilin108.b0a219fc409ae510a9be611c1df1851904f862374a3c7f1b4e977da9d38fc2d3`
- Log2/Log3 仍 200，但 Verify 固定 `F001`

处理：

1. 只在 V3 项目内取本地页 Init+Log2。
2. 恢复 field21：`========` + `072e8290`。
3. 整套替换 full/sparse 画像，UA 对齐 Chrome 150。
4. `run_v3_fast.py` 复测得到 `T001`。

经验沉淀：

- V3 日更与 V2 同源（FeiLin 画像），但项目、入口、动态脚本家族不同。
- 自动更新后，日常只需 `run_v3_fast.py`；过期时用 `--auto-update`。

## 完整请求图

```text
local challenge page (or business page)
  -> InitCaptchaV3
  -> FeiLin.js + pe.xxx.js + puzzle images
  -> UploadLog
  -> Log2   (full 133 device fields)
  -> Log3   (511 + 504 combat)
  -> VerifyCaptchaV3
```

不要在只看到 Init 和 Verify 后就开始调轨迹。

## 成功标准

```text
Success == true
Result.VerifyCode == "T001"
Result.VerifyResult == true
```

以下不能单独视为通过：

- HTTP 200
- 顶层 `Code == "Success"`
- Log2/Log3 `Code == "200"`
- 缺口距离识别正确
- token 能解密且 checksum 正确

## 主 RPC 与设备侧材料

主验证码接口与设备接口都采用阿里 RPC HMAC-SHA1：

```text
canonical = sort(params without Signature)
StringToSign = "POST&%2F&" + percent_encode(canonical_query)
Signature = Base64(HMAC-SHA1(secret + "&", StringToSign))
```

DeviceConfig：

```text
AES-CBC
key = 87f879f135f27da7
iv  = 0123456789ABCDEF
padding = PKCS7
```

deviceToken 外层：

```text
Base64("WEB#session_id#payload_ciphertext#counter#checksum")
checksum = MD5("WEB#session_id#payload_ciphertext#counter#daye,raolewoba!")
```

设备上传 key（Log2/Log3 外层）：

```text
a549a55c60a39aa0
```

这些常量是 bundle 版本相关材料，新目标仍需用捕获包复核。

## 轨迹与时钟

- V3 缺口滑块存在非线性 pointer→puzzle 映射，不要直接把自然缺口 x 当 drag。
- `run_v3_fast.py` 使用压缩前置历史时钟（默认目标约 2.5s）作为稳定快速配置。
- 声明耗时、真实 sleep、Log3/Verify 发送时刻必须一致。
- sparse token 的 field43 需要 `93`（及相邻 `92/94`）供时钟 rebase；缺失会在 `prepare_track` 处直接异常。

## 固定向量要求

至少建立：

- field21：106 / 107 / 108 各至少一组
- arg 固定输入输出（或 pe key 映射回归）
- data stream 固定输入输出
- profile 版本 pin：`feilinVersion` 不一致 fail fast
- 在线 Verify 返回 `T001`

## 交付检查

- [ ] 未改 V2 或其它无关项目
- [ ] 主入口是 `run_v3_fast.py`
- [ ] `DeviceConfig.version == profile.feilinVersion`
- [ ] field21 参数来自 profile 或已验证版本分支，且多样本命中
- [ ] full/sparse 画像整套更新，不是单字段拼接
- [ ] UA / sec-ch-ua 与画像一致
- [ ] Log2/Log3/Verify 同一轮 session
- [ ] 最终证据是 `T001 + VerifyResult=true`
