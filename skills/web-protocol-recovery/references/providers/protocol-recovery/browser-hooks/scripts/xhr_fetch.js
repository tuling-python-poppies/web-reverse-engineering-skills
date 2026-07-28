// web-protocol-recovery browser-hooks provider: XHR/fetch observer
// 同时 hook XHR 和 fetch，输出请求 URL/method/headers，带调用栈。
// 先设置非空 URL_FILTER；可按需收窄 HEADER_FILTER。未配置时拒绝安装。
// 注入：DevTools Console（页面加载前最早注入时机：Sources 首个脚本暂停后注入）

(function () {
  'use strict';

  const FULL_LOG = false;
  const URL_FILTER = '';
  const HEADER_FILTER = /authorization|token|sign|x-bogus|x-gnarly/i;
  const STATE_KEY = '__browserHookXhrFetch';

  if (!URL_FILTER) {
    console.warn('[hook] set a non-empty URL_FILTER before installing xhr+fetch observer');
    return;
  }

  if (window[STATE_KEY]) {
    console.warn('[hook] xhr+fetch already installed; call window.__restoreBrowserHookXhrFetch() first');
    return;
  }

  const state = { restores: [] };
  window[STATE_KEY] = state;

  function text(value) {
    if (value === undefined || value === null) return '';
    return String(value);
  }

  function preview(value, limit) {
    const valueText = text(value);
    return FULL_LOG ? valueText : '<redacted len=' + valueText.length + '>';
  }

  function matchesUrl(url) {
    return text(url).includes(URL_FILTER);
  }

  function matchesHeader(name) {
    return !HEADER_FILTER || HEADER_FILTER.test(text(name));
  }

  function safeUrl(url) {
    if (FULL_LOG) return text(url);
    try {
      const parsed = new URL(text(url), window.location.href);
      return parsed.origin + parsed.pathname + (parsed.search ? '?<redacted>' : '');
    } catch (error) {
      return '<url unavailable>';
    }
  }

  function bodyMeta(body) {
    if (body === undefined || body === null) return { bodyLen: 0, bodyType: 'none' };
    if (typeof body === 'string') return { bodyLen: body.length, body: preview(body, 80) };
    if (typeof Blob !== 'undefined' && body instanceof Blob) return { bodyLen: body.size, bodyType: 'Blob' };
    if (typeof body.byteLength === 'number') return { bodyLen: body.byteLength, bodyType: body.constructor && body.constructor.name };
    return { bodyType: body.constructor && body.constructor.name || typeof body, bodyNote: 'not read' };
  }

  function headersMeta(headers) {
    const result = {};
    if (!headers) return result;
    try {
      if (typeof headers.forEach === 'function') {
        headers.forEach(function (value, name) {
          if (matchesHeader(name)) result[name] = preview(value, 40);
        });
      } else if (Array.isArray(headers)) {
        headers.forEach(function (pair) {
          if (pair && matchesHeader(pair[0])) result[pair[0]] = preview(pair[1], 40);
        });
      } else if (typeof headers === 'object') {
        Object.keys(headers).forEach(function (name) {
          if (matchesHeader(name)) result[name] = preview(headers[name], 40);
        });
      }
    } catch (error) {
      result._error = error.message;
    }
    return result;
  }

  function log(label, meta, trace) {
    if (!matchesUrl(meta.url)) return;
    console.log(label, JSON.stringify(meta));
    if (trace) console.trace(label + ' call stack');
  }

  function restoreAll() {
    state.restores.reverse().forEach(function (restore) { restore(); });
    state.restores.length = 0;
    delete window.__restoreBrowserHookXhrFetch;
    delete window[STATE_KEY];
    console.log('[hook] xhr+fetch restored');
  }
  window.__restoreBrowserHookXhrFetch = restoreAll;

  // ---- XHR ----
  try {
  const origXHROpen = XMLHttpRequest.prototype.open;
  const origXHRSetHeader = XMLHttpRequest.prototype.setRequestHeader;
  const origXHRSend = XMLHttpRequest.prototype.send;
  const xhrMeta = new WeakMap();

  XMLHttpRequest.prototype.open = function (method, url) {
    xhrMeta.set(this, { method: text(method), url: text(url), headers: {} });
    return origXHROpen.apply(this, arguments);
  };
  state.restores.push(function () { XMLHttpRequest.prototype.open = origXHROpen; });

  XMLHttpRequest.prototype.setRequestHeader = function (name, value) {
    const h = xhrMeta.get(this) || { method: '?', url: '?', headers: {} };
    h.headers[text(name).toLowerCase()] = text(value);
    xhrMeta.set(this, h);
    if (matchesHeader(name)) {
      log('[hook-xhr-header]', {
        target: 'xhr', event: 'setRequestHeader', method: h.method, url: safeUrl(h.url),
        header: text(name), value: preview(value, 40)
      }, true);
    }
    return origXHRSetHeader.apply(this, arguments);
  };
  state.restores.push(function () { XMLHttpRequest.prototype.setRequestHeader = origXHRSetHeader; });

  XMLHttpRequest.prototype.send = function (body) {
    const h = xhrMeta.get(this) || { method: '?', url: '?', headers: {} };
    const meta = Object.assign({
      target: 'xhr',
      event: 'send',
      method: h.method,
      url: safeUrl(h.url),
      headers: headersMeta(h.headers),
    }, bodyMeta(body));
    log('[hook-xhr]', meta, true);

    this.addEventListener('load', function () {
      const rmeta = {
        target: 'xhr',
        event: 'response',
        method: h.method,
        url: safeUrl(h.url),
        status: this.status,
        respLen: null,
        responseType: this.responseType || 'text',
      };
      try {
        if (this.responseType === '' || this.responseType === 'text') rmeta.respLen = this.responseText ? this.responseText.length : 0;
      } catch (error) {
        rmeta.responseReadError = error.name;
      }
      log('[hook-xhr-resp]', rmeta, false);
    });
    return origXHRSend.apply(this, arguments);
  };
  state.restores.push(function () { XMLHttpRequest.prototype.send = origXHRSend; });

  // ---- fetch ----
  const origFetch = window.fetch;
  function fetchMeta(input, init) {
    const request = input && typeof input === 'object' ? input : null;
    const url = typeof input === 'string' ? input : (request && request.url) || '?';
    const method = (init && init.method) || (request && request.method) || 'GET';
    const headers = (init && init.headers) || (request && request.headers);
    const hasInitBody = !!(init && Object.prototype.hasOwnProperty.call(init, 'body'));
    const meta = Object.assign({
      target: 'fetch', event: 'send', method: text(method), url: safeUrl(url), headers: headersMeta(headers)
    }, bodyMeta(hasInitBody ? init.body : undefined));
    if (!hasInitBody && request) {
      meta.bodyType = request.body ? 'Request stream (not read)' : 'none';
      delete meta.bodyLen;
    }
    return meta;
  }

  window.fetch = function (input, init) {
    const meta = fetchMeta(input, init);
    log('[hook-fetch]', meta, true);

    return origFetch.apply(this, arguments).then(function (resp) {
      const rmeta = {
        target: 'fetch',
        event: 'response',
        method: meta.method,
        url: meta.url,
        status: resp.status,
      };
      log('[hook-fetch-resp]', rmeta, false);
      return resp;
    });
  };
  state.restores.push(function () { window.fetch = origFetch; });

  console.log('[hook] xhr+fetch installed; restore with window.__restoreBrowserHookXhrFetch()');
  } catch (error) {
    restoreAll();
    console.warn('[hook] xhr+fetch installation failed', error.message);
  }
})();
