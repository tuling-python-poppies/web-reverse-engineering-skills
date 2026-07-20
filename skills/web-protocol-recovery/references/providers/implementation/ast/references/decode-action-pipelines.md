# Decode Action Pipelines

这份文档把 `Decode_action-main` 的核心结构抽成可复用的方法论，供 WPR 的 AST Provider 在实际任务里直接套用。

目标不是照搬仓库代码，而是继承它最有效的设计：

1. 先识别家族
2. 再选择 plugin 式 pipeline
3. 用多个小 visitor 分轮推进
4. 每轮生成新代码后重新 parse

如果用户明确希望“先别精修，先给我一个能跑的模板把第一版结果打出来”，直接从 bundled script `scripts/decode_action_scaffold.js` 起手，然后再按本文件的家族说明继续加 pass。

## 仓库结构要点

`Decode_action-main` 的主入口大致是：

1. 读取 `input.js`
2. 依次尝试多个 plugin
3. 哪个 plugin 真正改动了代码，就采用哪个结果
4. 输出到 `output.js`

主入口插件顺序大意如下：

1. `obfuscator`
2. `ob2`
3. `sojsonv7`
4. `sojson`
5. `awsc`
6. `common`

当前 bundled 模板不内置独立 `jjencode` plugin；如果命中 jjencode，先剥壳拿到普通 JavaScript，再重新进入上述家族识别。

这个顺序体现了一个重要原则：

1. 先试特征强、收益高的家族
2. 再试兜底型通用清理
3. 如果某个家族没有命中，不要强行继续用它的假设做后续替换

## 可以直接借鉴的设计

### 1. Plugin 负责“家族级策略”

plugin 处理的是：

1. 命中条件
2. 家族特有初始化步骤
3. pass 的编排顺序
4. 最终生成选项

skill 中也应该这样做：

1. 主回答只负责路由与交付要求
2. 具体 pass 顺序放到 reference 里
3. 真正写脚本时按目标选择最小组合

补充：对于“库型样本”或“大基础对象”样本，plugin 的第一职责不是尽可能内联，而是先保护运行语义，再逐步提高可读性。

### 2. Visitor 负责“单一结构变换”

仓库里值得借鉴的 visitor 风格：

1. `delete-extra.js`：清理字面量 `extra`
2. `calculate-binary.js`：折叠可静态求值的二元表达式
3. `calculate-rstring.js`：合并或还原字符串表达式
4. `merge-object.js`：把拆散赋值合并回对象字面量
5. `parse-control-flow-storage.js`：处理局部控制流存储或分发表
6. `delete-unused-var.js`：删除未使用变量
7. `delete-illegal-return.js`：修复非法 `return` 等边界结构

skill 中应保持这种拆法：

1. 一个 visitor 只做一类低耦合工作
2. 大改动后重新 parse
3. 高风险 visitor 放在识别更充分的后半段

## 家族级 pipeline

### sojson / sojsonv7

仓库思路可以概括为：

1. 先 parse
2. 清掉字面量噪音
3. 找到全局解密入口并执行初始化代码
4. 只替换解密函数调用与其成员访问
5. 处理局部控制流存储
6. 清理死代码
7. 重新 parse
8. 做可读性整理
9. 清理反调试、自卫、console 限制

适合命中信号：

1. 前几句就是字符串数组、预处理函数、解密函数
2. `_0x...(...)` 高频调用
3. 伴随自卫、debugger、console 封锁

`_0x` 前缀不能单独作为任何家族证据。若同时出现 `split('|')`、已识别的 dispatcher table 或 `while { switch }`，再判为 obfuscator 或混合体；sojson/sojsonv7 至少再要求 `debugger`、`setInterval` 或已确认的前置 decrypt bootstrap 之一。只有一类证据时回退 common。

额外注意：

1. 运行初始化代码时只执行最小必要片段
2. 最好隔离执行环境，避免直接在宿主进程全局 `eval`
3. 只替换已确认命中的 decrypt call，不要泛化替换普通调用
4. 目录版模板默认关闭 bootstrap 执行；完成用户确认后才使用 `--execute-bootstrap`

### obfuscator / obfuscator2

仓库价值在于把“对象分发表 + 控制流存储 + 死代码清理”串成稳定顺序。

推荐顺序：

1. 清理字面量表示
2. 常量折叠
3. 合并对象字典
4. 内联简单 dispatcher property / call
5. 展开顺序表、while-switch
6. 清理 continue/break 尾巴
7. 删除死代码和无引用且初始化器可证明无副作用的变量；副作用初始化器必须保留
8. 规范 `obj['x']` 为 `obj.x`
9. 重新 parse 后再做下一轮

单文件和目录版模板默认只运行低风险规范化。`while-switch-unpack`、`merge-object`、`inline-dispatcher` 都属于显式 aggressive 变换，只有准备语义 fixture、保留中间产物并确认风险后才使用 `--aggressive` 或调用 `runObfuscator(ast, { aggressive: true })`。

适合命中信号：

1. 大量 `_0x` 前缀
2. 大字符串数组
3. `split('|')`
4. `table['xx'](a, b)` / `table['xx']`

### awsc

仓库里的 `awsc.js` 更像“结构整形器”。

重点不是先解字符串，而是先把不好读的表达式结构改回正常控制结构：

1. `void expr` 仅在独立表达式语句中还原；值上下文、sequence argument 和可折叠字符串保留 `void`，避免后续 pass 生成 directive prologue
2. 三元表达式转 `if`
3. `a && b()` 转 `if (a) { b(); }`
4. sequence expression 拆分
5. `if` / `switch` / `return` 归一化
6. 多层 block 拍平

适合命中信号：

1. 控制流不是典型 while-switch，而是表达式级压缩
2. 大量三元、逻辑表达式、sequence expression
3. `void 0`、逗号表达式、嵌套 block 很多

自动路由至少要求 `void`、条件表达式、逻辑 `&&` 三类信号中的两类。只有大量 `void` 仍回退 common；嵌套 block 拍平只在 `--aggressive` 下启用。

### jjencode

`jjencode` 不应和普通 AST 解混淆混在一开始做，当前 bundled 模板也不提供独立 `jjencode` plugin。

推荐流程：

1. 先剥壳拿到正常 JS
2. 再重新识别家族
3. 通常转交给 `common` 或 `obfuscator/sojson` pipeline

### common

这是兜底型 plugin，只做低风险通用步骤：

1. 字面量清理
2. 二元表达式折叠
3. 字符串合并
4. 轻量死代码清理；未使用变量只有在初始化器可证明纯净时才删除

当你还不确定目标属于哪个家族时，可以先跑这组低风险 pass，观察结构是否变清晰。

## 推荐的轮次切分

参考 `Decode_action-main`，建议这样拆：

### Round 1: Detect and Normalize

1. parse
2. 删除 `extra`
3. 初步格式化
4. 统计家族特征

### Round 2: Family Entry Pass

1. sojson 类：运行解密初始化并替换 decrypt 调用
2. obfuscator 类：合并对象和顺序表
3. awsc 类：先做结构整形

### Round 3: Control Flow and Cleanup

1. dispatcher object
2. while-switch
3. 恒定分支删除
4. 空语句删除
5. 未使用变量删除

### Round 4: Readability

1. `obj['x']` 变 `obj.x`
2. sequence 拆分
3. 字符串拼接收敛
4. 条件表达式转正常语句

### Round 5: Residual Runtime Work

如果还剩 VM/VMP、状态机、动态调用，停止硬还原，转插桩。

## 生成选项建议

生成代码时优先：

1. `comments: false`
2. `jsescOption: { minimal: true }`
3. 需要时再开启 `compact`

原因：

1. 最小化 `\x` / `\u` 重新转义
2. 避免把刚恢复的字符串又变回难读形式
3. 便于后续重新 parse 与人工复核

## 从仓库提炼出的实践规则

1. 不要先追求“万能识别器”，先做稳定路由
2. 不要把“运行初始化代码”和“全局执行整份脚本”混为一谈
3. 不要在一个 traverse 里同时做解密、控制流还原、死代码删除
4. 不要因为一类 pass 命中过几次，就默认对所有样本打开
5. 代码变清晰后，优先重新识别家族，再决定下一轮 pass
6. 对阅读版输出，优先做语义别名和关键入口顺序化，不要一开始就把整份库代码深度改写

## 何时退出静态还原

满足任一条件时，应停止继续硬改 AST，改走插桩：

1. case 顺序依赖运行时状态而不是静态顺序表
2. 关键分发函数依赖闭包、环境值或动态生成代码
3. 继续替换会改变求值顺序或副作用
4. 静态结果已经大幅变清晰，但还差最后一跳运行时证据

这时转 `references/instrumentation-patterns.md`。
