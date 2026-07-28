# Network Hooks

Use for request chains, request headers, realtime messages, wrapper transports, and page-main-world injection.

All snippets follow the local hook contract: log summaries by default, preserve original `this` and arguments, install idempotently, and expose a restore function. Example URLs log path-only or query-redacted output unless the work order explicitly allows raw values.

## XHR Open

Use when a URL fragment is already known.

```js
(function () {
  if (window.__restoreXhrOpenHook) return console.warn('xhr open hook already installed');
  const URL_FILTER = '/api/target';
  const rawOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url) {
    if (String(url).includes(URL_FILTER)) {
      console.log('[xhr:open]', method, String(url).split('?')[0]);
      console.trace('[xhr:open:stack]');
      debugger;
    }
    return rawOpen.apply(this, arguments);
  };
  window.__restoreXhrOpenHook = function () {
    XMLHttpRequest.prototype.open = rawOpen;
    delete window.__restoreXhrOpenHook;
  };
})();
```

## XHR Header

Use for `Authorization`, `x-sign`, token, or challenge headers.

```js
(function () {
  if (window.__restoreXhrHeaderHook) return console.warn('xhr header hook already installed');
  const HEADER_FILTER = /^authorization$/i;
  const rawSetHeader = XMLHttpRequest.prototype.setRequestHeader;
  XMLHttpRequest.prototype.setRequestHeader = function (key, value) {
    if (HEADER_FILTER.test(String(key))) {
      console.log('[xhr:header]', key, '<redacted len=' + String(value).length + '>');
      console.trace('[xhr:header:stack]');
      debugger;
    }
    return rawSetHeader.apply(this, arguments);
  };
  window.__restoreXhrHeaderHook = function () {
    XMLHttpRequest.prototype.setRequestHeader = rawSetHeader;
    delete window.__restoreXhrHeaderHook;
  };
})();
```

## Fetch

Use for modern request paths that do not use XHR.

```js
(function () {
  if (window.__restoreFetchHook) return console.warn('fetch hook already installed');
  const URL_FILTER = '/api/';
  const rawFetch = window.fetch;
  window.fetch = async function (input, init) {
    const url = typeof input === 'string' ? input : input && input.url;
    if (url && String(url).includes(URL_FILTER)) {
      const body = init && init.body;
      console.log('[fetch]', {
        url: String(url).split('?')[0],
        method: (init && init.method) || (input && input.method) || 'GET',
        bodyLen: body && (body.length || body.byteLength) || 0
      });
      console.trace('[fetch:stack]');
      debugger;
    }
    return rawFetch.apply(this, arguments);
  };
  window.__restoreFetchHook = function () {
    window.fetch = rawFetch;
    delete window.__restoreFetchHook;
  };
})();
```

When the user asks who initiated a request, prefer adding `console.trace()` before broader hooks. If the site may use SDK interceptors or both XHR and fetch, return both narrow hooks rather than observing only half the chain.

## WebSocket Send

Use for realtime upstream payloads.

```js
(function () {
  if (window.__restoreWebSocketSendHook) return console.warn('WebSocket send hook already installed');
  const rawSend = WebSocket.prototype.send;
  WebSocket.prototype.send = function (data) {
    console.log('[ws:send]', { type: typeof data, length: data && (data.length || data.byteLength) || 0 });
    console.trace('[ws:send:stack]');
    debugger;
    return rawSend.apply(this, arguments);
  };
  window.__restoreWebSocketSendHook = function () {
    WebSocket.prototype.send = rawSend;
    delete window.__restoreWebSocketSendHook;
  };
})();
```

## WebSocket Message

Use only when downstream message provenance matters; otherwise prefer the browser/network WebSocket collector.

```js
(function () {
  if (window.__restoreWebSocketMessageHook) return console.warn('WebSocket message hook already installed');
  const rawAddEventListener = WebSocket.prototype.addEventListener;
  const rawRemoveEventListener = WebSocket.prototype.removeEventListener;
  const loggers = new WeakMap();
  const sockets = new Set();
  WebSocket.prototype.addEventListener = function (type, listener) {
    if (type === 'message' && !loggers.has(this)) {
      const logger = function (event) {
        console.log('[ws:message]', { type: typeof event.data, length: event.data && (event.data.length || event.data.byteLength) || 0 });
      };
      loggers.set(this, logger);
      sockets.add(this);
      rawAddEventListener.call(this, type, logger, true);
    }
    return rawAddEventListener.apply(this, arguments);
  };
  window.__restoreWebSocketMessageHook = function () {
    sockets.forEach(function (socket) {
      const logger = loggers.get(socket);
      if (logger) rawRemoveEventListener.call(socket, 'message', logger, true);
    });
    WebSocket.prototype.addEventListener = rawAddEventListener;
    sockets.clear();
    delete window.__restoreWebSocketMessageHook;
  };
})();
```

## jQuery Ajax

Use for older sites or wrapper layers that add params or headers before the native request boundary.

```js
(function () {
  if (!window.jQuery || typeof window.jQuery.ajax !== 'function') {
    console.warn('jQuery.ajax unavailable');
    return;
  }
  if (window.__restoreJqueryAjaxHook) return console.warn('jQuery.ajax hook already installed');
  const rawAjax = window.jQuery.ajax;
  window.jQuery.ajax = function (options) {
    if (options && typeof options === 'object') {
      console.log('[jquery:ajax]', {
        url: String(options.url || '').split('?')[0],
        method: options.type || options.method,
        dataType: typeof options.data,
        headerNames: options.headers && Object.keys(options.headers)
      });
      console.trace('[jquery:ajax:stack]');
      debugger;
    }
    return rawAjax.apply(this, arguments);
  };
  window.__restoreJqueryAjaxHook = function () {
    window.jQuery.ajax = rawAjax;
    delete window.__restoreJqueryAjaxHook;
  };
})();
```

If the page clearly uses the wrapper, hook `$.ajax` first, then decide whether native XHR/fetch still needs observation.

## Window PostMessage

Use for iframe, extension bridge, page bridge, or worker wrapper traffic.

```js
(function () {
  if (window.__restoreWindowPostMessageHook) return console.warn('postMessage hook already installed');
  const rawPostMessage = window.postMessage;
  window.postMessage = function (message, targetOrigin, transfer) {
    console.log('[window.postMessage:send]', {
      type: typeof message,
      length: message && (message.length || message.byteLength) || 0,
      targetOrigin: targetOrigin
    });
    console.trace('[window.postMessage:send:stack]');
    debugger;
    return rawPostMessage.apply(this, arguments);
  };
  const onMessage = function (event) {
    console.log('[window.postMessage:recv]', event.origin, {
      type: typeof event.data,
      length: event.data && (event.data.length || event.data.byteLength) || 0
    });
  };
  window.addEventListener('message', onMessage, true);
  window.__restoreWindowPostMessageHook = function () {
    window.postMessage = rawPostMessage;
    window.removeEventListener('message', onMessage, true);
    delete window.__restoreWindowPostMessageHook;
  };
})();
```

## Page-Main-World Injection

Use when DevTools Console or isolated-world globals are not the same objects the target page code uses.

```js
const inject = function () {
  if (window.__restorePageXhrOpenHook) return;
  const rawOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function () {
    console.log('[xhr:open]', String(arguments[1]).split('?')[0]);
    console.trace('[xhr:stack]');
    return rawOpen.apply(this, arguments);
  };
  window.__restorePageXhrOpenHook = function () {
    XMLHttpRequest.prototype.open = rawOpen;
    delete window.__restorePageXhrOpenHook;
  };
};

const script = document.createElement('script');
script.textContent = '(' + inject + ')()';
try {
  (document.head || document.documentElement).appendChild(script);
} finally {
  script.remove();
}
```

If CSP or Trusted Types blocks script-tag injection, use the browser's main-world evaluate support or Sources breakpoints instead of broad fallback hooks.
