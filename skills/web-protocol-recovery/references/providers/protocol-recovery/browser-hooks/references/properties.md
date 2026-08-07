# Object Property And Method Hooks

Use only after the work order names one object and one property or method.
These snippets are deliberately narrower than a global `Object.defineProperty`
or `Proxy` probe.

## Known Property Read And Write

This example supports a configurable own data property or accessor. It logs
types and lengths, keeps the current value on restore, and refuses an
unconfigurable property.

```js
(function () {
  'use strict';

  const target = window;
  const property = '_knownState';
  const RESTORE_KEY = '__restoreBrowserHookKnownProperty';

  if (Object.prototype.hasOwnProperty.call(window, RESTORE_KEY)) {
    console.warn('[hook] known property already installed');
    return;
  }

  const original = Object.getOwnPropertyDescriptor(target, property);
  if (!original || !original.configurable) {
    console.warn('[hook] property must be a configurable own property:', property);
    return;
  }

  const isDataProperty = Object.prototype.hasOwnProperty.call(original, 'value');
  let currentValue = isDataProperty ? original.value : undefined;
  const lengthOf = function (value) {
    if (value === null || value === undefined) return 0;
    if (typeof value === 'string') return value.length;
    if (typeof ArrayBuffer !== 'undefined' && ArrayBuffer.isView(value)) return value.byteLength;
    if (typeof ArrayBuffer !== 'undefined' && value instanceof ArrayBuffer) return value.byteLength;
    return 0;
  };
  const meta = function (value) {
    return { type: typeof value, length: lengthOf(value) };
  };

  const hooked = {
    configurable: original.configurable,
    enumerable: original.enumerable,
  };
  let hookedGetter;
  let hookedSetter;

  if (isDataProperty) {
    hookedGetter = function () {
      try { console.log('[property:get]', property, meta(currentValue)); } catch (error) {}
      return currentValue;
    };
    hooked.get = hookedGetter;
    if (original.writable) {
      hookedSetter = function (value) {
        try {
          console.log('[property:set]', property, meta(value));
          console.trace('[property:set:stack]');
        } catch (error) {}
        currentValue = value;
      };
      hooked.set = hookedSetter;
    }
  } else {
    if (typeof original.get === 'function') {
      hookedGetter = function () {
        const value = original.get.call(this);
        try { console.log('[property:get]', property, meta(value)); } catch (error) {}
        return value;
      };
      hooked.get = hookedGetter;
    }
    if (typeof original.set === 'function') {
      hookedSetter = function (value) {
        try {
          console.log('[property:set]', property, meta(value));
          console.trace('[property:set:stack]');
        } catch (error) {}
        return original.set.call(this, value);
      };
      hooked.set = hookedSetter;
    }
  }

  const restore = function () {
    const current = Object.getOwnPropertyDescriptor(target, property);
    if (current && current.get === hookedGetter && current.set === hookedSetter) {
      if (isDataProperty) {
        Object.defineProperty(target, property, Object.assign({}, original, { value: currentValue }));
      } else {
        Object.defineProperty(target, property, original);
      }
    } else {
      console.warn('[hook] known property slot changed; current owner was preserved');
    }
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.log('[hook] known property restore finished');
  };
  try {
    Object.defineProperty(target, property, hooked);
    Object.defineProperty(window, RESTORE_KEY, {
      configurable: true,
      writable: false,
      value: restore,
    });
  } catch (error) {
    const current = Object.getOwnPropertyDescriptor(target, property);
    if (current && current.get === hookedGetter && current.set === hookedSetter) {
      Object.defineProperty(target, property, original);
    }
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.warn('[hook] known property installation failed:', error.name);
  }
})();
```

## Known Method Call

Use for one already identified helper such as `window.app.sign`. Do not use
this pattern to enumerate or wrap every function on `window`.

```js
(function () {
  'use strict';

  const target = window.app;
  const property = 'sign';
  const RESTORE_KEY = '__restoreBrowserHookKnownMethod';

  if (!target || Object.prototype.hasOwnProperty.call(window, RESTORE_KEY)) {
    console.warn('[hook] known method target unavailable or already installed');
    return;
  }

  const original = Object.getOwnPropertyDescriptor(target, property);
  if (!original || !original.configurable || typeof original.value !== 'function') {
    console.warn('[hook] method must be a configurable own function:', property);
    return;
  }

  const rawMethod = original.value;
  const wrappedMethod = function () {
    try {
      console.log('[method:call]', {
        method: property,
        argCount: arguments.length,
        argTypes: Array.prototype.map.call(arguments, function (value) { return typeof value; }),
      });
      console.trace('[method:call:stack]');
    } catch (error) {}
    if (new.target) {
      const constructorTarget = new.target === wrappedMethod ? rawMethod : new.target;
      return Reflect.construct(rawMethod, Array.prototype.slice.call(arguments), constructorTarget);
    }
    return Reflect.apply(rawMethod, this, arguments);
  };

  const restore = function () {
    const current = Object.getOwnPropertyDescriptor(target, property);
    if (current && current.value === wrappedMethod) {
      Object.defineProperty(target, property, original);
    } else {
      console.warn('[hook] known method slot changed; current owner was preserved');
    }
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.log('[hook] known method restore finished');
  };
  try {
    Object.defineProperty(target, property, Object.assign({}, original, { value: wrappedMethod }));
    Object.defineProperty(window, RESTORE_KEY, {
      configurable: true,
      writable: false,
      value: restore,
    });
  } catch (error) {
    const current = Object.getOwnPropertyDescriptor(target, property);
    if (current && current.value === wrappedMethod) Object.defineProperty(target, property, original);
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.warn('[hook] known method installation failed:', error.name);
  }
})();
```

If the target caches the original method before installation, move the hook
earlier or return a timing blocker. Do not add a broader proxy to compensate.
