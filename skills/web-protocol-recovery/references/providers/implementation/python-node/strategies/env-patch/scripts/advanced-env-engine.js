/**
 * advanced-env-engine.js - optional hand-written environment patch engine.
 *
 * Default path remains scripts/vm-browser-gap-diagnose.js + env/ modules.
 * Copy this file into the task js_reverse_cache/env/ and use it only when
 * the advanced path gate is met (native disguise, targeted monitor, or
 * cache-area hand-written verification before promoting mod.js/main.js).
 * Do not edit the skill-tree copy for site patches; patch in the task cache.
 */

const __env__ = (() => {
  const errors = [];
  const undefinedGets = Object.create(null);
  const functionCalls = Object.create(null);
  const successfulGets = Object.create(null);
  const proxyCache = new WeakMap();

  const nativeRef = {
    process,
    Buffer,
    setImmediate,
    clearImmediate,
  };

  const originalToString = Function.prototype.toString;
  const nativeFunctions = new WeakSet();

  function nativeToString() {
    if (nativeFunctions.has(this)) {
      const name = this.name || '';
      return `function ${name}() { [native code] }`;
    }
    return originalToString.call(this);
  }

  Object.defineProperty(nativeToString, 'name', {
    value: 'toString',
    writable: false,
    enumerable: false,
    configurable: true,
  });
  nativeFunctions.add(nativeToString);

  Object.defineProperty(Function.prototype, 'toString', {
    value: nativeToString,
    writable: true,
    enumerable: false,
    configurable: true,
  });

  function setFuncNative(fn, name, len) {
    if (typeof fn !== 'function') return fn;
    if (typeof name === 'number') {
      len = name;
      name = undefined;
    }
    if (typeof name === 'string') {
      Object.defineProperty(fn, 'name', {
        value: name,
        writable: false,
        enumerable: false,
        configurable: true,
      });
    }
    if (typeof len === 'number') {
      Object.defineProperty(fn, 'length', {
        value: len,
        writable: false,
        enumerable: false,
        configurable: true,
      });
    }
    nativeFunctions.add(fn);
    return fn;
  }

  function setObjNative(obj, name) {
    if (!obj || (typeof obj !== 'object' && typeof obj !== 'function')) return obj;
    Object.defineProperty(obj, Symbol.toStringTag, {
      value: name,
      writable: false,
      enumerable: false,
      configurable: true,
    });
    return obj;
  }

  function getNativeProto(ctorName, attrs = {}, opts = {}) {
    const Ctor = setFuncNative(function () {
      throw new TypeError('Illegal constructor');
    }, ctorName, opts.length || 0);

    Object.defineProperty(Ctor, 'prototype', {
      writable: false,
      enumerable: false,
      configurable: false,
    });
    Object.defineProperty(Ctor.prototype, 'constructor', {
      value: Ctor,
      writable: false,
      enumerable: false,
      configurable: true,
    });

    const instance = Object.create(Ctor.prototype);
    setObjNative(instance, ctorName);

    for (const [key, val] of Object.entries(attrs)) {
      if (val && typeof val === 'object' && ('get' in val || 'set' in val || 'value' in val)) {
        Object.defineProperty(instance, key, val);
      } else {
        Object.defineProperty(instance, key, {
          value: val,
          writable: true,
          enumerable: true,
          configurable: true,
        });
      }
    }

    return [Ctor, instance];
  }

  function setProtoAccessor(ctor, propName, getter, setter, enumerable = true) {
    const desc = {
      get: getter,
      enumerable,
      configurable: true,
    };
    if (setter) desc.set = setter;
    Object.defineProperty(ctor.prototype, propName, desc);
  }

  function wrapFunc(obj, method, callback) {
    const original = obj[method];
    const wrapped = function (...args) {
      return callback.call(this, original && original.bind(this), ...args);
    };
    setFuncNative(wrapped, method, original ? original.length : 0);
    obj[method] = wrapped;
    return wrapped;
  }

  function summarize(value) {
    if (value === undefined) return 'undefined';
    if (value === null) return 'null';
    const type = typeof value;
    if (type === 'function') return `fn:${value.name || '?'}`;
    if (type === 'string') return value.length > 60 ? JSON.stringify(value.slice(0, 60) + '...') : JSON.stringify(value);
    if (type === 'number' || type === 'boolean' || type === 'bigint') return String(value);
    if (type === 'symbol') return value.toString();
    if (Array.isArray(value)) return `Array(${value.length})`;
    try {
      const name = value.constructor && value.constructor.name;
      return name && name !== 'Object' ? `[${name}]` : '{...}';
    } catch (_) {
      return '{...}';
    }
  }

  function recordUndefined(path) {
    undefinedGets[path] = (undefinedGets[path] || 0) + 1;
  }

  function recordSuccess(path) {
    successfulGets[path] = (successfulGets[path] || 0) + 1;
  }

  function recordCall(path, args) {
    if (!functionCalls[path]) functionCalls[path] = { count: 0, args: [] };
    const entry = functionCalls[path];
    entry.count += 1;
    if (entry.args.length < 3) {
      const sample = args.map(summarize).join(', ');
      if (!entry.args.includes(sample)) entry.args.push(sample);
    }
  }

  function recordError(path, operation, err) {
    const message = err instanceof Error ? err.message : String(err);
    const key = `${path}|${operation}|${message}`;
    if (!errors.some((item) => `${item.path}|${item.operation}|${item.message}` === key)) {
      errors.push({ path, operation, message });
    }
  }

  const skipProps = new Set([
    'constructor', 'prototype', '__proto__', 'toJSON', 'hasOwnProperty',
    'isPrototypeOf', 'propertyIsEnumerable', 'valueOf', 'inspect', 'then',
    'asymmetricMatch', 'nodeType', '$$typeof', '@@__IMMUTABLE_ITERABLE__@@',
  ]);

  const noRecurseCtors = new Set([
    'ArrayBuffer', 'SharedArrayBuffer', 'DataView', 'Int8Array', 'Uint8Array',
    'Uint8ClampedArray', 'Int16Array', 'Uint16Array', 'Int32Array', 'Uint32Array',
    'Float32Array', 'Float64Array', 'BigInt64Array', 'BigUint64Array', 'Map',
    'Set', 'WeakMap', 'WeakSet', 'Date', 'RegExp', 'Promise', 'Error',
    'TypeError', 'RangeError', 'ReferenceError', 'SyntaxError',
  ]);

  function shouldProxy(obj) {
    if (obj === null || obj === undefined) return false;
    const type = typeof obj;
    if (type !== 'object' && type !== 'function') return false;
    try {
      const name = obj.constructor && obj.constructor.name;
      if (name && noRecurseCtors.has(name)) return false;
    } catch (_) {}
    return true;
  }

  function monitor(target, name, config = {}) {
    const {
      getLog, setLog, log,
      getKeys = [], setKeys = [], keys = [],
      getCb, setCb, cb,
      getParse = (key, value) => value,
      setParse = (key, value) => value,
      handles = {},
    } = config;

    return new Proxy(target, {
      get(obj, prop, receiver) {
        if (typeof prop === 'symbol') return Reflect.get(obj, prop, receiver);
        if (getLog || log) console.log(`[monitor] ${name}.${prop} GET`);
        if (getKeys.includes(prop) || keys.includes(prop)) debugger;
        (getCb || cb)?.(prop, name);
        return getParse(prop, Reflect.get(obj, prop, receiver), obj);
      },
      set(obj, prop, value, receiver) {
        if (typeof prop === 'symbol') return Reflect.set(obj, prop, value, receiver);
        if (setLog || log) console.log(`[monitor] ${name}.${prop} SET =`, value);
        if (setKeys.includes(prop) || keys.includes(prop)) debugger;
        (setCb || cb)?.(prop, value, name);
        return Reflect.set(obj, prop, setParse(prop, value, obj), receiver);
      },
      ...handles,
    });
  }

  function createProxy(target, name, depth = 0) {
    if (depth > 8) return target;
    if (!shouldProxy(target)) return target;
    if (proxyCache.has(target)) return proxyCache.get(target);

    const proxy = new Proxy(target, {
      get(obj, prop, receiver) {
        if (typeof prop === 'symbol') return Reflect.get(obj, prop, receiver);
        if (skipProps.has(prop)) return Reflect.get(obj, prop, receiver);

        const chain = `${name}.${prop}`;
        let value;
        try {
          value = Reflect.get(obj, prop, receiver);
        } catch (err) {
          recordError(chain, 'get', err);
          return undefined;
        }

        if (value === undefined) recordUndefined(chain);
        else recordSuccess(chain);

        if (typeof value === 'function') {
          const needsBind = obj instanceof Map || obj instanceof Set || obj instanceof Date || obj instanceof RegExp || obj instanceof Promise || ArrayBuffer.isView(obj);
          const wrappedFn = function (...args) {
            recordCall(chain, args);
            try {
              const thisArg = this === proxy ? obj : this;
              const result = needsBind ? value.apply(obj, args) : value.apply(thisArg, args);
              return shouldProxy(result) ? createProxy(result, `${chain}()`, depth + 1) : result;
            } catch (err) {
              recordError(chain, 'call', err);
              throw err;
            }
          };
          setFuncNative(wrappedFn, prop);
          return wrappedFn;
        }

        return shouldProxy(value) ? createProxy(value, chain, depth + 1) : value;
      },
      set(obj, prop, value, receiver) {
        try {
          return Reflect.set(obj, prop, value, receiver);
        } catch (err) {
          recordError(`${name}.${String(prop)}`, 'set', err);
          return false;
        }
      },
      has: (obj, prop) => Reflect.has(obj, prop),
      deleteProperty: (obj, prop) => Reflect.deleteProperty(obj, prop),
      getOwnPropertyDescriptor: (obj, prop) => Reflect.getOwnPropertyDescriptor(obj, prop),
      defineProperty: (obj, prop, desc) => Reflect.defineProperty(obj, prop, desc),
      ownKeys: (obj) => Reflect.ownKeys(obj),
      getPrototypeOf: (obj) => Reflect.getPrototypeOf(obj),
      ...(typeof target === 'function' ? {
        apply(fn, thisArg, args) {
          recordCall(name, args);
          try {
            const result = Reflect.apply(fn, thisArg, args);
            return shouldProxy(result) ? createProxy(result, `${name}()`, depth + 1) : result;
          } catch (err) {
            recordError(name, 'call', err);
            throw err;
          }
        },
        construct(fn, args, newTarget) {
          recordCall(`new ${name}`, args);
          try {
            const result = Reflect.construct(fn, args, newTarget);
            return shouldProxy(result) ? createProxy(result, `new ${name}()`, depth + 1) : result;
          } catch (err) {
            recordError(`new ${name}`, 'construct', err);
            throw err;
          }
        },
      } : {}),
    });

    proxyCache.set(target, proxy);
    return proxy;
  }

  function init(config = {}) {
    for (const key of ['process', 'Buffer', '__dirname', '__filename', 'setImmediate', 'clearImmediate']) {
      if (key in global) {
        try {
          Object.defineProperty(global, key, {
            value: undefined,
            writable: false,
            enumerable: false,
            configurable: true,
          });
        } catch (_) {}
      }
    }

    const globals = {};
    if (config.window) {
      globals.window = config.window;
      globals.self = config.window;
      globals.top = config.window;
      globals.parent = config.window;
      globals.globalThis = config.window;
    }
    if (config.document) globals.document = config.document;
    if (config.navigator) globals.navigator = config.navigator;
    if (config.location) globals.location = config.location;

    for (const [key, value] of Object.entries(globals)) {
      Object.defineProperty(global, key, {
        value,
        writable: true,
        configurable: true,
        enumerable: true,
      });
    }
  }

  function report() {
    const lines = [];
    const errorCount = errors.length;
    const undefCount = Object.keys(undefinedGets).length;
    const callCount = Object.keys(functionCalls).length;
    const okCount = Object.keys(successfulGets).length;

    lines.push('');
    lines.push('========== ENV PATCH REPORT ==========');
    lines.push('');
    if (errorCount) {
      lines.push(`[ERRORS] (${errorCount}) - must fix:`);
      for (const item of errors) lines.push(`  ${item.path} [${item.operation}] -> ${item.message}`);
      lines.push('');
    }
    if (undefCount) {
      lines.push(`[UNDEFINED] (${undefCount}) - likely need patching:`);
      for (const [path, count] of Object.entries(undefinedGets).sort((a, b) => b[1] - a[1])) {
        lines.push(`  ${path}  (x${count})`);
      }
      lines.push('');
    }
    if (callCount) {
      lines.push(`[CALLS] (${callCount}) - function calls observed:`);
      for (const [path, info] of Object.entries(functionCalls).sort((a, b) => b[1].count - a[1].count)) {
        const args = info.args.length ? `  args: [${info.args.join('] [')}]` : '';
        lines.push(`  ${path}  (x${info.count})${args}`);
      }
      lines.push('');
    }
    lines.push(`Summary: ${errorCount} errors, ${undefCount} undefined, ${callCount} calls, ${okCount} ok (hidden)`);
    lines.push('=======================================');
    lines.push('');

    console.log(lines.join('\n'));
    return { errors, undefined: undefinedGets, calls: functionCalls };
  }

  function reset() {
    errors.length = 0;
    for (const key of Object.keys(undefinedGets)) delete undefinedGets[key];
    for (const key of Object.keys(functionCalls)) delete functionCalls[key];
    for (const key of Object.keys(successfulGets)) delete successfulGets[key];
  }

  if (process.env.ENV_CORE_AUTO_REPORT !== '0') {
    process.on('exit', report);
  }

  return {
    setFuncNative,
    setObjNative,
    getNativeProto,
    setProtoAccessor,
    wrapFunc,
    monitor,
    createProxy,
    init,
    report,
    reset,
    _reset: reset,
    _nativeRef: nativeRef,
  };
})();

export const setFuncNative = __env__.setFuncNative;
export const setObjNative = __env__.setObjNative;
export const getNativeProto = __env__.getNativeProto;
export const setProtoAccessor = __env__.setProtoAccessor;
export const wrapFunc = __env__.wrapFunc;
export const monitor = __env__.monitor;
export const createProxy = __env__.createProxy;
export const init = __env__.init;
export const report = __env__.report;
export const reset = __env__.reset;
export const _reset = __env__._reset;
export const _nativeRef = __env__._nativeRef;

export default __env__;
