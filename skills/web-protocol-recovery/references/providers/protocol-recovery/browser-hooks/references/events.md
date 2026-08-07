# Event Hooks

Use for one known event type or legacy event-handler property. These examples
observe registration and assignment; they do not cancel, synthesize, or replay
user input.

## Event Listener Registration

Use when a page installs a handler for a concrete event on `window`,
`document`, or another known target.

```js
(function () {
  'use strict';

  const TARGET = document;
  const EVENT_TYPE = '';
  const RESTORE_KEY = '__restoreBrowserHookEventRegistration';

  if (!EVENT_TYPE) {
    console.warn('[hook] set one EVENT_TYPE before installing');
    return;
  }
  if (Object.prototype.hasOwnProperty.call(window, RESTORE_KEY)) {
    console.warn('[hook] event registration already installed');
    return;
  }

  const rawAddEventListener = EventTarget.prototype.addEventListener;
  const wrappedAddEventListener = function (type, listener) {
    const result = rawAddEventListener.apply(this, arguments);
    if (this === TARGET && typeof type === 'string' && type === EVENT_TYPE) {
      try {
        console.log('[event:register]', {
          target: TARGET === window ? 'window' : 'document',
          type: type,
          listenerType: typeof listener,
        });
        console.trace('[event:register:stack]');
      } catch (error) {}
    }
    return result;
  };
  const restore = function () {
    if (EventTarget.prototype.addEventListener === wrappedAddEventListener) {
      EventTarget.prototype.addEventListener = rawAddEventListener;
    } else {
      console.warn('[hook] event registration slot changed; current owner was preserved');
    }
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.log('[hook] event registration restored');
  };
  try {
    EventTarget.prototype.addEventListener = wrappedAddEventListener;
    Object.defineProperty(window, RESTORE_KEY, {
      configurable: true,
      writable: false,
      value: restore,
    });
  } catch (error) {
    if (EventTarget.prototype.addEventListener === wrappedAddEventListener) {
      EventTarget.prototype.addEventListener = rawAddEventListener;
    }
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.warn('[hook] event registration installation failed:', error.name);
  }
})();
```

This identifies who installs a handler without changing whether the event is
later delivered. To inspect the handler body, pause at the reported caller or
use the browser's event-listener breakpoint for the same event type.

## Legacy Event-Handler Property

Use when the page assigns a known property such as `document.onkeydown` or
`window.onresize` instead of calling `addEventListener`.

```js
(function () {
  'use strict';

  const target = document;
  const property = '';
  const RESTORE_KEY = '__restoreBrowserHookLegacyEvent';

  if (!property) {
    console.warn('[hook] set one legacy event property before installing');
    return;
  }
  if (Object.prototype.hasOwnProperty.call(window, RESTORE_KEY)) {
    console.warn('[hook] legacy event property already installed');
    return;
  }

  let owner = target;
  let descriptor = null;
  while (owner && !descriptor) {
    descriptor = Object.getOwnPropertyDescriptor(owner, property);
    if (!descriptor) owner = Object.getPrototypeOf(owner);
  }

  if (!owner || !descriptor || !descriptor.configurable || typeof descriptor.set !== 'function') {
    console.warn('[hook] event property descriptor unavailable:', property);
    return;
  }

  const wrappedSetter = function (value) {
    if (this === target) {
      try {
        console.log('[event:property-set]', {
          target: target === window ? 'window' : 'document',
          property: property,
          valueType: typeof value,
        });
        console.trace('[event:property-set:stack]');
      } catch (error) {}
    }
    return descriptor.set.call(this, value);
  };
  const hookedDescriptor = Object.assign({}, descriptor, { set: wrappedSetter });
  const restore = function () {
    const current = Object.getOwnPropertyDescriptor(owner, property);
    if (current && current.set === wrappedSetter) {
      Object.defineProperty(owner, property, descriptor);
    } else {
      console.warn('[hook] legacy event slot changed; current owner was preserved');
    }
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.log('[hook] legacy event property restored');
  };
  try {
    Object.defineProperty(owner, property, hookedDescriptor);
    Object.defineProperty(window, RESTORE_KEY, {
      configurable: true,
      writable: false,
      value: restore,
    });
  } catch (error) {
    const current = Object.getOwnPropertyDescriptor(owner, property);
    if (current && current.set === wrappedSetter) Object.defineProperty(owner, property, descriptor);
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.warn('[hook] legacy event installation failed:', error.name);
  }
})();
```

Do not use this to suppress F12, right-click, resize, or other page events.
The captured setter and caller are evidence for locating the page's behavior;
the wrapper forwards the native setter but remains visible to descriptor or
function-integrity checks.
