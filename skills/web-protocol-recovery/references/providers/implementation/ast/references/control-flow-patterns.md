# Control Flow Patterns

这份文档不是通用库，而是为当前目标快速落地脚本准备的 visitor 骨架。

## 适用方式

1. 先完成 Step 0，确认命中的是 `dispatcher object`、`while-switch`，还是两者同时存在。
2. 先做字符串恢复和常量折叠，再套用下面的骨架。
3. 骨架只覆盖高频模式；超出边界时保留结构，不要硬还原。

## 推荐流水线

```js
// 伪代码顺序
parse -> restore strings/order table -> fold constants ->
inline dispatcher object -> unwrap while-switch ->
remove dead helpers -> normalize member access -> rename -> generate
```

## Pattern A: dispatcher object

典型输入：

```js
var table = {
  add: function (a, b) { return a + b; },
  call: function (fn, arg) { return fn(arg); },
  text: 'hello'
};

table['add'](x, y);
table['text'];
```

目标输出：

```js
x + y;
'hello';
```

### 骨架

```js
const dispatchMap = new Map();

traverse(ast, {
  VariableDeclarator(path) {
    const { id, init } = path.node;
    if (!t.isIdentifier(id) || !t.isObjectExpression(init)) return;

    const binding = path.scope.getBinding(id.name);
    if (!binding || !binding.constant) return;

    const table = new Map();
    let ok = true;

    for (const prop of init.properties) {
      if (!t.isObjectProperty(prop)) {
        ok = false;
        break;
      }

      const key = t.isIdentifier(prop.key)
        ? prop.key.name
        : t.isStringLiteral(prop.key)
          ? prop.key.value
          : null;
      if (!key) {
        ok = false;
        break;
      }

      table.set(key, prop.value);
    }

    if (ok) dispatchMap.set(id.name, table);
  }
});

traverse(ast, {
  CallExpression(path) {
    const callee = path.node.callee;
    if (!t.isMemberExpression(callee) || !callee.computed) return;
    if (!t.isIdentifier(callee.object) || !t.isStringLiteral(callee.property)) return;

    const table = dispatchMap.get(callee.object.name);
    if (!table) return;

    const value = table.get(callee.property.value);
    if (!value) return;

    if (t.isFunctionExpression(value) || t.isArrowFunctionExpression(value)) {
      const body = value.body;
      if (!t.isBlockStatement(body) || body.body.length !== 1) return;
      const onlyStmt = body.body[0];
      if (!t.isReturnStatement(onlyStmt) || !onlyStmt.argument) return;

      // 这里只替换简单代理函数：return a+b / a&&b / fn(arg) / obj[prop]
      const params = value.params;
      const args = path.node.arguments;
      // 实战里在这里做参数替换，再 replaceWith(克隆后的表达式)
    }
  },

  MemberExpression(path) {
    if (!path.node.computed) return;
    if (!t.isIdentifier(path.node.object) || !t.isStringLiteral(path.node.property)) return;

    const table = dispatchMap.get(path.node.object.name);
    if (!table) return;

    const value = table.get(path.node.property.value);
    if (!value) return;
    if (t.isLiteral(value)) {
      path.replaceWith(t.cloneNode(value, true));
    }
  }
});
```

### 边界

不要自动内联以下情况：

1. 函数体超过一条语句
2. 存在 `this`、`arguments`、闭包变量、赋值副作用
3. 参数替换后会改变求值顺序

## Pattern B: while-switch

典型输入：

```js
var order = '2|0|1'.split('|');
var idx = 0;
while (true) {
  switch (order[idx++]) {
    case '0':
      a();
      continue;
    case '1':
      b();
      continue;
    case '2':
      c();
      continue;
  }
  break;
}
```

目标输出：

```js
c();
a();
b();
```

### 骨架

```js
function stripTrailingControl(stmts) {
  const out = stmts.map(stmt => t.cloneNode(stmt, true));
  while (out.length) {
    const last = out[out.length - 1];
    if (t.isContinueStatement(last) || t.isBreakStatement(last)) {
      out.pop();
      continue;
    }
    break;
  }
  return out;
}

traverse(ast, {
  WhileStatement(path) {
    const body = path.node.body;
    if (!t.isBlockStatement(body) || body.body.length !== 1) return;
    const stmt = body.body[0];
    if (!t.isSwitchStatement(stmt)) return;

    const disc = stmt.discriminant;
    if (!t.isMemberExpression(disc)) return;
    if (!t.isIdentifier(disc.object)) return;

    let orderName = null;
    let indexName = null;

    if (t.isUpdateExpression(disc.property) && t.isIdentifier(disc.property.argument)) {
      orderName = disc.object.name;
      indexName = disc.property.argument.name;
    } else if (t.isIdentifier(disc.property)) {
      orderName = disc.object.name;
      indexName = disc.property.name;
    }
    if (!orderName || !indexName) return;

    const orderBinding = path.scope.getBinding(orderName);
    if (!orderBinding) return;
    const orderInit = orderBinding.path.node.init;
    if (!t.isCallExpression(orderInit)) return;
    if (!t.isMemberExpression(orderInit.callee)) return;
    if (!t.isStringLiteral(orderInit.callee.object)) return;
    if (!t.isIdentifier(orderInit.callee.property, { name: 'split' })) return;
    if (orderInit.arguments.length !== 1 || !t.isStringLiteral(orderInit.arguments[0], { value: '|' })) return;

    const order = orderInit.callee.object.value.split('|');
    const caseMap = new Map();
    for (const item of stmt.cases) {
      const key = t.isStringLiteral(item.test) || t.isNumericLiteral(item.test)
        ? String(item.test.value)
        : null;
      if (key !== null) caseMap.set(key, item);
    }

    const replaceBody = [];
    for (const key of order) {
      const switchCase = caseMap.get(key);
      if (!switchCase) return;
      replaceBody.push(...stripTrailingControl(switchCase.consequent));
    }

    path.replaceWithMultiple(replaceBody);

    // 后续可根据 binding.referenced 再清理 order / idx
    path.scope.crawl();
  }
});
```

### 边界

以下情况不要直接展开：

1. 判别式依赖运行时 `state` 计算，不是静态顺序表
2. `case` 中既改写状态又跳转到下一轮
3. 多层 while-switch 共享同一状态变量

## 清理顺序

控制流展开完成后，建议立即做：

1. 删除已失效的顺序表绑定、索引变量、dispatcher object
2. 重新 `scope.crawl()`
3. 再跑一轮常量折叠和死代码删除
4. 最后再做 `obj['x'] -> obj.x` 和模式化重命名

## 最小交付物

面对一份实际混淆代码，至少交付：

1. `<target-project>/scripts/deobfuscate_target.js`
2. `intermediate/target_step4.js`
3. `source/deobfuscated/target_deobf.js`
4. 对残留未还原结构的简短说明
