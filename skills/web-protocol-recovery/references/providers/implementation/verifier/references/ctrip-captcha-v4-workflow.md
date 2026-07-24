# Ctrip captcha/v4 Workflow

携程登录页等场景可能使用自研 `captcha/v4` 风控验证。它不是极验、易盾、数美、云片或 360 天御；不要套第三方字段。常见链路是 `risk_inspect -> verify_jigsaw -> verify_icon`，也可能在 `risk_inspect` 阶段直接返回 `NONE` 放行。

## 适用信号

1. 请求域名和路径包含 `https://ic.ctrip.com/captcha/v4/`。
2. 出现 `risk_inspect`、`verify_jigsaw`、`refresh_jigsaw`、`verify_icon`。
3. 请求字段包含 `appid`、`business_site`、`version=1.0.6`、`dimensions`、`extend_param`、`verify_msg`、`sign`、`token`、`rid`。
4. 响应结构为 `code/message/result/risk_info`，`risk_info.process_type` 可能是 `NONE`、`JIGSAW`、`ICON`。
5. 图片字段可能是 `original_image`、`processed_image`、`jigsaw_image`、`big_image`、`small_image`。

## 请求链

1. `POST /captcha/v4/risk_inspect`
   发送 `appid/business_site/version/dimensions/extend_param/sign`。
2. 如果返回 `risk_level=0`、`process_type=NONE`，验证码链已通过。
3. 如果返回 `process_type=JIGSAW`，保存同轮 `token/rid/original_image/processed_image/jigsaw_image`。
4. 识别滑块缺口，提交 `POST /captcha/v4/verify_jigsaw`。
5. 如果 `verify_jigsaw` 后返回 `NONE`，验证通过。
6. 如果返回 `process_type=ICON`，保存同轮 `token/rid/big_image/small_image`。
7. 识别图标点选顺序和坐标，提交 `POST /captcha/v4/verify_icon`。
8. 最终必须以服务端 `risk_level=0`、`process_type=NONE` 为成功标记。

同一套本地模板连续调用时，`risk_inspect` 可能一轮返回 `NONE`，下一轮返回 `JIGSAW`。脚本必须按实际 `process_type` 分支，不能假设每次都会出现图片验证，也不能为了“拿图”把 `NONE` 当失败。

## 加密与签名

字段 `dimensions`、`extend_param`、`verify_msg` 是 AES-CBC 加密后的文本，再 URL encode。

已验证参数：

1. AES key hex: `8f235bc1cac17a46530c616ff234be78`
2. AES IV hex: `69783956775867344e5853626b645431`
3. Padding: PKCS7
4. 输出：Base64 ciphertext
5. 自检样本：明文 `{"a":1}` -> `dgTCfwitC8GOAvZgYUI3gA==`

`sign` 是固定顺序参数串的 MD5 hex。

`risk_inspect` 签名顺序：

```text
appid=<appid>&business_site=<business_site>&version=<version>&dimensions=<raw_dimensions>&extend_param=<raw_extend_param>
```

`verify_jigsaw` 签名顺序：

```text
appid=<appid>&business_site=<business_site>&version=<version>&verify_msg=<raw_verify_msg>&dimensions=<raw_dimensions>&extend_param=<raw_extend_param>&token=<token>&captcha_type=JIGSAW
```

`verify_icon` 签名顺序：

```text
appid=<appid>&business_site=<business_site>&version=<version>&verify_msg=<raw_verify_msg>&dimensions=<raw_dimensions>&extend_param=<raw_extend_param>&token=<token>&captcha_type=ICON
```

注意：这里参与 MD5 的是未 URL encode 的 Base64 字符串；请求体里再对这些字段做 URL encode。

### 两套 dimensions

不要假设 `risk_inspect` 与 `verify_jigsaw/verify_icon` 的 `dimensions` 密文相同。

1. loader 在 `risk_inspect` 前组装一次浏览器信息对象并加密为 `dimensions`。
2. captcha main 脚本初始化后会再次组装浏览器信息对象，验证阶段使用这份新 `dimensions`。
3. 两份对象字段相近，但运行时间、页面状态或采集值可能不同；成功样本中两份密文并不相等。
4. 本地模板应分别保存 `risk_dimensions_plain` 和 `verify_dimensions_plain`，各自做解密、重加密和签名回归。
5. `extend_param` 常是 `resolution_width/resolution_height/language` 这类较小对象；验证阶段仍会重新序列化和加密，不要只按字段名猜测明文用途。

## 非标准 JSON

页面使用类似 `__sJSON.stringify` 的序列化，可能保留 `undefined` 字面量。Python 标准 `json.dumps` 会把它改成 `null` 或无法表示，导致固定输入回归失败。

处理方式：

1. 本地实现 JS 风格紧凑序列化。
2. 明确支持 `undefined` 字面量。
3. 对手动成功样本做固定输入回归：重新加密 `verify_msg/dimensions/extend_param` 后必须和浏览器请求逐字节一致，`sign` 也必须一致。

实测 `verify_msg` 中可能存在 `"cpuClass":undefined`。通过普通 `JSON.stringify`、CDP JSON 导出或 Python JSON 保存运行时对象时，这个键可能被直接丢弃。应以解密后的真实 `verify_msg` 明文为准，并在 Python 中使用显式 `UNDEFINED` sentinel 按原字段顺序序列化。

## JIGSAW 滑块

图片字段：

1. `original_image`: 原图，通常 `300x150`。
2. `processed_image`: 带缺口图，通常 `300x150`。
3. `jigsaw_image`: 滑块图，常见 `41x148` 或类似尺寸。

坐标识别优先路线：

1. 对 `original_image` 与 `processed_image` 做 `absdiff`。
2. 灰度、模糊、阈值、形态学闭运算。
3. 取合理轮廓的 `x` 作为提交 `value`。
4. 记录候选图、mask 图和最终 `value`。

图片不一定是传统拼图缺口，也可能是纸飞机等透明异形块：`processed_image` 中出现白色轮廓，`jigsaw_image` 保存对应原图内容。此时仍优先使用原图/处理图差分，不要强行套矩形缺口模型。

JPEG 边缘会受压缩噪声影响。一个稳定做法是：

1. 用较高阈值和形态学操作找到差异核心轮廓。
2. 在核心轮廓附近的小 ROI 内使用较低阈值做连通域细化。
3. 选择与核心轮廓重叠最大的连通域，取其最左侧 x 作为最终 `value`。
4. 同时保存高阈值核心 x 与细化后的 value，避免靠固定减数校准。

Windows 项目路径包含中文时，OpenCV 4.x 的 `cv2.imread/cv2.imwrite` 可能无法打开文件。使用 `np.fromfile + cv2.imdecode` 读取，使用 `cv2.imencode(...).tofile` 写入。

行为字段要和坐标一致：

1. `value`: 缺口 x 坐标，使用背景图提交坐标系，不是页面绝对坐标。
2. `slidingTrack`: 页面鼠标坐标列表，通常不等于 `value` 本身。
3. `preJigsawSlidingTrack`: 滑动前鼠标轨迹。
4. `slidingTime`、`jigsawViewDuration`: 需要接近人工样本，过短容易触发升级。

坐标映射要读取当前响应的 `param.size`。常见背景图是 `big_width=300`，SDK 行为字段却使用 `jigsawPicWidth=320`。因此：

1. `value` 使用 300 宽背景图坐标。
2. 页面滑动轨迹的水平位移约为 `value * 320 / 300`，再叠加滑块起点的页面绝对坐标。
3. 不要把 `slidingTrack` 的终点 x 或页面位移直接当作 `value`。
4. 手工成功样本中 `value=197` 时，页面轨迹水平位移约为 211px，符合 300 到 320 的缩放。

### 时间一致性

行为时间必须形成真实、单调且已结束的时间线：

1. `st` 是按下滑块开始拖动的时间，不是发送请求的时间。
2. `jigsawSlidingTrack[*].t` 应位于 `st` 到 `st + slidingTime` 范围内。
3. 最后一条轨迹时间不能晚于实际 `verify_jigsaw` 请求发送时间。
4. `jigsawViewDuration` 应接近从风险响应/验证码展示到提交的真实耗时；纯 requests 流程需要真实等待，而不是只在 JSON 中伪造较大时长。
5. 已验证失败模式：风险响应后立即请求，同时生成“未来时间戳”轨迹，会得到新的 `JIGSAW`；等待约 3 秒并让轨迹在请求前结束后，同类流程可返回 `NONE`。

失败后可能返回新的 `JIGSAW`，也可能升级到 `ICON`。新的 `JIGSAW` 响应会带新的 `token/rid/图片`，旧状态立即作废；保存失败响应后，必须整套替换状态，不能只换图片或继续提交旧 token。同一轮失败后不要无限扫坐标。

## ICON 图标点选

图片字段：

1. `big_image`: 背景图，常见 `300x150`。
2. `small_image`: 提示顺序图，常见 `95x20`。

坐标识别路线：

1. 把 `small_image` 放在上方，`big_image` 放在下方，拼成干净的识别图。
2. 不要额外写英文或中文提示，避免干扰打码接口。
3. 使用通用图标点选识别服务时，传 `direction=top`、`click_num=3`。
4. 将识别返回坐标减去 `big_image` 在拼接图中的偏移，得到背景图坐标。
5. 组装 `value=[x1,y1,x2,y2,x3,y3]`。

云码 `jfbym` 可用字段：

```json
{
  "token": "...",
  "type": "30332",
  "image": "base64",
  "direction": "top",
  "click_num": "3"
}
```

必须保存：

1. 云码原始响应。
2. 拼接图。
3. `big_offset/small_offset` meta。
4. 映射后的 `icon_points`。
5. `verify_icon` 请求和响应。

行为字段不能只改 `value`：

1. `preIconClickTrack` 要落在屏幕范围内，不能出现如 `x=1633` 这类超屏坐标。
2. `iconClickTrack` 和 `selectMoveTrace` 要按当前云码坐标重建。
3. `selectMoveTime` 要与移动轨迹时间差一致。
4. `inputStartTs/inputEndTs/inputTime/iconViewDuration` 要和轨迹时间匹配。

## 成功标记

成功响应示例：

```json
{
  "code": 0,
  "message": "Success",
  "result": {
    "risk_info": {
      "risk_level": 0,
      "process_type": "NONE"
    }
  }
}
```

不要把 `code=0` 单独视为成功。失败、刷新、升级 ICON 也可能返回 `code=0`。

## 调试排查

1. `process_type=NONE`: 已通过，无需继续提交。
2. `verify_jigsaw` 后返回 `ICON`: 不是滑块接口错误，而是两段式验证，进入 `verify_icon`。
3. `ICON` 坐标识别成功但仍失败：先检查坐标是否映射回 `big_image` 坐标，再检查 `preIconClickTrack` 是否超屏、`iconClickTrack/selectMoveTrace` 是否仍复用旧样本。
4. 固定输入回归通过但 live 失败：优先怀疑轨迹/时长/坐标，不要先改 AES 或 MD5。
5. 连续失败会提高风控，可能每轮都升级 ICON；脚本应能重新开新会话或完成 ICON 分支。
6. `verify_jigsaw` 返回 `code=0` 但仍是 `JIGSAW`：这是刷新/失败，不是通过。检查 solver 坐标、300/320 映射、`st/slidingTime`、轨迹最后时间与真实等待。
7. risk 阶段重加密和签名通过、verify 阶段始终刷新：检查是否误把 risk 的 `dimensions` 密文直接复用于 verify。

## 推荐回归层级

1. AES 已知向量通过。
2. 三类密文解密后重新加密，与浏览器密文逐字节一致。
3. risk 和 verify 的 MD5 sign 都与浏览器一致。
4. 自定义 serializer 生成的 `verify_msg` 明文与解密明文一致，包含 `undefined`。
5. 图片 solver 输出与手工成功样本 value 一致。
6. 浏览器手工样本的服务端响应为 `risk_level=0/process_type=NONE`。
7. 最后新建一轮纯协议 live 请求；这是验证坐标、轨迹、时间和状态机是否一起正确的最强证据。

## 交付清单

1. `risk_inspect`、`verify_jigsaw`、`verify_icon` 的请求/响应样本。
2. AES/MD5 helper 和固定输入回归脚本。
3. 滑块缺口识别脚本及 debug 图片。
4. ICON 拼接图、云码响应、偏移映射和 `verify_icon` 交换文件。
5. 最终服务端 `risk_level=0/process_type=NONE` 响应证据。
