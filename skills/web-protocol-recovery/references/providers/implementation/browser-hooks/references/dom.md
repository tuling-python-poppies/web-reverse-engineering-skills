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
