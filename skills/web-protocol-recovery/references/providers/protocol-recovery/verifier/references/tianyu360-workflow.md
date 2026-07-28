# 360 天御滑块流程

来源参考案例：360天御滑块逆向项目。

## 文件角色

1. `360天御.py`：完整串联 auth、乱序图还原、OCR、轨迹、report 加密和 check。
2. `rsa_1.js`：JSEncrypt + crypto-js，导出 `encryptReport(plainText, vConfig)`。
3. `提问1.txt`：auth 请求体和 `sign` 生成逻辑分析。
4. `提问2.txt`：`decryptImage` 图片乱序还原逻辑分析。
5. `提问3.txt`：`report` 参数生成逻辑分析。
6. `restored.png`、`sl.png`：调试产物。

## 请求 auth

接口：`https://captcha.jiagu.360.cn/api/v3/auth`。

headers 关键点：

1. `origin=https://tianyu.360.cn`
2. `referer=https://tianyu.360.cn/`
3. `content-type=application/x-www-form-urlencoded`
4. `sec-fetch-site=same-site`
5. `user-agent`、`sec-ch-ua` 与浏览器环境一致。

请求体基础字段：

```python
body = {
    'appId': 'dc1db94ea7b3843c',
    'type': 1,
    'version': '2.0.0',
    'pn': 'com.web.tianyu',
    'os': 3,
    'sdkName': '360CaptchaSDK',
    'timestamp': int(time.time() * 1000),
    'nonce': str(timestamp) + str(random.randint(0, 99999999)).zfill(8),
    'ui': None,
    'rc': 0,
    'pc': 0,
    'ec': 0,
    'hc': 0,
    'xc': 0,
    'dc': 0,
    'phone': 10000000000,
}
```

`sign` 生成规则：

1. 对请求体所有 key 排序。
2. 拼接 `key + value`。
3. `None` 必须转成字符串 `null`。
4. 对拼接结果做 `md5(...).hexdigest()`。
5. 将 `sign` 放回请求体。

响应字段：

```python
bg = json_data['data']['bg'][0]
front = json_data['data']['front'][0]
captcha_id = json_data['data']['captchaId']
token = json_data['data']['token']
k = json_data['data']['k']
```

## 还原乱序背景图

背景图 URL 中包含 32 位 key，例如 `53bkf909haj9l91icg9768nemd94299o`。

提取规则：

```python
match = re.search(r'([a-z0-9]{32})', url)
key = match.group(1)
```

置换表生成：

```python
result = []
for char in key:
    code = ord(char)
    candidate = code % 32
    while candidate in result:
        code += 1
        candidate = code % 32
    result.append(candidate)
```

`perm_table` 表示 `原位置 -> 新位置`，还原时要构造逆置换：

```python
inverse_perm = [0] * 32
for original_pos, new_pos in enumerate(perm_table):
    inverse_perm[new_pos] = original_pos
```

图片横向切成 32 块，按逆置换复制到新图，得到 `restored.png`。

## 计算距离

```python
bg = open('restored.png', 'rb').read()
front = requests.get(front_url).content
ocr = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
result = ocr.slide_match(front, bg, simple_target=False)
raw_x = result['target'][0]
length = int(raw_x / 544 * 300)
```

注意：

1. OCR 背景必须是还原后的 `restored.png`。
2. 当前样本按 `544 -> 300` 做坐标缩放。
3. `length` 是 `/api/v3/check` 提交的滑动长度。

## 生成轨迹

`generate_dynamic_track(length)` 输出对象数组：

```json
[
  {"0":{"t":1773401715345,"y":221}},
  {"1":{"t":1773401715351,"y":221}}
]
```

轨迹特征：

1. 点数约为 `length * random(0.75, 0.95)`。
2. 时间戳从固定基准递增，间隔 `2/4/6ms` 或边缘段 `8/10/15ms`。
3. Y 轴围绕 `221` 小幅波动。
4. 每个点是单 key 对象，key 为字符串索引。
5. 序列化时使用紧凑 JSON：`json.dumps(track, separators=(',', ':'))`。

## 生成 report

入口：

```js
encryptReport(plainText, vConfig)
```

`vConfig`：

```json
{"k":"...","token":"...","captchaId":"..."}
```

算法：

1. `publicKey = atob(vConfig.k)`。
2. `rsa.setPublicKey(publicKey)`。
3. `signKey = MD5(captchaId + token).toString()`。
4. `finalPlainText = plainText + signKey`。
5. 明文短时用 `rsa.encrypt(finalPlainText)`。
6. 明文长时用 `rsa.getKey().encryptLong(finalPlainText)`。

Python 调用：

```python
report = execjs.compile(open('rsa_1.js', encoding='utf-8').read()).call(
    'encryptReport',
    track_json,
    {'k': k, 'token': token, 'captchaId': captcha_id},
)
```

## 请求 check

接口：`https://captcha.jiagu.360.cn/api/v3/check`。

表单字段：

```python
data = {
    'captchaId': captcha_id,
    'token': token,
    'length': str(length),
    'version': '2.0.0',
    'width': '300',
    'report': report,
    'tracking': '[object Object]',
}
```

## 排查清单

1. auth 失败：检查 `sign` 排序拼接、`None -> null`、`timestamp/nonce`、`content-type`。
2. 背景错位：检查 key 是否 32 位、置换方向是否是逆置换、切片数量是否 32。
3. 距离失败：检查 `raw_x / 544 * 300` 缩放是否适配当前图片。
4. report 为空：检查 `crypto-js` 是否安装，`k` 是否先 `atob`，`encryptLong` 是否可用。
5. check 失败：检查 `report` 是否追加 `md5(captchaId + token)`，`length`、`captchaId`、`token` 是否同轮。
