# 阿里云 Captcha V2 协议参考

> 状态：本文件是协议族与历史证据参考，不是当前目标的可运行实现。skill 不包含 `run_t001.py`、`verifier/aliyun_v2.py`、`vm_codec.js`、`t001_profile.json` 或更新器；文中这些名称仅指用户明确提供并授权的外部项目文件。
>
> 本文件中的 51job / FeiLin 观察、固定值、版本记录和在线结果均属于历史样本，不能作为当前目标验收、当前 cookie/profile 或 live replay 授权。当前案例以注册表和对应 `case.json` 的离线向量为准；最终 live egress 仍须走 `python-collector` work order。

## 适用信号

看到以下任一组信号时使用本参考：

- `InitCaptchaV2`、`VerifyCaptchaV2`
- `captcha-pro-open.aliyuncs.com`
- `DeviceConfig`、`deviceToken`、`CaptchaVerifyParam`
- FeiLin、动态 `sg.xxx` 脚本
- `device.captcha-open.aliyuncs.com` 的 `Log2`、`Log3`
- 最终码 `T001`、`F001`、`F025`

普通阿里云 RPC 签名、`acw_sc__v2` WAF cookie 或非验证码接口不属于本分支。

## 目标形态

最终交付应是：

- Python 拥有 HTTP、cookie、会话、真实等待和最终结果判断。
- AES、HMAC、MD5、Base64、zlib 等直接纯算。
- 动态 sg 的数学/VM codec 无法经济地改写时，可以保留无 DOM 依赖的本地 JS helper。
- 浏览器只用于取证、人工正样本和控制变量实验。
- 用户只做验证层时，停止在 `VerifyCaptchaV2`，不要回放业务接口。

### 业务 WAF 触发前置

部分站点不是裸调用业务接口就返回验证码挑战。冷会话、缺少页面 warmup、
或缺少站点自有签名头时，响应可能是 JSON 业务错误（例如未登录/状态异常）而
不是包含 `var requestInfo = {...}` 的挑战 HTML。此时不要先怀疑 Aliyun
验证码算法。

通用处理顺序：先打开目标业务页建立站点会话，再按网页真实请求补齐业务签名
头和设备 ID，触发一次业务 POST/GET，只有拿到 `requestInfo` 后才进入
`InitCaptchaV2` / `Log2` / `Log3` / `VerifyCaptchaV2`。验证通过后如需证明
业务门禁，再用同轮 `requestInfo.token` 与 `CertifyId` 回放业务接口；用户只
要求验证层时仍停在 `T001 + VerifyResult=true`。

排障顺序：签名业务触发返回 `NOT_LOGGED_IN` 时，不要先归因账号失效或
`ssxmod_*` 缺失。先与真实浏览器请求逐项对齐 `Referer`、Origin、业务签名
头、设备 ID 和 TLS/HTTP2 指纹；有些站点（例如 PZDS goodsPublic）要求业务
POST 使用根页 `Referer: https://www.pzds.com/`，详情页 referer 会被路由到
JSON 登录态错误。若响应 HTML 带 `aliyun_waf_aa/bb` 前缀，也不要当成失败页；
检查 `textarea#renderData` 内是否仍有 `var requestInfo = {...}`。

Python 3.9 特例：`curl_cffi 0.13.x` 不支持原生 `chrome146`，而
`curl_cffi>=0.14` 已要求 Python >=3.10。若当前站点需要新 Chrome 传输指纹，
可以用从新版本环境提取的 `ja3`、`akamai`、`extra_fp` 自定义 profile 复现，
并先用 challenge-only 探针连续命中 `requestInfo` 后再提交验证码。

## 分支总览（完整 vs 极速）

本文件保留两套可切换路径，**不是互相替换**：

| 分支 | 何时进入 | 核心输入 | 做什么 | 不做 |
|------|----------|----------|--------|------|
| **离线候选分支** | 用户要求先复用已知协议事实 | 历史常量/公式 + 当前目标 capture | 形成待验证的窄 helper；不能据此声称目标 runner 或 T001 已可用 | 把历史定值直接当作当前 profile、cookie、runner 或验收结果 |
| **完整分支（协议恢复）** | 用户说「走完整分支/从零」；或极速定值与 capture 冲突 | 网络/脚本证据 | 请求图、差分、算法换代 | 在定值仍有效时假装从零 |

**原则（极速）：**
固定不变、已 T001 验证过的层 → **写进 skill，直接用**。
随浏览器/会话变化的层（133 画像、IP、UA、FeiLin 资源 URL、combat 时间）→ **当前目标 capture 生成动态状态**。
外部参考项目不是前提。优先使用当前选中 case manifest 声明的资产；用户另给的历史项目只可按 read budget 读取，不能把旧实现直接复制进当前交付。

用户提示词含下列**任一**时，**必须进入极速分支**，不得先开完整分析：

```text
走极速分支
极速实现
极速固化
fast path
用历史候选事实形成待验证的窄 helper
```

用户提示词含下列**任一**时，进入完整分支：

```text
走完整分支
从零恢复
完整协议分析
不要用固化定值
```

未指定时：根据当前目标证据选择离线证明或完整恢复；历史样本不自动升级为极速实现路线。

## 极速分支（固化定值）

### 0. 分层：什么算“固定定值”，什么必须现采

**A. 固定定值（写入 skill，禁止每轮重解）**

下列材料来自历史的 51job / Captcha V2 / FeiLin 1.4.2 样本；只能作为候选假设，必须由当前目标的同轮 capture 和离线向量重新验证，不能直接写入不存在或未授权的目标实现。

```text
# 主验证码 RPC（InitCaptchaV2 / VerifyCaptchaV2）
MAIN_AK     = REDACTED_ALIYUN_AK
MAIN_SECRET = REDACTED_ALIYUN_SK
MAIN_VER    = 2023-03-05

# 设备侧 RPC（Log2 / Log3）
DEVICE_AK     = REDACTED_ALIYUN_AK
DEVICE_SECRET = REDACTED_ALIYUN_SK
DEVICE_VER    = 2020-10-15
DEVICE_HOST   = https://device.captcha-open.aliyuncs.com/

# AES / token
DEVICE_CONFIG_KEY = 87f879f135f27da7   # DeviceConfig
DEVICE_UPLOAD_KEY = a549a55c60a39aa0   # Log2/Log3 外层 Data
DEVICE_AES_IV     = 0123456789ABCDEF   # 16 字节 ASCII
DEVICE_TOKEN_SALT = daye,raolewoba!
TOKEN_PLATFORM    = WEB
# deviceToken outer: Base64("WEB#session_id#payload_b64#counter#md5hex")
# payload AES-CBC(session_key from DeviceConfig, IV above), 133 个 # 字段
# checksum = MD5("WEB#session_id#payload_b64#counter#daye,raolewoba!")

# data / arg stream（多 sg 路径共享）
STREAM_KEY_DEFAULT = 3e627e1b4c63f913
# data_input = Base64(zlib(nonce32hex + compact_track_json))
# data/arg 经无 DOM 的 vm stream codec(STREAM_KEY) 输出

# RPC 签名
# StringToSign = "POST&%2F&" + pct(sort(params without Signature))
# Signature = Base64(HMAC-SHA1(secret+"&", StringToSign))
# pct: RFC3986 safe=-_.~

# 设备 Log 公共语义
DEVICE_PLATFORM_TAG = W.10051
DEVICE_APP_NAME     = saf-captcha-waf
DEVICE_APP_VERSION  = W20220202
# Log2 event: 501#Base64(record6)
# Log3 event: Base64("511#Base64(status_record)-504#Base64(combat_record)")
# record6: session#AES(fields)#AES(saf-captcha-waf)#AES(W.10051)##AES(ts_ms)
# outer Data: AES_upload(session_prefix#W#AES_session(W.10051#saf-captcha-waf#sceneId)#W20220202#CLOUD#GatherCost#event)

# 成功码
Verify: Success==true && Result.VerifyCode=="T001" && Result.VerifyResult==true
Log2/Log3: Code=="200" && ResultObject==true
```

**field21 classic 族（FeiLin106–112，多样本已验证）：**

```text
input  = session_id[-8:]   # 8 hex
mixed  = 32 + ((ord(source[i])-32 + ord(suffix[i])-32) % 95)
field21 = Base64( mixed[i] XOR mask[i] )

FeiLin106: source=68fded68  mask=31f79ddc
FeiLin107: source=cccccccc  mask=8 zero bytes (xorMaskHex=0000000000000000)
FeiLin108: source========  mask=072e8290  (xorMaskHex 存 ASCII 的 hex: 3037326538323930)
FeiLin109: source=6b2f51d0  mask=072e8290
FeiLin110: source=}}}}}}}}  mask=8 zero bytes
FeiLin111: source=hhhhhhhh  mask=fde95c04  (hex 6664653935633034)
FeiLin112: source=""""""""  mask=0eb971e9  (hex 3065623937316539)

107 固定向量:
  e7f61587 -> SXpKeXR4e3o=
  2f894218 -> dUp7fHd1dHs=
106 固定向量:
  983c7551 -> fGEff0UdLyo=
  d4797207 -> SX0bSkUSIiw=
```

**field21 FeiLin113（算法换代，非 classic；按位规则，suffix 为 8 位小写 hex）：**

```text
algorithm = feilin113
for each pos, char in suffix:
  pos0: digit -> ord^0x31 ; letter -> ord^0x09
  pos1: digit -> ord^0x54 ; letter -> ord^0x64
  pos2: digit -> ord^0x38 ; letter -> (ord-37)&255
  pos3: digit -> ord^0x31 ; letter a-f: k=nibble-10; out=0x34+(k if k even else k+2)
  pos4: ord^0x36
  pos5: ord^0x35
  pos6: ord^0x36
  pos7: (103 + (int(char,16)^1)) & 255
field21 = Base64(8 bytes)

回归：对本目录 ≥3 个 session suffix 全命中 Log2/token 的 field21。
```

**历史目标样式示例（不得视为当前端点或定值）：**

```text
# 业务挑战页（用户 URL 优先）
DEFAULT 仅表示旧样本中可能出现的业务端点形态；当前 URL 必须来自当前目标证据。
# Init/Verify host 模式
Init:   https://{prefix}.captcha-pro-open.aliyuncs.com/
Verify: https://{prefix}-verify.captcha-pro-open.aliyuncs.com/
# 已验证样本 prefix（若 Init 响应/请求变化则以 capture 为准）
prefix 例: 93bc86fc5f88a01515ccdf7ea6192e9f
sceneId 例: 19x5u7lo
Mode=embed, Language=cn
# 挑战页 requestInfo 常在 textarea#renderData: var requestInfo = {...};
# 需要: sceneId, traceid, token, userId, userUserId
```

**B. 动态层（禁止当定值写死，必须由当前目标 capture 生成）**

```text
DeviceConfig.session_id / session AES key / ip / timestamp / feilinVersion 路径
fullDeviceFields 133（GPU/UA/屏幕/FeiLin URL 等）
sparse token 时间项、certifyId、counter≈Log2 GatherCost
combat504 轨迹时间、Log3 时间
StaticPath / 当轮 sg 文件名（codec 不变时只当 URL）
UserCertifyId/traceid 当轮值
```

### 1. 触发后立即执行（禁止插队）

1. **写目录硬锁。** 只写用户目标目录。任何外部参考路径只读；默认不打开历史项目，当前 case bundle 之外的材料必须先满足 read budget 和授权边界。
2. **在授权目标目录中记录候选固定层（先证明，不把历史定值当成当前实现）：**
   - 外部目标项目可能包含 RPC/helper/stream codec/profile/runner；这些文件不由本 skill 提供，必须先确认路径、授权和当前目标范围。
3. **本目录同轮 capture（只采动态层）：**
   - 至少一轮人工或已有 T001：Init + Log2 + Log3 + Verify；或 Init + Log2 + token + Log3
   - 解析 `DeviceConfig.version`、133 字段、combat511/504、sceneId、region/verify host、UA
4. **生成当前目标的动态状态快照：**
   - `feilinVersion` / `userAgent` / `fullDeviceFields` / `combat511` / `combat504`
   - `field21`: version 含 `feilin113` → `{"algorithm":"feilin113"}`；否则 classic 的 sourceKey+xorMaskHex（来自 skill 表，**不要**重拟合除非回归失败）
5. **固定向量（离线最低集，用候选事实 + 当前目标 capture）：**
   - 主 RPC / 设备 RPC：用 MAIN_SECRET / DEVICE_SECRET 对 capture 重算 Signature 一致
   - DeviceConfig 解密字段数与 session key 长度
   - deviceToken decrypt/rebuild/checksum
   - field21：≥3 suffix 命中
   - data_builder 对固定 compressed+key 有稳定输出（若有历史 data 向量则比对）
6. **验收：**
   不在本 skill 内执行 runner；若需要 live replay，必须另行通过 `python-collector` work order 交付并验收。
   唯一成功：`T001 && VerifyResult true`；Log2/Log3 `200/true`。

### 2. 极速硬停（转完整或日更）

- capture 上 MAIN/DEVICE 签名回归失败（密钥轮换）→ 完整分支重取密钥
- DeviceConfig AES 定值解密失败 → 完整分支
- field21：feilin113 + 全 classic 表均无法多样本命中 → 完整分支算法换代
- stream 固定输入输出或运行时 key ≠ `3e627e1b4c63f913` 且旧 vm 输出变 → 完整分支更新 VM
- token 非 133 字段或 envelope 变 → 完整分支
- 仅 `F025` 且 version 与 profile 不一致 → **日更分支**（换画像，不重解定值层）
- 缺少已确认的 stream codec 工件 → 停止并索取当前目标材料，或在批准的执行策略下重新提取；不得从旧项目复制后假装跑通

### 3. 极速 field21 顺序（禁止开局 AES/affine 漫搜）

```text
DeviceConfig.version 含 feilin113
  → 仅作为历史候选 `algorithm=feilin113`，须由当前样本确认
else 试 skill 内 classic 106–112 表（固定向量 + 当前 suffix）
  → 写入 sourceKey + xorMaskHex
else
  → 极速失败，完整分支
```

### 4. 极速禁止事项

1. **禁止把“极速”理解成“先找参考项目再抄”。** 定值在 skill；参考可选且只读。
2. 禁止重解已固化的 MAIN/DEVICE 密钥、CONFIG/UPLOAD AES、token salt、stream key（除非硬停）。
3. 禁止 jsdom/`Window`/`document`/`canvas` 补环境。
4. 禁止以自动拖滑块为交付主路径。
5. 禁止 `sg.xxx` 文件名变化就重提 VM。
6. 禁止把其他机器或历史项目的 profile 当作当前目标正式状态。
7. 禁止在参考项目写 artifact 或跑 updater。

### 5. 极速完成标准

```text
当前目标的窄 helper 只能使用已由当前证据确认的 AK/AES/stream/field21 候选
动态状态来自当前目标 capture 且 FeiLin 版本对齐
Log2 == 200 / true
Log3 == 200 / true
VerifyCode == T001 && VerifyResult == true
```

---

## 执行前硬门（完整分支与共用；极速以固化定值为先）

1. **确认写入目录。** 用户给出目标复现目录时，所有新文件、profile、runner、artifact 和验证命令都必须落在目标目录。用户另给的历史项目或文档路径只读；不得在参考项目运行 updater、替换 profile、改测试或留下新的采集目录。
2. **先搜同平台实现。** 仅在用户明确提供并授权的当前目标或参考目录中只读定位 runner/helper/profile；这些文件不属于本 skill，不能因文档提及其名称就假设它们存在。
3. **禁止无证据补浏览器环境。** 一旦开始给 Node/JS VM 广泛补 `Window`、`Element`、`Range`、`navigator`、`document`、`canvas`、`localStorage` 等环境，立即停止并回到当前目标的状态向量与已确认 helper 边界。
4. **profile 不能跨项目直接复制。** 当前目标必须用自己的 Init/Log2/Log3/Verify capture 生成动态状态；历史 profile 只可用于理解字段结构，不能直接进入交付。
5. **最短验收链由当前交付 Provider 定义。** 先通过固定向量和同轮状态证明 helper 边界；任何 live `T001 / true` 都必须在批准的 Python collector 中重新验证。

## 目标目录复现模式

### 默认：当前证据的离线证明

用户说「走极速分支」或未指定但任务为阿里 V2 复现时：

```text
历史候选定值仅进入受控的窄 helper 草稿
  -> 当前目标 capture 只采动态状态 / combat / host / scene
  -> 生成当前目标动态状态
  -> 固定向量回归 + 语义检查
```

### 可选：用户提供受控参考材料

仅当用户给出参考路径且当前阻塞点需要一个具体工件时：

```text
参考只读
  -> 只读检查一个与阻塞点直接相关的工件；不得复制历史实现到交付
  -> 密钥/field21/AES 只能作为候选，并以当前 capture 回归
  -> 禁止把历史 profile 当作当前目标正式状态
  -> 禁止在参考目录写文件
```

## 完整分支（协议恢复，极速失败或用户点名时）

从本节起至文末「错误分支与反模式」之前的协议细节（请求图、DeviceConfig、token、Log2/Log3、field21 经典族、data/arg VM、控制变量、固定向量全表）构成**完整分支**。

完整分支入口条件：

- 用户明确「走完整分支 / 从零 / 完整协议分析」
- 或极速硬停触发（无 runner、codec 真变、field21 骨架断裂等）

完整分支仍遵守：禁止无必要 jsdom、禁止把日更做成从零、禁止忽略同平台已有实现搜索。

## FeiLin/sg 日更快速分支（版本轮换与灰度发布）

当用户明确描述“阿里 V2 每天更新”“下午还能 T001，晚上变 F025”时，优先执行本分支。此时不要先改轨迹，也不要因为 `StaticPath` 变化就重提整套 VM。

### 1. 固定取证条件

1. 使用用户明确指定的浏览器和二进制；项目更新器固定 CloakBrowser 时只允许该 Cloak 二进制，不得静默切换普通 Chrome。用户指定 `js-reverse` 普通 Chrome 时，先确认 `browser_binary_info.cloak_active == false`。
2. 页面必须是用户给出的完整目标 URL，不能用首页或同源空白页代替；否则 URL、Referer、viewport 和资源字段会污染差分。
3. 清空 MCP 网络队列后再开始，保留页面 cookie，除非控制实验明确要求清理。
4. 纯协议入口、浏览器 Init、Log2、getToken 和 Verify 必须来自同一个目标、同一轮 challenge。

### 2. 先判定是哪一层更新

按以下顺序核对：

```text
DeviceConfig.version
  -> FeiLin 完整画像 / 稀疏 token
  -> field21 版本绑定
  -> FeiLin 资源自证字段
  -> Log3 511/504
  -> 动态 sg VM 字节码与 stream key
  -> 轨迹
```

不要用单次 Init 的版本与本地 profile 比较后立即定案。FeiLin 可能同时灰度下发相邻版本；单次命中新版本只说明该 cohort 存在，不代表它已经成为主流。

默认预检策略：

```text
收集 7 个成功的 Challenge + Init 版本样本
  -> 临时 HTTP/TLS 错误在独立尝试预算内重试
  -> 按版本出现次数选择目标 cohort
  -> 计数相同时选择 FeiLin 代数较新的版本
  -> 保存完整版本分布作为证据
```

若主流 `DeviceConfig.version == profile.feilinVersion`，画像仍是当前主流；此时偶发的 minority stale 不能触发覆盖。若主流版本不同，再把本地 profile 判为过期并进入更新。只有已有独立证据时才手工指定目标版本，不要为了追新强行选择少数 cohort。

### 3. 用户项目已有更新器时的审计边界

如果用户明确提供当前项目更新器，先审计它是否满足以下安全契约；本 skill 不提供更新器，也不在 skill 目录内运行外部脚本：

```powershell
# 仅在用户明确授权的目标项目目录中执行其更新器。
```

安全契约：

1. 版本相同时不启动浏览器，也不改 profile。
2. 只启动项目明确指定的取证浏览器。
3. 默认收集 24 个目标 cohort 的 Init/Log2/token 轮次；其他 cohort 原样归档并跳过，不混入推导，也不因一次跨版本立即中止。
4. 每个接受轮次都校验同 session、token checksum、133 字段和已知稀疏索引。
5. field21 使用训练样本推导、保留样本验证，不能用单向量猜常量。
6. 候选 profile 只在内存中注入现有纯协议入口；在线验收若命中其他 cohort，只重试 stale 轮次。
7. 只有 Log2/Log3 `200 / true` 且 Verify `T001 / true` 才加锁并用 `os.replace` 原子提升。
8. 失败时保留旧 profile，并把预检分布、全部采集尝试、候选和在线响应写入 `js_reverse_cache/`。

更新器成功后无需再走手工差分。更新器缺失、停止或暴露结构变化时，再执行下面的手工分支；不能用 `--force` 绕过验收。

### 4. 采集当前版本材料

在用户指定的取证浏览器中至少保存：

- Init 请求/响应，包含 `StaticPath` 和 `DeviceConfig`。
- FeiLin 与动态 `sg` 的最终脚本 URL。
- 浏览器自动发送的 Log2 请求。
- `window.um.getToken()` 的 token；必要时仅在取证页临时观察 133 项数组的 `join("#")` 输入。
- 一次人工或可信输入产生的 Log3 与 Verify。

自动采集必须只接受目标 cohort。若同一浏览器连续得到 FeiLin109、FeiLin110 等不同版本，按版本分别归档；非目标版本不计入 24 轮，不参与 field21 或稳定画像选择。

网络导出使用完整 request/response body，不要依赖列表页截断预览。

### 5. 自动解密并差分

使用本 Provider 的只读助手：

```powershell
python scripts/aliyun_v2_profile_diff.py `
  --init current_init.json `
  --log2 current_log2.json `
  --token current_token.json `
  --old-profile <projectRoot>/profile.json
```

脚本输出：

- 当前 FeiLin version、session、IP、Log2 GatherCost。
- 当前完整 133 字段画像。
- 当前稀疏 token 画像和 checksum 状态。
- 与旧 profile 的逐索引差分及已知字段角色。

### 6. 同浏览器版本控制实验

若环境变化导致差分太多，使用同一个用户指定浏览器、同一完整目标 URL 做旧/新 FeiLin 对照。只在诊断轮临时把新 FeiLin script URL 改写到旧 URL，采集旧脚本生成的 Log2/token；诊断结束立即恢复。该轮只能用于定位版本差异，不能作为最终 T001 样本。

同环境差分中优先关注：

- `21`：session 后缀绑定值，常随版本替换 source/mask 或等价混合逻辑。
- `52`：版本相关设备摘要，不能从另一浏览器直接复制到旧画像。
- `88`：Base64 能力位图，先解码再逐位比较。
- `117/118`：FeiLin script URL、resource timing 和脚本大小。
- Log2 与稀疏 token 共同非空的字段。

### 7. field21 更新方法

不要凭一个样本猜常量。连续取得至少 5 个当前版本 session：

```text
input  = session_id[-8:]
output = browser token/full profile field 21
```

先验证旧 classic 算法是否仍命中；不命中时，记录多个固定向量，再定位 field21 写入点或拟合当前可打印字符混合。新算法必须同时用于 Log2 完整画像和 Verify 稀疏 token。

**分支（别把“换版本”当成永远只换常量）：**

```text
classic source/mask 多样本有唯一解  → 写 field21.sourceKey + xorMaskHex
classic 穷举无解 / holdout 失败     → 算法换代，停止更新器硬拟合
  → 跟写入点，或多样本做按字节/分段映射
  → profile 可写 field21.algorithm，实现落在项目 verifier
  → 固定向量 + Log2/token 同算子 + 在线 T001 后再落盘
```

更新器只覆盖已知家族轮换；骨架断裂后的新算法要单独分析进项目代码，不要在 skill 里为每个 FeiLin 代数维护长表。

已验证 classic 版本参数（示例，非穷尽）：

```text
FeiLin106:
  source = 68fded68
  mask   = 31f79ddc

FeiLin107:
  source = cccccccc
  mask   = 0000000000000000 (8 个零字节)

FeiLin108:
  source = ========
  mask   = 072e8290

FeiLin109:
  source = 6b2f51d0
  mask   = 072e8290

FeiLin110:
  source = }}}}}}}}
  mask   = 0000000000000000 (8 个零字节)

FeiLin111:
  source = hhhhhhhh
  mask   = fde95c04  (ASCII 8 字节)

FeiLin112:
  source = """"""""
  mask   = 0eb971e9  (ASCII 8 字节)
```

这里的 `072e8290` / `fde95c04` / `0eb971e9` 都是 8 个 ASCII mask 字节；JSON profile 中分别保存为十六进制 `3037326538323930`、`6664653935633034`、`3065623937316539`。FeiLin110 参数已通过 24 样本推导、holdout 和在线 T001 验证，零 mask 在 JSON 中保存为 `0000000000000000`。FeiLin111 参数已通过 12 样本全量拟合与在线 T001 验证；该版本 field 52/88 为轮次本地值，稳定画像比较时应忽略。FeiLin112 的部分采样位置可能因十六进制 suffix 覆盖不足出现等价候选；只有当多样本显示唯一 shared-source 家族，并且候选 profile 在线 `Log2/Log3 200 true + Verify T001 true` 后，才可采用上述参数。

107 固定向量：

```text
e7f61587 -> SXpKeXR4e3o=
2f894218 -> dUp7fHd1dHs=
```

### 8. 动态 sg 不要靠文件名猜

`sg.001`、`sg.029` 等路径轮换不等于 codec 或 key 已变。对当前脚本：

1. 提取最小 VM bytecode/constants，对旧 helper 做固定输入输出比较。
2. 在 VM stream 调用点断住，读取运行时参数数组 `[compressed, key]`。
3. 只有 VM 输出或运行时 key 真正变化时，才更新 helper/key。

已验证的 106 -> 107 案例中，stream VM 与 key `3e627e1b4c63f913` 均未变化；故障来自 FeiLin 画像版本，不是 sg。

### 9. profile 必须整套更新

禁止只替换 `field21` 或 FeiLin URL。完整画像中的摘要、能力位、UA/Client-Hints、屏幕、GPU、资源信息存在交叉一致性；从新浏览器抄一个字段进旧浏览器画像仍可能返回 `F025`。

正确做法：

1. 保存当前浏览器完整 Log2 画像。
2. 保存同一浏览器的稀疏 token，或从完整画像按当前非空索引生成稀疏模板。
3. profile 写入精确 `feilinVersion`、UA、field21 参数和 133 字段。
4. 程序收到未知 version 时 fail fast，提示刷新 profile，不发送猜测 Verify。
5. 先跑离线 profile/field21/token 测试，再做在线 Verify。

### 10. 日更完成标准

必须同时满足：

```text
当前 DeviceConfig.version == 本地 profile.feilinVersion
Log2 == 200 / true
Log3 == 200 / true
VerifyCode == T001
VerifyResult == true
```

若完整当前 profile 可 `T001`，而旧/新混合 profile 固定 `F025`，即可确认是版本画像更新；不要再把失败归因到轨迹。

在线验收处于灰度期时，候选 profile 可能在某轮 Init 命中其他 cohort 并 fail fast。该轮应归类为 rollout mismatch 后重试，不能直接判定候选算法失败；其他网络错误也应与协议拒绝分开记录。

### 11. 自动化停止边界

以下任一变化都超出普通日更，必须停止、保留旧 profile，并转入当前版本重新分析：

- DeviceConfig AES key、padding 或字段布局不再匹配。
- 完整画像或稀疏 token 不再是 133 字段，或稀疏非空索引出现未知变化。
- token envelope、checksum、Log2/Log3 签名或加密结构变化。
- field21 已知 classic 公式无法得到唯一参数，或 holdout 不通过（含骨架换代）。
- 动态 sg VM 固定输入输出或运行时 key 真正变化。
- 候选在目标 cohort 上不能同时得到 Log2/Log3 `200 / true` 和 Verify `T001 / true`。

更新器负责已知算法家族内的画像与参数轮换，不是通用算法逆向器。field21 骨架断裂时停在更新器外做分析，把可跑实现写回项目后再纳入已知家族。灰度期间，仍只支持单 profile 的纯协议 runner 偶尔命中 minority cohort 时会按设计 stale；要同时支持多个 cohort，必须明确修改 runner 的版本到 profile 映射，不能靠更新器覆盖同一个文件解决。

### 12. 历史实证（2026-07-19，非当前验收）

历史样本摘要（不构成当前验收）：

```text
预检             = FeiLin109 7/7
目标采集         = FeiLin109 24 轮
跳过并归档       = FeiLin110 3 轮
field21 source   = 6b2f51d0
field21 mask     = 072e8290
在线更新器验收   = T001 / true
独立磁盘 runner  = T001 / true
```

历史记录中，候选状态只在在线验收后替换；不同轮次分别出现 rollout mismatch、TLS EOF 和目标 cohort 成功。这三类结果只能用于说明分类方法，不能证明当前目标状态仍然有效。

### 13. TLS EOF 传输层处理

若看到 `requests.exceptions.SSLError`、`SSLEOFError` 或 `Max retries exceeded`，先确认 DNS 与 TCP 443，再检查实际 HTTP 客户端。标准 `requests` 能偶尔成功不代表 TLS 路径稳定；同一项目中 README 声称使用 `curl_cffi`、但 runner 又把普通 `requests.Session` 传给 Verify，是应优先修复的实现不一致。

正确处理：

1. Challenge、Init、Log2、Log3、Verify 统一使用同一个 `curl_cffi` 浏览器 TLS session，并显式保持项目 UA。
2. 只把 DNS、连接、timeout、TLS EOF 归为可重试传输错误。
3. 传输失败后丢弃整个 challenge/session，重新开始一轮；不要重放可能已经到达服务端的同一个 Verify。
4. profile stale、HTTP 业务响应、F001/F025 和非 T001 结果不得被传输重试吞掉。
5. 保留有限重试预算；预算耗尽后输出最后一个传输异常。

### 14. FeiLin110 稳定画像变化与失败续跑

FeiLin110 成为 7/7 主流后，24 个有效轮次只有字段 `52` 在每轮变化，其他稳定字段完全一致。字段 52 是该版本新增的 round-local 摘要，因此只对 FeiLin110 的稳定签名排除它；候选 profile 仍保存代表轮真实值，且必须经过在线 T001，不能全版本忽略字段 52。

默认最大采集尝试数应根据预检目标 cohort 占比估算，并保留约 25% 余量；24 轮且目标 7/7 时使用 32 次上限，不应显示固定 96。上限不是必跑轮数，收齐 24 轮立即停止。

若采集已完成但后续稳定性、field21 或在线验收失败，保留完整 artifact 并提供 `--resume-artifact PATH` 续跑，避免重新启动浏览器和重复采集。该案例复用原 24 轮后恢复：

```text
field21 source = }}}}}}}}
field21 mask   = 8 zero bytes
Verify         = T001 / true
CertifyId      = ac11000117844625766162970e00cc
```

随后同 session 追加 `u_atoken=requestInfo.token`、`u_asig=CertifyId` 请求业务接口，返回 JSON `status="1"` 和 20 条结果，证明验证码与业务门禁均通过。

## 第一步：建立完整请求图

按同一轮 session 固定以下请求：

```text
challenge page
  -> InitCaptchaV2
  -> Log2
  -> Log3
  -> VerifyCaptchaV2
```

不要在只看到 Init 和 Verify 后就开始轨迹调参。设备日志域通常是独立域名，容易被误认为无关埋点。

至少保存：

- challenge 页和结构化 `requestInfo`
- Init 请求/响应
- DeviceConfig 原文和解密结果
- FeiLin 原始脚本、格式化脚本、动态 sg 脚本
- Log2/Log3 完整 form body 和响应
- Verify 完整 form body 和最终响应
- 一轮人工 `T001` 正样本
- 一轮有意阻断 sidecar 的对照样本

## 第二步：确认成功标准

阿里 V2 的成功标准是：

```text
Success == true
Result.VerifyCode == "T001"
Result.VerifyResult == true
```

以下状态都不能单独视为通过：

- HTTP 200
- 顶层 `Code == "Success"`
- Log2/Log3 `Code == "200"`
- Log2/Log3 `ResultObject == true`

## 第三步：主 RPC 签名

主验证码接口和设备接口都采用阿里 RPC HMAC-SHA1：

```text
canonical = sort(params without Signature)
StringToSign = "POST&%2F&" + percent_encode(canonical_query)
Signature = Base64(HMAC-SHA1(secret + "&", StringToSign))
```

编码必须符合 RFC 3986，`safe=-_.~`。先用捕获包做固定输入回归，再发送动态请求。

主接口和设备接口使用不同 AccessKey，不要混用。

## 第四步：DeviceConfig

FeiLin 1.4.2 已验证样本使用：

```text
AES-CBC
key = 87f879f135f27da7
iv  = 0123456789ABCDEF
padding = PKCS7
```

明文是 `#` 分隔字段，常见布局：

```text
Base64(session AES key)
Base64(switch)
session_id
FeiLin version/path
plugin elements
plugin resource
global variable
server timestamp
IP
optional extension
```

这些常量和字段布局是 bundle 版本相关材料。新目标必须先用当前响应验证 AES padding、字段数和 Base64 内容。

## 第五步：deviceToken

外层：

```text
Base64("WEB#session_id#payload_ciphertext#counter#checksum")
```

内部：

- payload 使用 DeviceConfig 的 session AES key。
- IV 为 `0123456789ABCDEF`。
- 明文是 133 个 `#` 分隔字段。
- checksum 常见为：

```text
MD5("WEB#session_id#payload_ciphertext#counter#daye,raolewoba!")
```

先实现 parse/decrypt/verify-checksum/rebuild 四个函数，并要求捕获 token 往返完全一致。

### 完整画像与稀疏增量

FeiLin 会先在 Log2 上传完整 133 字段画像，Verify token 再上传稀疏增量。必须保持：

- 相同 session_id 和 session AES key
- 相同 field 21
- 相同 IP
- 相同采集起点字段
- 相同初始 telemetry 项
- token counter 与 Log2 `GatherCost` 对齐
- Verify 阶段只更新应变化的时间、certifyId 和行为项

若两份 payload 分别随机生成，即使都能解密且 checksum 正确，也可能返回 `F025`。

## 第六步：field 21

FeiLin 1.4.2 常见 **classic** 算法（多代数只换 source/mask）：

```text
source = 68fded68
mask   = 31f79ddc
suffix = session_id[-8:]
```

```python
mixed = bytes(
    32 + ((ord(a) - 32 + ord(b) - 32) % 95)
    for a, b in zip(source, suffix)
)
field21 = base64.b64encode(
    bytes(x ^ ord(m) for x, m in zip(mixed, mask))
).decode()
```

固定向量：

```text
983c7551 -> fGEff0UdLyo=
d4797207 -> SX0bSkUSIiw=
```

如果当前 bundle 固定向量不一致：先多样本验 classic；仍不一致时重新跟 field 21 写入点，不要继续套旧常量。
若 classic 逐字节穷举已无解，按上文“算法换代”分支处理；profile 可挂 `field21.algorithm`，实现以项目 `verifier` 为准（例如某代出现的分段映射），skill 不维护逐日版本表。

## 第七步：arg 与滑动 data

动态 `sg.xxx` 路径会变化，但多个路径可能共享同一 VM codec。先做以下固定输入实验：

1. 捕获 `arg` 入口输入、key、输出。
2. 捕获 `data` 入口输入、key、输出。
3. 比较两个入口是否调用相同 VM/stream 函数。
4. 更换 sg 路径后复测同一固定输入。

常见结构：

```text
arg_input = CertifyId
arg_key   = 16 位小写字母数字

data_input = Base64(zlib(nonce + compact_track_json))
nonce      = 32 位小写十六进制
data_key   = 16 字节 stream key
```

如果只需保留纯数学 VM helper，明确检查它不读取 DOM、navigator、canvas、storage 或 cookie。

## 第八步：Log2/Log3 sidecar

### 设备 RPC 已验证材料

FeiLin 1.4.2 样本：

```text
endpoint    = https://device.captcha-open.aliyuncs.com/
AccessKeyId = REDACTED_ALIYUN_AK
secret      = REDACTED_ALIYUN_SK
Version     = 2020-10-15
upload key  = a549a55c60a39aa0
iv          = 0123456789ABCDEF
```

这些值来自客户端公开 bundle，但仍必须视为版本相关并用捕获签名复核。

### 公共 record

```text
Base64(
  session_id
  # AES_config(payload)
  # AES_config("saf-captcha-waf")
  # AES_config("W.10051")
  # ""
  # AES_config(timestamp_ms)
)
```

### 外层 Data

外层明文：

```text
session_prefix
# W
# AES_config("W.10051#saf-captcha-waf#sceneId")
# W20220202
# CLOUD
# GatherCost
# event_data
```

然后使用 upload key 做 AES-CBC/PKCS7 并 Base64。

### Log2

```text
Action = Log2
event_data = 501#Base64(full_133_fields_record)
```

Log2 的完整画像应更新当前 session/IP/timestamp，不要原样重放旧密文。

### Log3

```text
Action = Log3
combat = 511#Base64(status_record)-504#Base64(combat_json_record)
event_data = Base64(combat)
```

504 JSON 常见字段：

```json
{
  "mousemove": [],
  "mouseclick": [],
  "keyup": [],
  "scrollTop": [],
  "scrollLeft": [],
  "clientType": "desktop",
  "startTime": 0,
  "timestamp": "0"
}
```

重映射行为时必须保证最后事件不晚于 Log3/Verify 的真实发送时间。

## 第九步：控制变量诊断

人工能滑过而纯协议 `F001` 时，不要立刻重写轨迹。按以下矩阵隔离：

1. 浏览器人工轨迹 + 允许全部设备请求。
2. 同一人工用户 + 仅阻断设备日志域。
3. 纯协议 + Log2 only。
4. 纯协议 + Log2/Log3。
5. 同 session 比较完整画像和增量 token 解密字段。

若阻断设备域后人工轨迹也从 `T001` 变为 `F001`，可以证明 sidecar 是必要变量。

## 第十步：错误码分层

以下结论来自历史样本，应作为诊断候选而不是当前目标或全局文档定义：

- `F025`：优先检查 DeviceConfig、session、token envelope、checksum、完整画像/增量一致性。
- `F001`：结构通过后的风险拒绝；先确认 sidecar，再检查轨迹和时序。
- `T001`：最终通过。

推荐排查顺序：

```text
challenge/Init
  -> DeviceConfig
  -> Log2 full profile
  -> Log3 sidecar
  -> sparse deviceToken consistency
  -> arg/data VM
  -> VerifyCode
```

## 固定向量要求

至少建立以下测试：

- 主 RPC signature 与捕获包一致。
- 设备 RPC signature 与捕获包一致。
- DeviceConfig 解密字段数和 session key 长度。
- deviceToken decrypt/rebuild 完全一致。
- field 21 固定向量。
- arg 固定输入输出。
- data 固定输入输出。
- Log2 整包 SHA256。
- Log3 整包 SHA256。
- 在线 Verify 返回 `T001`。

## 交付检查

- [ ] 入口 GET 的 headers 已按真实页面验证，未把某个 Referer 例外扩散到全链路。
- [ ] Init、Log2、Log3、Verify 保持同一轮状态。
- [ ] Log2 完整画像与 token 稀疏增量共享基线。
- [ ] 轨迹声明耗时与真实等待一致。
- [ ] HTTP 由 Python 发出，浏览器不在运行依赖中。
- [ ] 用户只做验证层时没有业务接口回放。
- [ ] 最终证据是 `T001 + VerifyResult=true`。

## 错误分支与反模式（必须避开）

以下来自历史失败记录：目标被正确识别为阿里 V2，但执行路径把画像更新误做成了从零协议恢复。它只说明应先定位变化层，不能替代当前目标证据或授权。

### 错误分支长什么样

```text
错误分支（慢、重复劳动）:
  从零拼 RPC / DeviceConfig / token / Log2 / Log3
  → 大量浏览器自动化拖滑块、CDP 重放轨迹
  → StaticPath/sg 文件名一变就重猜 data 算法（RC4/AES/手写 stream）
  → 几小时后才发现用户项目已有前一轮可用实现与状态材料

正确分支（默认 = 当前证据驱动，不是从零猜测、不是抄历史参考）:
  用户说「走极速分支」
  → 候选事实 + 当前目标动态状态 + 当前交付实现 → fresh 语义验收
   当前目标出现上一轮成功与本轮失败，且用户已提供实现
  → 先比 DeviceConfig.version 与 profile.feilinVersion
  → 有用户提供的更新器则先审计；只在当前证据支持时更新动态状态与 field21
  → 固定输入核对 sg codec/key 是否真变
  → 纯协议 runner 验收 T001
  仅当极速定值冲突或用户要从零
  → 进入完整分支做协议恢复
```

### 禁止事项

1. **禁止在用户已提供可跑通 V2 项目时从零重写协议。** 先只读确认其 runner/helper/profile 契约，再决定当前目标需要适配还是重建；历史项目代码不得直接复制进交付，也不得修改用户指定的参考路径。
2. **禁止把 FeiLin 版本号上升当成“整条链失效”。** `DeviceConfig.version` 与历史成功样本并存时，先判断画像/field21/资源自证层是否变化，不要直接重做 RPC、Log 封装或 sg 算法；当前目标仍需重新取证。
3. **禁止 `StaticPath` / `sg.xxx` 文件名轮换就重提 VM。** 多个脚本路径可能共享同一 stream codec 与 key。先对当前已确认 helper 做固定输入输出比较；只有输出或运行时 key 真变才更新实现。
4. **禁止用长时间滑块 UI 自动化替代协议日更。** 浏览器只用于取证、人工 T001 正样本、更新器采集。合成 PointerEvent、CDP 拖滑块、反复“帮用户拖到底”不是交付主路径；用户已提供人工 T001 或已有更新器时，应立刻回到 profile/field21/data codec 对齐。
5. **禁止忽略 skill 核心规则第 8 条。** 动手重写前必须先搜用户授权的同平台实现、当前 case bundle 和候选事实；复用后仍须用当前 Init/Log2/Verify 结果复核，不能盲信历史 profile、key 或 field21 家族。
6. **禁止只改 field21 或只抄单个新字段进旧画像。** 必须整套更新完整 Log2 133 字段、稀疏 token 拓扑、UA/能力位/FeiLin URL 与 `feilinVersion`；候选须先内存验收 Log2/Log3 `200/true` 且 Verify `T001/true`，再原子替换。
7. **禁止把 `F017`/`F001`/`F025` 一上来归因轨迹。** 分层：`F025` 先查 session/画像/token 一致性；sidecar 缺失先查 Log2/Log3；`data`/arg 固定向量失败再动 codec；结构都通仍风险拒绝才调轨迹。错误分支里在 sidecar 与 data codec 未对齐前烧时间拖滑块，属于诊断顺序反了。
8. **禁止用户只要验证层时把业务接口回放写进成功条件。** 成功证据停在 `T001 + VerifyResult=true`。

### 开跑前自检（日更/已有项目场景）

进入阿里 V2 任务且存在任一条件时，必须先做本自检，再写新代码：

- 用户说“昨天还能 T001 / 版本到了 FeiLin11x / 更新进去”
- 用户给出已成功项目路径或邻目录存在同类结构
- 用户明确提供当前项目实现或更新器

自检清单：

```text
[ ] 是否已只读定位用户授权的同平台 runner / helper / profile / updater 契约
[ ] 是否已用多样本看 DeviceConfig.version 分布，而不是单次 Init 定案
[ ] 是否先审计用户提供的更新器，而不是假设 skill 内存在 runner
[ ] 是否确认 sg codec 固定输入输出与 stream key 未变，才考虑重提 VM
[ ] 浏览器是否仅用于取证/更新器采集，而不是交付依赖
[ ] 是否整套 profile 验收 T001 后再替换，而不是只改 field21
```

任一答案为“否”且仍在从零解协议、自动化拖滑块、猜 `data` 加密：立即停止，回到正确分支。
