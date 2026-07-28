# 网易易盾滑块流程

来源参考案例：网易易盾滑块逆向项目。

## 文件角色

1. `1.请求测试.py`：固定参数请求 `https://c.dun.163.com/api/v3/get`，用于观察 JSONP 响应结构。
2. `2.获取cb值.js`：补最小浏览器环境并加载 NECaptcha 源码，导出动态 `get_cb()`。
3. `3.携带动态cb值获取验证码资源.py`：用动态 `cb` 请求 `api/v3/get`，提取 `bg/front/token`。
4. `4.获取data参数.js`：基于 `token`、轨迹和滑动距离生成 `/api/v3/check` 的 `data` 参数。
5. `5.计算验证码滑动距离.py`：下载 `front/bg`，用 `ddddocr` 计算滑动距离。
6. `trace_data.py`：用贝塞尔曲线生成 `[x, y, time, 1]` 轨迹。
7. `6.网易易盾.py`：整合 get、OCR、轨迹、data 生成和 check 请求。

## 请求 get

接口：`https://c.dun.163.com/api/v3/get`。

关键请求头：

1. `Referer: https://dun.163.com/`
2. `Sec-Fetch-Dest: script`
3. `Sec-Fetch-Mode: no-cors`
4. `Sec-Fetch-Site: same-site`
5. `User-Agent` 和 `sec-ch-ua` 保持同一浏览器版本。

关键参数：

1. `referer=https://dun.163.com/trial/jigsaw`
2. `zoneId=CN31`
3. `dt`、`irToken`、`id`、`fp` 来自站点初始化材料，不能长期假设固定有效。
4. `type=2` 表示滑块。
5. `version=2.28.5`、`loadVersion=2.5.3`、`width=320`、`iv=4` 与样本保持一致。
6. `cb` 由 `2.获取cb值.js` 的 `get_cb()` 生成。
7. `callback` 由 `4.获取data参数.js` 的 `get_callback()` 生成，形如 `__JSONP_<random>_1`。

响应是 JSONP，解析时不要写死 callback：

```python
json_data = json.loads(re.findall(r'__JSONP_.*?_\d\((.*?)\)', response.text)[0])
```

提取字段：

```python
bg = json_data['data']['bg'][0]
front = json_data['data']['front'][0]
token = json_data['data']['token']
```

## 计算距离

下载 `front` 和 `bg` 后，用：

```python
ocr = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
result = ocr.slide_match(target_bytes=front_bytes, background_bytes=bg_bytes, simple_target=True)
slide_distance = int(result['target'][0])
```

注意：

1. `front` 是滑块图，`bg` 是背景图。
2. OCR 前先检查响应是否为图片，不要把错误页写入 `front.jpg/bg.jpg`。
3. check 阶段 `slide` 传原始识别距离；轨迹终点可以按案例使用 `slide_distance + 5`。

## 生成轨迹

`trace_data.py` 的 `BezierTrajectory.generate_trajectory(slider_x)`：

1. 起点 `[4, 0]`。
2. 终点 `[slider_x + 10, 2]`。
3. 点数约为 `slider_x + 25`。
4. 每个点的时间从 `132` 开始，每步增加 `50-80ms`。
5. 输出点格式：`[int(x), int(y), time, 1]`。

整合脚本中使用：

```python
trace = BezierTrajectory().generate_trajectory(slide_distance + 5)
```

## 生成 data

`4.获取data参数.js` 的核心入口：

```js
get_params_data(trace, token, slide)
```

内部逻辑：

1. 对每个轨迹点执行 `window._0x3855dc(token, point + '')`。
2. 用 `window._0x148293.sample(trace_data, 50)` 对轨迹编码结果采样。
3. `p` 使用 `slide / 320 * 100`，再做 token 相关编码。
4. `f` 使用 `window._0x148293.unique2DArray(trace, 0x2)` 去重后摘要编码。
5. `ext` 使用 `1,trace_data.length` 编码。

最终返回紧凑 JSON 字符串：

```json
{"d":"...","m":"","p":"...","f":"...","ext":"..."}
```

关键边界：

1. `token` 必须来自当前 `api/v3/get`。
2. `trace` 必须由当前滑动距离生成。
3. `slide` 用当前 OCR 识别距离。
4. 不要复用上一轮 `data`。

## 请求 check

接口：`https://c.dun.163.com/api/v3/check`。

关键参数：

1. `referer=https://dun.163.com/trial/jigsaw`
2. `zoneId=CN31`
3. `dt`、`id` 与当前站点材料一致。
4. `token` 来自同一次 get。
5. `data` 来自 `get_params_data(trace, token, slide)`。
6. `width=320`、`type=2`、`version=2.28.5`、`loadVersion=2.5.3`、`iv=4`。
7. `cb` 每次用 `get_cb()` 重新生成。
8. `callback` 每次用 `get_callback()` 重新生成。

## 推荐封装

标准类结构：

1. `__init__` 编译 `2.获取cb值.js` 和 `4.获取data参数.js`，初始化 headers/cookies/session。
2. `get_captcha_images_and_token()` 请求 get 并返回 `bg/front/token`。
3. `parse_slide(front_bytes, bg_bytes)` 返回滑动距离。
4. `send_verify(trace, slide_distance, token)` 生成 `data` 并请求 check。
5. `main()` 串联整轮流程。

## 排查清单

1. get 没有返回图片：检查 `cb/callback/fp/irToken/dt/id` 是否过期。
2. JSONP 解析失败：检查 callback 正则是否过窄。
3. OCR 距离异常：检查 `front/bg` 是否拿反或图片响应是否损坏。
4. check 失败：检查 `token/data/trace/slide` 是否同轮。
5. data 异常：确认 `2.获取cb值.js` 已先加载，`window._0x3855dc`、`window._0x3ebd00`、`window._0x6e07ce` 已挂到全局。
