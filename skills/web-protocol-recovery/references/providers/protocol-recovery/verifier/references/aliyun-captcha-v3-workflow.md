# 阿里云 Captcha V3 协议参考

> 状态：本文件保留协议逆向经验和历史样本，不是当前目标的可运行实现。skill 不包含 V3 runner、自动更新器、profile 或本机取证页；文中出现的外部项目文件名只可在用户明确提供并授权后使用。
>
> FeiLin/field21、画像、`pe/arg/data`、时钟和错误码结论来自历史样本，不能作为当前目标验收、当前 profile 或 live replay 授权。当前目标必须重新取得同轮证据，最终 live egress 仍由批准的 Python collector 负责。

## 适用信号

至少看到一个 V3 代际信号时才使用本参考：

- `InitCaptchaV3`、`VerifyCaptchaV3`（可出现在 `5xyk05.captcha-open.aliyuncs.com` / `*-verify.captcha-open.aliyuncs.com`）
- 同一阿里云 Init 响应同时出现 `CaptchaType == "PUZZLE"` 和 `StaticPath` `3.28.0/pe.015.xxx` / `3.28.0/pe.032.xxx`

FeiLin `DeviceConfig`、`deviceToken`、`Log2`、`Log3`、`T001/F001/F025` 是 V2/V3 共享信号，只能先选 `route: verifier`，不能单独决定读取哪一代参考。缺少代际信号时先索要 Init/Verify action 或 `sg.xxx/pe.xxx`，不要同时预读 V2/V3。

与 V2 的关键区别：

| 项 | V2 | V3 |
|---|---|---|
| Init/Verify | `InitCaptchaV2` / `VerifyCaptchaV2` | `InitCaptchaV3` / `VerifyCaptchaV3` |
| 动态脚本 | `sg.xxx` | `pe.xxx`（`dynamicJS/3.28.0/pe.*`） |
| 设备日志域 | 常为 `device.captcha-open.aliyuncs.com` | 常见 `cloudauth-device-dualstack.cn-shanghai.aliyuncs.com` |
| 挑战类型 | `SLIDING` 等 | 本地页常见 `PUZZLE` 缺口滑块 |
| 交付入口 | 由当前目标和 delivery Provider 确定 | 用户提供并授权的外部实现（本 skill 不内置 runner） |

普通阿里云 RPC 签名、`acw_sc__v2` WAF cookie 或非验证码接口不属于本分支。
阿里 V2 日更请走 `references/aliyun-captcha-v2-workflow.md`；**不要把 V2 项目文件改到 V3 目录，也不要用 V2 会话句柄覆盖 V3 画像。**

## 目标形态

最终交付应是：

- Python 拥有 HTTP、cookie、会话、真实等待和最终结果判断。
- AES、HMAC、MD5、Base64、zlib 等直接纯算。
- `arg`/`data` 的 pe VM 可纯 Python 或无 DOM 的本地 helper。
- 浏览器只用于取证与日更画像采集，不是运行依赖。
- 用户只做验证层时，停止在 `VerifyCaptchaV3`，不要回放业务接口。

当前目标实现入口（若用户提供）：

```powershell
由用户授权的目标项目自行定义；本文件不提供可执行命令。
```

## FeiLin 日更快速分支（昨日 T001，今日 F001/F025）

当用户明确描述“阿里 V3 每天更新”“昨天还能过、今天又挂”时，优先执行本分支。
**不要先改轨迹，也不要因为 `StaticPath`/`pe.xxx` 轮换就重提整套 VM。**

### 1. 固定边界

1. 工作目录固定为用户指定的 V3 项目本身；本 skill 不假设该目录或实现存在。
2. V2 项目与本 Provider 的 V2 日更逻辑**只作参考**，禁止改其它项目文件。
3. 取证页必须来自当前目标证据或用户授权的目标项目，不使用 skill 内假定的本机页面。
4. 主运行入口由当前目标实现定义，不从历史文档名推断。

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

不要用单次 Init 立即判定本地状态过期。FeiLin 可能灰度下发相邻版本；在已批准的请求预算内，默认收集 7 个成功 Init 的版本样本，按出现次数选择主流 cohort，计数相同时选较新的 FeiLin 代数，并保存版本分布。预算不足且没有更强的当前目标证据时 fail closed，不能用少数样本覆盖状态。只有主流 `DeviceConfig.version` 与当前目标保存的 FeiLin 版本不同时，才进入画像更新。

版本未判定前，不要继续发送混合版本 Verify 来调轨迹。

### 3. 已验证的 FeiLin field21 家族

field21 **常见 classic** 骨架（多代数只换 source/mask）：

```text
mixed[i] = 32 + ((ord(source[i]) - 32 + ord(session_suffix[i]) - 32) % 95)
field21  = Base64(mixed XOR mask)
session_suffix = session_id[-8:]   # 8 位小写 hex
```

`sourceKey` 是 8 个 ASCII 字节。非零 mask 也按 8 个 ASCII 字节参与 XOR；`xorMaskHex` 保存这 8 个字节的十六进制表示。零 mask 是 8 个原始 `0x00` 字节。不要把 8 字符的 mask 文本直接当 4 字节 hex 解码。

已验证 classic 参数（示例）：

```text
FeiLin106:
  sourceKey   = 68fded68
  maskAscii   = 31f79ddc
  xorMaskHex  = 3331663739646463

FeiLin107:
  sourceKey   = cccccccc
  maskBytes   = 00 00 00 00 00 00 00 00
  xorMaskHex  = 0000000000000000

FeiLin108:
  sourceKey   = ========
  maskAscii   = 072e8290
  xorMaskHex  = 3037326538323930
```

固定向量：

```text
FeiLin106:
983c7551 -> fGEff0UdLyo=

FeiLin107:
e7f61587 -> SXpKeXR4e3o=
2f894218 -> dUp7fHd1dHs=

FeiLin108:
58c88084 -> YmITMG1/bGE=
554f0616 -> YmVjQXVhd2M=
```

恢复方法（不要只靠一个样本猜常量）：

1. 从已确认的同一主流 cohort 连续采集样本；2 个只是起点，不设“最多 5 个”的停止条件。
2. 先试 classic：逐字节枚举可打印 source，要求 mask 在多样本间恒定，且 8 个位置都只剩唯一候选。
3. 把至少一个未参与拟合的新 session 留作 holdout；holdout 不命中就继续采样，不写回状态。
4. 先命中已知家族，再通用 classic 拟合；十六进制 suffix 覆盖不足导致多个等价候选时继续采样。
5. classic 穷举无解或 holdout 失败 = 算法换代：停止硬拟合；当前目标可保存 `field21.algorithm`，实现落在其 verifier 模块。
6. 新参数/算法必须同时用于 Log2 完整画像和 Verify 稀疏 token；获批 live verify 时以在线 `T001 + VerifyResult=true` 收口，否则停在离线 holdout 并明确未做在线验收。

### 4. profile 必须整套更新

禁止只替换 `field21` 或 FeiLin URL。下面是概念字段名，必须映射到当前目标自己的状态 schema，不能假设存在同名 profile 文件：

```text
storedFeilinVersion
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

### 5. 自动日更边界（如用户提供更新器）

若用户提供了当前目标更新器：

```powershell
# 仅在用户明确授权的目标项目目录中运行其更新器；本 skill 不提供该脚本。
```

脚本行为：

1. InitCaptchaV3 收集在线 `DeviceConfig.version` 分布，按本节的主流 cohort 规则判定目标版本。
2. 与当前目标保存的 FeiLin 状态版本比较。
3. 主流版本一致：不抓包、不改文件；少数灰度版本不能触发覆盖。
4. 主流版本不一致时，在批准的浏览器取证流程中监听页面网络拿到同 cohort 的 Init + Log2；不依赖历史本机页面或系统代理。
5. 解密 Log2 完整 133 字段，持续采样到 field21 唯一解并通过独立 holdout。
6. 只在用户授权的当前目标目录写回动态状态，并同步请求 UA / sec-ch-ua。
7. 备份和证据材料遵守当前 projectRoot 与 artifactPolicy。

### 6. 手工取证最小集

若自动脚本不可用，至少保存同一轮：

- Init 请求/响应（含 `DeviceConfig`、`StaticPath`、`CertifyId`）
- 浏览器自动发出的 Log2 完整 form body
- 当前 FeiLin 脚本 URL（`g.alicdn.com/captcha-frontend/FeiLin/.../feilin108.xxx.js`）
- 一次可信 Verify（可选，用于 sparse token 对照）

解密 Log2：

```text
outer = AES_CBC_decrypt_base64(Data, key=a549a55c60a39aa0, iv=0123456789ABCDEF)
outer_fields = outer.split("#")
# outer: session_prefix#W#...#GatherCost#event_data
event_data = "#".join(outer_fields[-2:])
event_type, record_b64 = event_data.split("#", 1)
assert event_type == "501"
record_fields = Base64Decode(record_b64).decode().split("#")
# record: session_id#AES(payload)#...
payload_ciphertext = record_fields[1]
full_133 = AES_CBC_decrypt(payload_ciphertext, DeviceConfig.session_key).split("#")
```

### 7. pe / arg / data 不要和 FeiLin 混为一谈

`StaticPath` 从 `pe.015` 轮到 `pe.032` 不等于 FeiLin 画像过期。

- FeiLin 日更：更新当前目标自己的完整 FeiLin 状态与 field21，不假设文件名。
- pe 轮换：动 arg key 表 / data stream codec。
- 历史实现曾支持 `3.28.0` 多 pe 的 arg key 映射；当前目标应先看 FeiLin 版本和同轮证据，不要直接重写 pe VM。

历史样本中 data stream key 曾跨多个版本保持为：

```text
3e627e1b4c63f913
```

它不是协议不变量。路径变了仍应做固定输入输出回归；只有当前 bundle 的 VM 输出或运行时 key 真变才更新 helper。

### 8. 错误码分层（V3 实战）

- `F025`：优先查 DeviceConfig / token envelope / checksum / 完整画像与稀疏增量一致性 / 版本混用。
- `F001`：结构过了以后的风险拒绝；**版本画像过期时也可能直接表现为 F001**，不要先当轨迹问题硬调。
- `T001` 且 `VerifyResult=true`：最终通过。

Log2/Log3 返回 `Code=200` 只能说明 sidecar 接收成功，不能当作 Verify 通过。

### 9. 日更完成标准

必须同时满足：

```text
主流 DeviceConfig.version == 当前目标保存的 FeiLin 版本
field21 唯一解 + 独立 holdout 命中
Log2 == 200 / true
Log3 == 200 / true
VerifyCode == T001
VerifyResult == true
当前目标交付入口：由用户授权的实现定义，并通过语义验收
```

### 10. 历史样本（2026-07-17，FeiLin107 -> 108；非当前验收）

现象：

- 历史目标状态仍记录 `feilin107...`
- 在线 Init 已发 `1.4.2/feilin108.b0a219fc409ae510a9be611c1df1851904f862374a3c7f1b4e977da9d38fc2d3`
- Log2/Log3 仍 200，但 Verify 固定 `F001`

处理：

1. 只在当前目标授权范围内取同轮 Init+Log2。
2. 恢复 field21：`========` + `072e8290`。
3. 整套替换 full/sparse 画像，UA 对齐 Chrome 150。
4. 用当前目标交付入口复测得到语义成功；历史 runner 名称不构成当前验收。

经验沉淀：

- V3 日更与 V2 同源（FeiLin 画像），但项目、入口、动态脚本家族不同。
- 自动更新经验只说明状态变化的处理顺序，当前目标仍需自己的更新器和验收证据。

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
- 历史实现使用过压缩前置历史时钟；当前目标必须从同轮证据确认时钟模型。
- 声明耗时、真实 sleep、Log3/Verify 发送时刻必须一致。
- 历史实现中，sparse token 的 field43 时钟 rebase 依赖 `92/93/94`；当前目标若采用同一模型，必须在自己的轨迹准备阶段显式校验这些输入，不能假设任何历史函数名或调用层级仍存在。

## 固定向量要求

至少建立：

- field21：本参考中的 106 / 107 / 108 向量必须通过；当前版本另做唯一解与 holdout
- arg：为当前 pe 建立固定输入输出（或 pe key 映射回归）
- data stream：为当前 bundle 建立固定输入输出；不能只断言历史 key 未变
- 状态版本 pin：主流 FeiLin 版本不一致时 fail closed
- 在线 Verify 返回 `T001`

## 交付检查

- [ ] 未改 V2 或其它无关项目
- [ ] 主入口来自用户授权的当前目标实现，并已通过当前 work order 验收
- [ ] 主流 `DeviceConfig.version` 等于当前目标保存的 FeiLin 版本
- [ ] field21 参数来自当前目标状态或已验证版本分支，且唯一解与独立 holdout 命中
- [ ] full/sparse 画像整套更新，不是单字段拼接
- [ ] UA / sec-ch-ua 与画像一致
- [ ] Log2/Log3/Verify 同一轮 session
- [ ] 最终证据是 `T001 + VerifyResult=true`
