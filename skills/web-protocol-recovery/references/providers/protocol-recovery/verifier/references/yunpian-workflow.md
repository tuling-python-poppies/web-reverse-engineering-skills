# 云片滑块流程

来源参考案例：云片滑块逆向项目。

## 文件角色

1. `yp.py`：完整串联 captcha/get、OCR、轨迹、参数生成和 captcha/verify。
2. `yp.js`：加载 `env.js`、`code.js`，导出 `get_i_k()` 和 `get_i_k_position()`。
3. `env.js`：补浏览器环境并挂代理日志，支持 `code.js` 在 Node/execjs 中运行。
4. `code.js`：云片 SDK 相关 bundle，提供 `window.CryptoJS`、RSA 构造器 `window.qm` 等能力。

## JS 参数生成

`yp.js` 的关键能力：

1. `getRandomStr(16)` 生成 AES key 和 IV。
2. `AES_encrypt(plain, key, iv)` 使用 `CryptoJS.AES.encrypt`，`mode=CBC`，`padding=Pkcs7`，`key/iv` 用 `Latin1.parse`。
3. RSA 公钥写死在 `yp.js` 中，通过 `new window.qm()` 和 `setPublicKey()` 初始化。
4. `k = RSA.encrypt(key + iv)`。
5. `cb = Math.random().toString(32).replace('0.', '')`。

get 阶段入口：

```js
get_i_k(fingerprintPayload)
```

verify 阶段入口：

```js
get_i_k_position(actionPayload, position)
```

`get_i_k_position()` 会先用 `get_e(position)` 对轨迹采样：

1. 轨迹长度小于等于 50 时原样返回。
2. 超过 50 时保留首点、末点，并按 `Math.floor(length / 50)` 间隔采样。
3. 采样结果写入 `actionPayload.points`。

## 请求 captcha/get

接口：`https://captcha.yunpian.com/v1/jsonp/captcha/get`。

headers 关键点：

1. `Sec-Fetch-Dest: script`
2. `Sec-Fetch-Mode: no-cors`
3. `Sec-Fetch-Site: same-site`
4. `User-Agent`、`sec-ch-ua`、`sec-ch-ua-platform` 与环境对象保持一致。

指纹 payload 示例字段：

```json
{
  "browserInfo": [
    {"key":"userAgent","value":"Mozilla/5.0 ... Chrome/145.0.0.0 Safari/537.36"},
    {"key":"language","value":"zh-CN"},
    {"key":"hardware_concurrency","value":16},
    {"key":"resolution","value":[1536,864]},
    {"key":"navigator_platform","value":"Win32"}
  ],
  "nativeInfo": null,
  "additions": {},
  "options": {
    "sdk": "https://www.yunpian.com/static/official/js/libs/riddler-sdk-0.2.2.js",
    "sdkBuildVersion": "1.5.0(2021111001)",
    "hosts": "https://captcha.yunpian.com"
  },
  "fp": "807c50615df5c6624dcbed1a70d820b6",
  "address": "https://www.yunpian.com",
  "yp_riddler_id": "a414f89c-9f2d-46a4-905b-ab4326976f2a"
}
```

流程：

```python
params = js_obj.call('get_i_k', fingerprint_payload)
params['captchaId'] = '974cd565f11545b6a5006d10dc324281'
response = requests.get(get_url, headers=headers, cookies=cookies, params=params)
json_data = json.loads(re.findall(r'ypjsonp\((.*?)\)', response.text)[0])
bg_url = json_data['data']['bg']
front_url = json_data['data']['front']
token = json_data['data']['token']
```

## 计算距离

```python
bg = requests.get(bg_url).content
front = requests.get(front_url).content
det = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
result = det.slide_match(front, bg, simple_target=True)
x = int(result['target'][0] / 1.45) + random.randint(1, 2)
```

注意：

1. `front` 是滑块图，`bg` 是背景图。
2. 当前案例使用 `1.45` 缩放系数，再加 `1-2` 像素扰动。
3. 迁移站点时必须用成功样本确认缩放系数。

## 生成轨迹

主脚本使用 `generate_dense_track(start_x, start_y, distance)`。

当前参数：

1. `start_x=916`
2. `start_y=1969`
3. `distance=x`

轨迹特征：

1. 目标点数约 `distance * 1.42`。
2. 起始时间戳随机 `85-95`。
3. X 轴每步小幅前进，前后慢中间快。
4. 中段有小概率回退和停滞。
5. Y 轴有缓慢漂移、正弦波和随机抖动。
6. 时间间隔大多 `2-12ms`，少量 `15-30ms` 或 `40-120ms`。
7. 到达目标后追加 `2-4` 个终点微抖点。

轨迹点格式：

```python
[x, y, timestamp]
```

## 请求 captcha/verify

接口：`https://captcha.yunpian.com/v1/jsonp/captcha/verify`。

先计算行为 payload：

```python
distance_x = (304 - 62) * (x / (304 - 42)) / 304
payload = {
    'distanceX': distance_x,
    'fp': '807c50615df5c6624dcbed1a70d820b6',
    'address': 'https://www.yunpian.com',
    'yp_riddler_id': 'a414f89c-9f2d-46a4-905b-ab4326976f2a',
}
params = js_obj.call('get_i_k_position', payload, track)
params['captchaId'] = '974cd565f11545b6a5006d10dc324281'
params['token'] = token
```

验证响应：

```python
json_data = json.loads(re.findall(r'ypjsonp\((.*?)\)', response.text)[0])
verify_token = json_data['data']['token']
```

能拿到 `data.token` 表示本轮滑动校验通过。

## 排查清单

1. get 失败：检查 `captchaId`、`fp`、`yp_riddler_id`、`address`、Cookie 和 `ypjsonp` 包装。
2. JS 编译失败：检查 `env.js` 是否补齐 `window`、`CryptoJS`、`qm` 依赖，以及 `require('./env')`、`require('./code')` 路径。
3. verify 失败：检查 `token` 是否来自同一次 get，`captchaId` 是否一致，`points` 是否经过 `get_e()` 采样。
4. 距离失败：检查 `target_x / 1.45` 和 `distanceX` 公式是否适配当前图片尺寸。
5. 风控失败：检查 `browserInfo` 与 headers、Cookie、`fp`、`yp_riddler_id` 是否一致。
