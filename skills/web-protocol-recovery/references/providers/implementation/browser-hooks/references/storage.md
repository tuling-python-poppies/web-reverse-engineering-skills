# Storage Hooks

Use for cookie, browser storage, and form value provenance.

## Document Cookie

This only observes JavaScript writes through `document.cookie = ...`. It will not see cookies created by HTTP `Set-Cookie`; inspect the matching Network response headers when the source may be server-side.

```js
(function () {
  if (window.__restoreCookieHook) return console.warn('cookie hook already installed');
  function findCookieDescriptor() {
    let proto = Object.getPrototypeOf(document);
    while (proto) {
      const descriptor = Object.getOwnPropertyDescriptor(proto, 'cookie');
      if (descriptor) return { owner: proto, descriptor: descriptor };
      proto = Object.getPrototypeOf(proto);
    }
    return null;
  }
  const found = findCookieDescriptor();
  if (!found || !found.descriptor || !found.descriptor.configurable) {
    console.warn('cookie descriptor unavailable');
    return;
  }
  const cookieDesc = found.descriptor;
  Object.defineProperty(found.owner, 'cookie', {
    configurable: true,
    enumerable: cookieDesc.enumerable,
    get() {
      const value = cookieDesc.get.call(this);
      console.log('[cookie:get]', '<redacted len=' + String(value).length + '>');
      return value;
    },
    set(value) {
      console.log('[cookie:set]', '<redacted len=' + String(value).length + '>');
      console.trace('[cookie:stack]');
      debugger;
      return cookieDesc.set.call(this, value);
    }
  });
  window.__restoreCookieHook = function () {
    Object.defineProperty(found.owner, 'cookie', cookieDesc);
    delete window.__restoreCookieHook;
  };
})();
```

Prefer finding the descriptor owner through the prototype chain; do not assume it is always on the document instance. If the suspected source is HTTP, check XHR/fetch/document responses and `set-cookie` before widening JS hooks.

## Local And Session Storage

Use for tokens, device fingerprint cache, one-time challenges, and challenge state.

```js
(function () {
  if (window.__restoreStorageHook) return console.warn('storage hook already installed');
  const KEY_FILTER = /token|sign|challenge/i;
  const rawSetItem = Storage.prototype.setItem;
  const rawGetItem = Storage.prototype.getItem;
  const rawRemoveItem = Storage.prototype.removeItem;
  function match(key) { return KEY_FILTER.test(String(key)); }
  Storage.prototype.setItem = function (key, value) {
    if (match(key)) {
      console.log('[storage:setItem]', this === localStorage ? 'local' : 'session', key, '<redacted len=' + String(value).length + '>');
      console.trace('[storage:setItem:stack]');
      debugger;
    }
    return rawSetItem.apply(this, arguments);
  };
  Storage.prototype.getItem = function (key) {
    const value = rawGetItem.apply(this, arguments);
    if (match(key)) {
      console.log('[storage:getItem]', this === localStorage ? 'local' : 'session', key, value === null ? 'null' : '<redacted len=' + value.length + '>');
    }
    return value;
  };
  Storage.prototype.removeItem = function (key) {
    if (match(key)) console.log('[storage:removeItem]', this === localStorage ? 'local' : 'session', key);
    return rawRemoveItem.apply(this, arguments);
  };
  window.__restoreStorageHook = function () {
    Storage.prototype.setItem = rawSetItem;
    Storage.prototype.getItem = rawGetItem;
    Storage.prototype.removeItem = rawRemoveItem;
    delete window.__restoreStorageHook;
  };
})();
```

If the site uses `localStorage.foo = value`, `setItem` hooks will not fire. Prefer the request/header hook, a concrete-key writer breakpoint, or the caller path; do not conclude there was no write.

## Input Value Descriptor

Use when a specific input field is repeatedly read or overwritten by script.

```js
(function () {
  if (window.__restoreInputValueHook) return console.warn('input value hook already installed');
  const input = document.querySelector('#username');
  if (!input) {
    console.warn('target input not found');
    return;
  }
  const ownDescriptor = Object.getOwnPropertyDescriptor(input, 'value');
  let owner = ownDescriptor ? input : Object.getPrototypeOf(input);
  let descriptor = ownDescriptor;
  while (owner && !descriptor) {
    descriptor = Object.getOwnPropertyDescriptor(owner, 'value');
    if (!descriptor) owner = Object.getPrototypeOf(owner);
  }
  if (!descriptor || typeof descriptor.get !== 'function' || typeof descriptor.set !== 'function') {
    console.warn('native input value descriptor unavailable');
    return;
  }
  Object.defineProperty(input, 'value', {
    configurable: true,
    enumerable: descriptor.enumerable,
    get() {
      const currentValue = descriptor.get.call(this);
      console.log('[input:get]', '<redacted len=' + String(currentValue).length + '>');
      return currentValue;
    },
    set(value) {
      console.log('[input:set]', '<redacted len=' + String(value).length + '>');
      console.trace('[input:set:stack]');
      debugger;
      return descriptor.set.call(this, value);
    }
  });
  window.__restoreInputValueHook = function () {
    if (ownDescriptor) Object.defineProperty(input, 'value', ownDescriptor);
    else delete input.value;
    delete window.__restoreInputValueHook;
  };
})();
```
