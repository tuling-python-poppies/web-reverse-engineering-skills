# Decode Action Pipelines

这份文档把常见 decode-action / AST 去混淆流水线的核心结构整理成可复用方法论，供 web-protocol-recovery 的 AST Provider 在实际任务里直接套用。

目标不是绑定某个外部仓库，而是固定下列有效设计：

1. 先识别家族
2. 再选择 plugin 式 pipeline
3. 用多个小 visitor 分轮推进
4. 每轮生成新代码后重新 parse

如果用户明确希望“先别精修，先给我一个能跑的模板把第一版结果打出来”，直接从 bundled script `scripts/decode_action_scaffold.js` 起手，然后再按本文件的家族说明继续加 pass。

## 主入口结构要点

典型主入口大致是：

1. 读取 `input.js`
2. 依次尝试多个 plugin
3. 哪个 plugin 真正改动了代码，就采用哪个结果
4. 输出到 `output.js`

主入口插件顺序以 bundled 代码为准：

1. `sojsonv7`
2. `sojson`
3. `obfuscator`
4. `awsc`
5. `common`

当前 bundled 模板不提供 `ob2` 插件，也不内置独立 `jjencode` plugin；如果命中 jjencode，先剥壳拿到普通 JavaScript，再重新进入上述家族识别。

判定规则是 `isOnlyFamilyMatch`：只有“恰好一个家族”分数达标才会选中该家族，多个家族同时达标时直接回退 `common`。这个顺序体现了一个重要原则：

1. 先试特征强、收益高的家族
2. 再试兜底型通用清理
3. 如果某个家族没有命中，不要强行继续用它的假设做后续替换
4. `plugin=common` 只代表“没有唯一命中的家族”，不代表文件没有混淆；字符串表型样本常因多家族同时命中而回退 `common`

## 家族判定实测（两个真实生产样本）

样本 A：`jsjiami.com.v7` 生成的业务 bundle（单行，约 2736 个 `_0x` 标识符）。
样本 B：obfuscator.io 风格 `page_decrypt` 模块（字符串数组 467 项、双参数 decoder、rotation IIFE）。

对两个样本执行 bundled `scripts/decode_action_scaffold.js`：

- A：`sojsonv7=2`、`obfuscator=2`、`awsc=3` 同时达标 → `plugin=common`
- B：`obfuscator=2`、`awsc=3` 同时达标 → `plugin=common`

两个样本都没有 `split('|')`；B 也没有 `while { switch }`，但都具备“数组函数 + 双参数 decoder + rotation IIFE + 大量别名调用”的字符串表形态。`awsc` 只要 `void`、条件表达式、逻辑 `&&` 中任意两类出现就得 2 分，在真实混淆代码上几乎必然命中，是当前最常见的误路由来源。结论：字符串表型样本先按 skill 根目录的 `references/obfuscation-guide.md` 手工恢复字符串表，再评估是否需要家族 plugin；不要把 `plugin=common` 当作“无混淆”结论。

## 推荐设计

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

`_0x` 前缀不能单独作为任何家族证据。字符串表形态（数组函数 + 双参数 decoder + rotation + 别名调用）是 obfuscator 类的主证据；`split('|')`、已识别的 dispatcher table、`while { switch }` 只是部分版本/混合体的附加形态，缺失它们不能排除 obfuscator。sojson/sojsonv7 至少再要求 `debugger`、`setInterval` 或已确认的前置 decrypt bootstrap 之一——注意 `setInterval` 也是 jsjiami.v7 的反调试特征，会把 jsjiami 误判为 sojsonv7。只有一类证据时回退 common。

额外注意：

1. 运行初始化代码时只执行最小必要片段
2. 最好隔离执行环境，避免直接在宿主进程全局 `eval`
3. 只替换已确认命中的 decrypt call，不要泛化替换普通调用
4. 目录版模板默认关闭 bootstrap 执行；完成用户确认后才使用 `--execute-bootstrap`

jsjiami.com.v6/v7 与 sojson 共享 `_0x` + 字符串表外形，但会自标识：`var _0xodf="jsjiami.com.v7"`，且该字符串同时是数组第 0 项（解码缓存的 key 盐）。jsjiami.v7 的 rotation IIFE 在运行时拼出方法名（`"tfi"+"hs"` 经 transform 得 `shift`），用 `.push(`/`.shift()` token 判断“没有 rotation”会漏掉真实顺序表。替换时必须按别名闭包处理：实测单个 decoder 有 42 个局部别名、823 个调用点；`plugins/sojson.js` 只按引用数选择一个名字，且 sandbox 只执行前 8 条 bootstrap 语句（不含数组函数与 rotation），对 jsjiami.v7 会静默零替换。先按 `references/obfuscation-guide.md` 手工恢复字符串表，再进入本 pipeline。

### obfuscator / obfuscator2

仓库价值在于把“对象分发表 + 控制流存储 + 死代码清理”串成稳定顺序。

字符串表恢复必须先于下面的结构变换：抽取数组函数、decoder、rotation 三个表面，在隔离 vm 中执行 rotation 后再按调用点解码，并按别名闭包替换全部 decoder 调用（完整流程与实测数据见 skill 根目录的 `references/obfuscation-guide.md`）。bundled `obfuscator` plugin 目前只做 dispatcher / 顺序表 / 成员规范化，不包含字符串表恢复；因此对字符串表样本，`plugin=obfuscator` 也不是“已还原字符串”的意思。

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

适合命中信号（按实测强度排序）：

1. 自赋值字符串数组函数 + 双参数 decoder 调用（`decoder(index, key)`）
2. rotation / 自卫 IIFE：`for(;[];)`、`try/catch` 内 `push(shift())`，或运行时拼接方法名
3. 同一 decoder 被大量局部别名引用
4. 大量 `_0x` 前缀、`void 0`、`!![]`
5. `split('|')`、dispatcher table、`while { switch }` 只出现在部分旧版本 / 混合体，缺失它们不能排除 obfuscator 家族

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

自动路由按 `familyScore` 计分：`void`、条件表达式、逻辑 `&&` 各记 1 分，任意两类出现即达标（实测在真实混淆样本上 awsc 恒为 3 分）。由于 scaffold 与目录模板都要求“只有一个家族达标”，awsc 的过度命中会把 obfuscator 等真实家族一起拖回 common；因此 awsc 分数只能当作结构提示，不能当作家族结论。字符串表型样本先恢复字符串表，再人工确认是否真的需要 awsc 结构整形；嵌套 block 拍平只在 `--aggressive` 下启用。

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

建议按下列轮次拆分：

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
