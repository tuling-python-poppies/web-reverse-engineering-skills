# Runtime Hooks

Use for dynamic code, dynamic resources, Worker execution paths, JSON boundaries, and timer-driven logic.

Default to type, length, URL, and stack. Do not print dynamic code, Blob, Worker messages, or JSON content unless the work order explicitly approves raw fields.

## JSON Parse And Stringify

Use when request or response payloads are processed at JSON boundaries.

```js
(function () {
  if (window.__restoreJsonHook) return console.warn('json hook already installed');
  const rawParse = JSON.parse;
  const rawStringify = JSON.stringify;
  JSON.parse = function (text) {
    console.log('[json:parse]', { type: typeof text, length: String(text).length });
    console.trace('[json:parse:stack]');
    return rawParse.apply(this, arguments);
  };
  JSON.stringify = function (value) {
    console.log('[json:stringify]', { type: typeof value });
    console.trace('[json:stringify:stack]');
    return rawStringify.apply(this, arguments);
  };
  window.__restoreJsonHook = function () {
    JSON.parse = rawParse;
    JSON.stringify = rawStringify;
    delete window.__restoreJsonHook;
  };
})();
```

## Safe Console Capture

Use this before the target bundle runs when the page may replace console
methods. It preserves one bound logger without replacing any page API.

```js
(function () {
  'use strict';

  if (Object.prototype.hasOwnProperty.call(window, '__restoreBrowserHookSafeConsole')) {
    return console.warn('[hook] safe console already installed');
  }
  if (!window.console || typeof console.log !== 'function') return;

  const originalLog = console.log;
  const safeLog = originalLog.bind(console);
  const logKey = '__browserHookSafeLog';
  const checkKey = '__browserHookCheckConsole';
  const restoreKey = '__restoreBrowserHookSafeConsole';
  if ([logKey, checkKey, restoreKey].some(function (key) {
    return Object.prototype.hasOwnProperty.call(window, key);
  })) {
    return console.warn('[hook] safe console keys already owned');
  }

  const safeLogFunction = function () {
    return safeLog.apply(null, arguments);
  };
  const checkFunction = function () {
    return console.log === originalLog;
  };
  const restoreFunction = function () {
    if (window[logKey] === safeLogFunction) delete window[logKey];
    else safeLog('[hook] safe log key changed; current owner was preserved');
    if (window[checkKey] === checkFunction) delete window[checkKey];
    else safeLog('[hook] console check key changed; current owner was preserved');
    if (window[restoreKey] === restoreFunction) delete window[restoreKey];
  };
  try {
    Object.defineProperties(window, {
      [logKey]: { configurable: true, writable: false, value: safeLogFunction },
      [checkKey]: { configurable: true, writable: false, value: checkFunction },
      [restoreKey]: { configurable: true, writable: false, value: restoreFunction },
    });
  } catch (error) {
    if (window[logKey] === safeLogFunction) delete window[logKey];
    if (window[checkKey] === checkFunction) delete window[checkKey];
    if (window[restoreKey] === restoreFunction) delete window[restoreKey];
    return safeLog('[hook] safe console installation failed:', error.name);
  }
  safeLog('[hook] safe console capture installed');
})();
```

This is an observation aid, not a console bypass. Install it before a page
replaces `console.log`; if the page has already replaced the method, use the
browser console collector or a page-main-world injection instead.

## eval And Function

Use to locate dynamically generated code. Do not wrap global `eval`; wrapping direct eval turns it into indirect eval and changes lexical scope. In Chrome DevTools Console, prefer command-line breakpoints:

```js
debug(window.eval);
debug(window.Function);

// restore
undebug(window.eval);
undebug(window.Function);
```

`debug` and `undebug` are DevTools command-line APIs. In normal page scripts, snippets, or browsers that do not provide them, use Sources breakpoints or return to entry-point localization instead of an opaque eval wrapper.

To cover generated `Function`, generator, and async-function bodies without
changing direct-eval scope semantics, pause at their constructors and inspect
the last argument in the call frame:

```js
if (typeof debug === 'function' && typeof undebug === 'function') {
  const GeneratorFunction = Object.getPrototypeOf(function* () {}).constructor;
  const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
  debug(window.Function);
  debug(GeneratorFunction);
  debug(AsyncFunction);

  // Restore after the source and caller are recorded.
  // undebug(window.Function);
  // undebug(GeneratorFunction);
  // undebug(AsyncFunction);
} else {
  console.warn('[hook] use Sources constructor breakpoints for dynamic code');
}
```

Do not print generated source automatically. Copy only the bounded source
span needed by the current work order and keep the original call arguments
and return behavior untouched.

The generator/async constructor example requires modern Chromium syntax. On a
legacy WebView, omit those two constructor expressions and use Sources
breakpoints on the syntax that the target engine actually supports.

## Blob And URL.createObjectURL

Use to locate dynamically assembled scripts, images, downloads, and worker
payloads after a MIME or object-URL boundary is known.

```js
(function () {
  'use strict';

  const RESTORE_KEY = '__restoreBlobUrlHook';
  const MIME_FILTER = '';
  if (!MIME_FILTER) return console.warn('[hook] set one MIME_FILTER before installing');
  if (Object.prototype.hasOwnProperty.call(window, RESTORE_KEY)) {
    return console.warn('[hook] Blob/objectURL hook already installed');
  }
  const RawBlob = window.Blob;
  const rawCreateObjectURL = URL.createObjectURL;
  if (typeof RawBlob !== 'function' || typeof rawCreateObjectURL !== 'function') {
    return console.warn('[hook] Blob/objectURL unavailable');
  }

  const wrappedBlob = function (parts, options) {
    const result = Reflect.construct(RawBlob, Array.prototype.slice.call(arguments), new.target || RawBlob);
    try {
      if (typeof result.type === 'string' && result.type.includes(MIME_FILTER)) {
        console.log('[Blob]', { type: result.type, size: result.size });
        console.trace('[Blob:stack]');
        debugger;
      }
    } catch (error) {}
    return result;
  };
  wrappedBlob.prototype = RawBlob.prototype;
  const wrappedCreateObjectURL = function (object) {
    const result = rawCreateObjectURL.apply(this, arguments);
    try {
      if (object && typeof object.type === 'string' && object.type.includes(MIME_FILTER)) {
        console.log('[URL.createObjectURL]', { type: object.type, size: object.size });
        console.trace('[URL.createObjectURL:stack]');
        debugger;
      }
    } catch (error) {}
    return result;
  };
  const restore = function () {
    if (window.Blob === wrappedBlob) window.Blob = RawBlob;
    else console.warn('[hook] Blob slot changed; current owner was preserved');
    if (URL.createObjectURL === wrappedCreateObjectURL) URL.createObjectURL = rawCreateObjectURL;
    else console.warn('[hook] object URL slot changed; current owner was preserved');
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
  };
  try {
    window.Blob = wrappedBlob;
    URL.createObjectURL = wrappedCreateObjectURL;
    Object.defineProperty(window, RESTORE_KEY, { configurable: true, writable: false, value: restore });
  } catch (error) {
    if (window.Blob === wrappedBlob) window.Blob = RawBlob;
    if (URL.createObjectURL === wrappedCreateObjectURL) URL.createObjectURL = rawCreateObjectURL;
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.warn('[hook] Blob/objectURL installation failed:', error.name);
  }
})();
```

If only text Blob parts are relevant, log text-part counts and lengths rather than content:

```js
(function () {
  'use strict';

  const RESTORE_KEY = '__restoreBlobTextHook';
  const MAX_PARTS = 32;
  if (Object.prototype.hasOwnProperty.call(window, RESTORE_KEY)) {
    return console.warn('[hook] Blob text hook already installed');
  }
  const RawBlob = window.Blob;
  if (typeof RawBlob !== 'function') return console.warn('[hook] Blob unavailable');
  const wrappedBlob = function (parts, options) {
    const result = Reflect.construct(RawBlob, Array.prototype.slice.call(arguments), new.target || RawBlob);
    const list = Array.isArray(parts) ? parts.slice(0, MAX_PARTS) : [];
    const textParts = list.filter(function (part) { return typeof part === 'string'; });
    if (textParts.length) {
      console.log('[Blob:text]', { partCount: textParts.length, totalLength: textParts.reduce(function (sum, part) { return sum + part.length; }, 0) });
      console.trace('[Blob:text:stack]');
      debugger;
    }
    return result;
  };
  wrappedBlob.prototype = RawBlob.prototype;
  const restore = function () {
    if (window.Blob === wrappedBlob) window.Blob = RawBlob;
    else console.warn('[hook] Blob slot changed; current owner was preserved');
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
  };
  try {
    window.Blob = wrappedBlob;
    Object.defineProperty(window, RESTORE_KEY, { configurable: true, writable: false, value: restore });
  } catch (error) {
    if (window.Blob === wrappedBlob) window.Blob = RawBlob;
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.warn('[hook] Blob text installation failed:', error.name);
  }
})();
```

## Webpack Chunk Registration

Use when source or initiator evidence already names the webpack chunk global
and module ID. Install after the webpack runtime owns the array's `push`
property. The hook observes future registrations without dumping or executing
module factories.

```js
(function () {
  'use strict';

  const CHUNK_GLOBAL = '';
  const MODULE_ID = '';
  const RESTORE_KEY = '__restoreBrowserHookWebpackChunk';
  if (!CHUNK_GLOBAL || !MODULE_ID) {
    return console.warn('[hook] set one CHUNK_GLOBAL and MODULE_ID before installing');
  }
  const chunks = window[CHUNK_GLOBAL];

  if (Object.prototype.hasOwnProperty.call(window, RESTORE_KEY)) {
    return console.warn('[hook] webpack chunk hook already installed');
  }
  if (!Array.isArray(chunks)) {
    return console.warn('[hook] webpack chunk global unavailable:', CHUNK_GLOBAL);
  }

  const pushDescriptor = Object.getOwnPropertyDescriptor(chunks, 'push');
  if (!pushDescriptor || !pushDescriptor.configurable || typeof pushDescriptor.value !== 'function') {
    return console.warn('[hook] install after webpack owns a configurable push property');
  }

  const rawPush = pushDescriptor.value;
  const wrappedPush = function (payload) {
    const result = rawPush.apply(this, arguments);
    try {
      const modules = Array.isArray(payload) ? payload[1] : null;
      if (modules && typeof modules === 'object'
          && Object.prototype.hasOwnProperty.call(modules, MODULE_ID)) {
        console.log('[webpack:chunk]', {
          moduleId: MODULE_ID,
          chunkIdCount: Array.isArray(payload[0]) ? payload[0].length : 1,
        });
        console.trace('[webpack:chunk:stack]');
      }
    } catch (error) {}
    return result;
  };
  const restore = function () {
    const current = Object.getOwnPropertyDescriptor(chunks, 'push');
    if (current && current.value === wrappedPush) {
      Object.defineProperty(chunks, 'push', pushDescriptor);
    } else {
      console.warn('[hook] webpack push slot changed; current runtime owner was preserved');
    }
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.log('[hook] webpack chunk hook restored');
  };
  try {
    Object.defineProperty(chunks, 'push', Object.assign({}, pushDescriptor, { value: wrappedPush }));
    Object.defineProperty(window, RESTORE_KEY, {
      configurable: true,
      writable: false,
      value: restore,
    });
  } catch (error) {
    const current = Object.getOwnPropertyDescriptor(chunks, 'push');
    if (current && current.value === wrappedPush) Object.defineProperty(chunks, 'push', pushDescriptor);
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.warn('[hook] webpack chunk installation failed:', error.name);
  }
})();
```

For an already exposed `__webpack_require__`, use a breakpoint on the known
module ID instead of wrapping the loader globally. If the loader is closure-
local, continue with the implementation Provider's offline module extraction
workflow.

## Bounded String Assembly

Use only when JSVMP or a signer trace already points to `Array.prototype.join`
as a likely assembly boundary. The filter and capture cap are mandatory for
this high-frequency surface.

```js
(function () {
  'use strict';

  const RESULT_FILTER = null;
  const MAX_CALLS = 500;
  const MAX_HITS = 20;
  const RESTORE_KEY = '__restoreBrowserHookArrayJoin';
  if (!(RESULT_FILTER instanceof RegExp)) {
    return console.warn('[hook] set one target-specific RESULT_FILTER before installing');
  }
  if (Object.prototype.hasOwnProperty.call(window, RESTORE_KEY)) {
    return console.warn('[hook] array join already installed');
  }

  const rawJoin = Array.prototype.join;
  let calls = 0;
  let hits = 0;
  const stop = function (reason) {
    if (Array.prototype.join === wrappedJoin) Array.prototype.join = rawJoin;
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    try { console.log('[hook] array join stopped:', reason); } catch (error) {}
  };
  const wrappedJoin = function (separator) {
    const result = rawJoin.apply(this, arguments);
    calls += 1;
    try {
      RESULT_FILTER.lastIndex = 0;
      if (hits < MAX_HITS && RESULT_FILTER.test(result)) {
        hits += 1;
        console.log('[array:join]', {
          call: calls,
          hit: hits,
          separatorType: typeof separator,
          resultLength: result.length,
        });
        console.trace('[array:join:stack]');
      }
    } catch (error) {}
    if (calls >= MAX_CALLS || hits >= MAX_HITS) {
      stop(calls >= MAX_CALLS ? 'call cap reached' : 'hit cap reached');
    }
    return result;
  };
  const restore = function () {
    if (Array.prototype.join === wrappedJoin) {
      Array.prototype.join = rawJoin;
    } else {
      console.warn('[hook] array join slot changed; current owner was preserved');
    }
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.log('[hook] array join restore finished');
  };
  try {
    Array.prototype.join = wrappedJoin;
    Object.defineProperty(window, RESTORE_KEY, {
      configurable: true,
      writable: false,
      value: restore,
    });
  } catch (error) {
    if (Array.prototype.join === wrappedJoin) Array.prototype.join = rawJoin;
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.warn('[hook] array join installation failed:', error.name);
  }
})();
```

This observes the returned shape but never prints the assembled string. The
wrapper removes itself at either cap. If no useful boundary appears, move to
source-level or interpreter instrumentation rather than increasing the caps
without a new acceptance reason.

## Worker

Use to locate crypto, signing, verification, or decoding logic moved into one
known worker script. The wrapper keeps the native constructor and restores
per-worker listeners and methods it owns.

```js
(function () {
  'use strict';

  const RESTORE_KEY = '__restoreWorkerHook';
  const SCRIPT_FILTER = '';
  if (!SCRIPT_FILTER) return console.warn('[hook] set one worker script filter before installing');
  if (Object.prototype.hasOwnProperty.call(window, RESTORE_KEY)) {
    return console.warn('[hook] Worker hook already installed');
  }
  const RawWorker = window.Worker;
  if (typeof RawWorker !== 'function') return console.warn('[hook] Worker unavailable');
  const workers = [];
  const wrappedWorker = function (scriptURL, options) {
    const worker = Reflect.construct(RawWorker, Array.prototype.slice.call(arguments), new.target || RawWorker);
    if (typeof scriptURL !== 'string' || !scriptURL.includes(SCRIPT_FILTER)) return worker;
    const rawPostMessage = worker.postMessage;
    const wrappedPostMessage = function (message) {
      const result = rawPostMessage.apply(this, arguments);
      try {
        console.log('[Worker:postMessage]', { type: typeof message, length: typeof message === 'string' ? message.length : 0 });
        console.trace('[Worker:postMessage:stack]');
      } catch (error) {}
      return result;
    };
    const onMessage = function (event) {
      try {
        console.log('[Worker:message]', { type: typeof event.data, length: typeof event.data === 'string' ? event.data.length : 0 });
      } catch (error) {}
    };
    worker.postMessage = wrappedPostMessage;
    worker.addEventListener('message', onMessage, true);
    workers.push({ worker: worker, rawPostMessage: rawPostMessage, wrappedPostMessage: wrappedPostMessage, onMessage: onMessage });
    console.log('[Worker:new]', { url: scriptURL.split('?')[0] });
    console.trace('[Worker:new:stack]');
    debugger;
    return worker;
  };
  wrappedWorker.prototype = RawWorker.prototype;
  const restore = function () {
    workers.forEach(function (entry) {
      if (entry.worker.postMessage === entry.wrappedPostMessage) entry.worker.postMessage = entry.rawPostMessage;
      entry.worker.removeEventListener('message', entry.onMessage, true);
    });
    workers.length = 0;
    if (window.Worker === wrappedWorker) window.Worker = RawWorker;
    else console.warn('[hook] Worker slot changed; current owner was preserved');
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
  };
  try {
    window.Worker = wrappedWorker;
    Object.defineProperty(window, RESTORE_KEY, { configurable: true, writable: false, value: restore });
  } catch (error) {
    if (window.Worker === wrappedWorker) window.Worker = RawWorker;
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.warn('[hook] Worker installation failed:', error.name);
  }
})();
```

If changing the constructor in Console has no effect, use a page-main-world injection version before widening the hook.

## Targeted Timers And Single-ID Cancellation

Use when a specific callback source marker is already suspected to schedule a
debugger trap, signature refresh, or delayed state transition. Configure one
filter before installation. Observation is bounded, and cancellation requires
one captured timer ID.

```js
(function () {
  'use strict';

  const SOURCE_FILTER = null;
  const MAX_CALLS = 100;
  const RESTORE_KEY = '__restoreBrowserHookTargetTimer';
  const CANCEL_KEY = '__cancelBrowserHookTimerById';
  if (!(SOURCE_FILTER instanceof RegExp)) {
    return console.warn('[hook] set one target-specific SOURCE_FILTER before installing');
  }
  if (Object.prototype.hasOwnProperty.call(window, RESTORE_KEY)
      || Object.prototype.hasOwnProperty.call(window, CANCEL_KEY)) {
    return console.warn('[hook] target timer keys already owned');
  }

  const rawSetTimeout = window.setTimeout;
  const rawSetInterval = window.setInterval;
  const rawClearTimeout = window.clearTimeout;
  const rawClearInterval = window.clearInterval;
  const matches = new Map();
  let inspectedCalls = 0;

  const callbackSource = function (callback) {
    if (typeof callback === 'function') return Function.prototype.toString.call(callback);
    if (typeof callback === 'string') return callback;
    return '';
  };
  const inspect = function (kind, id, callback, delay) {
    if (inspectedCalls >= MAX_CALLS) return;
    inspectedCalls += 1;
    try {
      const source = callbackSource(callback);
      SOURCE_FILTER.lastIndex = 0;
      if (!source || !SOURCE_FILTER.test(source)) return;
      matches.set(id, kind);
      console.log('[timer:match]', {
        id: id,
        kind: kind,
        delayType: typeof delay,
        callbackType: typeof callback,
        sourceLength: source.length,
      });
      console.trace('[timer:match:stack]');
    } catch (error) {}
  };

  const wrappedSetTimeout = function (callback, delay) {
    const id = rawSetTimeout.apply(this, arguments);
    inspect('timeout', id, callback, delay);
    return id;
  };
  const wrappedSetInterval = function (callback, delay) {
    const id = rawSetInterval.apply(this, arguments);
    inspect('interval', id, callback, delay);
    return id;
  };
  const cancelOne = function (id) {
    const kind = matches.get(id);
    if (!kind) return false;
    if (kind === 'timeout') rawClearTimeout.call(window, id);
    else rawClearInterval.call(window, id);
    matches.delete(id);
    try { console.log('[timer:cancel]', { id: id, kind: kind }); } catch (error) {}
    return true;
  };
  const restore = function () {
    if (window.setTimeout === wrappedSetTimeout) window.setTimeout = rawSetTimeout;
    else console.warn('[hook] setTimeout slot changed; current owner was preserved');
    if (window.setInterval === wrappedSetInterval) window.setInterval = rawSetInterval;
    else console.warn('[hook] setInterval slot changed; current owner was preserved');
    if (window[CANCEL_KEY] === cancelOne) delete window[CANCEL_KEY];
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.log('[hook] target timer restore finished; captured timers were not cancelled automatically');
  };
  try {
    window.setTimeout = wrappedSetTimeout;
    window.setInterval = wrappedSetInterval;
    Object.defineProperties(window, {
      [CANCEL_KEY]: { configurable: true, writable: false, value: cancelOne },
      [RESTORE_KEY]: { configurable: true, writable: false, value: restore },
    });
  } catch (error) {
    if (window.setTimeout === wrappedSetTimeout) window.setTimeout = rawSetTimeout;
    if (window.setInterval === wrappedSetInterval) window.setInterval = rawSetInterval;
    if (window[CANCEL_KEY] === cancelOne) delete window[CANCEL_KEY];
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.warn('[hook] target timer installation failed:', error.name);
  }
})();
```

Call `window.__cancelBrowserHookTimerById(id)` only after that exact ID is
proven to be the target. Restoring the hook leaves existing timers intact. At
the inspection cap, the wrappers stop reading callback source; restore them
once the caller has been identified.
