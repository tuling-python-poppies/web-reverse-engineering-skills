# CSDN Embedded Captcha 文字点选流程

本分支用于 CSDN `embedded_captcha`、`click_v2`、`cdn_cgi_bs_captcha/convert`、`cdn_cgi_bs_captcha/verify`、`randomKey`、`targetImage`、`background`、`captcha_protect`、`fpv`、`wlocation`，以及被 WAF 验证码拦截的短信/登录请求。

## 当前已跑通的本地流程

案例项目路径：

```text
目标项目根目录：`<projectRoot>`
```

主脚本：

```text
tools/csdn_live_verify_flow.py
```

完整成功链路：

```text
POST /v1/register/pc/sendVerifyCode
-> WAF 521，返回 Challenge 和 X-Request-Id
-> GET /cdn_cgi_bs_captcha/convert type=template
-> GET /cdn_cgi_bs_captcha/convert type=point_pic
-> 下载 background.jpg 和 targetImage.png
-> PaddleOCR 识别 targetImage 中的点击顺序
-> JFBYM 类型 300010 返回背景图中的有序点击坐标
-> 构造加密后的 /cdn_cgi_bs_captcha/verify form
-> POST /cdn_cgi_bs_captcha/verify?callback=callback_<ts>
-> 解析 JSONP，成功时得到 yd_captcha_token
```

## 后端是否返回文字顺序

目前 `/convert` 不直接返回点击文字顺序。解码后的点选图片响应只有：

```json
{
  "targetImage": "...-tg.png",
  "randomKey": "...",
  "background": "...-bg.jpg"
}
```

`targetImage.png` 没有可用 metadata。除非后续找到新的私有接口，否则点击顺序必须从图片像素 OCR。

## OCR 与坐标识别

本案例已使用的 OCR 运行栈：

```text
paddlepaddle==2.6.2
paddleocr==2.7.3
numpy==1.26.4
opencv-python==4.6.0.66
```

安装慢时使用清华镜像：

```powershell
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple paddlepaddle==2.6.2 paddleocr==2.7.3
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple "numpy<2" --force-reinstall
```

NumPy 要用 1.26 的原因：PaddleOCR 2.7.x 拉取的 OpenCV 4.6 wheel 按 NumPy 1.x ABI 编译。NumPy 2.x 可能触发 `numpy.core.multiarray failed to import`。

目标文字 OCR 脚本：

```text
tools/recognize_target_text.py
```

输出文件：

```text
js_reverse_cache/captcha_images/target_text.json
js_reverse_cache/captcha_images/targetImage_ocr_preprocessed.png
```

坐标识别脚本：

```text
tools/jfbym_points_api.py
JFBYM_CAPTCHA_TYPE=300010
```

如果返回点数不等于目标文字数量，必须拒绝这次识别结果，不要继续提交 `/verify`。

## 实时运行命令

全自动流程：

```powershell
$env:JFBYM_CAPTCHA_TYPE='300010'
$env:CSDN_TARGET_OCR_ENGINE='paddleocr'
python .\tools\csdn_live_verify_flow.py
```

只拉取同一轮验证码图片后停止：

```powershell
$env:CSDN_STOP_AFTER_IMAGES='1'
python .\tools\csdn_live_verify_flow.py
```

复用同一轮已保存验证码，手动输入文字顺序，绕过 OCR：

```powershell
$env:JFBYM_CAPTCHA_TYPE='300010'
$env:CSDN_RESUME_FROM_IMAGES='1'
$env:CSDN_MANUAL_EXTRA='<逗号分隔的目标文字>'
python .\tools\csdn_live_verify_flow.py
```

复用同一轮已保存验证码，手动输入坐标，绕过 OCR 和 JFBYM：

```powershell
$env:CSDN_RESUME_FROM_IMAGES='1'
$env:CSDN_MANUAL_POINTS='17,57;145,18;64,19;215,72'
python .\tools\csdn_live_verify_flow.py
```

## 协议细节

已确认的静态部分：

```text
X-Req-Token = prefix16 + MD5(prefix16 + "shyundun")[:16]
verify URL 必须带 ?callback=callback_<timestamp>
verify headers 需要 real_referer: https://passport.csdn.net/v1/register/pc/sendVerifyCode
```

Form 字段：

```text
captcha_protect = gzip(rsa(signKey) + "captcha_protect" + aes(protectJson, signKey))
body = aes(gzip(JSON.stringify({"tracks", "checkPosArr", "randomKey"})), fpv)
fpv = rsa(plain_fpv)
isUpgrade = false
refreshTimes = 0
type = points
wlocation = gzip(JSON.stringify(wlocation))
```

AES 派生：

```text
md5hex = MD5(seed).hexdigest()
key = md5hex[:16]
iv = md5hex[16:]
AES-CBC-PKCS7
```

`body` 使用明文 `fpv` 作为 seed。`captcha_protect` 的 AES seed 是：

```text
signKey = MD5(protect.name + "_" + protect.fpv)
```

## 坐标与轨迹

`checkPosArr` 使用背景图图片相对坐标。

`tracks` 使用页面坐标：

```text
absolute_click = imageOrigin + checkPosArr
imageOrigin = 829,165 in the recovered browser sample
```

合成轨迹中，`t=1` 必须只出现在真实点击点上。每次点击前最后一个移动点要等于目标绝对坐标，因此 `t=1` 点击点满足：

```text
click.x - checkPosArr.x == imageOrigin.x
click.y - checkPosArr.y == imageOrigin.y
```

## 成功与失败解析

响应是 JSONP 时先解析 callback。成功样例：

```json
{"ret":0,"result":"success","yd_captcha_token":"...","code":200}
```

常见失败含义：

```text
点击误差超过容错值 / checkPosArray.size ~= points.size
```

`ret == 0` 不能单独当成成功。

如果返回 WAF HTML 500，优先检查请求形态、callback query、`real_referer`、cookies、challenge headers。

如果 HTTP 200 JSONP 返回点击错误，说明协议提交已被 WAF 接受，阻塞点在目标文字 OCR 或坐标识别。

## 已验证样例

手动坐标成功：

```text
points = 17,57;145,18;64,19;215,72
verify = success
```

JFBYM 300010 成功：

```text
points = 69,117;117,117;219,62;11,67
verify = success
```

PaddleOCR + JFBYM 全自动成功：

```text
PaddleOCR extra = 4 个有序中文字符
JFBYM points = 85,92;158,65;113,13;203,115
verify = success
```

已知不稳定样例：

```text
PaddleOCR extra = 4 个有序中文字符
JFBYM points = 20,10;69,10;113,115;170,97
verify = 点击误差超过容错值
```

这说明该失败来自坐标准确度，不是文字顺序 OCR。

## 产物检查清单

每次运行后重点看：

```text
js_reverse_cache/live_verify_result.json
js_reverse_cache/live_verify_form.json
js_reverse_cache/business_challenge_result.json
js_reverse_cache/captcha_images/convert_image_fetch.json
js_reverse_cache/captcha_images/target_text.json
js_reverse_cache/captcha_images/jfbym_points_result.json
js_reverse_cache/captcha_images/background.jpg
js_reverse_cache/captcha_images/targetImage.png
js_reverse_cache/live_runs/<timestamp>_<images|verify>/
```

不要把 JFBYM token 写进报告或公开日志。
