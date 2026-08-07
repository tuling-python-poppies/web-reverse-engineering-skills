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
  const RESTORE_KEY = '__restoreWebSocketSendHook';
  if (Object.prototype.hasOwnProperty.call(window, RESTORE_KEY)) {
    return console.warn('WebSocket send hook already installed');
  }
  const URL_FILTER = '';
  if (!URL_FILTER) return console.warn('[hook] set one WebSocket URL filter before installing');
  const rawSend = WebSocket.prototype.send;
  const wrappedSend = function (data) {
    const result = rawSend.apply(this, arguments);
    try {
      if (typeof this.url === 'string' && this.url.includes(URL_FILTER)) {
        console.log('[ws:send]', {
          url: this.url.split('?')[0],
          type: typeof data,
          length: typeof data === 'string' ? data.length : 0,
        });
        console.trace('[ws:send:stack]');
        debugger;
      }
    } catch (error) {}
    return result;
  };
  const restore = function () {
    if (WebSocket.prototype.send === wrappedSend) {
      WebSocket.prototype.send = rawSend;
    } else {
      console.warn('[hook] WebSocket send slot changed; current owner was preserved');
    }
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
  };
  try {
    WebSocket.prototype.send = wrappedSend;
    Object.defineProperty(window, RESTORE_KEY, {
      configurable: true,
      writable: false,
      value: restore,
    });
  } catch (error) {
    if (WebSocket.prototype.send === wrappedSend) WebSocket.prototype.send = rawSend;
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.warn('[hook] WebSocket send installation failed:', error.name);
  }
})();
```

Calling `this.send(data)` from the replacement is recursive. Always retain the
prototype method and call it with `rawSend.apply(this, arguments)`.

## WebSocket Message

Use only when downstream message provenance matters; otherwise prefer the browser/network WebSocket collector.

```js
(function () {
  const RESTORE_KEY = '__restoreWebSocketMessageHook';
  if (Object.prototype.hasOwnProperty.call(window, RESTORE_KEY)) {
    return console.warn('WebSocket message hook already installed');
  }
  const URL_FILTER = '';
  if (!URL_FILTER) return console.warn('[hook] set one WebSocket URL filter before installing');
  const rawAddEventListener = WebSocket.prototype.addEventListener;
  const rawRemoveEventListener = WebSocket.prototype.removeEventListener;
  const loggers = new WeakMap();
  const sockets = new Set();
  const wrappedAddEventListener = function (type, listener) {
    const result = rawAddEventListener.apply(this, arguments);
    try {
      if (type === 'message' && typeof this.url === 'string' && this.url.includes(URL_FILTER) && !loggers.has(this)) {
        const logger = function (event) {
          try {
            console.log('[ws:message]', {
              type: typeof event.data,
              length: typeof event.data === 'string' ? event.data.length : 0,
            });
          } catch (error) {}
        };
        loggers.set(this, logger);
        sockets.add(this);
        rawAddEventListener.call(this, type, logger, true);
      }
    } catch (error) {}
    return result;
  };
  const restore = function () {
    sockets.forEach(function (socket) {
      const logger = loggers.get(socket);
      if (logger) rawRemoveEventListener.call(socket, 'message', logger, true);
    });
    if (WebSocket.prototype.addEventListener === wrappedAddEventListener) {
      WebSocket.prototype.addEventListener = rawAddEventListener;
    } else {
      console.warn('[hook] WebSocket listener slot changed; current owner was preserved');
    }
    sockets.clear();
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
  };
  try {
    WebSocket.prototype.addEventListener = wrappedAddEventListener;
    Object.defineProperty(window, RESTORE_KEY, {
      configurable: true,
      writable: false,
      value: restore,
    });
  } catch (error) {
    if (WebSocket.prototype.addEventListener === wrappedAddEventListener) {
      WebSocket.prototype.addEventListener = rawAddEventListener;
    }
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.warn('[hook] WebSocket message installation failed:', error.name);
  }
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

## MessagePort Send

Use when a worker, iframe, or page bridge carries the target artifact through
`MessagePort` rather than `window.postMessage`.

```js
(function () {
  'use strict';

  if (typeof MessagePort === 'undefined') {
    return console.warn('[hook] MessagePort unavailable');
  }
  const RESTORE_KEY = '__restoreBrowserHookMessagePort';
  if (Object.prototype.hasOwnProperty.call(window, RESTORE_KEY)) {
    return console.warn('[hook] MessagePort hook already installed');
  }

  const TARGET_PORT = window.targetPort;
  const MESSAGE_TYPE = '';
  if (!TARGET_PORT || !MESSAGE_TYPE) {
    return console.warn('[hook] set TARGET_PORT and MESSAGE_TYPE before installing');
  }

  const originalOwnDescriptor = Object.getOwnPropertyDescriptor(TARGET_PORT, 'postMessage');
  if ((originalOwnDescriptor && !originalOwnDescriptor.configurable)
      || (!originalOwnDescriptor && !Object.isExtensible(TARGET_PORT))) {
    return console.warn('[hook] target port cannot accept a reversible own wrapper');
  }
  const rawPostMessage = TARGET_PORT.postMessage;
  if (typeof rawPostMessage !== 'function') {
    return console.warn('[hook] target port postMessage unavailable');
  }
  const rawAddEventListener = EventTarget.prototype.addEventListener;
  const rawRemoveEventListener = EventTarget.prototype.removeEventListener;
  const messageKind = function (message) {
    if (typeof message === 'string') return 'string';
    if (!message || typeof message !== 'object') return '';
    try {
      const descriptor = Object.getOwnPropertyDescriptor(message, 'type');
      return descriptor && Object.prototype.hasOwnProperty.call(descriptor, 'value')
        && typeof descriptor.value === 'string' ? descriptor.value : '';
    } catch (error) {
      return '';
    }
  };
  const messageLength = function (message) {
    if (typeof message === 'string') return message.length;
    if (typeof ArrayBuffer !== 'undefined' && ArrayBuffer.isView(message)) return message.byteLength;
    if (typeof ArrayBuffer !== 'undefined' && message instanceof ArrayBuffer) return message.byteLength;
    return 0;
  };

  const wrappedPostMessage = function (message) {
    const result = rawPostMessage.apply(this, arguments);
    if (this === TARGET_PORT) {
      try {
        const kind = messageKind(message);
        if (kind === MESSAGE_TYPE) {
          console.log('[messagePort:send]', { type: kind, length: messageLength(message) });
          console.trace('[messagePort:send:stack]');
        }
      } catch (error) {}
    }
    return result;
  };
  const onMessage = function (event) {
    try {
      const kind = messageKind(event.data);
      if (kind === MESSAGE_TYPE) {
        console.log('[messagePort:receive]', { type: kind, length: messageLength(event.data) });
      }
    } catch (error) {}
  };
  let listenerAdded = false;
  const restore = function () {
    if (TARGET_PORT.postMessage === wrappedPostMessage) {
      if (originalOwnDescriptor) Object.defineProperty(TARGET_PORT, 'postMessage', originalOwnDescriptor);
      else delete TARGET_PORT.postMessage;
    } else {
      console.warn('[hook] MessagePort slot changed; current owner was preserved');
    }
    if (listenerAdded) rawRemoveEventListener.call(TARGET_PORT, 'message', onMessage, true);
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.log('[hook] MessagePort restored');
  };
  try {
    Object.defineProperty(TARGET_PORT, 'postMessage', {
      configurable: true,
      enumerable: originalOwnDescriptor ? originalOwnDescriptor.enumerable : false,
      writable: true,
      value: wrappedPostMessage,
    });
    rawAddEventListener.call(TARGET_PORT, 'message', onMessage, true);
    listenerAdded = true;
    Object.defineProperty(window, RESTORE_KEY, {
      configurable: true,
      writable: false,
      value: restore,
    });
  } catch (error) {
    if (TARGET_PORT.postMessage === wrappedPostMessage) {
      if (originalOwnDescriptor) Object.defineProperty(TARGET_PORT, 'postMessage', originalOwnDescriptor);
      else delete TARGET_PORT.postMessage;
    }
    if (listenerAdded) rawRemoveEventListener.call(TARGET_PORT, 'message', onMessage, true);
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    return console.warn('[hook] MessagePort installation failed:', error.name);
  }
})();
```

The port must already be known and started by the page; this example does not
call `start()` or alter the port's lifecycle. It observes both directions but
does not read or print complete payloads by default.

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
