# Webpack Module Extraction

当已定位的加密入口位于 webpack bundle 中时使用。入口未知时不要先做本流程，返回 blocker 让 web-protocol-recovery 选择侦察 Provider。

## 识别模式

webpack 5 chunk push：

```javascript
(self.webpackChunkapp = self.webpackChunkapp || []).push([["chunkId"], {
  12345: function(module, exports, __webpack_require__) { /* ... */ },
}]);
```

webpack 4 IIFE：

```javascript
(function(modules) { /* runtime */ })({
  0: function(module, exports, __webpack_require__) { /* ... */ },
});
```

## 提取步骤

1. 从已确认的入口函数追溯到模块 ID。
2. 提取入口模块和它的 `__webpack_require__(id)` 依赖。
3. 将模块按 `id: function(module, exports, __webpack_require__) { ... }` 填入 `scripts/webpack-module-runtime.js` 的副本。
4. 在运行入口里先补环境，再 `import runtime from './webpack-module-runtime.js'`，最后调用 `runtime(entryId)`。
5. 报 `webpack module not found` 时，回 bundle 中继续提取缺失 ID。

## 落地位置

把 `webpack-module-runtime.js` 复制到执行代码工作区的 `js_reverse_cache/env/`。如果 `js_reverse_cache/` 不存在，先创建。

`webpack-module-runtime.js` 是 ESM `.js` 文件。复制后确保 `js_reverse_cache/env/package.json` 含 `{ "type": "module" }`，或目标项目根目录已启用 ESM，否则 `import runtime from './webpack-module-runtime.js'` 会在 CommonJS 项目中失败。

## 注意

1. 环境补丁必须在加载目标模块前完成。
2. 不要修改原始 bundle；提取物放到 `js_reverse_cache/source/` 或 `js_reverse_cache/env/`。
3. 如果模块依赖异步 chunk，先记录 chunk 变量名，再决定是否补 chunk push 拦截。
