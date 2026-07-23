from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from curl_cffi import requests

try:
    from .http_session import UA, browser_headers
except ImportError:  # pragma: no cover
    from http_session import UA, browser_headers  # type: ignore


def _logger():
    try:
        from utils.logger import logger  # project delivery
        return logger
    except Exception:
        class _L:
            @staticmethod
            def info(msg, *args):
                if args:
                    try:
                        msg = msg.format(*args)
                    except Exception:
                        msg = str(msg) + " " + " ".join(map(str, args))
                print(msg)
        return _L()


logger = _logger()
iv8 = None  # lazy-loaded in generate_reese84


def _import_iv8():
    try:
        from utils.iv8_silent import import_iv8_silent
        return import_iv8_silent()
    except Exception:
        import iv8 as _iv8
        return _iv8

MAX_TICKS = 60
SLEEP_MS = 200


def generate_reese84(
    session: requests.Session,
    *,
    entry_url: str,
    entry_html: str,
    challenge_url: str,
    challenge_js: str,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Run challenge in iv8; Python owns all live HTTP via __iv8__.data.pyHttp."""
    global iv8
    if iv8 is None:
        iv8 = _import_iv8()
    token_state: dict[str, Any] = {
        "token": None,
        "renewInSec": None,
        "cookieDomain": None,
        "exchanges": [],
        "errors": [],
    }
    origin = f"{urlparse(entry_url).scheme}://{urlparse(entry_url).netloc}"
    challenge_headers = browser_headers(
        {
            "Accept": "application/json; charset=utf-8",
            "Content-Type": "text/plain; charset=utf-8",
            "Referer": entry_url,
            "Origin": origin,
        }
    )

    def py_http(method, url, body, headers_json):
        method_s = str(method).upper()
        request_url = urljoin(entry_url, str(url))
        extra = {}
        try:
            if headers_json:
                extra = json.loads(str(headers_json))
        except Exception:
            extra = {}
        for k in list(extra.keys()):
            if str(k).lower() in {"host", "content-length", "connection"}:
                extra.pop(k, None)
        hdrs = {**challenge_headers, **extra}
        data = None if body is None else str(body)
        try:
            if method_s == "GET":
                resp = session.get(request_url, headers=hdrs, timeout=30)
            elif method_s == "POST":
                resp = session.post(request_url, data=data, headers=hdrs, timeout=30)
            elif method_s == "PUT":
                resp = session.put(request_url, data=data, headers=hdrs, timeout=30)
            else:
                resp = session.request(method_s, request_url, data=data, headers=hdrs, timeout=30)  # type: ignore[arg-type]
        except Exception as e:
            token_state["errors"].append(f"py_http {method_s} {request_url}: {e}")
            return json.dumps(
                {"url": request_url, "status": 0, "statusText": "error", "headers": {}, "body": ""}
            )
        if resp is None:
            return json.dumps(
                {"url": request_url, "status": 0, "statusText": "null", "headers": {}, "body": ""}
            )
        body_text = resp.text or ""
        token_state["exchanges"].append(
            {
                "method": method_s,
                "url": request_url,
                "status": int(resp.status_code),
                "req_len": len(data or ""),
                "resp_len": len(body_text),
                "req_prefix": (data or "")[:80],
                "resp_prefix": body_text[:200],
            }
        )
        logger.info(
            "pyHttp {} {} status={} req_len={} resp_len={} req_prefix={}",
            method_s,
            request_url[:80],
            int(resp.status_code),
            len(data or ""),
            len(body_text),
            (data or "")[:40],
        )
        # Always keep long/error request bodies for diagnostics
        if data and (len(data) > 40 or "error" in data or "solution" in data):
            token_state.setdefault("request_bodies", []).append(data[:4000])
            logger.info("long/error request body prefix={}", data[:200].replace("\n", " "))

        if int(resp.status_code) == 200 and body_text:
            try:
                j = json.loads(body_text)
                if isinstance(j, dict):
                    if isinstance(j.get("token"), str) and j["token"]:
                        token_state["token"] = j["token"]
                        token_state["renewInSec"] = j.get("renewInSec")
                        token_state["cookieDomain"] = j.get("cookieDomain") or "bangkokair.com"
                        logger.info(
                            "captured reese token len={} renewInSec={} domain={}",
                            len(token_state["token"]),
                            token_state["renewInSec"],
                            token_state["cookieDomain"],
                        )
                    else:
                        logger.info(
                            "json response keys={} prefix={}",
                            list(j.keys())[:12],
                            body_text[:120].replace("\n", " "),
                        )
            except Exception:
                # gpc often returns a JSON-encoded base64 string
                logger.info("body prefix={}", body_text[:120].replace("\n", " "))
        body_for_js = body_text if len(body_text) <= 2_000_000 else body_text[:2_000_000]
        # Only pass safe response headers into JS Response (Set-Cookie etc. break constructors).
        raw_headers = {str(k): str(v) for k, v in dict(resp.headers).items()}
        safe_headers = {}
        for k, v in raw_headers.items():
            lk = k.lower()
            if lk in {
                "set-cookie",
                "set-cookie2",
                "content-encoding",
                "content-length",
                "transfer-encoding",
                "connection",
            }:
                continue
            safe_headers[k] = v
        if "content-type" not in {k.lower() for k in safe_headers}:
            # gpc returns a JSON string; force JSON content-type for response.json()
            safe_headers["content-type"] = "application/json; charset=utf-8"
        return json.dumps(
            {
                "url": request_url,
                "status": int(resp.status_code),
                "statusText": getattr(resp, "reason", "") or "OK",
                "headers": safe_headers,
                "body": body_for_js,
            }
        )

    parsed = urlparse(entry_url)
    env = {
        "location": {
            "href": entry_url,
            "origin": origin,
            "protocol": f"{parsed.scheme}:",
            "host": parsed.netloc,
            "hostname": parsed.hostname or "",
            "port": "",
            "pathname": parsed.path or "/",
            "search": f"?{parsed.query}" if parsed.query else "",
            "hash": "",
        },
        "navigator": {
            "userAgent": UA,
            "appVersion": UA.replace("Mozilla/", ""),
            "language": "en-GB",
            "languages": ["en-GB", "en-US", "en"],
            "platform": "Win32",
            "webdriver": False,
            "hardwareConcurrency": 8,
            "deviceMemory": 8,
            "maxTouchPoints": 0,
            "vendor": "Google Inc.",
            "cookieEnabled": True,
            "onLine": True,
            "pdfViewerEnabled": True,
        },
        "screen": {
            "width": 1920,
            "height": 1080,
            "availWidth": 1920,
            "availHeight": 1040,
            "colorDepth": 24,
            "pixelDepth": 24,
            "orientation": {"type": "landscape-primary", "angle": 0},
        },
    }

    env_patch_js = r"""
    (function() {
      try {
        if (!window.chrome) {
          window.chrome = {
            runtime: {},
            app: { isInstalled: false, InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' }, RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' } },
            csi: function() { return {}; },
            loadTimes: function() { return {}; }
          };
        }
        if (!navigator.userAgentData) {
          navigator.userAgentData = {
            brands: [
              { brand: 'Chromium', version: '146' },
              { brand: 'Not-A.Brand', version: '24' },
              { brand: 'Google Chrome', version: '146' }
            ],
            mobile: false,
            platform: 'Windows',
            getHighEntropyValues: function() {
              return Promise.resolve({
                architecture: 'x86',
                bitness: '64',
                model: '',
                platform: 'Windows',
                platformVersion: '15.0.0',
                uaFullVersion: '146.0.0.0',
                fullVersionList: [
                  { brand: 'Chromium', version: '146.0.0.0' },
                  { brand: 'Not-A.Brand', version: '10.0.0.0' },
                  { brand: 'Google Chrome', version: '146.0.0.0' }
                ]
              });
            },
            toJSON: function() { return { brands: this.brands, mobile: false, platform: 'Windows' }; }
          };
        }
        // ALWAYS replace permissions.query so fingerprint probes NEVER call into
        // iv8 EnvironmentAccessor for unknown names (speaker-selection, usb, hid, ...).
        // Calling the native query is what prints the ERROR spam.
        (function() {
          var perms = {
            query: function(desc) {
              var name = '';
              try { name = String((desc && (desc.name || desc)) || ''); } catch (_) {}
              return Promise.resolve({ state: 'prompt', name: name, onchange: null });
            }
          };
          try {
            Object.defineProperty(navigator, 'permissions', {
              configurable: true,
              enumerable: true,
              get: function() { return perms; },
              set: function() {}
            });
          } catch (_) {
            try { navigator.permissions = perms; } catch (__){}
          }
          try {
            if (Navigator && Navigator.prototype) {
              Object.defineProperty(Navigator.prototype, 'permissions', {
                configurable: true,
                enumerable: true,
                get: function() { return perms; },
                set: function() {}
              });
            }
          } catch (_) {}
        })();
        if (!navigator.connection) {
          navigator.connection = {
            effectiveType: '4g', rtt: 50, downlink: 10, saveData: false,
            addEventListener: function(){}, removeEventListener: function(){}
          };
        }
        if (!window.matchMedia) {
          window.matchMedia = function(q) {
            return {
              matches: false, media: String(q || ''),
              addListener: function(){}, removeListener: function(){},
              addEventListener: function(){}, removeEventListener: function(){},
              dispatchEvent: function(){ return false; }, onchange: null
            };
          };
        }
        if (typeof document.hasFocus !== 'function') document.hasFocus = function() { return true; };
        if (!document.visibilityState) {
          try {
            Object.defineProperty(document, 'visibilityState', { configurable: true, get: function() { return 'visible'; } });
            Object.defineProperty(document, 'hidden', { configurable: true, get: function() { return false; } });
          } catch (_) {}
        }
        // basic Notification / speech shims
        if (typeof Notification === 'undefined') {
          globalThis.Notification = function() {};
          globalThis.Notification.permission = 'default';
          globalThis.Notification.requestPermission = function() { return Promise.resolve('default'); };
        }
      } catch (e) {
        globalThis.__reeseBridgeErrors = globalThis.__reeseBridgeErrors || [];
        globalThis.__reeseBridgeErrors.push('env_patch:' + String(e));
      }
    })();
    """

    # Bridge uses captured function bag.
    # NOTE: iv8's __iv8__ is a special identifier: !!__iv8__ is false and
    # assigning the host object loses it. Capture functions via property access.
    bridge_js = r"""
    (function() {
      const bag = globalThis.__reeseHostRef;
      if (!bag || typeof bag.pyHttp !== 'function' || typeof bag.pageLoad !== 'function') {
        throw new Error('reese host ref missing');
      }
      globalThis.__reeseBridgeErrors = [];
      globalThis.addEventListener('error', function(e) {
        try { globalThis.__reeseBridgeErrors.push(String(e && e.message || e)); } catch (_) {}
      });
      globalThis.addEventListener('unhandledrejection', function(e) {
        try { globalThis.__reeseBridgeErrors.push(String(e && e.reason || e)); } catch (_) {}
      });

      function makeResponse(raw) {
        const data = (typeof raw === 'string') ? JSON.parse(raw) : raw;
        // Preserve body exactly; gpc returns a JSON-encoded base64 string including quotes.
        const bodyStr = data.body == null ? '' : String(data.body);
        const headers = {};
        for (const k of Object.keys(data.headers || {})) {
          headers[String(k).toLowerCase()] = data.headers[k];
        }
        if (!headers['content-type']) {
          headers['content-type'] = 'application/json; charset=utf-8';
        }
        // Custom Response-like object: more reliable than iv8 native Response body edge cases.
        const resp = {
          ok: (data.status || 0) >= 200 && (data.status || 0) < 300,
          status: data.status || 0,
          statusText: data.statusText || 'OK',
          url: data.url || '',
          redirected: false,
          type: 'basic',
          bodyUsed: false,
          headers: {
            get(name) {
              const key = String(name || '').toLowerCase();
              return headers[key] == null ? null : String(headers[key]);
            },
            has(name) {
              const key = String(name || '').toLowerCase();
              return Object.prototype.hasOwnProperty.call(headers, key);
            },
            forEach(cb) {
              Object.keys(headers).forEach(function(k) { cb(headers[k], k); });
            }
          },
          text: function() {
            this.bodyUsed = true;
            return Promise.resolve(bodyStr);
          },
          json: function() {
            this.bodyUsed = true;
            try {
              // bodyStr is already a JSON document (object or JSON string)
              return Promise.resolve(JSON.parse(bodyStr));
            } catch (e) {
              globalThis.__reeseBridgeErrors.push('json parse fail bodyPrefix=' + bodyStr.slice(0, 80) + ' err=' + String(e));
              return Promise.reject(e);
            }
          },
          arrayBuffer: function() {
            this.bodyUsed = true;
            const enc = new TextEncoder();
            return Promise.resolve(enc.encode(bodyStr).buffer);
          },
          blob: function() {
            this.bodyUsed = true;
            return Promise.resolve(new Blob([bodyStr]));
          },
          clone: function() {
            return makeResponse(data);
          }
        };
        return resp;
      }

      globalThis.fetch = function(input, init) {
        try {
          init = init || {};
          const url = (typeof input === 'string') ? input : (input && input.url) || String(input);
          const method = (init.method || 'GET').toUpperCase();
          let body = init.body == null ? null : String(init.body);
          let headersObj = {};
          if (init.headers) {
            if (typeof init.headers.forEach === 'function') {
              init.headers.forEach(function(v, k) { headersObj[k] = v; });
            } else {
              headersObj = Object.assign({}, init.headers);
            }
          }
          const raw = bag.pyHttp(method, url, body, JSON.stringify(headersObj));
          return Promise.resolve(makeResponse(raw));
        } catch (e) {
          globalThis.__reeseBridgeErrors.push(String(e));
          return Promise.reject(e);
        }
      };

      const XHR = globalThis.XMLHttpRequest;
      if (XHR && XHR.prototype) {
        const open = XHR.prototype.open;
        const send = XHR.prototype.send;
        const setRequestHeader = XHR.prototype.setRequestHeader;
        XHR.prototype.open = function(method, url) {
          this.__reeseMethod = String(method || 'GET');
          this.__reeseUrl = String(url || '');
          this.__reeseHeaders = {};
          return open.apply(this, arguments);
        };
        XHR.prototype.setRequestHeader = function(k, v) {
          try { this.__reeseHeaders[String(k)] = String(v); } catch (_) {}
          return setRequestHeader.apply(this, arguments);
        };
        XHR.prototype.send = function(body) {
          const self = this;
          try {
            const raw = bag.pyHttp(
              self.__reeseMethod || 'GET',
              self.__reeseUrl || '',
              body == null ? null : String(body),
              JSON.stringify(self.__reeseHeaders || {})
            );
            const data = JSON.parse(raw);
            setTimeout(function() {
              try {
                Object.defineProperty(self, 'status', { configurable: true, get: function() { return data.status || 0; } });
                Object.defineProperty(self, 'statusText', { configurable: true, get: function() { return data.statusText || ''; } });
                Object.defineProperty(self, 'responseText', { configurable: true, get: function() { return String(data.body || ''); } });
                Object.defineProperty(self, 'response', { configurable: true, get: function() { return String(data.body || ''); } });
                Object.defineProperty(self, 'readyState', { configurable: true, get: function() { return 4; } });
                Object.defineProperty(self, 'responseURL', { configurable: true, get: function() { return data.url || self.__reeseUrl || ''; } });
                if (typeof self.onreadystatechange === 'function') self.onreadystatechange();
                if (typeof self.onload === 'function') self.onload();
                if (typeof self.onloadend === 'function') self.onloadend();
              } catch (e2) {
                globalThis.__reeseBridgeErrors.push(String(e2));
              }
            }, 0);
          } catch (e) {
            globalThis.__reeseBridgeErrors.push(String(e));
            setTimeout(function() {
              if (typeof self.onerror === 'function') self.onerror(e);
            }, 0);
          }
        };
      }

      // Global wrap: Reese may call EventTarget.prototype.addEventListener directly.
      // Catch TypeError inside load handlers so iv8 C++ verbose EventListener log is reduced.
      try {
        if (typeof EventTarget !== 'undefined' && EventTarget.prototype && EventTarget.prototype.addEventListener) {
          var _etAdd = EventTarget.prototype.addEventListener;
          EventTarget.prototype.addEventListener = function(type, listener, options) {
            if (String(type) === 'load' && typeof listener === 'function') {
              var tag = '';
              try { tag = String(this && this.tagName || ''); } catch (_) {}
              if (tag.toLowerCase() === 'iframe' || this === window || this === document) {
                var wrapped = function(ev) {
                  try { return listener.call(this, ev); }
                  catch (err) {
                    try {
                      globalThis.__reeseBridgeErrors.push(
                        'load_handler:' + String(err && err.message || err)
                      );
                    } catch (_) {}
                  }
                };
                return _etAdd.call(this, type, wrapped, options);
              }
            }
            return _etAdd.call(this, type, listener, options);
          };
        }
      } catch (_) {}

      // iframe lifecycle: interrogator creates IFRAME; fire load and patch child realm
      function patchIframeRealm(win) {
        if (!win || win.__reesePatched) return;
        try { win.__reesePatched = true; } catch (_) {}
        try {
          // hide host in child if present
          try { delete win.__iv8__; } catch (_) {}
          try {
            if (win.Object && win.Object.getOwnPropertyNames) {
              const gopn = win.Object.getOwnPropertyNames;
              win.Object.defineProperty(win.Object, 'getOwnPropertyNames', {
                configurable: true,
                writable: true,
                value: function(obj) {
                  return gopn(obj).filter(function(k) { return k !== '__iv8__'; });
                }
              });
            }
          } catch (_) {}
          // share fetch/XHR bridge into child
          try { win.fetch = globalThis.fetch; } catch (_) {}
          try {
            if (win.XMLHttpRequest && globalThis.XMLHttpRequest) {
              win.XMLHttpRequest = globalThis.XMLHttpRequest;
            }
          } catch (_) {}
          try {
            if (!win.chrome && window.chrome) win.chrome = window.chrome;
          } catch (_) {}
          try {
            if (win.navigator && !win.navigator.userAgentData && navigator.userAgentData) {
              win.navigator.userAgentData = navigator.userAgentData;
            }
          } catch (_) {}
          // permissions wrapper in child realm too
          try {
            var childPerms = {
              query: function(desc) {
                var name = '';
                try { name = String((desc && (desc.name || desc)) || ''); } catch (_) {}
                return Promise.resolve({ state: 'prompt', name: name, onchange: null });
              }
            };
            Object.defineProperty(win.navigator, 'permissions', {
              configurable: true,
              enumerable: true,
              get: function() { return childPerms; },
              set: function() {}
            });
          } catch (_) {}
        } catch (e) {
          globalThis.__reeseBridgeErrors.push('iframe_patch:' + String(e));
        }
      }

      function armIframe(iframe) {
        if (!iframe || iframe.__reeseArmed) return;
        iframe.__reeseArmed = true;

        // Observe native/synthetic load: mark fired so we never double-dispatch.
        try {
          var _markLoad = function() {
            iframe.__reeseLoadFired = true;
            try { patchIframeRealm(iframe.contentWindow); } catch (_) {}
          };
          if (iframe.addEventListener) {
            iframe.addEventListener('load', _markLoad, true);
          }
        } catch (_) {}

        // Wrap element-level handlers for safer challenge callbacks.
        (function wrapLoadHandlers(el) {
          try {
            var origAdd = el.addEventListener && el.addEventListener.bind(el);
            if (origAdd) {
              el.addEventListener = function(type, listener, options) {
                if (String(type) === 'load' && typeof listener === 'function') {
                  var wrapped = function(ev) {
                    try { return listener.call(this, ev); }
                    catch (err) {
                      try {
                        globalThis.__reeseBridgeErrors.push(
                          'iframe_load_handler:' + String(err && err.message || err)
                        );
                      } catch (_) {}
                    }
                  };
                  return origAdd(type, wrapped, options);
                }
                return origAdd(type, listener, options);
              };
            }
          } catch (_) {}
          try {
            var current = null;
            Object.defineProperty(el, 'onload', {
              configurable: true,
              enumerable: true,
              get: function() { return current; },
              set: function(fn) {
                if (typeof fn !== 'function') {
                  current = fn;
                  return;
                }
                current = function(ev) {
                  try { return fn.call(this, ev); }
                  catch (err) {
                    try {
                      globalThis.__reeseBridgeErrors.push(
                        'iframe_onload_prop:' + String(err && err.message || err)
                      );
                    } catch (_) {}
                  }
                };
              }
            });
          } catch (_) {}
        })(iframe);

        // Fire load at most once, and only if native load did not already run.
        const fireLoadOnce = function() {
          if (iframe.__reeseLoadFired) return;
          iframe.__reeseLoadFired = true;
          try {
            patchIframeRealm(iframe.contentWindow);
            try {
              if (typeof Event === 'function') {
                iframe.dispatchEvent(new Event('load'));
                return;
              }
            } catch (_) {}
            try {
              var ev = document.createEvent('Event');
              ev.initEvent('load', false, false);
              iframe.dispatchEvent(ev);
            } catch (__) {}
          } catch (e) {
            globalThis.__reeseBridgeErrors.push('iframe_load:' + String(e));
          }
        };

        const scheduleFire = function() {
          if (iframe.__reeseLoadScheduled) return;
          iframe.__reeseLoadScheduled = true;
          var tries = 0;
          var tick = function() {
            tries += 1;
            if (iframe.__reeseLoadFired) return;
            try {
              var win = iframe.contentWindow;
              var doc = iframe.contentDocument || (win && win.document);
              patchIframeRealm(win);
              var ready = !doc || doc.readyState === 'complete' || doc.readyState === 'interactive';
              if (ready || tries >= 10) {
                // Wait for challenge to attach listeners; skip if native load already fired.
                setTimeout(function() {
                  if (!iframe.__reeseLoadFired) fireLoadOnce();
                }, 40);
                return;
              }
            } catch (_) {
              setTimeout(function() {
                if (!iframe.__reeseLoadFired) fireLoadOnce();
              }, 40);
              return;
            }
            setTimeout(tick, 8);
          };
          setTimeout(tick, 0);
        };

        try {
          var setAttr = iframe.setAttribute ? iframe.setAttribute.bind(iframe) : null;
          if (setAttr) {
            iframe.setAttribute = function(name, value) {
              var r = setAttr(name, value);
              if (String(name).toLowerCase() === 'src') {
                iframe.__reeseLoadScheduled = false;
                scheduleFire();
              }
              return r;
            };
          }
        } catch (_) {}

        scheduleFire();
      }

      try {
        const ce = document.createElement.bind(document);
        document.createElement = function(tag) {
          const el = ce(tag);
          if (String(tag).toLowerCase() === 'iframe') {
            armIframe(el);
          }
          return el;
        };
      } catch (e) {
        globalThis.__reeseBridgeErrors.push('createElement hook:' + String(e));
      }

      try {
        const ap = Node.prototype.appendChild;
        Node.prototype.appendChild = function(child) {
          const r = ap.call(this, child);
          try {
            if (child && String(child.tagName || '').toLowerCase() === 'iframe') {
              armIframe(child);
            }
          } catch (_) {}
          return r;
        };
      } catch (e) {
        globalThis.__reeseBridgeErrors.push('appendChild hook:' + String(e));
      }

      try {
        const ib = Node.prototype.insertBefore;
        Node.prototype.insertBefore = function(newNode, ref) {
          const r = ib.call(this, newNode, ref);
          try {
            if (newNode && String(newNode.tagName || '').toLowerCase() === 'iframe') {
              armIframe(newNode);
            }
          } catch (_) {}
          return r;
        };
      } catch (_) {}
    })();
    """

    # Challenge expects a real <script src="..."> in the DOM (throws if missing).
    # Serve JS via page.load resources map under full URL + path-only keys.
    parsed_ch = urlparse(challenge_url)
    path_only = parsed_ch.path or ""
    path_with_query = path_only + (f"?{parsed_ch.query}" if parsed_ch.query else "")
    resource_map = {
        challenge_url: {"body": challenge_js, "contentType": "application/javascript"},
        path_only: {"body": challenge_js, "contentType": "application/javascript"},
        path_with_query: {"body": challenge_js, "contentType": "application/javascript"},
        urljoin(entry_url, path_only): {
            "body": challenge_js,
            "contentType": "application/javascript",
        },
        urljoin(entry_url, path_with_query): {
            "body": challenge_js,
            "contentType": "application/javascript",
        },
    }

    # Minimal HTML: only one challenge script tag (avoid double interstitial injectors).
    script_src = path_with_query if path_with_query else path_only
    if not script_src:
        script_src = challenge_url
    html_for_load = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Reese</title>"
        f'<script src="{script_src}"></script>'
        "</head><body></body></html>"
    )

    snapshot = {
        "baseURL": entry_url,
        "html": html_for_load,
        "headers": {"content-type": "text/html; charset=utf-8"},
        "resources": resource_map,
    }

    capture_host_js = r"""
    (function() {
      // __iv8__ is a special binding: !!__iv8__ === false and assigning the host
      // object loses it. Capture FUNCTIONS via property access only.
      var pageLoad = __iv8__.page.load;
      var drain = __iv8__.eventLoop.drain;
      var drainMicrotasks = __iv8__.eventLoop.drainMicrotasks;
      var sleep = __iv8__.eventLoop.sleep;
      var pyHttp = __iv8__.data.pyHttp;
      // capture snapshot object now (cannot rely on __iv8__.data after hide)
      var snapshotObj = __iv8__.data.snapshot;
      if (typeof pageLoad !== 'function') throw new Error('iv8.page.load missing');
      if (typeof drain !== 'function') throw new Error('iv8.eventLoop.drain missing');
      if (typeof pyHttp !== 'function') throw new Error('iv8.data.pyHttp missing (expose first)');
      if (!snapshotObj) throw new Error('snapshot missing on __iv8__.data');
      globalThis.__reeseHostRef = {
        pageLoad: pageLoad,
        drain: drain,
        drainMicrotasks: drainMicrotasks,
        sleep: sleep,
        pyHttp: pyHttp,
        snapshot: snapshotObj
      };
      return true;
    })()
    """

    hide_host_js = r"""
    (function() {
      // Hide window.__iv8__ from enumeration AFTER host capture.
      // Do this only after bridge is installed and host members are captured.
      try { delete window.__iv8__; } catch (_) {}
      try {
        const _gopn = Object.getOwnPropertyNames;
        Object.defineProperty(Object, 'getOwnPropertyNames', {
          configurable: true,
          writable: true,
          value: function(obj) {
            return _gopn(obj).filter(function(k) { return k !== '__iv8__'; });
          }
        });
      } catch (_) {}
      return !Object.getOwnPropertyNames(window).includes('__iv8__');
    })()
    """

    drive_protection_js = r"""
    (function() {
      try {
        if (typeof initializeProtection !== 'function') return 'no-init';
        const p = initializeProtection();
        globalThis.__prot = p;
        try { if (typeof p.start === 'function') p.start(); } catch (_) {}
        try { if (typeof p.startInternal === 'function') p.startInternal(); } catch (_) {}
        try { if (typeof p.solve === 'function') p.solve(); } catch (_) {}
        try {
          if (p.interrogator && typeof p.interrogator.interrogate === 'function') {
            p.interrogator.interrogate();
          }
        } catch (_) {}
        try {
          if (typeof p.exportToken === 'function') {
            p.exportToken(20000).then(function(t) {
              globalThis.__exportedToken = t;
              globalThis.__exportDone = true;
            }).catch(function(e) {
              globalThis.__exportErr = String(e);
              globalThis.__exportDone = true;
            });
          }
        } catch (e) {
          globalThis.__exportErr = String(e);
        }
        return 'driven';
      } catch (e) {
        globalThis.__reeseBridgeErrors = globalThis.__reeseBridgeErrors || [];
        globalThis.__reeseBridgeErrors.push('drive:' + String(e));
        return 'drive-err:' + String(e);
      }
    })()
    """

    # Fill every known config.permissions.* default so fingerprint probes prefer
    # registered paths. Unknown names are still handled by the JS wrapper above.
    perm_config = {}
    try:
        defaults = iv8.JSContext.get_defaults()
        for path, default in defaults.items():
            if not str(path).startswith("config.permissions."):
                continue
            # path like config.permissions.geolocation or config.permissions.camera.state
            parts = str(path).split(".")
            if len(parts) < 3:
                continue
            key = parts[2]
            # Prefer prompt for decision-style, granted for sensors when default says so
            if isinstance(default, str) and default in {"granted", "denied", "prompt"}:
                perm_config[key] = default
            else:
                perm_config.setdefault(key, "prompt")
    except Exception:
        perm_config = {
            "geolocation": "prompt",
            "notifications": "prompt",
            "camera": "prompt",
            "microphone": "prompt",
            "clipboard-read": "prompt",
            "clipboard-write": "granted",
            "accelerometer": "granted",
            "gyroscope": "granted",
        }

    ctx_config = {
        "timezone": "UTC",
        "permissions": perm_config,
    }

    with iv8.JSContext(environment=env, config=ctx_config, time_mode="system") as ctx:
        ctx.expose(py_http, "pyHttp")
        ctx.expose(snapshot, "snapshot")

        # 1) capture page/data/eventLoop via property access on special identifier
        try:
            ok_host = ctx.eval(capture_host_js, to_py=True)
            logger.info("host APIs captured={}", ok_host)
        except Exception as e:
            token_state["errors"].append(f"capture_host: {e}")
            raise RuntimeError(f"cannot capture iv8 host APIs: {e}") from e

        # 2) install network bridge BEFORE hide (uses captured ref only)
        ctx.eval(bridge_js)
        # env shims used by interrogator
        try:
            ctx.eval(env_patch_js)
        except Exception as e:
            token_state["errors"].append(f"env_patch: {e}")

        # 3) hide window.__iv8__ from enumeration for challenge scripts
        try:
            hidden = ctx.eval(hide_host_js, to_py=True)
            logger.info("host hidden from window GOPN={}", hidden)
        except Exception as e:
            token_state["errors"].append(f"hide_host: {e}")
            logger.info("hide host warn: {}", e)

        try:
            load_result = ctx.eval(
                """
                (function(){
                  var bag = globalThis.__reeseHostRef;
                  if (!bag || typeof bag.pageLoad !== 'function') throw new Error('host bag incomplete');
                  if (!bag.snapshot) throw new Error('snapshot missing');
                  return bag.pageLoad(bag.snapshot);
                })()
                """,
                to_py=True,
            )
            logger.info("page.load result={}", load_result)
            try:
                leak = ctx.eval(
                    "Object.getOwnPropertyNames(window).includes('__iv8__')",
                    to_py=True,
                )
                logger.info("window.__iv8__ leaked after load={}", leak)
            except Exception:
                pass
        except Exception as e:
            token_state["errors"].append(f"page.load: {e}")
            logger.info("page.load error: {}", e)
            raise

        # 4) drive Protection API
        try:
            drive_ret = ctx.eval(drive_protection_js, to_py=True)
            logger.info("drive protection={}", drive_ret)
        except Exception as e:
            token_state["errors"].append(f"drive: {e}")
            logger.info("drive protection error: {}", e)

        for i in range(MAX_TICKS):
            # Real wall-clock wait: iv8 eventLoop.sleep is not reliable for wall time.
            time.sleep(SLEEP_MS / 1000.0)
            for _ in range(12):
                try:
                    ctx.eval(
                        """
                        (function(){
                          var b = globalThis.__reeseHostRef;
                          if (b.drainMicrotasks) b.drainMicrotasks();
                          if (b.drain) b.drain();
                          if (b.sleep) b.sleep(50);
                        })()
                        """
                    )
                except Exception:
                    try:
                        ctx.eval("__iv8__.eventLoop.drainMicrotasks()")
                        ctx.eval("__iv8__.eventLoop.drain()")
                        ctx.eval("__iv8__.eventLoop.sleep(50)")
                    except Exception:
                        pass
            if token_state.get("token"):
                logger.info("token ready at tick={}", i)
                break
            # also accept exported token string from Protection API
            try:
                exported = ctx.eval(
                    "globalThis.__exportedToken ? String(globalThis.__exportedToken) : ''",
                    to_py=True,
                )
                if isinstance(exported, str) and exported.startswith("3:") and len(exported) > 40:
                    token_state["token"] = exported
                    token_state["cookieDomain"] = token_state.get("cookieDomain") or "bangkokair.com"
                    logger.info("captured exported token len={}", len(exported))
                    break
            except Exception:
                pass
            if i % 5 == 4:
                try:
                    errs = ctx.eval("globalThis.__reeseBridgeErrors || []", to_py=True)
                    if errs:
                        token_state["errors"].extend([str(x) for x in list(errs)[-5:]])
                        logger.info("bridge errors sample: {}", list(errs)[-3:])
                except Exception:
                    pass
                try:
                    st = ctx.eval(
                        """
                        ({
                          count: globalThis.__prot && globalThis.__prot.scriptInterrogationCount,
                          running: globalThis.__prot && globalThis.__prot.running,
                          currentToken: globalThis.__prot && globalThis.__prot.currentToken,
                          exportErr: globalThis.__exportErr || null,
                          exportDone: !!globalThis.__exportDone
                        })
                        """,
                        to_py=True,
                    )
                    logger.info("prot state={}", st)
                except Exception:
                    pass
                logger.info(
                    "tick={} exchanges={} token={}",
                    i,
                    len(token_state["exchanges"]),
                    bool(token_state.get("token")),
                )

        try:
            errs = ctx.eval("globalThis.__reeseBridgeErrors || []", to_py=True)
            if errs:
                token_state["errors"].extend([str(x) for x in list(errs)[-20:]])
        except Exception:
            pass

    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        ch_sha = hashlib.sha256(challenge_js.encode("utf-8", errors="ignore")).hexdigest()
        meta = {
            "challenge_url": challenge_url,
            "challenge_sha256": ch_sha,
            "challenge_size": len(challenge_js),
            "token_len": len(token_state["token"] or ""),
            "renewInSec": token_state.get("renewInSec"),
            "cookieDomain": token_state.get("cookieDomain"),
            "exchange_count": len(token_state["exchanges"]),
            "exchanges": token_state["exchanges"][-15:],
            "errors": token_state["errors"][-20:],
        }
        (cache_dir / "last_l2_meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    if not token_state.get("token"):
        raise RuntimeError(
            "L2 failed: no reese token captured; "
            f"exchanges={len(token_state['exchanges'])} "
            f"errors={token_state['errors'][-8:]}"
        )

    return {
        "token": token_state["token"],
        "renewInSec": token_state.get("renewInSec"),
        "cookieDomain": token_state.get("cookieDomain") or "bangkokair.com",
        "exchanges": token_state["exchanges"],
        "errors": token_state["errors"],
        "challenge_url": challenge_url,
        "challenge_sha256": hashlib.sha256(
            challenge_js.encode("utf-8", errors="ignore")
        ).hexdigest(),
    }
