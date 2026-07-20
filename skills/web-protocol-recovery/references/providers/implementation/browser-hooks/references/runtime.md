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

## Blob And URL.createObjectURL

Use to locate dynamically assembled scripts, images, downloads, and worker payloads.

```js
(function () {
  if (window.__restoreBlobUrlHook) return console.warn('Blob/objectURL hook already installed');
  const RawBlob = window.Blob;
  const rawCreateObjectURL = URL.createObjectURL;
  window.Blob = function (parts, options) {
    console.log('[Blob]', { partCount: (parts || []).length, types: (parts || []).map(function (part) { return typeof part; }), options: options && Object.keys(options) });
    console.trace('[Blob:stack]');
    debugger;
    return new RawBlob(parts, options);
  };
  window.Blob.prototype = RawBlob.prototype;
  window.Blob.toString = RawBlob.toString.bind(RawBlob);
  URL.createObjectURL = function (object) {
    console.log('[URL.createObjectURL]', { type: object && object.constructor && object.constructor.name, size: object && object.size });
    console.trace('[URL.createObjectURL:stack]');
    debugger;
    return rawCreateObjectURL.apply(this, arguments);
  };
  window.__restoreBlobUrlHook = function () {
    window.Blob = RawBlob;
    URL.createObjectURL = rawCreateObjectURL;
    delete window.__restoreBlobUrlHook;
  };
})();
```

If only text Blob parts are relevant, log text-part counts and lengths rather than content:

```js
(function () {
  if (window.__restoreBlobTextHook) return console.warn('Blob text hook already installed');
  const RawBlob = window.Blob;
  window.Blob = function (parts, options) {
    const textParts = (parts || []).filter(function (part) { return typeof part === 'string'; });
    if (textParts.length) {
      console.log('[Blob:text]', { partCount: textParts.length, totalLength: textParts.reduce(function (sum, part) { return sum + part.length; }, 0) });
      console.trace('[Blob:text:stack]');
      debugger;
    }
    return new RawBlob(parts, options);
  };
  window.Blob.prototype = RawBlob.prototype;
  window.__restoreBlobTextHook = function () {
    window.Blob = RawBlob;
    delete window.__restoreBlobTextHook;
  };
})();
```

## Worker

Use to locate crypto, signing, verification, or decoding logic moved into a worker.

```js
(function () {
  if (window.__restoreWorkerHook) return console.warn('Worker hook already installed');
  const RawWorker = window.Worker;
  window.Worker = function (scriptURL, options) {
    console.log('[Worker:new]', scriptURL, options);
    console.trace('[Worker:new:stack]');
    debugger;
    const worker = new RawWorker(scriptURL, options);
    const rawPostMessage = worker.postMessage;
    worker.postMessage = function (message, transfer) {
      console.log('[Worker:postMessage]', scriptURL, { type: typeof message, length: message && (message.length || message.byteLength) || 0, transferCount: transfer && transfer.length || 0 });
      console.trace('[Worker:postMessage:stack]');
      debugger;
      return rawPostMessage.apply(this, arguments);
    };
    worker.addEventListener('message', function (event) {
      console.log('[Worker:message]', scriptURL, { type: typeof event.data, length: event.data && (event.data.length || event.data.byteLength) || 0 });
    });
    return worker;
  };
  window.Worker.prototype = RawWorker.prototype;
  window.Worker.toString = RawWorker.toString.bind(RawWorker);
  window.__restoreWorkerHook = function () {
    window.Worker = RawWorker;
    delete window.__restoreWorkerHook;
  };
})();
```

If changing the constructor in Console has no effect, use a page-main-world injection version before widening the hook.

## setTimeout And setInterval

Use to locate periodic signature refresh, delayed execution, or targeted anti-debug timers.

```js
(function () {
  if (window.__restoreTimerHook) return console.warn('timer hook already installed');
  const rawSetTimeout = window.setTimeout;
  const rawSetInterval = window.setInterval;
  function shouldLog(fn) {
    const source = typeof fn === 'function' ? fn.toString() : String(fn);
    return /debugger|sign|token|cookie/i.test(source);
  }
  window.setTimeout = function (fn, delay) {
    if (shouldLog(fn)) {
      console.log('[setTimeout]', delay, { type: typeof fn, sourceLength: String(fn).length });
      console.trace('[setTimeout:stack]');
      debugger;
    }
    return rawSetTimeout.apply(this, arguments);
  };
  window.setInterval = function (fn, delay) {
    if (shouldLog(fn)) {
      console.log('[setInterval]', delay, { type: typeof fn, sourceLength: String(fn).length });
      console.trace('[setInterval:stack]');
      debugger;
    }
    return rawSetInterval.apply(this, arguments);
  };
  window.__restoreTimerHook = function () {
    window.setTimeout = rawSetTimeout;
    window.setInterval = rawSetInterval;
    delete window.__restoreTimerHook;
  };
})();
```

Default to targeted observation. Do not clear or intercept all timers broadly; that commonly breaks page behavior.
