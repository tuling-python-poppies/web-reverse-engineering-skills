// web-protocol-recovery browser-hooks provider: Web Crypto observer
// 先把 API_FILTER 设置为目标 API 的 RegExp；未配置时拒绝安装。
// 注入：DevTools Console（需页面已加载 crypto API）

(function () {
  'use strict';

  const FULL_LOG = false;
  const API_FILTER = null;
  const STATE_KEY = '__browserHookCrypto';
  if (!(API_FILTER instanceof RegExp)) {
    console.warn('[hook] set API_FILTER to a target-specific RegExp before installing crypto observer');
    return;
  }
  if (window[STATE_KEY]) {
    console.warn('[hook] crypto already installed; call window.__restoreBrowserHookCrypto() first');
    return;
  }
  const state = { restores: [] };
  window[STATE_KEY] = state;
  function text(value) { return value === undefined || value === null ? '' : String(value); }
  function lengthOf(value) {
    if (value === undefined || value === null) return 0;
    if (typeof value.byteLength === 'number') return value.byteLength;
    if (typeof value.length === 'number') return value.length;
    return text(value).length;
  }
  function preview(value) {
    const valueText = text(value);
    return FULL_LOG ? valueText : '<redacted len=' + valueText.length + '>';
  }
  function algorithmName(value) {
    try {
      return value && value.name ? String(value.name) : '?';
    } catch (error) {
      return '<unavailable>';
    }
  }
  function argumentMeta(value) {
    if (value === undefined || value === null) return { type: String(value), length: 0 };
    const type = value.constructor && value.constructor.name || typeof value;
    if (typeof value.byteLength === 'number') return { type: type, length: value.byteLength };
    if (typeof value.length === 'number') return { type: type, length: value.length };
    if (typeof value === 'string') return { type: 'String', length: value.length };
    return { type: type };
  }
  function restoreAll() {
    state.restores.reverse().forEach(function (restore) { restore(); });
    state.restores.length = 0;
    delete window.__restoreBrowserHookCrypto;
    delete window[STATE_KEY];
    console.log('[hook] crypto restored');
  }
  window.__restoreBrowserHookCrypto = restoreAll;

  // ---- WebCrypto.subtle ----
  if (typeof crypto !== 'undefined' && crypto.subtle && typeof SubtleCrypto !== 'undefined') {
    const methods = ['encrypt', 'decrypt', 'sign', 'verify', 'digest', 'importKey', 'exportKey', 'generateKey', 'deriveBits', 'deriveKey'];
    const subtleProto = SubtleCrypto.prototype;
    methods.forEach(function (m) {
      if (!API_FILTER.test('crypto.subtle.' + m)) return;
      const origFn = subtleProto[m];
      if (typeof origFn === 'function') {
        const wrapped = function () {
          const entry = {
            target: 'crypto',
            event: 'call',
            api: 'crypto.subtle.' + m,
            algo: algorithmName(arguments[0]),
            argCount: arguments.length,
            inputs: Array.prototype.slice.call(arguments, 1).map(argumentMeta),
          };
          console.log('[hook-crypto]', JSON.stringify(entry));
          return origFn.apply(this, arguments).then(function (result) {
            const outLen = lengthOf(result);
            const output = FULL_LOG ? preview(result) : '<redacted len=' + outLen + '>';
            console.log('[hook-crypto-result]', JSON.stringify({ target: 'crypto', event: 'result', api: 'crypto.subtle.' + m, output: output }));
            return result;
          });
        };
        try {
          subtleProto[m] = wrapped;
          state.restores.push(function () { subtleProto[m] = origFn; });
        } catch (error) {
          console.warn('[hook-crypto] cannot wrap ' + m, error.message);
        }
      }
    });
    console.log('[hook] crypto.subtle installed');
  }

  // ---- CryptoJS ----
  if (typeof CryptoJS !== 'undefined') {
    const algos = ['MD5', 'SHA1', 'SHA256', 'SHA512', 'AES', 'DES', 'TripleDES', 'RC4', 'Rabbit', 'HmacMD5', 'HmacSHA1', 'HmacSHA256'];
    algos.forEach(function (algo) {
      if (!API_FILTER.test('CryptoJS.' + algo)) return;
      if (CryptoJS[algo] && typeof CryptoJS[algo] === 'function') {
        const origFn = CryptoJS[algo];
        try {
          CryptoJS[algo] = function () {
            const input = typeof arguments[0] === 'string' ? preview(arguments[0]) : '[obj]';
            console.log('[hook-CryptoJS]', JSON.stringify({ target: 'crypto', event: 'call', api: 'CryptoJS.' + algo, input: input }));
            const result = origFn.apply(this, arguments);
            console.log('[hook-CryptoJS]', JSON.stringify({ target: 'crypto', event: 'result', api: 'CryptoJS.' + algo, outputLen: result && result.toString ? result.toString().length : 0 }));
            return result;
          };
          state.restores.push(function () { CryptoJS[algo] = origFn; });
        } catch (error) {
          console.warn('[hook-CryptoJS] cannot wrap ' + algo, error.message);
        }
      }
    });
    console.log('[hook] CryptoJS installed');
  }
  console.log('[hook] crypto restore: window.__restoreBrowserHookCrypto()');
})();
