// WPR browser-hooks provider: storage observer
// 先把 KEY_FILTER 设置为目标 key 的 RegExp；未配置时拒绝安装。
// 注入：DevTools Console

(function () {
  'use strict';

  var FULL_LOG = false;
  var KEY_FILTER = null;
  var STATE_KEY = '__browserHookStorage';
  if (!(KEY_FILTER instanceof RegExp)) {
    console.warn('[hook] set KEY_FILTER to a target-specific RegExp before installing storage observer');
    return;
  }
  if (typeof Storage === 'undefined') {
    console.warn('[hook] Storage unavailable');
    return;
  }
  if (window[STATE_KEY]) {
    console.warn('[hook] storage already installed; call window.__restoreBrowserHookStorage() first');
    return;
  }
  var state = { restores: [] };
  window[STATE_KEY] = state;

  function text(value) { return value === undefined || value === null ? '' : String(value); }
  function valueMeta(value) {
    var valueText = text(value);
    return { valueLen: valueText.length, value: FULL_LOG ? valueText : '<redacted len=' + valueText.length + '>' };
  }
  function matches(key) { return KEY_FILTER.test(text(key)); }
  function restoreAll() {
    state.restores.reverse().forEach(function (restore) { restore(); });
    state.restores.length = 0;
    delete window.__restoreBrowserHookStorage;
    delete window[STATE_KEY];
    console.log('[hook] storage restored');
  }
  window.__restoreBrowserHookStorage = restoreAll;

  var rawSetItem = Storage.prototype.setItem;
  var rawGetItem = Storage.prototype.getItem;
  var rawRemoveItem = Storage.prototype.removeItem;
  try {
    Storage.prototype.setItem = function (key, value) {
      if (matches(key)) {
        console.log('[hook-storage-set]', JSON.stringify(Object.assign({
          target: 'storage', event: 'setItem', storage: this === window.localStorage ? 'local' : 'session', key: text(key)
        }, valueMeta(value))));
        console.trace('[hook-storage-set] call stack');
      }
      return rawSetItem.apply(this, arguments);
    };
    Storage.prototype.getItem = function (key) {
      var value = rawGetItem.apply(this, arguments);
      if (matches(key) && value !== null) {
        console.log('[hook-storage-get]', JSON.stringify({
          target: 'storage', event: 'getItem', storage: this === window.localStorage ? 'local' : 'session', key: text(key), valueLen: value.length
        }));
      }
      return value;
    };
    Storage.prototype.removeItem = function (key) {
      if (matches(key)) console.log('[hook-storage-remove]', JSON.stringify({ target: 'storage', event: 'removeItem', key: text(key) }));
      return rawRemoveItem.apply(this, arguments);
    };
    state.restores.push(function () {
      Storage.prototype.setItem = rawSetItem;
      Storage.prototype.getItem = rawGetItem;
      Storage.prototype.removeItem = rawRemoveItem;
    });
  } catch (error) {
    try { Storage.prototype.setItem = rawSetItem; } catch (_) {}
    try { Storage.prototype.getItem = rawGetItem; } catch (_) {}
    try { Storage.prototype.removeItem = rawRemoveItem; } catch (_) {}
    restoreAll();
    console.warn('[hook] Storage methods unavailable', error.message);
    return;
  }
  console.log('[hook] storage installed; restore with window.__restoreBrowserHookStorage()');
})();
