# 数美滑块流程

来源参考案例：数美滑块逆向项目。

## 文件角色

1. `数美滑块.py`：完整串联 register、OCR、轨迹、参数生成和 fverify。
2. `get_params.js`：用 DES + Base64 生成数美 `fverify` 所需参数。
3. `鼠标移动轨迹.py`：备用自然鼠标轨迹生成器。
4. `sm.js`：数美原始/参考 JS bundle。
5. `extract_final.js`：用于分析 `sm.js` 字符串数组和加密配置的辅助脚本。
6. `bg.jpg`、`fg.jpg`、`result.png`：调试图片产物。

## 请求 register

接口：`https://captcha1.fengkongcloud.cn/ca/v1/register`。

关键请求头：

1. `Origin: https://console.ishumei.com`
2. `Referer: https://console.ishumei.com/`
3. `Sec-Fetch-Dest: script`
4. `Sec-Fetch-Mode: cors`
5. `Sec-Fetch-Site: cross-site`
6. `User-Agent`、`sec-ch-ua`、`sec-ch-ua-platform` 与目标浏览器一致。

`captchaUuid` 生成方式：

```python
def generate_custom_code(random_length=16):
    time_str = datetime.now().strftime('%Y%m%d%H%M%S')
    chars = string.ascii_letters + string.digits
    return time_str + ''.join(random.choice(chars) for _ in range(random_length))
```

关键参数：

1. `organization=d6tpAY1oV0Kv5jRSgxQr`
2. `appId=default`
3. `rversion=1.0.4`
4. `data={}`
5. `callback=sm_<当前毫秒时间戳>`
6. `channel=default`
7. `lang=zh-cn`
8. `captchaUuid=<本轮生成值>`
9. `model=slide`
10. `sdkver=1.1.3`

响应是 JSONP：

```python
data = json.loads(re.findall(r'sm_\d+\((.*?)\)', response.text)[0])
bg_url = 'https://castatic.fengkongcloud.cn' + data['detail']['bg']
fg_url = 'https://castatic.fengkongcloud.cn' + data['detail']['fg']
rid = data['detail']['rid']
```

## 计算距离

数美案例中：

```python
bg = requests.get(bg_url).content
fg = requests.get(fg_url).content
det = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
result = det.slide_match(fg, bg, simple_target=True)
x = result['target'][0] / 2
```

注意：

1. `fg` 是滑块图，`bg` 是背景图。
2. 当前实现把 OCR 识别距离除以 `2`，这是图片缩放/坐标系换算点；迁移站点时要用成功样本确认是否仍需除以 `2`。
3. 图片下载后先验证内容类型和尺寸，避免 OCR 处理错误页。

## 生成轨迹

主脚本实际使用 `get_track(distance)`，不是备用的 `generate_mouse_path()`。

轨迹生成逻辑：

1. 初始 `x=[0,0]`、`y=[0,0,0]`、`z=[0]`。
2. 用 `np.linspace(-pi/2, pi/2, random.randrange(20, 30))` 生成正弦序列。
3. 加 `10-14` 像素随机超调，再回落到目标距离。
4. `y` 轴在 `0-30` 范围内上下轻微抖动。
5. 时间戳每步约增加 `100ms`，少量点增加 `1-2ms`。
6. 输出 `track = [[x, y, timestamp], ...]`，`times = track[-1][-1] + random.randint(1, 5)`。

备用轨迹 `鼠标移动轨迹.py` 使用 easeOutCubic，可在主轨迹被风控时作为替换参考。

## 生成 fverify 参数

入口：

```js
get_params(res, track, timer, rid)
```

参数含义：

1. `res`：滑动距离，当前案例为 `ocr_x / 2`。
2. `track`：轨迹数组 `[[x,y,t], ...]`。
3. `timer`：滑动总耗时。
4. `rid`：register 返回的同轮 `rid`。

`get_params.js` 主要使用 DES + Base64：

```js
_0x6ebde7(_0x4bf4de(key, value, 1, 0))
```

字段来源：

1. `ww = enc('36937571', 'default')`
2. `bb = enc('bd7d3fb7', 'default')`
3. `vj = enc('b7cdc6b2', 'zh-cn')`
4. `hq = enc('42ccd3c8', '11')`
5. `wi = enc('363f9192', String(res / 300))`
6. `gq = enc('ffd9ef14', JSON.stringify(track))`
7. `vs = enc('80fefdd1', String(timer))`
8. `lx = enc('61ad6eff', '300')`
9. `es = enc('620302a1', '150')`
10. `jq = enc('118c4021', '1')`
11. `zm = enc('da718702', '0')`
12. `tx = enc('786ef59e', '-1')`

固定明文字段：

1. `sdkver=1.1.3`
2. `organization=d6tpAY1oV0Kv5jRSgxQr`
3. `ostype=web`
4. `rid=<本轮rid>`
5. `callback=sm_<当前毫秒时间戳>`
6. `act.os=web_pc`
7. `protocol=206`
8. `rversion=1.0.4`

主脚本在 JS 返回后补：

```python
params['captchaUuid'] = captcha_uuid
```

## 请求 fverify

接口：`https://captcha1.fengkongcloud.cn/ca/v2/fverify`。

流程：

1. register 获取 `bg/fg/rid`。
2. OCR 得到 `x`。
3. 生成 `track/times`。
4. 调用 `get_params(x, track, times, rid)`。
5. 补 `captchaUuid`。
6. GET `fverify`。
7. 响应文本包含 `PASS` 才算通过。

## 排查清单

1. register 返回异常：检查 `organization`、`captchaUuid`、`callback`、`Origin/Referer`。
2. 图片距离异常：检查 `fg/bg` 是否拿反、是否需要除以 `2`、图片是否被 CDN 返回错误内容。
3. fverify 不通过：检查 `rid` 和 `captchaUuid` 是否同轮，`gq` 是否使用当前 `track`，`vs` 是否使用当前 `times`。
4. 参数缺失：确认 `get_params.js` 返回的 `ww/bb/vj/hq/wi/gq/vs/lx/es/jq/zm/tx` 都存在。
5. 迁移到新站点：优先确认 `organization`、`sdkver`、`rversion`、图片坐标缩放和请求头是否变化。
