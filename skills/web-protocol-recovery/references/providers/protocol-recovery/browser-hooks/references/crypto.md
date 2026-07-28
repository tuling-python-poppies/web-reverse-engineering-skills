# Crypto And Encoding Hooks

Use for base64, WebCrypto, random values, and byte/text encoding boundaries.

## atob And btoa

Use to locate base64 encode/decode boundaries.

```js
(function () {
  if (window.__restoreBase64Hook) return console.warn('base64 hook already installed');
  const rawAtob = window.atob;
  const rawBtoa = window.btoa;
  window.atob = function (input) {
    const output = rawAtob.apply(this, arguments);
    console.log('[atob]', { inputLen: String(input).length, outputLen: output.length });
    console.trace('[atob:stack]');
    debugger;
    return output;
  };
  window.btoa = function (input) {
    const output = rawBtoa.apply(this, arguments);
    console.log('[btoa]', { inputLen: String(input).length, outputLen: output.length });
    console.trace('[btoa:stack]');
    debugger;
    return output;
  };
  window.atob.toString = rawAtob.toString.bind(rawAtob);
  window.btoa.toString = rawBtoa.toString.bind(rawBtoa);
  window.__restoreBase64Hook = function () {
    window.atob = rawAtob;
    window.btoa = rawBtoa;
    delete window.__restoreBase64Hook;
  };
})();
```

## WebCrypto SubtleCrypto

Use to locate digest, encryption, signing, verification, and key import boundaries. Prefer changing `SubtleCrypto.prototype` rather than the `window.crypto.subtle` instance for better browser compatibility.

```js
(function () {
  if (!window.crypto || !window.crypto.subtle || typeof SubtleCrypto === 'undefined') {
    console.warn('crypto.subtle unavailable');
    return;
  }
  if (window.__restoreSubtleCryptoHook) return console.warn('subtle crypto hook already installed');
  const subtleProto = SubtleCrypto.prototype;
  const restores = [];
  function hookMethod(name) {
    if (typeof subtleProto[name] !== 'function') return;
    const raw = subtleProto[name];
    subtleProto[name] = async function () {
      console.log('[subtle:' + name + ']', { algorithm: arguments[0] && arguments[0].name, argCount: arguments.length });
      console.trace('[subtle:' + name + ':stack]');
      debugger;
      return raw.apply(this, arguments);
    };
    restores.push(function () { subtleProto[name] = raw; });
  }
  ['digest', 'encrypt', 'decrypt', 'sign', 'verify', 'importKey', 'deriveBits', 'deriveKey'].forEach(hookMethod);
  window.__restoreSubtleCryptoHook = function () {
    restores.reverse().forEach(function (restore) { restore(); });
    delete window.__restoreSubtleCryptoHook;
  };
})();
```

For bounded hex conversion of known-safe `ArrayBuffer` values:

```js
function toHex(buffer) {
  const view = buffer instanceof ArrayBuffer ? new Uint8Array(buffer) : new Uint8Array(buffer.buffer || buffer);
  return Array.from(view, b => b.toString(16).padStart(2, '0')).join('');
}
```

## crypto.getRandomValues

Use to locate nonce, random challenge, or one-time salt sources. Prefer `Crypto.prototype` when available because some browsers do not allow direct instance overwrite.

```js
(function () {
  if (!window.crypto || typeof window.crypto.getRandomValues !== 'function' || typeof Crypto === 'undefined') {
    console.warn('crypto.getRandomValues unavailable');
    return;
  }
  if (window.__restoreGetRandomValuesHook) return console.warn('getRandomValues hook already installed');
  const rawGetRandomValues = Crypto.prototype.getRandomValues;
  Crypto.prototype.getRandomValues = function (typedArray) {
    const result = rawGetRandomValues.apply(this, arguments);
    console.log('[crypto.getRandomValues]', typedArray && typedArray.constructor && typedArray.constructor.name, { byteLength: typedArray && typedArray.byteLength });
    console.trace('[crypto.getRandomValues:stack]');
    debugger;
    return result;
  };
  window.__restoreGetRandomValuesHook = function () {
    Crypto.prototype.getRandomValues = rawGetRandomValues;
    delete window.__restoreGetRandomValuesHook;
  };
})();
```

## TextEncoder And TextDecoder

Use when data is UTF-8 encoded before hashing, signing, encryption, or decoding.

```js
(function () {
  if (window.__restoreTextCodecHook) return console.warn('text codec hook already installed');
  const rawEncode = TextEncoder.prototype.encode;
  const rawDecode = TextDecoder.prototype.decode;
  TextEncoder.prototype.encode = function (input) {
    const output = rawEncode.apply(this, arguments);
    console.log('[TextEncoder.encode]', { inputLen: String(input).length, outputLen: output.byteLength });
    return output;
  };
  TextDecoder.prototype.decode = function (input) {
    const output = rawDecode.apply(this, arguments);
    console.log('[TextDecoder.decode]', { inputLen: input && input.byteLength || 0, outputLen: output.length });
    return output;
  };
  window.__restoreTextCodecHook = function () {
    TextEncoder.prototype.encode = rawEncode;
    TextDecoder.prototype.decode = rawDecode;
    delete window.__restoreTextCodecHook;
  };
})();
```
