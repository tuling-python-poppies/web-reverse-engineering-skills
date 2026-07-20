# web-protocol-recovery AST Template Project

这是目录化模板，适合已经确认要持续迭代某个混淆目标的场景。

## 目录

```text
template-project/
├── input.js
├── package.json
└── src/
    ├── main.js
    ├── lib/
    │   └── core.js
    ├── plugins/
    │   ├── awsc.js
    │   ├── common.js
    │   ├── obfuscator.js
    │   ├── sojson.js
    │   └── sojsonv7.js
    └── visitors/
        ├── delete-extra.js
        ├── fold-binary.js
        ├── fold-boolean.js
        ├── merge-strings.js
        ├── normalize-member.js
        ├── remove-empty.js
        └── split-sequence.js
```

## 起手

1. 先把整个模板复制到工作单允许的 `js_reverse_cache/ast/` 路径；不要在已安装 skill 内运行。
2. 把目标脚本放到复制后的 `input.js`。
3. 用户批准依赖安装后，在复制目录安装依赖：

```bash
npm install
```

4. 运行：

```bash
npm run decode
```

如果你要自定义输入输出，也可以继续直接用：

```bash
node src/main.js -i input.js -o output.js
```

## 何时用这个模板

1. 你要对某个样本持续补 visitor
2. 你想把家族策略和 visitor 分开维护

## 工作方式

1. `src/main.js` 负责插件路由
2. `src/plugins/*.js` 负责家族级 pipeline
3. `src/visitors/*.js` 负责单一 AST 变换
4. 每加一组 visitor 后，优先 `reparse()` 再进入下一轮

## 当前内置能力

1. `sojson` / `sojsonv7`：默认只做保守 pass；双重信任参数下可执行最小 bootstrap 并按原始 binding 替换解密调用
2. `obfuscator` / `awsc`：仅负责家族识别并运行保守通用 pass
3. `common`：字面量规范化、有限常量折叠、字符串合并、成员访问规范化、受保护的 sequence 拆分和列表内空语句清理。它不删除分支或变量。

## 还需要按样本继续补的地方

1. `sojson` 的 bootstrap 识别偏保守，只覆盖常见“前几句初始化 + 解密函数”结构
2. 对象合并、dispatcher 内联、while-switch 展开和 block 拍平必须在任务缓存中按目标实现，并用负例与语义等价 fixture 约束
3. 复杂 VM/VMP、动态状态机应转插桩

输出路径必须与输入路径不同且尚不存在。模板使用排他发布，绝不覆盖原始输入或已有输出。

## 回归样例

新增或修改 visitor 前，先看 `test-fixtures/README.md`。模板项目建议用小 fixture 回归单个结构，不要直接用大型真实 bundle 当模板回归样本。

## 残留指标

在复制后的缓存项目中，可用只解析、不执行目标代码的工具判断下一步方向：

```bash
npm run metrics -- metrics.json
node src/tools/compare-with-reference.js output.js reference.js compare.json case-id
```

指标覆盖 `.split('|')` 顺序表、loop+switch 平坦化、opcode `if` 链、dispatcher wrapper、`_0x` 标识符和行数。它们只能提示残留结构，不能证明语义正确：行数更少不一定更好；优先保证 parse/reparse、负例和可观察语义。控制流或 dispatcher 指标稳定存在时，才在任务缓存中增加目标专用 visitor；结构已清楚时把重命名放到最后。
