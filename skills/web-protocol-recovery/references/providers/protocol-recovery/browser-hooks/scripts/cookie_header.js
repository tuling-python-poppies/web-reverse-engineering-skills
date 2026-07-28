// web-protocol-recovery browser-hooks provider: cookie/header observer
// 先设置目标 COOKIE_FILTER 或 HEADER_FILTER；两者均未配置时拒绝安装。
// 注入：DevTools Console（越早越好，建议页面加载前注入）

(function () {
  'use strict';

  const FULL_LOG = false;
  const COOKIE_FILTER = null;
  const HEADER_FILTER = null;
  const STATE_KEY = '__browserHookCookieHeader';
  if (!(COOKIE_FILTER instanceof RegExp) && !(HEADER_FILTER instanceof RegExp)) {
    console.warn('[hook] set COOKIE_FILTER or HEADER_FILTER before installing cookie+header observer');
    return;
  }
  if (window[STATE_KEY]) {
    console.warn('[hook] cookie+Headers already installed; call window.__restoreBrowserHookCookieHeader() first');
    return;
  }
  const state = { restores: [] };
  window[STATE_KEY] = state;

  function valueText(value) { return value === undefined || value === null ? '' : String(value); }
  function preview(value, limit) {
    const text = valueText(value);
    return FULL_LOG ? text : '<redacted len=' + text.length + '>';
  }
  function restoreAll() {
    state.restores.reverse().forEach(function (restore) { restore(); });
    state.restores.length = 0;
    delete window.__restoreBrowserHookCookieHeader;
    delete window[STATE_KEY];
    console.log('[hook] cookie+Headers restored');
  }
  window.__restoreBrowserHookCookieHeader = restoreAll;

  // ---- document.cookie 写入 ----
  let cookieOwner = Object.getPrototypeOf(document);
  let desc = null;
  while (cookieOwner && !desc) {
    desc = Object.getOwnPropertyDescriptor(cookieOwner, 'cookie');
    if (!desc) cookieOwner = Object.getPrototypeOf(cookieOwner);
  }
  if (cookieOwner && desc && desc.configurable) {
    Object.defineProperty(cookieOwner, 'cookie', {
      get: function () { return desc.get.call(this); },
      set: function (val) {
        const parts = valueText(val).split(';')[0].split('=');
        const key = parts[0].trim();
        const value = parts.slice(1).join('=');
        const entry = {
          target: 'cookie',
          event: 'set',
          key,
          valLen: value.length,
          value: preview(value, 20),
        };
        if (COOKIE_FILTER && COOKIE_FILTER.test(key)) {
          console.log('[hook-cookie-set]', JSON.stringify(entry));
          console.trace('[hook-cookie-set] call stack');
        }
        return desc.set.call(this, val);
      },
      enumerable: desc.enumerable,
      configurable: true,
    });
    state.restores.push(function () { Object.defineProperty(cookieOwner, 'cookie', desc); });
    console.log('[hook] cookie installed');
  } else {
    console.warn('[hook] cookie descriptor not configurable');
  }

  // ---- Headers.set/append（不覆盖构造器 init，也不覆盖 XHR）----
  const OrigHeaders = window.Headers;
  if (OrigHeaders && OrigHeaders.prototype) {
    const rawSet = OrigHeaders.prototype.set;
    const rawAppend = OrigHeaders.prototype.append;
    try {
      OrigHeaders.prototype.set = function (name, value) {
        if (HEADER_FILTER && HEADER_FILTER.test(valueText(name))) {
          console.log('[hook-header-set]', JSON.stringify({ target: 'headers', event: 'set', header: valueText(name), value: preview(value, 40) }));
        }
        return rawSet.apply(this, arguments);
      };
      OrigHeaders.prototype.append = function (name, value) {
        if (HEADER_FILTER && HEADER_FILTER.test(valueText(name))) {
          console.log('[hook-header-append]', JSON.stringify({ target: 'headers', event: 'append', header: valueText(name), value: preview(value, 40) }));
        }
        return rawAppend.apply(this, arguments);
      };
      state.restores.push(function () {
        OrigHeaders.prototype.set = rawSet;
        OrigHeaders.prototype.append = rawAppend;
      });
      console.log('[hook] Headers methods installed');
    } catch (error) {
      try { OrigHeaders.prototype.set = rawSet; } catch (_) {}
      try { OrigHeaders.prototype.append = rawAppend; } catch (_) {}
      console.warn('[hook] Headers methods unavailable', error.message);
    }
  }

})();
