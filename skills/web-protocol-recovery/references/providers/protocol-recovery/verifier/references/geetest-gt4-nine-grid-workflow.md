# Geetest GT4 Nine-Grid Workflow

用于极验 GT4 九宫格 `risk_type=nine` 的同轮 `/load -> 合图切片 -> 识别 -> pow/GCT/w -> /verify` 复现。共享的 bundle 元数据、PoW、GCT、AES/RSA 规则仍以 `geetest-gt4-workflow.md` 为准；本文件只记录九宫格独有的 wire shape、识别约束和模型复用规则。

## 识别信号

- `/load` 请求明确携带 `risk_type=nine`。
- `/load` 响应同时包含 `captcha_type="nine"`、单张合图 `imgs`、提示图数组 `ques`、网格边长 `nine_nums`。
- 当前公开 Demo 的 `nine_nums=3`，答案固定为三格。
- `/verify` 仍复用同轮 `lot_number/payload/process_token/payload_protocol/pt`，并提交动态 `w`。

以下不是九宫格的充分信号：只有 `imgs/ques`、泛称“点选”、页面出现九个视觉元素，或用户仅猜测“可能是九宫格”。必须以 `/load` 的 `risk_type/captcha_type/nine_nums` 共同确认。

## Demo 侦察

`https://gt4.geetest.com/` 默认初始化滑块并先发 `risk_type=slide`。要抓九宫格证据，先在右侧“验证形式选择”中选择“九宫格验证”，再触发验证按钮；随后应观察到新的 `/load?...&risk_type=nine`。不要把默认滑块响应当成九宫格样本，也不要依赖 Demo UI 作为最终交付。

浏览器只用于证据。最终 `/load`、静态资源下载和 `/verify` 都由 Python collector 发出。

## 同轮数据链

1. 请求 `/load`，最小参数为动态 `callback`、`captcha_id`、`client_type=web`、`risk_type=nine`、`lang=zh`。
2. 校验 `status=success`、`captcha_type=nine`、`nine_nums` 为正整数，并冻结同轮 `lot_number/payload/process_token/payload_protocol/pt/pow_detail/static_path/js/gct_path`。
3. 下载 `imgs` 合图、每个 `ques[]` 提示图、当前 raw GCT 和当前 raw `gcaptcha4.js`。
4. 合图按 `round(col * width / count)` / `round(row * height / count)` 边界切为 `count * count` 个瓦片。当前 `count=3`。
5. 识别目标与三格答案，构造 `userresponse`。
6. 复用 GT4 公共 shell：动态 bundle 字段、PoW、raw GCT `biht`、`gee_guard`、`em`、AES-CBC-PKCS7 和 RSA-PKCS1-v1_5。
7. 用同轮外层字段请求 `/verify`。仅当 `status == "success"`、`data.result == "success"`、`data.fail_count == 0` 才通过。

## userresponse Wire Shape

九宫格提交的不是原始格号，也不是像素坐标。零基、从左到右、从上到下的格号转换为 1-based `[row, col]`：

```python
def indices_to_userresponse(indices, count=3):
    return [[index // count + 1, index % count + 1] for index in indices]

# [1, 5, 6] -> [[1, 2], [2, 3], [3, 1]]
```

保留点击顺序。若识别器只输出无序集合，当前服务端样本接受按升序格号构造；遇到语义失败时必须回到浏览器证据确认当前版本是否新增顺序约束，不能在同一 lot 上扫描排列。

## 识别不对称与模型策略

`ques` 是线稿/图标式提示，九宫格瓦片通常是实拍图。用只在瓦片照片上训练的分类模型直接分类 `ques` 容易跨域误判；典型信号是“提示图预测某类别，但该类别在九格上的最高置信度仍接近零”。

当前 hash-bound 模型的稳健策略：

1. 九格各自分类并按 top-1 标签分组。
2. 恰好三格的组唯一时，优先使用瓦片共识。
3. 多个三格组并存时，才用 `ques` 对候选类别的概率裁决。
4. 无三格组时，用 `ques` 目标类别在各瓦片上的置信度排序；若最高仍低于明确阈值，视为提示图误判并使用最大瓦片组。
5. 单轮识别失败不能证明协议错误；新建 fresh lot 做一次受预算约束的重试。禁止在同一 lot 上枚举组合。

模型是实现资产，不是协议字段。case 自带模型和 labels，可离线恢复；加载前必须校验 `MODEL.json` 中的 SHA-256、字节数和类别数。模型更新必须递增 case revision 并重新做 hash cascade、离线测试和新 challenge 语义验证。

## 缓存与离线复用

- case 的 `assets/geetest_nine_model.pt` 与 `assets/labels.txt` 是稳定、hash-bound 资产。
- 项目首次安装时可从 case 离线复制到 `<projectRoot>/models/geetest-v4-nine-grid/`。
- challenge JSONP、bundle、GCT、图片、切片、推理摘要和 verify 响应只写入 `<projectRoot>/js_reverse_cache/**`。
- `torch`、Hugging Face、Ultralytics 和 Matplotlib 的运行缓存必须在显式函数中重定向到 `<projectRoot>/js_reverse_cache/_runtime/**`，不得在 import 时创建目录或修改用户缓存。
- 不允许模型加载器静默访问 `%USERPROFILE%/.cache`、`AppData` 或网络。模型缺失或 hash 不匹配时 fail closed。

## 共享 GT4 Shell

九宫格沿用 `geetest-gt4-workflow.md` 已验证的下列规则，不在此重复硬编码版本样本：

- `pow_msg = version|bits|hashfunc|datetime|captcha_id|lot_number||nonce`
- `_lib` 固定字段和 `lib._abo` lot rule 必须从当前完整 bundle 提取。
- raw GCT 中以 `=5381;` 定位函数并按 JS int32、UTF-16 code unit 语义计算 `biht`。
- `pt=1` 的 AES IV 是 16 个 ASCII 字符 `0`：`b"0000000000000000"`，不是 16 个 NUL 字节。
- `w = aes_ciphertext.hex() + rsa_encrypted_key.hex()`。

## 失败分流

| 症状 | 判断 | 下一步 |
|---|---|---|
| `/load` 返回 slide/word/icon | 不是九宫格同轮 | 重新确认 `risk_type=nine`，不要混轮 |
| `-50002 param decrypt error` | w 加密壳或 RSA/AES 参数错误 | 先检查 ASCII-zero IV、当前公钥、w 拼接顺序 |
| `-50306 process_token Error` | lot 已消费、过期或混轮 | 新建 fresh lot，不复用旧 token |
| `status=success, result=fail, fail_count=1` | w 已解密，答案语义错误 | 查模型输出、三格映射和 userresponse；不用重做 AES |
| `status=success, result=forbidden, fail_count=0` | bundle/GCT/动态字段版本不一致 | 按通用 GT4 bundle 更新流程处理 |
| 提示图类别在九格上全部低置信度 | 线稿/照片域差异导致提示图误判 | 使用瓦片共识或 fresh-lot 失败关闭 |

## 验收

1. `/load` 明确确认 nine subtype，且图片、提示图、bundle、GCT、tokens 全部同轮。
2. 离线测试通过：模型/labels SHA-256、90 类、格号映射、lot rule、PoW 验证、GCT hash 和 AES 固定向量。
3. 模型推理输出恰好三个合法格号，低置信或歧义必须 fail closed 或只做受预算约束的 fresh-lot 重试。
4. live proof 至少一轮 fresh challenge 返回 `status=success`、`data.result=success`、`fail_count=0`；正式 collector 扩大重试前仍需 request-budget 确认。
5. Python 拥有 `/load`、静态资源和 `/verify` 的最终 live egress；模型与本地 helper 无浏览器依赖。
