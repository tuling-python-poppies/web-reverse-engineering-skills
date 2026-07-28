/*
 * Browser-side seed collector.
 * Paste into DevTools Console/Snippets when a Node.js env rebuild needs real
 * browser seed values. It only reads local browser state and prints JSON; it
 * does not send data over the network.
 */
(function collectBrowserEnv() {
  function safeCall(fn, fallback) {
    try {
      return fn();
    } catch (err) {
      return fallback;
    }
  }

  function dumpStorage(storage) {
    const out = {};
    if (!storage) return out;
    for (let i = 0; i < storage.length; i += 1) {
      const key = storage.key(i);
      out[key] = storage.getItem(key);
    }
    return out;
  }

  function dumpNavigator() {
    return {
      userAgent: safeCall(() => navigator.userAgent, ""),
      platform: safeCall(() => navigator.platform, ""),
      vendor: safeCall(() => navigator.vendor, ""),
      language: safeCall(() => navigator.language, ""),
      languages: safeCall(() => Array.from(navigator.languages || []), []),
      webdriver: safeCall(() => navigator.webdriver, undefined),
      hardwareConcurrency: safeCall(() => navigator.hardwareConcurrency, undefined),
      deviceMemory: safeCall(() => navigator.deviceMemory, undefined),
      maxTouchPoints: safeCall(() => navigator.maxTouchPoints, undefined),
      cookieEnabled: safeCall(() => navigator.cookieEnabled, undefined),
      pdfViewerEnabled: safeCall(() => navigator.pdfViewerEnabled, undefined),
      userAgentData: safeCall(() => navigator.userAgentData ? JSON.parse(JSON.stringify(navigator.userAgentData)) : null, null),
      connection: safeCall(() => navigator.connection ? JSON.parse(JSON.stringify(navigator.connection)) : null, null),
    };
  }

  function dumpDocument() {
    return {
      URL: safeCall(() => document.URL, ""),
      referrer: safeCall(() => document.referrer, ""),
      documentURI: safeCall(() => document.documentURI, ""),
      compatMode: safeCall(() => document.compatMode, ""),
      dir: safeCall(() => document.dir, ""),
      title: safeCall(() => document.title, ""),
      designMode: safeCall(() => document.designMode, ""),
      readyState: safeCall(() => document.readyState, ""),
      contentType: safeCall(() => document.contentType, ""),
      inputEncoding: safeCall(() => document.inputEncoding, ""),
      domain: safeCall(() => document.domain, ""),
      characterSet: safeCall(() => document.characterSet, ""),
      charset: safeCall(() => document.charset, ""),
      hidden: safeCall(() => document.hidden, undefined),
      cookie: safeCall(() => document.cookie, ""),
    };
  }

  function collectCanvasFingerprint() {
    return safeCall(() => {
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");
      if (!ctx) return { canvas2d: null, webgl: null };
      ctx.textBaseline = "top";
      ctx.font = "14px Arial";
      ctx.fillStyle = "#f60";
      ctx.fillRect(10, 10, 120, 40);
      ctx.fillStyle = "#069";
      ctx.fillText("env-patch", 14, 16);

      const canvas2d = safeCall(() => canvas.toDataURL(), null);
      const gl = safeCall(() => canvas.getContext("webgl") || canvas.getContext("experimental-webgl"), null);
      const webgl = gl ? {
        vendor: safeCall(() => gl.getParameter(37445), null),
        renderer: safeCall(() => gl.getParameter(37446), null),
      } : null;
      return { canvas2d, webgl };
    }, { canvas2d: null, webgl: null });
  }

  const payload = {
    timestamp: new Date().toISOString(),
    location: {
      href: safeCall(() => location.href, ""),
      origin: safeCall(() => location.origin, ""),
      protocol: safeCall(() => location.protocol, ""),
      host: safeCall(() => location.host, ""),
      hostname: safeCall(() => location.hostname, ""),
      pathname: safeCall(() => location.pathname, ""),
      search: safeCall(() => location.search, ""),
      hash: safeCall(() => location.hash, ""),
    },
    history: {
      length: safeCall(() => history.length, undefined),
      scrollRestoration: safeCall(() => history.scrollRestoration, undefined),
    },
    navigator: dumpNavigator(),
    document: dumpDocument(),
    screen: safeCall(() => ({
      width: screen.width,
      height: screen.height,
      availWidth: screen.availWidth,
      availHeight: screen.availHeight,
      availLeft: screen.availLeft,
      availTop: screen.availTop,
      colorDepth: screen.colorDepth,
      pixelDepth: screen.pixelDepth,
      orientation: screen.orientation,
    }), {}),
    windowMetrics: safeCall(() => ({
      devicePixelRatio: window.devicePixelRatio,
      innerWidth: window.innerWidth,
      innerHeight: window.innerHeight,
      outerWidth: window.outerWidth,
      outerHeight: window.outerHeight,
      isSecureContext: window.isSecureContext,
    }), {}),
    localStorage: dumpStorage(window.localStorage),
    sessionStorage: dumpStorage(window.sessionStorage),
    fingerprint: collectCanvasFingerprint(),
  };

  console.log(JSON.stringify(payload, null, 2));
  return payload;
})();
