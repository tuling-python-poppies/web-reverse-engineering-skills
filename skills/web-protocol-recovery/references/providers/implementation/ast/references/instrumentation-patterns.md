# Instrumentation Patterns

当静态还原已经清掉大部分噪音，但仍然存在 VM/VMP、状态机、动态分发或难以静态证明的控制流时，不要继续硬还原。补一份插桩脚本，帮助拿到运行时证据。

## 何时启用插桩

满足任一条件即可：

1. `while-switch` 的顺序依赖运行时 `state`
2. 大量 `CallExpression` 无法静态确定真实 callee
3. 已恢复出部分可读代码，但关键分支仍靠运行时值驱动
4. 用户目标是“先把签名流程跑通，再继续收敛”

## 交付目标

插桩模式不是替代静态解混淆，而是补一个第二输出：

1. `<target-project>/scripts/instrument_target.js`
2. `intermediate/target_instrumented.js`
3. 一份简短说明：插桩观察点、预期日志、如何继续收敛

注意：带 `<target-project>/` 的路径都是目标项目内生成产物，不是 skill 内置文件。

## 插桩原则

1. 只插高价值点，不要全文件无差别打印
2. 优先记录“状态变化”和“关键调用”，不要只打普通变量
3. 插桩代码本身保持可回退，集中写在一个 pass 里
4. 默认只用 `console.log` 级别的最小插桩，不引入额外运行时依赖
5. 不要为了方便直接 `eval` 外部片段

## 推荐观察点

### 1. 状态机/控制流

适合：`while-switch`、label+continue、VM dispatch loop

关注：

1. 当前 state / case 值
2. state 何时被改写
3. 下一跳目标是什么

骨架：

```js
traverse(ast, {
  SwitchCase(path) {
    const test = path.node.test;
    const label = test && (t.isStringLiteral(test) || t.isNumericLiteral(test))
      ? String(test.value)
      : 'default';

    path.node.consequent.unshift(
      t.expressionStatement(
        t.callExpression(
          t.memberExpression(t.identifier('console'), t.identifier('log')),
          [t.stringLiteral(`[case-enter] ${label}`)]
        )
      )
    );
  }
});
```

### 2. 关键函数调用

适合：签名函数、解密函数、dispatcher call、疑似 VM handler

关注：

1. callee 名称
2. 关键参数
3. 返回值

骨架思路：

```js
// 对目标 CallExpression 外包一层 helper，例如:
// traceCall('decrypt', () => decrypt(a, b))
```

如果不想改求值顺序，优先在函数体入口/出口插日志，而不是直接包裹表达式。

### 3. 赋值与状态迁移

适合：`state = nextState`、`ptr++`、`stack.push(...)`

关注：

1. 哪个变量被改了
2. 改前改后值是什么

骨架：

```js
traverse(ast, {
  AssignmentExpression(path) {
    if (!t.isIdentifier(path.node.left, { name: 'state' })) return;

    path.replaceWith(
      t.sequenceExpression([
        t.callExpression(
          t.memberExpression(t.identifier('console'), t.identifier('log')),
          [t.stringLiteral('[state-before]'), t.identifier('state')]
        ),
        path.node,
        t.callExpression(
          t.memberExpression(t.identifier('console'), t.identifier('log')),
          [t.stringLiteral('[state-after]'), t.identifier('state')]
        )
      ])
    );
  }
});
```

## 生成后重新 parse

插桩 pass 也遵守“生成 -> 重新解析”的规则：

1. 写完插桩后先生成 `target_instrumented.js`
2. 重新 parse 一次，确保插桩没有破坏语法
3. 再运行插桩脚本收集日志

## 不要做的事

1. 不要把所有 `Identifier` 都打印一遍
2. 不要默认给所有函数包日志
3. 不要默认对整个 `window` 或全局对象做大范围代理
4. 不要把插桩脚本当最终交付，除非用户明确就是要动态跟踪版

## 最小交付说明模板

```md
已补充插桩版脚本：`<target-project>/scripts/instrument_target.js`

本轮插桩观察点：
1. switch case 进入顺序
2. state 变量变化
3. decrypt 函数入参与返回值

建议先运行插桩版，确认真实执行顺序后，再回到静态还原继续收敛。
```
