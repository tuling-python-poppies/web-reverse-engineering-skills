# Node.js Detection Notes

安全 SDK 常通过 Node.js 特征检测运行环境。只在签名格式降级、长度不一致或诊断报告无法解释偏差时读取。

## 常见检测项

### Buffer

浏览器通常没有 `Buffer`，Node.js 有：

```javascript
const originalBuffer = globalThis.Buffer;
delete globalThis.Buffer;
// 目标执行完成后再按需恢复
globalThis.Buffer = originalBuffer;
```

不要用 getter 返回 `undefined` 伪装不存在；某些 VMP 会检查 `Object.getOwnPropertyDescriptor`，accessor 反而暴露异常。

### process

有些 webpack 浏览器包会注入 `process`，有些页面没有。不要盲删，先对照浏览器：

```javascript
const originalProcess = globalThis.process;
globalThis.process = { env: { BROWSER: true, BUILD_ENV: 'production' } };
// 目标执行完成后恢复
globalThis.process = originalProcess;
```

### Error.prepareStackTrace

Node.js V8 特有 API：

```javascript
delete Error.prepareStackTrace;
```

### module / exports / require

CommonJS 特征可能被检测。能从入口依赖数组或加载包装层移除最好；不能时再在运行上下文里隐藏。

### Node 新版内置 Web API

Node 18+ 有 `fetch`，Node 19+ 有 WebCrypto，Node 21+ 有 `navigator`。覆盖全局变量时优先用 `Object.defineProperty`：

```javascript
Object.defineProperty(global, 'navigator', {
  value: proxiedNavigator,
  writable: true,
  configurable: true,
  enumerable: true,
});
```

## toString / toStringTag

```javascript
Object.defineProperty(window, Symbol.toStringTag, { value: 'Window', configurable: true });
Object.defineProperty(document, Symbol.toStringTag, { value: 'HTMLDocument', configurable: true });
```

函数外形先匹配浏览器的 `name` / `length` descriptor，再用诊断器自动加载的全局 `safefunction()` 统一提供 native-looking `Function.prototype.toString`；不要每个函数手写 `toString`。该 helper 用闭包内 `WeakMap` 保存 source，不应改变 `Reflect.ownKeys(func)` 或函数自身 descriptor；把这两项也纳入反射回归。

当模块化路径仍无法统一构造器外形、`toString` 或需要定向 `monitor` 时，在 advanced gate 满足后改用 `scripts/advanced-env-engine.js` 的 `setFuncNative` / `setObjNative` / `getNativeProto`（见 `references/advanced-env-path.md`），不要并行发明第三套 toString 补丁。

## 注意

这些对策不能保证绕过所有检测。VMP 可能在 opcode 层面完成检测，不经过外部 JS API。遇到这种情况，返回该 blocker；只有在新的 work order 将 `references/limitations.md` 选为唯一 Provider-local reference 后再读取。
