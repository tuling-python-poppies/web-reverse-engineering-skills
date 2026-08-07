# DOM Hooks

Use for element creation, node insertion, canvas drawing/export, and DOM mutation provenance.

## document.createElement

Use to locate who creates `script`, `iframe`, `canvas`, or another concrete tag.

```js
(function () {
  if (window.__restoreCreateElementHook) return console.warn('createElement hook already installed');
  const TAG_FILTER = /^(script|iframe|canvas)$/i;
  const rawCreateElement = document.createElement.bind(document);
  document.createElement = function (tagName, options) {
    if (TAG_FILTER.test(String(tagName))) {
      console.log('[createElement]', tagName);
      console.trace('[createElement:stack]');
      debugger;
    }
    return rawCreateElement(tagName, options);
  };
  window.__restoreCreateElementHook = function () {
    document.createElement = rawCreateElement;
    delete window.__restoreCreateElementHook;
  };
})();
```

## appendChild And insertBefore

Use to locate dynamic `script`, `iframe`, canvas, or hidden node insertion.

```js
(function () {
  if (window.__restoreNodeInsertHook) return console.warn('node insert hook already installed');
  const rawAppendChild = Node.prototype.appendChild;
  const rawInsertBefore = Node.prototype.insertBefore;
  function logNode(prefix, node, parent) {
    if (!node || !node.tagName) return;
    const tag = node.tagName.toLowerCase();
    if (/^(script|iframe|canvas)$/.test(tag)) {
      console.log('[' + prefix + ']', { tag: tag, id: node.id || '', parent: parent && parent.tagName || '' });
      console.trace('[' + prefix + ':stack]');
      debugger;
    }
  }
  Node.prototype.appendChild = function (node) {
    logNode('appendChild', node, this);
    return rawAppendChild.apply(this, arguments);
  };
  Node.prototype.insertBefore = function (node) {
    logNode('insertBefore', node, this);
    return rawInsertBefore.apply(this, arguments);
  };
  window.__restoreNodeInsertHook = function () {
    Node.prototype.appendChild = rawAppendChild;
    Node.prototype.insertBefore = rawInsertBefore;
    delete window.__restoreNodeInsertHook;
  };
})();
```

## MutationObserver

Use when the page repeatedly mutates DOM and the inserted node, not the writer, is easiest to observe.

```js
(function () {
  if (window.__hookMutationObserver) return console.warn('mutation observer already installed');
  const observer = new MutationObserver(function (mutations) {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (node.nodeType === 1) {
          console.log('[MutationObserver:add]', node.tagName, node);
          if (/^(SCRIPT|IFRAME|CANVAS)$/i.test(node.tagName)) debugger;
        }
      }
    }
  });
  observer.observe(document.documentElement || document, { childList: true, subtree: true });
  window.__hookMutationObserver = observer;
})();

// restore
window.__hookMutationObserver && window.__hookMutationObserver.disconnect();
delete window.__hookMutationObserver;
```

## Canvas Context And Drawing

Use for canvas fingerprinting, captcha/image generation, or canvas export paths.

```js
(function () {
  if (window.__restoreCanvasContextHook) return console.warn('canvas context hook already installed');
  const rawGetContext = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (type) {
    console.log('[canvas:getContext]', type, { width: this.width, height: this.height });
    if (type === '2d' || type === 'webgl') {
      console.trace('[canvas:getContext:stack]');
      debugger;
    }
    return rawGetContext.apply(this, arguments);
  };
  window.__restoreCanvasContextHook = function () {
    HTMLCanvasElement.prototype.getContext = rawGetContext;
    delete window.__restoreCanvasContextHook;
  };
})();
```

For text drawing:

```js
(function () {
  if (window.__restoreCanvasFillTextHook) return console.warn('canvas fillText hook already installed');
  const rawFillText = CanvasRenderingContext2D.prototype.fillText;
  CanvasRenderingContext2D.prototype.fillText = function (text, x, y) {
    console.log('[canvas:fillText]', { textLength: String(text).length, x: x, y: y });
    console.trace('[canvas:fillText:stack]');
    debugger;
    return rawFillText.apply(this, arguments);
  };
  window.__restoreCanvasFillTextHook = function () {
    CanvasRenderingContext2D.prototype.fillText = rawFillText;
    delete window.__restoreCanvasFillTextHook;
  };
})();
```

For export results:

```js
(function () {
  if (window.__restoreCanvasToDataURLHook) return console.warn('canvas toDataURL hook already installed');
  const rawToDataURL = HTMLCanvasElement.prototype.toDataURL;
  let calls = 0;
  HTMLCanvasElement.prototype.toDataURL = function () {
    const result = rawToDataURL.apply(this, arguments);
    calls += 1;
    console.log('[canvas:toDataURL]', { call: calls, length: result.length, type: typeof result });
    console.trace('[canvas:toDataURL:stack]');
    debugger;
    return result;
  };
  window.__restoreCanvasToDataURLHook = function () {
    HTMLCanvasElement.prototype.toDataURL = rawToDataURL;
    delete window.__restoreCanvasToDataURLHook;
  };
})();
```

## Targeted Attribute Writes

Use when a known script, iframe, or worker URL is assembled through
`setAttribute`. Configure the value filter before installing the hook.

```js
(function () {
  'use strict';

  const RESTORE_KEY = '__restoreBrowserHookSetAttribute';
  if (Object.prototype.hasOwnProperty.call(window, RESTORE_KEY)) {
    return console.warn('[hook] setAttribute hook already installed');
  }

  const TAG_NAME = 'script';
  const ATTRIBUTE_NAME = 'src';
  const VALUE_FRAGMENT = '';
  if (!VALUE_FRAGMENT) {
    return console.warn('[hook] set one VALUE_FRAGMENT before installing');
  }
  const rawSetAttribute = Element.prototype.setAttribute;

  const wrappedSetAttribute = function (name, value) {
    const result = rawSetAttribute.apply(this, arguments);
    try {
      if (
        typeof this.tagName === 'string'
        && this.tagName.toLowerCase() === TAG_NAME
        && typeof name === 'string'
        && name.toLowerCase() === ATTRIBUTE_NAME
        && typeof value === 'string'
        && value.includes(VALUE_FRAGMENT)
      ) {
        console.log('[dom:setAttribute]', {
          tag: TAG_NAME,
          attribute: ATTRIBUTE_NAME,
          valueType: typeof value,
          valueLength: value.length,
        });
        console.trace('[dom:setAttribute:stack]');
        debugger;
      }
    } catch (error) {}
    return result;
  };
  const restore = function () {
    if (Element.prototype.setAttribute === wrappedSetAttribute) {
      Element.prototype.setAttribute = rawSetAttribute;
    } else {
      console.warn('[hook] setAttribute slot changed; current owner was preserved');
    }
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.log('[hook] setAttribute restored');
  };
  try {
    Element.prototype.setAttribute = wrappedSetAttribute;
    Object.defineProperty(window, RESTORE_KEY, {
      configurable: true,
      writable: false,
      value: restore,
    });
  } catch (error) {
    if (Element.prototype.setAttribute === wrappedSetAttribute) {
      Element.prototype.setAttribute = rawSetAttribute;
    }
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.warn('[hook] setAttribute installation failed:', error.name);
  }
})();
```

The filter is used only to decide whether to log; the attribute value is
forwarded unchanged and is not printed.

## Targeted `getElementById`

Use when a known field or state container is located by one specific ID.

```js
(function () {
  'use strict';

  const RESTORE_KEY = '__restoreBrowserHookGetElementById';
  if (typeof Document === 'undefined' || Object.prototype.hasOwnProperty.call(window, RESTORE_KEY)) {
    return console.warn('[hook] getElementById unavailable or already installed');
  }

  const TARGET_ID = '';
  if (!TARGET_ID) {
    return console.warn('[hook] set one TARGET_ID before installing');
  }
  const rawGetElementById = Document.prototype.getElementById;
  const wrappedGetElementById = function (id) {
    const result = rawGetElementById.apply(this, arguments);
    try {
      if (typeof id === 'string' && id === TARGET_ID) {
        console.log('[dom:getElementById]', { id: TARGET_ID });
        console.trace('[dom:getElementById:stack]');
      }
    } catch (error) {}
    return result;
  };
  const restore = function () {
    if (Document.prototype.getElementById === wrappedGetElementById) {
      Document.prototype.getElementById = rawGetElementById;
    } else {
      console.warn('[hook] getElementById slot changed; current owner was preserved');
    }
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.log('[hook] getElementById restored');
  };
  try {
    Document.prototype.getElementById = wrappedGetElementById;
    Object.defineProperty(window, RESTORE_KEY, {
      configurable: true,
      writable: false,
      value: restore,
    });
  } catch (error) {
    if (Document.prototype.getElementById === wrappedGetElementById) {
      Document.prototype.getElementById = rawGetElementById;
    }
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.warn('[hook] getElementById installation failed:', error.name);
  }
})();
```

Pair this with the input descriptor example in `storage.md` when the question
is whether the returned element is subsequently read or overwritten.

## Same-Origin Iframe Load

Use when a named same-origin iframe owns a challenge or bridge document.

```js
(function () {
  'use strict';

  const RESTORE_KEY = '__restoreBrowserHookFrameLoad';
  const frame = document.querySelector('#target-frame');
  if (!frame || Object.prototype.hasOwnProperty.call(window, RESTORE_KEY)) {
    return console.warn('[hook] target iframe unavailable or already installed');
  }

  const onLoad = function () {
    let locationMeta = { sameOrigin: false };
    try {
      const url = new URL(frame.contentWindow.location.href);
      locationMeta = { sameOrigin: true, origin: url.origin, pathname: url.pathname };
    } catch (error) {
      locationMeta.error = error.name;
    }
    console.log('[iframe:load]', locationMeta);
    console.trace('[iframe:load:stack]');
  };

  const restore = function () {
    frame.removeEventListener('load', onLoad, true);
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.log('[hook] iframe load restored');
  };
  try {
    frame.addEventListener('load', onLoad, true);
    Object.defineProperty(window, RESTORE_KEY, {
      configurable: true,
      writable: false,
      value: restore,
    });
  } catch (error) {
    frame.removeEventListener('load', onLoad, true);
    if (window[RESTORE_KEY] === restore) delete window[RESTORE_KEY];
    console.warn('[hook] iframe load installation failed:', error.name);
  }
})();
```

Do not use this to bypass same-origin policy or inject code into a cross-origin
frame. A cross-origin result is a boundary observation, not a failure to work
around.
