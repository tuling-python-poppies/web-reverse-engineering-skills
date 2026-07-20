#!/usr/bin/env node
/**
 * VM browser gap diagnosis tool.
 * 在 Node.js VM 兼容性环境中执行已信任的目标 JS，诊断缺失的浏览器属性。
 * node:vm 不是安全隔离边界，必须显式传入 --trusted-code。
 *
 * 用法:
 *   node vm-browser-gap-diagnose.js --trusted-code target.js
 *   node vm-browser-gap-diagnose.js --trusted-code --env bom/navigator-fingerprint.js,bom/web-crypto.js target.js
 *   node vm-browser-gap-diagnose.js --trusted-code --env bom/navigator-fingerprint.js --env dom/document-dom-runtime.js target.js
 *
 * 输出: JSON 到 stdout
 *   {
 *     "success": true/false,
 *     "error": null | "错误信息",
 *     "undefinedPaths": ["window.crypto.getRandomValues", ...],
 *     "moduleLoadErrors": [{ "module": "...", "path": "...", "error": "..." }],
 *     "stats": { "get": N, "set": N, "call": N, "construct": N, "total": N },
 *     "consoleOutput": [["log", "msg"], ["error", "msg"], ...]
 *   }
 */

import vm from 'vm';
import { webcrypto } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ─── 参数解析 ─────────────────────────────────────────────
const args = process.argv.slice(2);
const workerTokenIndex = args.indexOf('--internal-worker-token');
const workerToken = workerTokenIndex >= 0 ? args[workerTokenIndex + 1] : null;
const internalWorker = Boolean(
  workerToken && process.env.WPR_DIAGNOSE_INTERNAL_WORKER_TOKEN === workerToken,
);
let targetFile = null;
let envModules = [];
let timeout = 60000;
let quiet = false;
let profileName = null;
let profileFile = null;
let trustedCode = false;

for (let i = 0; i < args.length; i++) {
  const arg = args[i];
  if ((arg === '--env' || arg === '-e') && i + 1 < args.length) {
    // 支持逗号分隔和多次 --env
    envModules.push(...args[++i].split(',').map(s => s.trim()).filter(Boolean));
  } else if (arg === '--timeout' && i + 1 < args.length) {
    timeout = parseInt(args[++i], 10);
  } else if (arg === '--profile' && i + 1 < args.length) {
    profileName = args[++i];
  } else if (arg === '--profile-file' && i + 1 < args.length) {
    profileFile = args[++i];
  } else if (arg === '--quiet' || arg === '-q') {
    quiet = true;
  } else if (arg === '--trusted-code') {
    trustedCode = true;
  } else if (arg === '--internal-worker-token' && i + 1 < args.length) {
    i++;
  } else if (arg === '--help' || arg === '-h') {
    console.log(`用法: node vm-browser-gap-diagnose.js [选项] <目标脚本>

选项:
  --env, -e <模块列表>      加载的 env 模块（逗号分隔或多次指定）
                            内置路径相对于 skill/env/；项目模块必须位于
                            js_reverse_cache/env/，也可传入已审查的绝对路径
  --timeout <毫秒>          执行超时（默认 60000）
  --profile <名称>          加载 skill/profiles/<名称>.json
  --profile-file <路径>     加载自定义 profile JSON
  --trusted-code           确认目标和自定义 env 模块已审查且受信任
                           node:vm 不提供安全隔离
  --quiet, -q              不输出日志到 stderr
  --help, -h               显示帮助

示例:
  node vm-browser-gap-diagnose.js --trusted-code target.js
  node vm-browser-gap-diagnose.js --trusted-code --env bom/navigator-fingerprint.js,bom/web-crypto.js target.js
  node vm-browser-gap-diagnose.js --trusted-code --profile default --env bom/navigator-fingerprint.js,bom/screen-fingerprint.js target.js
  node vm-browser-gap-diagnose.js --trusted-code --env bom/navigator-fingerprint.js --env dom/document-dom-runtime.js target.js`);
    process.exit(0);
  } else if (!targetFile) {
    targetFile = arg;
  }
}

if (!targetFile) {
  console.error('错误: 请提供目标脚本文件');
  process.exit(1);
}

if (!trustedCode) {
  console.error('错误: 拒绝执行未确认的代码。node:vm 不是安全沙箱；仅在目标和自定义 env 模块已审查且受信任时传入 --trusted-code');
  process.exit(1);
}

if (!Number.isInteger(timeout) || timeout <= 0) {
  console.error('错误: --timeout 必须是正整数');
  process.exit(1);
}

if (!internalWorker) {
  const forwardedArgs = [];
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--internal-worker-token') {
      i++;
      continue;
    }
    forwardedArgs.push(args[i]);
  }
  const internalToken = webcrypto.randomUUID();
  const worker = spawnSync(process.execPath, [__filename, ...forwardedArgs, '--internal-worker-token', internalToken], {
    encoding: 'utf8',
    timeout,
    maxBuffer: 16 * 1024 * 1024,
    windowsHide: true,
    env: { ...process.env, WPR_DIAGNOSE_INTERNAL_WORKER_TOKEN: internalToken },
  });
  if (worker.error?.code === 'ETIMEDOUT' || worker.error?.code === 'ENOBUFS') {
    const message = worker.error.code === 'ETIMEDOUT'
      ? `Async execution timed out after ${timeout}ms`
      : 'Worker output exceeded the 16 MiB protocol limit';
    const result = {
      success: false,
      error: message,
      undefinedPaths: [],
      moduleLoadErrors: [],
      stats: { get: 0, set: 0, call: 0, construct: 0, total: 0 },
      consoleOutput: [],
    };
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
    process.exit(1);
  }
  if (worker.stdout) process.stdout.write(worker.stdout);
  if (worker.stderr) process.stderr.write(worker.stderr);
  if (worker.error) {
    console.error(`错误: 诊断 worker 启动失败: ${worker.error.message}`);
    process.exit(1);
  }
  process.exit(worker.status ?? 1);
}

// ─── 定位框架目录 ─────────────────────────────────────────
function findSkillDir() {
  // skill 自包含，env 目录固定在 skill 根目录下
  const skillRoot = path.resolve(__dirname, '..');
  const envDir = path.join(skillRoot, 'env');
  if (!fs.existsSync(path.join(envDir, 'core', 'proxy-access-monitor.js'))) {
    console.error(`错误: env 目录不完整，缺少 core/proxy-access-monitor.js: ${envDir}`);
    process.exit(1);
  }
  return skillRoot;
}

const FRAMEWORK = findSkillDir();
const ENV_DIR = path.join(FRAMEWORK, 'env');
const PROFILE_DIR = path.join(FRAMEWORK, 'profiles');

function log(msg) {
  if (!quiet) process.stderr.write(msg + '\n');
}

function resolveEnvModule(mod) {
  if (path.isAbsolute(mod)) return mod;

  const normalized = mod.replace(/\\/g, '/');
  const segments = normalized.split('/');
  if (segments.some(segment => !segment || segment === '.' || segment === '..')) {
    throw new Error('env module path contains an empty or traversal segment');
  }

  const builtinRoots = new Set(['bom', 'core', 'dom', 'encoding', 'timer', 'webapi']);
  const builtinSegments = segments[0] === 'env' ? segments.slice(1) : segments;
  if (builtinRoots.has(builtinSegments[0])) {
    return path.join(ENV_DIR, ...builtinSegments);
  }

  if (segments[0] === 'js_reverse_cache' && segments[1] === 'env' && segments.length > 2) {
    const projectRoot = path.resolve(process.cwd());
    const projectEnvRoot = path.resolve(projectRoot, 'js_reverse_cache', 'env');
    const candidate = path.resolve(process.cwd(), ...segments);
    if (candidate === projectEnvRoot || !candidate.startsWith(`${projectEnvRoot}${path.sep}`)) {
      throw new Error('project env module escapes js_reverse_cache/env/');
    }

    let current = projectRoot;
    for (const segment of segments) {
      current = path.join(current, segment);
      if (!fs.existsSync(current)) break;
      if (fs.lstatSync(current).isSymbolicLink()) {
        throw new Error('project env module path contains a symlink or junction');
      }
    }

    if (fs.existsSync(candidate)) {
      const realProjectRoot = fs.realpathSync.native(projectRoot);
      const realEnvRoot = fs.realpathSync.native(projectEnvRoot);
      const realCandidate = fs.realpathSync.native(candidate);
      const envRelative = path.relative(realProjectRoot, realEnvRoot);
      const candidateRelative = path.relative(realEnvRoot, realCandidate);
      if (!envRelative || envRelative.startsWith('..') || path.isAbsolute(envRelative)
          || !candidateRelative || candidateRelative.startsWith('..') || path.isAbsolute(candidateRelative)) {
        throw new Error('project env module real path escapes the project boundary');
      }
    }
    return candidate;
  }

  throw new Error('relative custom env modules must be under js_reverse_cache/env/');
}

// ─── 创建沙箱 ─────────────────────────────────────────────
const consoleOutput = [];
const scheduledTasks = [];
const activeTimerIds = new Set();
const pendingHostOperations = new Set();
let nextTimerId = 1;
let virtualTime = 0;
let consoleTruncated = false;

function captureConsole(level, ...values) {
  if (consoleOutput.length >= 999) {
    if (!consoleTruncated) consoleOutput.push(['warn', '[console output truncated]']);
    consoleTruncated = true;
    return;
  }
  consoleOutput.push([
    level,
    ...values.map(value => typeof value === 'string' && value.length > 65536
      ? `${value.slice(0, 65536)}... [truncated]`
      : value),
  ]);
}

function scheduleTask(kind, callback, delay, callbackArgs) {
  const id = nextTimerId++;
  const numericDelay = Number(delay);
  const normalizedDelay = Number.isFinite(numericDelay) && numericDelay > 0 ? numericDelay : 0;
  scheduledTasks.push({
    id,
    kind,
    callback,
    dueTime: virtualTime + normalizedDelay,
    callbackArgs,
  });
  activeTimerIds.add(id);
  return id;
}

function cancelTask(id) {
  activeTimerIds.delete(id);
}

function trackHostOperation(value) {
  const operation = Promise.resolve(value);
  pendingHostOperations.add(operation);
  operation.then(
    () => pendingHostOperations.delete(operation),
    () => pendingHostOperations.delete(operation),
  );
  return operation;
}

const trackedSubtle = {};
for (const name of [
  'decrypt', 'deriveBits', 'deriveKey', 'digest', 'encrypt', 'exportKey',
  'generateKey', 'importKey', 'sign', 'unwrapKey', 'verify', 'wrapKey',
]) {
  trackedSubtle[name] = (...operationArgs) => trackHostOperation(webcrypto.subtle[name](...operationArgs));
}

const sandbox = {
  console: {
    log:   (...a) => captureConsole('log',   ...a),
    error: (...a) => captureConsole('error', ...a),
    warn:  (...a) => captureConsole('warn',  ...a),
    info:  (...a) => captureConsole('info',  ...a),
    debug: (...a) => captureConsole('debug', ...a),
    trace: (...a) => captureConsole('trace', ...a),
    dir:   (...a) => captureConsole('dir',   ...a),
    table: (...a) => captureConsole('table', ...a),
    group:          (...a) => {},
    groupCollapsed: (...a) => {},
    groupEnd:       ()     => {},
    time:           ()     => {},
    timeEnd:        ()     => {},
    timeLog:        ()     => {},
    count:          ()     => {},
    countReset:     ()     => {},
    assert:         ()     => {},
    clear:          ()     => {},
  },
  setTimeout:    (fn, delay, ...callbackArgs) => scheduleTask('timeout', fn, delay, callbackArgs),
  setInterval:   (fn, delay, ...callbackArgs) => scheduleTask('interval', fn, delay, callbackArgs),
  clearTimeout:  cancelTask,
  clearInterval: cancelTask,
  atob: (str) => Buffer.from(str, 'base64').toString('binary'),
  btoa: (str) => Buffer.from(str, 'binary').toString('base64'),
  XMLHttpRequest: class XMLHttpRequest {
    constructor() { this.bdmsInvokeList = []; }
    open() {}
    send() {}
    setRequestHeader() {}
    getResponseHeader() { return null; }
    getAllResponseHeaders() { return ''; }
    addEventListener() {}
    removeEventListener() {}
  },
  __WPR_HOST_WEBCRYPTO__: Object.freeze({
    subtle: Object.freeze(trackedSubtle),
    getRandomValues: webcrypto.getRandomValues.bind(webcrypto),
    randomUUID: webcrypto.randomUUID.bind(webcrypto),
  }),
  __output__: consoleOutput,
};

sandbox.window = sandbox;
sandbox.global = sandbox;
sandbox.globalThis = sandbox;
sandbox.self = sandbox;

const context = vm.createContext(sandbox, { microtaskMode: 'afterEvaluate' });
vm.runInContext(
  'globalThis.queueMicrotask ||= callback => { Promise.resolve().then(callback); }',
  context,
  { timeout },
);

function remainingTimeout(deadline) {
  const remaining = deadline - Date.now();
  if (remaining <= 0) {
    throw new Error(`Async execution timed out after ${timeout}ms`);
  }
  return remaining;
}

function takeNextScheduledTask() {
  let nextIndex = -1;
  for (let i = 0; i < scheduledTasks.length; i++) {
    const task = scheduledTasks[i];
    if (!activeTimerIds.has(task.id)) continue;
    if (nextIndex === -1) {
      nextIndex = i;
      continue;
    }
    const current = scheduledTasks[nextIndex];
    if (task.dueTime < current.dueTime ||
        (task.dueTime === current.dueTime && task.id < current.id)) {
      nextIndex = i;
    }
  }

  if (nextIndex === -1) return null;
  const [task] = scheduledTasks.splice(nextIndex, 1);
  activeTimerIds.delete(task.id);
  return task;
}

function hasScheduledTasks() {
  return scheduledTasks.some(task => activeTimerIds.has(task.id));
}

function trackAsyncResult(value, label, pendingStates, deadline) {
  const state = { label, settled: false, rejected: false, error: null };
  pendingStates.add(state);
  sandbox.__diagnoseTrackedValue__ = value;
  sandbox.__diagnoseTrackedState__ = state;
  try {
    vm.runInContext(
      `((value, state) => {
        Promise.resolve(value).then(
          () => { state.settled = true; },
          error => { state.error = error; state.rejected = true; state.settled = true; },
        );
      })(__diagnoseTrackedValue__, __diagnoseTrackedState__)`,
      context,
      { timeout: remainingTimeout(deadline) },
    );
  } finally {
    delete sandbox.__diagnoseTrackedValue__;
    delete sandbox.__diagnoseTrackedState__;
  }
}

function settleCompletedStates(pendingStates) {
  for (const state of [...pendingStates]) {
    if (!state.settled) continue;
    pendingStates.delete(state);
    if (state.rejected) {
      if (state.error && (typeof state.error === 'object' || typeof state.error === 'function')) {
        throw state.error;
      }
      throw new Error(`Async rejection from ${state.label}: ${String(state.error)}`);
    }
  }
}

function cleanupScheduledTasks(deadline) {
  try {
    if (Date.now() < deadline) {
      vm.runInContext(
        'typeof __clearAllTimers__ === "function" ? __clearAllTimers__() : undefined',
        context,
        { timeout: remainingTimeout(deadline) },
      );
    }
  } catch (_) {}
  activeTimerIds.clear();
  scheduledTasks.length = 0;
  delete sandbox.__diagnoseTimerCallback__;
  delete sandbox.__diagnoseTimerArgs__;
}

async function drainAsyncExecution(initialResult, deadline) {
  const maxCallbacks = 1000;
  const pendingStates = new Set();
  let processed = 0;
  trackAsyncResult(initialResult, 'target', pendingStates, deadline);

  try {
    while (true) {
      settleCompletedStates(pendingStates);
      const task = takeNextScheduledTask();

      if (!task) {
        vm.runInContext('void 0', context, { timeout: remainingTimeout(deadline) });
        settleCompletedStates(pendingStates);
        if (pendingStates.size === 0 && pendingHostOperations.size === 0) break;
        if (!hasScheduledTasks()) {
          await new Promise(resolve => setTimeout(resolve, Math.min(1, remainingTimeout(deadline))));
        }
        continue;
      }

      if (processed >= maxCallbacks) {
        throw new Error(`Scheduled callback limit exceeded (${maxCallbacks})`);
      }

      virtualTime = task.dueTime;
      let callbackResult;
      if (typeof task.callback === 'function') {
        sandbox.__diagnoseTimerCallback__ = task.callback;
        sandbox.__diagnoseTimerArgs__ = task.callbackArgs;
        callbackResult = vm.runInContext(
          '__diagnoseTimerCallback__(...__diagnoseTimerArgs__)',
          context,
          { timeout: remainingTimeout(deadline) },
        );
      } else {
        callbackResult = vm.runInContext(
          String(task.callback),
          context,
          { timeout: remainingTimeout(deadline) },
        );
      }
      trackAsyncResult(callbackResult, `${task.kind}#${task.id}`, pendingStates, deadline);
      processed++;
    }
  } finally {
    cleanupScheduledTasks(deadline);
  }
}

// ─── 加载 Profile ──────────────────────────────────────────
if (profileName || profileFile) {
  const profilePath = profileFile
    ? path.resolve(profileFile)
    : path.join(PROFILE_DIR, `${profileName}.json`);

  if (!fs.existsSync(profilePath)) {
    console.error(`错误: profile 不存在: ${profilePath}`);
    process.exit(1);
  }

  try {
    sandbox.__profile__ = JSON.parse(fs.readFileSync(profilePath, 'utf-8'));
    log(`[diagnose] 加载 profile: ${sandbox.__profile__.meta?.name || profileName || profilePath}`);
  } catch (e) {
    console.error(`错误: profile 解析失败: ${e.message}`);
    process.exit(1);
  }
}

// ─── 加载 ProxyMonitor ────────────────────────────────────
const proxyMonitorPath = path.join(ENV_DIR, 'core', 'proxy-access-monitor.js');
if (!fs.existsSync(proxyMonitorPath)) {
  console.error(`错误: proxy-access-monitor.js 不存在: ${proxyMonitorPath}`);
  process.exit(1);
}

log('[diagnose] 加载 ProxyMonitor...');
vm.runInContext(fs.readFileSync(proxyMonitorPath, 'utf-8'), context, { timeout });

const profileManagerPath = path.join(ENV_DIR, 'core', 'profile-seed-manager.js');
if ((profileName || profileFile) && fs.existsSync(profileManagerPath)) {
  log('[diagnose] 加载 ProfileManager...');
  vm.runInContext(fs.readFileSync(profileManagerPath, 'utf-8'), context, { timeout });
}

// Always establish a monitored baseline. Built-in roots are configurable so
// selected env modules can replace them before the roots are wrapped again.
const proxyEnvPath = path.join(ENV_DIR, 'core', 'minimal-proxy-browser-env.js');
if (fs.existsSync(proxyEnvPath)) {
  log('[diagnose] 加载 ProxyEnv（可被 env 模块覆盖的监控基线）...');
  vm.runInContext(fs.readFileSync(proxyEnvPath, 'utf-8'), context, { timeout });
}

// ─── 加载用户指定的 env 模块 ──────────────────────────────
const moduleLoadErrors = [];

for (const mod of envModules) {
  // 支持 skill 内模块、受限项目缓存路径或已审查的绝对路径。
  let modPath;
  try {
    modPath = resolveEnvModule(mod);
  } catch (e) {
    moduleLoadErrors.push({ module: mod, path: null, error: e.message || String(e) });
    log(`[diagnose] 模块路径被拒绝 ${mod}: ${e.message}`);
    continue;
  }

  if (!fs.existsSync(modPath)) {
    const error = { module: mod, path: modPath, error: 'module not found' };
    moduleLoadErrors.push(error);
    log(`[diagnose] 错误: 模块不存在: ${modPath}`);
    continue;
  }

  log(`[diagnose] 加载 env 模块: ${mod}`);
  try {
    vm.runInContext(fs.readFileSync(modPath, 'utf-8'), context, { timeout });
  } catch (e) {
    moduleLoadErrors.push({ module: mod, path: modPath, error: e.message || String(e) });
    log(`[diagnose] 加载模块失败 ${mod}: ${e.message}`);
  }
}

try {
  vm.runInContext('delete globalThis.__WPR_HOST_WEBCRYPTO__', context, { timeout });
} catch (e) {
  moduleLoadErrors.push({ module: '<host-webcrypto-cleanup>', path: proxyEnvPath, error: e.message || String(e) });
}

// Modules commonly replace ProxyEnv roots with plain objects. Re-wrap those
// roots so every diagnose iteration keeps the same missing-property signal.
try {
  vm.runInContext(`
    (() => {
      const roots = [
        'document', 'navigator', 'location', 'history', 'screen',
        'localStorage', 'sessionStorage', 'crypto', 'performance'
      ];
      for (const name of roots) {
        const descriptor = Object.getOwnPropertyDescriptor(globalThis, name);
        if (descriptor && !Object.prototype.hasOwnProperty.call(descriptor, 'value')) {
          if (!descriptor.configurable || typeof descriptor.get !== 'function') continue;
          const originalGet = descriptor.get;
          const monitoredGet = function() {
            const value = Reflect.apply(originalGet, this, []);
            if (value === null || (typeof value !== 'object' && typeof value !== 'function')) return value;
            return watch(value, name);
          };
          Object.defineProperty(globalThis, name, {
            get: monitoredGet,
            set: descriptor.set,
            enumerable: descriptor.enumerable,
            configurable: true
          });
          continue;
        }
        const value = descriptor ? descriptor.value : globalThis[name];
        if (value === null || (typeof value !== 'object' && typeof value !== 'function')) continue;
        const wrapped = watch(value, name);
        if (!descriptor) {
          globalThis[name] = wrapped;
        } else if (descriptor.writable) {
          globalThis[name] = wrapped;
        } else if (descriptor.configurable) {
          Object.defineProperty(globalThis, name, {
            value: wrapped,
            writable: descriptor.writable,
            enumerable: descriptor.enumerable,
            configurable: true
          });
        }
      }
    })()
  `, context, { timeout });
} catch (e) {
  moduleLoadErrors.push({ module: '<monitor-roots>', path: proxyEnvPath, error: e.message || String(e) });
}

// ─── 清空 ProxyMonitor 日志（env 加载期间的日志不算） ──────
try {
  vm.runInContext('__ProxyMonitor__.clearLogs()', context);
} catch (_) {}

// 也清空 console 输出（env 模块的加载日志不算）
consoleOutput.length = 0;

// 抑制 ProxyMonitor 的 console 输出，但保留 LogStore 记录
// 通过替换 sandbox console 为一个过滤版本
const proxyLogPattern = /^方法: (get|set|has|ownKeys|getOwnPropertyDescriptor|defineProperty|deleteProperty|getPrototypeOf|setPrototypeOf|apply|construct)\s+\|/;
const originalLog = sandbox.console.log;
sandbox.console.log = (...a) => {
  // 过滤掉 ProxyMonitor 的结构化日志
  if (typeof a[0] === 'string' && proxyLogPattern.test(a[0])) return;
  if (typeof a[0] === 'string' && a[0].startsWith('[ProxyMonitor]')) return;
  originalLog(...a);
};

// ─── 执行目标脚本 ─────────────────────────────────────────
const targetPath = path.resolve(targetFile);
if (!fs.existsSync(targetPath)) {
  console.error(`错误: 目标脚本不存在: ${targetPath}`);
  process.exit(1);
}

const code = fs.readFileSync(targetPath, 'utf-8');

let success = moduleLoadErrors.length === 0;
let errorMsg = success
  ? null
  : `Failed to load ${moduleLoadErrors.length} env module(s)`;
const unhandledAsyncErrors = [];
const handleUnhandledRejection = reason => {
  unhandledAsyncErrors.push(reason);
};

if (success) {
  log(`[diagnose] 执行目标脚本: ${targetFile}`);
  const executionDeadline = Date.now() + timeout;
  process.on('unhandledRejection', handleUnhandledRejection);
  try {
    const result = vm.runInContext(code, context, {
      timeout: remainingTimeout(executionDeadline),
      filename: path.basename(targetFile),
      displayErrors: true,
    });
    await drainAsyncExecution(result, executionDeadline);
    await new Promise(resolve => setImmediate(resolve));
    if (unhandledAsyncErrors.length > 0) {
      const reason = unhandledAsyncErrors[0];
      if (reason && (typeof reason === 'object' || typeof reason === 'function')) {
        throw reason;
      }
      throw new Error(`Unhandled async rejection: ${String(reason)}`);
    }
  } catch (e) {
    success = false;
    // V8 错误格式: "filename:line\n<整行源码>\n<指针>\n\nErrorType: message"
    // 压缩 JS 的源码行可能有几十 KB，必须截断
    const msg = e.message || String(e);
    const MAX_ERROR_LEN = 500;
    if (msg.length > MAX_ERROR_LEN) {
      errorMsg = msg.substring(0, MAX_ERROR_LEN) + '... [truncated]';
    } else {
      errorMsg = msg;
    }
    // 提取 stack 中有用的帧信息（跳过源码行）
    if (e.stack) {
      const frames = e.stack.split('\n').filter(line =>
        line.trim().startsWith('at ') || line.match(/^\w*Error:/)
      ).slice(0, 5);
      if (frames.length > 0) {
        errorMsg = frames.join('\n');
      }
    }
  } finally {
    process.off('unhandledRejection', handleUnhandledRejection);
  }
} else {
  log('[diagnose] env 模块加载失败，跳过目标脚本');
}

// ─── 收集诊断结果 ─────────────────────────────────────────
let stats = { get: 0, set: 0, call: 0, construct: 0, total: 0 };
let undefinedPaths = [];

try {
  stats = vm.runInContext('__ProxyMonitor__.getStats()', context);
} catch (_) {}

// 从 getLogs('get') 中提取 valueType === 'undefined' 的条目
try {
  const getLogs = vm.runInContext('__ProxyMonitor__.getLogs("get")', context);
  if (Array.isArray(getLogs)) {
    const seen = new Set();
    for (const entry of getLogs) {
      if (entry.valueType === 'undefined' && entry.propertyType === 'string') {
        const fullPath = `${entry.object}.${entry.property}`;
        if (!seen.has(fullPath)) {
          seen.add(fullPath);
          undefinedPaths.push(fullPath);
        }
      }
    }
  }
} catch (_) {}

// 对 consoleOutput 做序列化安全处理
function boundedString(value, budget) {
  if (budget.remaining <= 0) return '[Truncated]';
  const limit = Math.min(value.length, budget.remaining, 16384);
  budget.remaining -= limit;
  return limit < value.length ? `${value.slice(0, limit)}... [truncated]` : value;
}

function toJsonSafe(value, seen, budget, depth = 0) {
  if (typeof value === 'bigint') return boundedString(`${value}n`, budget);
  if (typeof value === 'symbol' || typeof value === 'function') return boundedString(String(value), budget);
  if (typeof value === 'string') return boundedString(value, budget);
  if (value === undefined || value === null || typeof value !== 'object') return value;
  if (depth >= 8) return '[Max depth]';
  if (seen.has(value)) return '[Circular]';
  seen.add(value);
  if (Array.isArray(value)) return value.slice(0, 1000).map(item => toJsonSafe(item, seen, budget, depth + 1));
  const copy = {};
  for (const key of Object.keys(value).slice(0, 1000)) {
    try { copy[key] = toJsonSafe(value[key], seen, budget, depth + 1); }
    catch (error) { copy[key] = `[Unserializable: ${error.message || String(error)}]`; }
  }
  return copy;
}

const consoleBudget = { remaining: 1024 * 1024 };
const safeConsoleOutput = consoleOutput.map(entry => entry.map(item => toJsonSafe(item, new WeakSet(), consoleBudget)));

// ─── 输出 JSON ────────────────────────────────────────────
const result = {
  success,
  error: errorMsg,
  undefinedPaths,
  moduleLoadErrors,
  stats,
  consoleOutput: safeConsoleOutput,
};

console.log(JSON.stringify(result, null, 2));
process.exit(success ? 0 : 1);
