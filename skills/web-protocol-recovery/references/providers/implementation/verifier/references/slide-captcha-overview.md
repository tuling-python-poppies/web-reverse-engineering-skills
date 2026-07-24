# Slider Captcha Overview
把验证码滑块任务按平台分流到同一个执行框架：先识别平台，再复现请求链，再生成动态参数，最后验证整轮结果。

## 触发条件

出现任一信号时使用本 Provider：

1. 极验 GT3：`register-slide`、`gettype.php`、`fullpage.9.x`、`slide.7.x`、`apiv6.geetest.com/get.php`、`api.geevisit.com/ajax.php`、`$_BCm`、`GeeTestAjaxUser`、`bg/fullbg/slice/c/s`、最终 `validate/seccode`。
2. 极验 GT4：`captcha_id`、`lot_number`、`pow_detail`、`payload`、`process_token`、`/gcaptcha4.geetest.com/load`、`/verify`、`w`、`pow_msg`、`pow_sign`。
3. 腾讯滑块：`TDC`、`getData(true)`、`TCaptcha`、`slide.js`、`drag_ele.html`、`__TENCENT_CHAOS_VM`、`cap_union_prehandle`、`cap_union_new_verify`、`collect`、`eks`。
4. 网易易盾：`NECaptcha`、`c.dun.163.com/api/v3/get`、`/api/v3/check`、`cb`、`data`、`token`、`front/bg`、`yidun`、`dun.163.com/trial/jigsaw`。
5. 数美滑块：`captcha1.fengkongcloud.cn/ca/v1/register`、`/ca/v2/fverify`、`captchaUuid`、`rid`、`fg/bg`、`sm.js`、`get_params.js`、`ww/bb/vj/hq/wi/gq/vs`。
6. 云片滑块：`captcha.yunpian.com/v1/jsonp/captcha/get`、`/captcha/verify`、`captchaId`、`ypjsonp`、`yp_riddler_id`、`yp.js`、`i/k/cb`、`distanceX`、`points`。
7. 360 天御：`captcha.jiagu.360.cn/api/v3/auth`、`/api/v3/check`、`360CaptchaSDK`、`dc1db94ea7b3843c`、`captchaId`、`k`、`report`、`tracking`、`decryptImage`、`rsa_1.js`。
8. 顶象/鼎象滑块：`captcha.vivo.com.cn`、`/api/a`、`/api/p1`、`/api/p2`、`/api/v1`、`dingxiang-sdk.js`、`greenseer.js`、`const-id.js`、`_dx.UA.init`、`sendSA`、`sendTemp`、`getUA`、`_dx_app_*`、`_dx_captcha_vid`、`_dx_uzZo5y`、`ac=s_v3#...`、`4012 POSITION_MISMATCH`、`4011 HIGH_RISK`。
9. 字节系 VerifyCenter：`rmc.bytedance.com/verifycenter/captcha/v2`、`verify.zijieapi.com/captcha/get`、`/captcha/verify`、`captchaBody`、`cyfreso`、`captcha.wasm`、`bdms.js`、`mssdk/web/r/token`、`xx-tt-dd`、`msToken`、`a_bogus`。
10. 百度 Passport 旋转：`passport.baidu.com/cap/init`、`/cap/style`、`/cap/img`、`/cap/log`、`spin-0`、`backstr`、`ext.p`、`en_conf`、`mkd_v2.js`、`work.js`、`cv=submit`、`typeid=spin-0`、响应 `data.op`。
11. 用户要把滑块验证码链路做成本地 Python/Node 脚本，包含图片缺口、轨迹、加密参数和 verify/check 请求。

不要在这些场景使用本 Provider：

1. 只做图片缺口识别，不做验证码协议或动态参数。
2. 只要浏览器 hook 脚本，转 web-protocol-recovery 内部 `browser-hooks` Provider。
3. 只泛化定位某个 sign/token 入口，转正常 evidence/recon 路由，不进入验证码协议分支。
4. 只做通用 Node.js 补环境，转 web-protocol-recovery 内部 `env-patch` Provider。
5. 明确要求 Python + iv8 跑完整浏览器 JS 并请求接口，转 web-protocol-recovery 内部 `iv8` Provider；验证码状态机仍由 `verifier` 接收验收。

## 总体流程

1. 先确认平台：GT3、GT4、腾讯 TDC、网易易盾、数美、云片、360 天御、顶象/鼎象、字节 VerifyCenter 不要混用字段和算法。
2. 固定同一轮会话：`load/get/prehandle` 返回的 token、payload、sess、图片、POW 配置必须和后续 verify/check 同轮使用。
3. 优先动态生成：`cb`、`callback`、`pow`、`data`、`w`、`collect`、轨迹和耗时不要硬编码样本值。
4. 图片阶段先校验响应内容，再交给 `ddddocr`；OCR 失败时丢弃本轮 token 并重新拉取资源。
5. 最终验证以服务端响应为准：GT3 看 final `/ajax.php` 的 `success: 1` 和业务 `validate-slide`，GT4 看 `result: success`，腾讯看 `cap_union_new_verify`，易盾看 `/api/v3/check` JSONP 内结果，数美看 `/ca/v2/fverify` 是否 `PASS`，云片看 `/captcha/verify` JSONP 内是否返回二次 `token`，360 天御看 `/api/v3/check` 的 `error/data.result`，字节 VerifyCenter 看最终 `/captcha/verify` 的 `code == 200`。

## 字节 VerifyCenter 分支

适用信号：`verifycenter/captcha/v2 -> mssdk/web/r/token -> captcha/get -> captcha/verify`，并出现 `captchaBody`、`cyfreso`、WASM、BDMS 和 `a_bogus`。

详细取证、iv8/WASM 参数边界、BDMS 环境分支、服务端时钟对齐和验收标准见 `references/bytedance-verifycenter-workflow.md`。

优先路线：

1. 自动回放业务登录拿新鲜 `verify_center_decision_conf`，不要把手工复制 iframe URL 设计成正常输入。
2. 保持同轮 decision、mssdk、challenge、图片、距离、轨迹、WASM ciphertext 和签名。
3. 双图识别返回的原图缺口坐标必须映射到页面背景宽度。
4. 区分 `wasm.encrypt(source)` 的公开单参数与内部 `entry(source, utf8_byte_length)`；内部 number 不是 `cyfreso`。
5. 用 `/captcha/get` 回包的 `x-tt-timestamp` 判断真实发送窗口；轨迹声明 1.3 秒但 HTTP 立即发送，同样可能被拒绝。
6. 浏览器发送同一条本地 URL/body 能通过时，先查 Python 的发送时序、URL 字节、body hash 和传输层，不要继续盲改识别距离。

## 极验 GT3 分支

适用信号：`register-slide -> gettype.php -> fullpage.9.x -> initial get.php w -> pre ajax.php w -> slide get.php -> final ajax.php w`。

详细流程及参考实现见 `references/geetest-gt3-workflow.md`。

优先路线：

1. 请求业务 `register-slide` 拿 `gt` 和 base `challenge`，再请求 `gettype.php` 确认 `type=fullpage`、`fullpage.9.x`、`slide.7.x`。
2. 用当前 `fullpage.9.x` 在本地 VM 中生成 initial `/get.php` 的 `w`，同时导出这一轮 `aeskey`。
3. 真实请求 `apiv6.geetest.com/get.php`，拿 first-round `c/s/api_server`。
4. 用同一个 `aeskey` 和真实 initial 响应生成 pre `/ajax.php` 的 `w`；如果这里 `param decrypt error`，优先查 `aeskey` 是否断轮。
5. 请求 pre `/ajax.php`，必须得到 `{"result":"slide"}`，再请求 slide `/get.php` 拿 slide challenge、`bg/fullbg/slice`、second-round `c/s` 和 `gct_path`。
6. 还原 52 块乱序图，识别距离，生成或缩放同轮轨迹。
7. 用当前 `slide.7.x` 和 `gct_path` 本地生成 final `w`，提交 `$_BCm=0` 的 final `/ajax.php`。
8. 成功后把 `validate`、slide challenge、`validate|jordan` 交给业务验证接口。

高频排查：

1. GT3 不要套 GT4 的 `lot_number/pow_detail/process_token` 逻辑。
2. pre `/ajax.php` `param decrypt error` 通常是 initial `w` 和 pre `w` 没复用同一轮 `aeskey`。
3. final `forbidden` 优先查 final payload：slide challenge、second-round `c/s`、`aa`、`ep.tm`、gct 动态字段、距离和轨迹是否同轮。
4. 空 pre `w` 兼容路径即使能拿 slide，也可能造成状态不稳；优先走真实 fullpage initial + pre-radar 链。
5. 最终运行不得依赖浏览器自动化；浏览器或 MCP 只用于侦察和人工轨迹样本采集。

## 百度 Passport Spin V2 分支

适用信号：`passport.baidu.com/cap/init -> /cap/style -> /cap/img -> /cap/log`，并出现 `spin-0`、`backstr`、`ext.p`、`en_conf`、`mkd_v2.js`、`work.js`、`cv=submit` 或响应 `data.op`。

详细请求链、`getNewKey`/Keccak、PoW、`rzData`、双层 AES `fs`、`/cap/log` 埋点与验证包区分、`op==1` 成功标准和快速回放经验见 `references/baidu-passport-spin-v2-workflow.md`。

优先路线：

1. 固定同一轮 `tk/as/backstr/ext.p/en_conf/image`，不要混用相邻轮。
2. 在浏览器包里不要只看 URL；同为 `/cap/log` 时，用 `cv=submit`、`typeid=spin-0` 和响应 `data.op` 区分验证提交与普通埋点。
3. 本地先验 `getNewKey`、`en_conf`、PoW、双层 AES `fs`，再接角度候选。
4. `op=3` 后立即刷新新轮，不要在同一挑战上连续打多次角度猜测。
5. 成功标准必须是 `code == 0 && data.op == 1`；`code=0` 或 `msg=Success` 单独不是成功。

## 极验 GT4 分支

适用信号：`/load -> lot_number/pow_detail/payload/process_token/pt -> w -> /verify`。

详细流程、bundle 升级后的动态字段提取及 `forbidden` 修复见 `references/geetest-gt4-workflow.md`。

优先路线：

1. 用 `/load` 动态读取 `lot_number`、`payload`、`process_token`、`payload_protocol`、`pt`、`pow_detail`、图片地址。
2. 图片识别得到前端坐标系下的 `setLeft`。
3. 用 `pow_detail` 和 `payload` 生成 `pow_msg`、`pow_sign`。
4. 对 `pt=1`，常见 `w` 形态是 `AES-CBC-PKCS7(JSON.stringify(wPayload), session_key, iv='0000000000000000') + RSA-PKCS1-v1_5(session_key)` 的 hex 拼接。
5. 从当前 bundle 的 `_lib` 和 `lib._abo` 提取固定字段与 `lot_number` 派生规则，不要写死旧版字段名、字段值或嵌套公式。
6. `/verify` 外层参数必须来自同一次 `/load`。

高频排查：

1. `param decrypt error` 优先查 `w` 加密层级、`pt` 分支、RSA 公钥、AES IV 和 JSON 紧凑序列化。
2. `status=success, result=forbidden, fail_count=0` 连续出现时，优先对比新旧 bundle 的 `_lib/lib._abo`、webpack require 暴露正则、`lot_number` 派生字段，再查 `setLeft/userresponse`。
3. `fail` 优先查 Cookie、Session 是否同轮复用。
4. 官方 Demo 被分配到 `svg_seed` 点选不代表滑块协议已移除；以直接 `risk_type=slide` 的 `/load` 响应为准。

## 腾讯滑块分支

适用信号：`TDC.getData(true)`、`slide.js`、`drag_ele.html`、`cap_union_prehandle`、`cap_union_new_verify`。

优先路线：

1. 不改原始 `slide.js`，先用 `env.js` 或 VM2 原型链模板直跑。
2. 首轮记录真实错误，不先堆 DOM；`Bind must be called on a function` 通常先补 `window.Array/Object/Function` 等全局构造器。
3. `window.TDC` 挂出后必须调用 `window.TDC.getData(true)`；如果返回 `Err%3A...`，先 `decodeURIComponent` 看真实错误。
4. 再按错误补最小布局环境：`document.documentElement/body/head`、`clientWidth/clientHeight`、`createElement`、`getBoundingClientRect`、`querySelector`。
5. 真实 `location` 要同步到 `location`、`document.URL`、`document.documentURI`、`document.baseURI`、`document.referrer`，不要只改 `href`。
6. 标准交付是 `runtime.js`、`server.js`、Python 最小请求脚本，并验证两次 `fresh: true` 返回不同值。

完整请求链：

1. `cap_union_prehandle` 获取 `sess`、`pow_cfg`、`tdc_path`、图片 URL 和初始坐标。
2. 请求 `tdc_path` 提取 `eks`。
3. 本地 `TDC.getData(true)` 生成 `collect`，`tlg = len(collect)`。
4. 图片识别生成 `ans`，格式是紧凑 JSON。
5. 用 `pow_cfg.prefix` 和 `pow_cfg.md5` 暴力生成 `pow_answer = prefix + ans` 和真实 `pow_calc_time`。
6. POST `cap_union_new_verify`，字段不要跨轮混用。

## 网易易盾分支

适用信号：`NECaptcha`、`api/v3/get`、`api/v3/check`、`cb`、`data`、`token`、`front/bg`。

详细流程及参考实现见 `references/yidun-workflow.md`。

优先路线：

1. 用 `2.获取cb值.js` 中的环境和源码生成动态 `cb`，不要继续使用请求样本里的固定 `cb`。
2. `api/v3/get` 请求带上 `referer`、`zoneId`、`dt`、`irToken`、`id`、`fp`、`type=2`、`version`、`width=320`、动态 `cb` 和动态 JSONP `callback`。
3. 从 JSONP 中提取 `data.bg[0]`、`data.front[0]`、`data.token`。
4. 下载 `front` 和 `bg`，用 `ddddocr.slide_match(target_bytes=front, background_bytes=bg, simple_target=True)` 得到滑动距离。
5. 用 `trace_data.BezierTrajectory().generate_trajectory(slide_distance + 5)` 生成轨迹点，轨迹点格式为 `[x, y, time, 1]`。
6. 用 `4.获取data参数.js` 的 `get_params_data(trace, token, slide)` 生成 `/api/v3/check` 的 `data`。
7. 请求 `/api/v3/check` 时传同轮 `token`、动态 `data`、动态 `cb`、动态 `callback`，并保持 `referer/zoneId/id/width/type/version/loadVersion/iv` 与 get 阶段一致。

易盾 `data` 结构：

```json
{"d":"...","m":"","p":"...","f":"...","ext":"..."}
```

字段来源：

1. `d`：轨迹点经 `window._0x3855dc(token, pointString)` 逐点处理、采样 50 个、拼接后再编码。
2. `p`：`slide / 320 * 100` 经 token 相关编码。
3. `f`：轨迹去重后摘要编码。
4. `ext`：`1,trace_data.length` 经 token 相关编码。

高频排查：

1. `/api/v3/get` 失败先查 `cb`、`callback`、`fp`、`irToken`、`dt` 是否过期或与站点不匹配。
2. `/api/v3/check` 失败先查 `data` 是否由当前 `token` 生成，轨迹是否和滑动距离同轮，`slide` 是否用原始识别距离而不是偏移后的轨迹终点。
3. JSONP 正则不要写死某一个 callback，例如用 `__JSONP_.*?_\d\((.*?)\)`。
4. 图片下载后先校验是否为真实图片，避免把错误页交给 OCR。

## 数美滑块分支

适用信号：`captcha1.fengkongcloud.cn`、`/ca/v1/register`、`/ca/v2/fverify`、`captchaUuid`、`rid`、`fg/bg`、`sm.js`、`get_params.js`。

详细流程及参考实现见 `references/shumei-workflow.md`。

优先路线：

1. 生成 `captchaUuid`，格式是 `YYYYMMDDHHMMSS + 16位随机字母数字`。
2. 请求 `https://captcha1.fengkongcloud.cn/ca/v1/register`，参数带 `organization`、`appId=default`、`rversion=1.0.4`、`model=slide`、`sdkver=1.1.3`、动态 `callback=sm_<timestamp>`、当前 `captchaUuid`。
3. 从 JSONP 中提取 `detail.bg`、`detail.fg`、`detail.rid`，图片域名前缀拼 `https://castatic.fengkongcloud.cn`。
4. 下载 `fg` 和 `bg`，用 `ddddocr.slide_match(fg, bg, simple_target=True)` 得到缺口距离；当前案例把识别结果除以 `2` 后作为参数生成用的 `x`。
5. 用正弦曲线生成轨迹 `track`，格式为 `[x, y, timestamp]`，并得到总耗时 `times`。
6. 调用 `get_params.js` 的 `get_params(x, track, times, rid)` 生成 `/ca/v2/fverify` 参数，再补上同轮 `captchaUuid`。
7. 请求 `/ca/v2/fverify`，响应包含 `PASS` 才算通过。

数美参数来源：

1. `ww/bb/vj/hq`：固定值 `default`、`zh-cn`、`11` 等经 DES + Base64 生成。
2. `wi`：`x / 300` 字符串经 DES + Base64 生成。
3. `gq`：`JSON.stringify(track)` 经 DES + Base64 生成。
4. `vs`：滑动耗时 `times` 字符串经 DES + Base64 生成。
5. `lx/es`：宽高相关固定值 `300/150` 经 DES + Base64 生成。
6. `rid`：来自同一次 `register`，不能本地生成。

高频排查：

1. `register` 失败先查 `organization`、`captchaUuid`、`callback`、`Origin/Referer` 是否和目标站点一致。
2. `fverify` 不通过先查 `rid/captchaUuid` 是否同轮，`x` 是否按目标图片缩放除以 `2`，`track/times` 是否与 `x` 同轮生成。
3. `get_params.js` 里的 DES key 和字段名不要随意改，字段缺失会导致服务端无法验签。
4. 图片识别距离异常时先保存 `bg/fg` 检查是否拿反、是否缩放、是否下载到错误页。

## 云片滑块分支

适用信号：`captcha.yunpian.com`、`/v1/jsonp/captcha/get`、`/v1/jsonp/captcha/verify`、`ypjsonp`、`captchaId`、`yp_riddler_id`、`i/k/cb`、`yp.js`。

详细流程及参考实现见 `references/yunpian-workflow.md`。

优先路线：

1. 用 `yp.js` 加载 `env.js` 和 `code.js`，复用 `window.CryptoJS`、`window.qm` RSA、公钥和 `get_i_k()` / `get_i_k_position()`。
2. 组装浏览器指纹对象，至少包含 `browserInfo`、`options.sdk`、`options.sdkBuildVersion`、`options.hosts`、`fp`、`address`、`yp_riddler_id`。
3. 调 `get_i_k(fingerprintPayload)` 生成 `captcha/get` 的 `i/k/cb`，再补 `captchaId`。
4. 请求 `https://captcha.yunpian.com/v1/jsonp/captcha/get`，从 `ypjsonp(...)` 中提取 `data.bg`、`data.front`、`data.token`。
5. 下载 `front/bg` 后用 `ddddocr.slide_match(front, bg, simple_target=True)` 识别距离；当前案例使用 `int(target_x / 1.45) + random.randint(1, 2)` 做坐标换算。
6. 生成高密度轨迹 `points`，格式 `[x, y, timestamp]`，起点示例为 `(916, 1969)`。
7. 计算 `distanceX = (304 - 62) * (x / (304 - 42)) / 304`，和 `fp/address/yp_riddler_id/points` 一起调用 `get_i_k_position()` 生成 verify 的 `i/k/cb`。
8. 请求 `/v1/jsonp/captcha/verify` 时补同轮 `captchaId` 和 get 阶段返回的 `token`，响应里拿到新的 `data.token` 才算通过。

云片加密参数来源：

1. `i`：`AES-CBC-Pkcs7(JSON.stringify(payload), random16Key, random16Iv)`，返回 CryptoJS 默认字符串格式。
2. `k`：RSA 公钥加密 `random16Key + random16Iv`。
3. `cb`：`Math.random().toString(32).replace('0.', '')`。
4. get 阶段 payload 是浏览器指纹对象。
5. verify 阶段 payload 是行为对象，必须包含 `distanceX`、`fp`、`address`、`yp_riddler_id`，并由 `get_i_k_position()` 加入采样后的 `points`。

高频排查：

1. get 失败先查 `captchaId`、`fp`、`yp_riddler_id`、`address`、Cookie 和 `ypjsonp` 解析。
2. verify 失败先查 get 返回的 `token` 是否同轮、`points` 是否被采样到 50 个以内、`distanceX` 换算是否符合目标站点。
3. `i/k` 异常先查 `env.js` 是否成功挂出 `window.CryptoJS` 和 `window.qm`，RSA 公钥是否完整。
4. 图片距离异常先检查 `target_x / 1.45` 缩放系数是否仍适用，不要把 OCR 原始像素直接提交。

## 顶象/鼎象滑块分支

适用信号：`/api/a`、`/api/p1`、`/api/p2`、`/api/v1`、`dingxiang-sdk.js`、`greenseer.js`、`const-id.js`、`_dx.UA.init`、`sendSA`、`sendTemp`、`getUA`、`ac=s_v3#...`、`_dx_app_*`、`_dx_captcha_vid`、`4012 POSITION_MISMATCH`、`4011 HIGH_RISK`。

优先路线：

1. 先请求站点验证码配置接口或页面配置，提取 `appId/ak`、`apiServer`、`ua_js=greenseer.js`、`constID_js=const-id.js`、`jsv`、`constIDServer`；不要先碰业务查询接口。
2. 请求顶象 `/api/a` 获取同轮 `sid`、`aid`、`y`、`p1`、`p2`、`o`、`ak`、`apiServer`；后续 `/api/v1` 必须使用同一轮这些字段。
3. 下载 `/api/p1` 背景图和 `/api/p2` 滑块图后，先检查是否存在切片乱序；顶象常见背景是 32 个纵向切片，原图 400px，实际渲染还原宽度为 `32 * 12 = 384px`。
4. 使用 `/api/a` 返回的 `o` 值还原背景：取 `o` 最后一段 basename 的前 32 个字符，对每个字符取 `ord(char) % 32`，冲突时 `value += 1` 直到未占用，得到 source slice order；按 `drawImage(img, srcIndex * 12, 0, 12, 200, dstIndex * 12, 0, 12, 200)` 还原。
5. 调试图片固定保存成少量可复查文件即可，例如 `bg.png`、`sl.png`、`out.png`、`meta.json`；不要按 sid 无限堆积图片。
6. 在还原后的 `out.png` 上做缺口识别，可用 `ddddocr.slide_match`、OpenCV 边缘/模板匹配或打码平台双图识别；识别前不要把乱序原图直接交给 OCR。
7. 坐标换算以还原图宽度为准，常见提交候选优先从 `round(raw_x * 300 / restored_width)`、相邻 `±1`、再加 `+10` 兜底；不要把 400px 原图坐标、384px 还原坐标和 300px 页面坐标混用。
8. 本地执行 `greenseer.js` 生成 `ac`：`_dx.UA.init({ token: sid })` 后模拟 `mouseenter/mouseover/mousedown/mousemove/mouseup/click` 轨迹，再调用 `sendSA()`、`sendTemp('x=' + x + '&y=' + y)`、`getUA()`。
9. POST `/api/v1` 使用 `application/x-www-form-urlencoded`，字段通常为 `ac`、`ak`、`c`、`uid`、`jsv`、`sid`、`aid`、`x`、`y`；成功响应含 `token`，同时通常需要同步 `_dx_captcha_vid=token`。
10. `c` 通常来自 `_dx_app_<appId>` 或 `const-id.js`/`/udid/c1`，但裸调 `/udid/c1?` 可能污染状态；若已有稳定 `_dx_app`，优先复用或通过真实 `param` 获取，不要无脑刷新。

顶象图片还原参考伪代码：

```python
def restore_bg(p1, o):
    from PIL import Image
    src = Image.open(p1).convert('RGB')
    columns, piece_w = 32, 12
    seed = str(o).split('/')[-1].split('.')[0]
    order = []
    for ch in seed[:columns]:
        value = ord(ch)
        while value % columns in order:
            value += 1
        order.append(value % columns)
    dst = Image.new('RGB', (columns * piece_w, src.height), 'white')
    for dst_i, src_i in enumerate(order):
        box = (src_i * piece_w, 0, src_i * piece_w + piece_w, src.height)
        dst.paste(src.crop(box), (dst_i * piece_w, 0))
    return dst
```

高频排查：

1. 连续 `4012 POSITION_MISMATCH`：先看是否忘了用 `o` 还原 `p1`，再看坐标是否从 384px 还原图换算到 300px 页面坐标；不要先怀疑 `ac`。
2. 同轮多次提交后出现 `4011 HIGH_RISK`：减少每轮坐标尝试数，失败后重新拉 `/api/a` 新挑战；不要在同一 `sid` 上扫大量坐标。
3. `/api/v1` 一直 `4012` 且坐标准确：检查 `greenseer` 是否只调用了 `sendTemp` 而没有模拟完整鼠标事件；缺少事件轨迹时服务端可能能解析 `ac` 但不认可位置。
4. `ac` 生成异常：检查 Node/jsdom/vm 沙箱中的 `navigator`、`screen`、`document.cookie`、storage、canvas/webgl、`location`、计时 API 是否能被 `greenseer` 读取。
5. 打码平台返回的 `x` 是背景图缺口左边缘原图坐标，不一定等于提交距离；必须结合还原图宽度和页面展示宽度做映射。

## 360 天御分支

适用信号：`captcha.jiagu.360.cn`、`/api/v3/auth`、`/api/v3/check`、`360CaptchaSDK`、`captchaId`、`k`、`report`、`tracking`、`decryptImage`、`rsa_1.js`。

详细流程及参考实现见 `references/tianyu360-workflow.md`。

优先路线：

1. 构造 auth 请求体：`appId=dc1db94ea7b3843c`、`type=1`、`version=2.0.0`、`pn=com.web.tianyu`、`os=3`、`sdkName=360CaptchaSDK`、毫秒 `timestamp`、`nonce=timestamp+8位随机数`、`ui=null`、各计数字段为 `0`、`phone=10000000000`。
2. 生成 `sign`：所有参数按 key 排序，拼接 `key + value`，`None` 转字符串 `null`，最后 MD5 hex。
3. POST `https://captcha.jiagu.360.cn/api/v3/auth`，提取 `data.bg[0]`、`data.front[0]`、`captchaId`、`token`、`k`。
4. 从背景图 URL 提取 32 位 key，根据 key 生成 32 块置换表，还原乱序背景图。
5. 用 `ddddocr.slide_match(slice, restored_bg, simple_target=False)` 识别缺口，再按 `int(raw_x / 544 * 300)` 转成提交长度。
6. 生成动态轨迹对象数组，形如 `[{"0":{"t":...,"y":...}}, ...]`，再紧凑 JSON 序列化。
7. 调用 `rsa_1.js` 的 `encryptReport(trackJson, {k, token, captchaId})` 生成 `report`。
8. POST `/api/v3/check`，字段包含 `captchaId`、`token`、`length`、`version=2.0.0`、`width=300`、`report`、`tracking=[object Object]`。

360 天御关键算法：

1. 图片还原：背景 URL 中的 32 位 key 生成 `perm_table`，规则是每个字符 `ord(char) % 32`，冲突时 `ord+1` 递增直到未占用；再构造逆置换表恢复 32 个横向切片。
2. `report`：`plainText = JSON.stringify(track)`，`signKey = md5(captchaId + token)`，最终明文是 `plainText + signKey`。
3. RSA 公钥：`k` 是 base64 后的公钥，先 `atob(k)` 再 `JSEncrypt.setPublicKey()`。
4. 长明文加密：短文本用 `rsa.encrypt()`，长文本用 `rsa.getKey().encryptLong()`。

高频排查：

1. auth 失败先查 `sign` 拼接顺序、`None -> null`、`nonce` 长度、headers 的 `origin/referer/content-type`。
2. 图片距离异常先查背景是否完成 32 切片还原，`perm_table` 是否用逆置换，`raw_x / 544 * 300` 是否符合当前图片尺寸。
3. check 失败先查 `report` 是否追加了 `md5(captchaId + token)`，`k` 是否先 base64 解码，`length` 是否提交字符串化后的前端坐标。
4. 轨迹失败先查轨迹对象 key 是否是字符串索引，`tracking` 是否按样本传 `"[object Object]"`。

## 交付标准

1. 明确平台和请求链，不混用 GT3、GT4、腾讯、易盾、数美、云片、360 天御、顶象/鼎象字段。
2. 动态参数能重新生成，不依赖固定样本值。
3. 图片、轨迹、加密参数和 verify/check 属于同一轮 token/session。
4. 提供可运行脚本或明确指出缺失的动态材料。
5. 失败时打印关键中间值：GT3 的 initial/pre/final `/ajax.php` 响应、`w` 长度、`aeskey` 是否同轮、slide challenge、`c/s`、距离、`aa` 长度、`ep.tm`、`validate`，GT4 的 `wPayload`，腾讯的 `collect/ans/pow_cfg`，易盾的 `token/slide/data/trace length`，数美的 `captchaUuid/rid/x/track length/times/params`，云片的 `captchaId/token/x/distanceX/points length/i/k/cb`，360 天御的 `captchaId/token/k/key/perm_table/raw_x/length/report length`，顶象的 `sid/aid/o/y/c/ac length/raw_x/x candidates/api_v1 code`。
