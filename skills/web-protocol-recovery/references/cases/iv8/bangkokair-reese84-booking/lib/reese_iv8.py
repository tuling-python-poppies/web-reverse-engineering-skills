# Offline-only case module. Final live egress belongs to python-collector under an approved project work-order.
from __future__ import annotations

def _reject_case_live_egress(action: str='live HTTP') -> None:
    raise RuntimeError(f'case entry refuses {action}: offline-only. Use projectRoot main.py + python-collector with a validated work-order.')
import hashlib
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
pass
try:
    from .http_session import UA, browser_headers
except ImportError:
    from http_session import UA, browser_headers

def _logger():
    try:
        from utils.logger import logger
        return logger
    except Exception:

        class _L:

            @staticmethod
            def info(msg, *args):
                if args:
                    try:
                        msg = msg.format(*args)
                    except Exception:
                        msg = str(msg) + ' ' + ' '.join(map(str, args))
                print(msg)
        return _L()
logger = _logger()
iv8 = None

def _import_iv8():
    try:
        from utils.iv8_silent import import_iv8_silent
        return import_iv8_silent()
    except Exception:
        import iv8 as _iv8
        return _iv8
MAX_TICKS = 60
SLEEP_MS = 200

def generate_reese84(session: requests.Session, *, entry_url: str, entry_html: str, challenge_url: str, challenge_js: str, cache_dir: Path | None=None) -> dict[str, Any]:
    """Run challenge in iv8; Python owns all live HTTP via __iv8__.data.pyHttp."""
    global iv8
    if iv8 is None:
        iv8 = _import_iv8()
    token_state: dict[str, Any] = {'token': None, 'renewInSec': None, 'cookieDomain': None, 'exchanges': [], 'errors': []}
    origin = f'{urlparse(entry_url).scheme}://{urlparse(entry_url).netloc}'
    challenge_headers = browser_headers({'Accept': 'application/json; charset=utf-8', 'Content-Type': 'text/plain; charset=utf-8', 'Referer': entry_url, 'Origin': origin})

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
            if str(k).lower() in {'host', 'content-length', 'connection'}:
                extra.pop(k, None)
        hdrs = {**challenge_headers, **extra}
        data = None if body is None else str(body)
        try:
            if method_s == 'GET':
                resp = (_reject_case_live_egress('session.get'), None)[1]
            elif method_s == 'POST':
                resp = (_reject_case_live_egress('session.post'), None)[1]
            elif method_s == 'PUT':
                resp = (_reject_case_live_egress('session.put'), None)[1]
            else:
                resp = (_reject_case_live_egress('session.request'), None)[1]
        except Exception as e:
            token_state['errors'].append(f'py_http {method_s} {request_url}: {e}')
            return json.dumps({'url': request_url, 'status': 0, 'statusText': 'error', 'headers': {}, 'body': ''})
        if resp is None:
            return json.dumps({'url': request_url, 'status': 0, 'statusText': 'null', 'headers': {}, 'body': ''})
        body_text = resp.text or ''
        token_state['exchanges'].append({'method': method_s, 'url': request_url, 'status': int(resp.status_code), 'req_len': len(data or ''), 'resp_len': len(body_text), 'req_prefix': (data or '')[:80], 'resp_prefix': body_text[:200]})
        logger.info('pyHttp {} {} status={} req_len={} resp_len={} req_prefix={}', method_s, request_url[:80], int(resp.status_code), len(data or ''), len(body_text), (data or '')[:40])
        if data and (len(data) > 40 or 'error' in data or 'solution' in data):
            token_state.setdefault('request_bodies', []).append(data[:4000])
            logger.info('long/error request body prefix={}', data[:200].replace('\n', ' '))
        if int(resp.status_code) == 200 and body_text:
            try:
                j = json.loads(body_text)
                if isinstance(j, dict):
                    if isinstance(j.get('token'), str) and j['token']:
                        token_state['token'] = j['token']
                        token_state['renewInSec'] = j.get('renewInSec')
                        token_state['cookieDomain'] = j.get('cookieDomain') or 'bangkokair.com'
                        logger.info('captured reese token len={} renewInSec={} domain={}', len(token_state['token']), token_state['renewInSec'], token_state['cookieDomain'])
                    else:
                        logger.info('json response keys={} prefix={}', list(j.keys())[:12], body_text[:120].replace('\n', ' '))
            except Exception:
                logger.info('body prefix={}', body_text[:120].replace('\n', ' '))
        body_for_js = body_text if len(body_text) <= 2000000 else body_text[:2000000]
        raw_headers = {str(k): str(v) for k, v in dict(resp.headers).items()}
        safe_headers = {}
        for k, v in raw_headers.items():
            lk = k.lower()
            if lk in {'set-cookie', 'set-cookie2', 'content-encoding', 'content-length', 'transfer-encoding', 'connection'}:
                continue
            safe_headers[k] = v
        if 'content-type' not in {k.lower() for k in safe_headers}:
            safe_headers['content-type'] = 'application/json; charset=utf-8'
        return json.dumps({'url': request_url, 'status': int(resp.status_code), 'statusText': getattr(resp, 'reason', '') or 'OK', 'headers': safe_headers, 'body': body_for_js})
    parsed = urlparse(entry_url)
    env = {'location': {'href': entry_url, 'origin': origin, 'protocol': f'{parsed.scheme}:', 'host': parsed.netloc, 'hostname': parsed.hostname or '', 'port': '', 'pathname': parsed.path or '/', 'search': f'?{parsed.query}' if parsed.query else '', 'hash': ''}, 'navigator': {'userAgent': UA, 'appVersion': UA.replace('Mozilla/', ''), 'language': 'en-GB', 'languages': ['en-GB', 'en-US', 'en'], 'platform': 'Win32', 'webdriver': False, 'hardwareConcurrency': 8, 'deviceMemory': 8, 'maxTouchPoints': 0, 'vendor': 'Google Inc.', 'cookieEnabled': True, 'onLine': True, 'pdfViewerEnabled': True}, 'screen': {'width': 1920, 'height': 1080, 'availWidth': 1920, 'availHeight': 1040, 'colorDepth': 24, 'pixelDepth': 24, 'orientation': {'type': 'landscape-primary', 'angle': 0}}}
    env_patch_js = "\n    (function() {\n      try {\n        if (!window.chrome) {\n          window.chrome = {\n            runtime: {},\n            app: { isInstalled: false, InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' }, RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' } },\n            csi: function() { return {}; },\n            loadTimes: function() { return {}; }\n          };\n        }\n        if (!navigator.userAgentData) {\n          navigator.userAgentData = {\n            brands: [\n              { brand: 'Chromium', version: '146' },\n              { brand: 'Not-A.Brand', version: '24' },\n              { brand: 'Google Chrome', version: '146' }\n            ],\n            mobile: false,\n            platform: 'Windows',\n            getHighEntropyValues: function() {\n              return Promise.resolve({\n                architecture: 'x86',\n                bitness: '64',\n                model: '',\n                platform: 'Windows',\n                platformVersion: '15.0.0',\n                uaFullVersion: '146.0.0.0',\n                fullVersionList: [\n                  { brand: 'Chromium', version: '146.0.0.0' },\n                  { brand: 'Not-A.Brand', version: '10.0.0.0' },\n                  { brand: 'Google Chrome', version: '146.0.0.0' }\n                ]\n              });\n            },\n            toJSON: function() { return { brands: this.brands, mobile: false, platform: 'Windows' }; }\n          };\n        }\n        // ALWAYS replace permissions.query so fingerprint probes NEVER call into\n        // iv8 EnvironmentAccessor for unknown names (speaker-selection, usb, hid, ...).\n        // Calling the native query is what prints the ERROR spam.\n        (function() {\n          var perms = {\n            query: function(desc) {\n              var name = '';\n              try { name = String((desc && (desc.name || desc)) || ''); } catch (_) {}\n              return Promise.resolve({ state: 'prompt', name: name, onchange: null });\n            }\n          };\n          try {\n            Object.defineProperty(navigator, 'permissions', {\n              configurable: true,\n              enumerable: true,\n              get: function() { return perms; },\n              set: function() {}\n            });\n          } catch (_) {\n            try { navigator.permissions = perms; } catch (__){}\n          }\n          try {\n            if (Navigator && Navigator.prototype) {\n              Object.defineProperty(Navigator.prototype, 'permissions', {\n                configurable: true,\n                enumerable: true,\n                get: function() { return perms; },\n                set: function() {}\n              });\n            }\n          } catch (_) {}\n        })();\n        if (!navigator.connection) {\n          navigator.connection = {\n            effectiveType: '4g', rtt: 50, downlink: 10, saveData: false,\n            addEventListener: function(){}, removeEventListener: function(){}\n          };\n        }\n        if (!window.matchMedia) {\n          window.matchMedia = function(q) {\n            return {\n              matches: false, media: String(q || ''),\n              addListener: function(){}, removeListener: function(){},\n              addEventListener: function(){}, removeEventListener: function(){},\n              dispatchEvent: function(){ return false; }, onchange: null\n            };\n          };\n        }\n        if (typeof document.hasFocus !== 'function') document.hasFocus = function() { return true; };\n        if (!document.visibilityState) {\n          try {\n            Object.defineProperty(document, 'visibilityState', { configurable: true, get: function() { return 'visible'; } });\n            Object.defineProperty(document, 'hidden', { configurable: true, get: function() { return false; } });\n          } catch (_) {}\n        }\n        // basic Notification / speech shims\n        if (typeof Notification === 'undefined') {\n          globalThis.Notification = function() {};\n          globalThis.Notification.permission = 'default';\n          globalThis.Notification.requestPermission = function() { return Promise.resolve('default'); };\n        }\n      } catch (e) {\n        globalThis.__reeseBridgeErrors = globalThis.__reeseBridgeErrors || [];\n        globalThis.__reeseBridgeErrors.push('env_patch:' + String(e));\n      }\n    })();\n    "
    bridge_js = "\n    (function() {\n      const bag = globalThis.__reeseHostRef;\n      if (!bag || typeof bag.pyHttp !== 'function' || typeof bag.pageLoad !== 'function') {\n        throw new Error('reese host ref missing');\n      }\n      globalThis.__reeseBridgeErrors = [];\n      globalThis.addEventListener('error', function(e) {\n        try { globalThis.__reeseBridgeErrors.push(String(e && e.message || e)); } catch (_) {}\n      });\n      globalThis.addEventListener('unhandledrejection', function(e) {\n        try { globalThis.__reeseBridgeErrors.push(String(e && e.reason || e)); } catch (_) {}\n      });\n\n      function makeResponse(raw) {\n        const data = (typeof raw === 'string') ? JSON.parse(raw) : raw;\n        // Preserve body exactly; gpc returns a JSON-encoded base64 string including quotes.\n        const bodyStr = data.body == null ? '' : String(data.body);\n        const headers = {};\n        for (const k of Object.keys(data.headers || {})) {\n          headers[String(k).toLowerCase()] = data.headers[k];\n        }\n        if (!headers['content-type']) {\n          headers['content-type'] = 'application/json; charset=utf-8';\n        }\n        // Custom Response-like object: more reliable than iv8 native Response body edge cases.\n        const resp = {\n          ok: (data.status || 0) >= 200 && (data.status || 0) < 300,\n          status: data.status || 0,\n          statusText: data.statusText || 'OK',\n          url: data.url || '',\n          redirected: false,\n          type: 'basic',\n          bodyUsed: false,\n          headers: {\n            get(name) {\n              const key = String(name || '').toLowerCase();\n              return headers[key] == null ? null : String(headers[key]);\n            },\n            has(name) {\n              const key = String(name || '').toLowerCase();\n              return Object.prototype.hasOwnProperty.call(headers, key);\n            },\n            forEach(cb) {\n              Object.keys(headers).forEach(function(k) { cb(headers[k], k); });\n            }\n          },\n          text: function() {\n            this.bodyUsed = true;\n            return Promise.resolve(bodyStr);\n          },\n          json: function() {\n            this.bodyUsed = true;\n            try {\n              // bodyStr is already a JSON document (object or JSON string)\n              return Promise.resolve(JSON.parse(bodyStr));\n            } catch (e) {\n              globalThis.__reeseBridgeErrors.push('json parse fail bodyPrefix=' + bodyStr.slice(0, 80) + ' err=' + String(e));\n              return Promise.reject(e);\n            }\n          },\n          arrayBuffer: function() {\n            this.bodyUsed = true;\n            const enc = new TextEncoder();\n            return Promise.resolve(enc.encode(bodyStr).buffer);\n          },\n          blob: function() {\n            this.bodyUsed = true;\n            return Promise.resolve(new Blob([bodyStr]));\n          },\n          clone: function() {\n            return makeResponse(data);\n          }\n        };\n        return resp;\n      }\n\n      globalThis.fetch = function(input, init) {\n        try {\n          init = init || {};\n          const url = (typeof input === 'string') ? input : (input && input.url) || String(input);\n          const method = (init.method || 'GET').toUpperCase();\n          let body = init.body == null ? null : String(init.body);\n          let headersObj = {};\n          if (init.headers) {\n            if (typeof init.headers.forEach === 'function') {\n              init.headers.forEach(function(v, k) { headersObj[k] = v; });\n            } else {\n              headersObj = Object.assign({}, init.headers);\n            }\n          }\n          const raw = bag.pyHttp(method, url, body, JSON.stringify(headersObj));\n          return Promise.resolve(makeResponse(raw));\n        } catch (e) {\n          globalThis.__reeseBridgeErrors.push(String(e));\n          return Promise.reject(e);\n        }\n      };\n\n      const XHR = globalThis.XMLHttpRequest;\n      if (XHR && XHR.prototype) {\n        const open = XHR.prototype.open;\n        const send = XHR.prototype.send;\n        const setRequestHeader = XHR.prototype.setRequestHeader;\n        XHR.prototype.open = function(method, url) {\n          this.__reeseMethod = String(method || 'GET');\n          this.__reeseUrl = String(url || '');\n          this.__reeseHeaders = {};\n          return open.apply(this, arguments);\n        };\n        XHR.prototype.setRequestHeader = function(k, v) {\n          try { this.__reeseHeaders[String(k)] = String(v); } catch (_) {}\n          return setRequestHeader.apply(this, arguments);\n        };\n        XHR.prototype.send = function(body) {\n          const self = this;\n          try {\n            const raw = bag.pyHttp(\n              self.__reeseMethod || 'GET',\n              self.__reeseUrl || '',\n              body == null ? null : String(body),\n              JSON.stringify(self.__reeseHeaders || {})\n            );\n            const data = JSON.parse(raw);\n            setTimeout(function() {\n              try {\n                Object.defineProperty(self, 'status', { configurable: true, get: function() { return data.status || 0; } });\n                Object.defineProperty(self, 'statusText', { configurable: true, get: function() { return data.statusText || ''; } });\n                Object.defineProperty(self, 'responseText', { configurable: true, get: function() { return String(data.body || ''); } });\n                Object.defineProperty(self, 'response', { configurable: true, get: function() { return String(data.body || ''); } });\n                Object.defineProperty(self, 'readyState', { configurable: true, get: function() { return 4; } });\n                Object.defineProperty(self, 'responseURL', { configurable: true, get: function() { return data.url || self.__reeseUrl || ''; } });\n                if (typeof self.onreadystatechange === 'function') self.onreadystatechange();\n                if (typeof self.onload === 'function') self.onload();\n                if (typeof self.onloadend === 'function') self.onloadend();\n              } catch (e2) {\n                globalThis.__reeseBridgeErrors.push(String(e2));\n              }\n            }, 0);\n          } catch (e) {\n            globalThis.__reeseBridgeErrors.push(String(e));\n            setTimeout(function() {\n              if (typeof self.onerror === 'function') self.onerror(e);\n            }, 0);\n          }\n        };\n      }\n\n      // Global wrap: Reese may call EventTarget.prototype.addEventListener directly.\n      // Catch TypeError inside load handlers so iv8 C++ verbose EventListener log is reduced.\n      try {\n        if (typeof EventTarget !== 'undefined' && EventTarget.prototype && EventTarget.prototype.addEventListener) {\n          var _etAdd = EventTarget.prototype.addEventListener;\n          EventTarget.prototype.addEventListener = function(type, listener, options) {\n            if (String(type) === 'load' && typeof listener === 'function') {\n              var tag = '';\n              try { tag = String(this && this.tagName || ''); } catch (_) {}\n              if (tag.toLowerCase() === 'iframe' || this === window || this === document) {\n                var wrapped = function(ev) {\n                  try { return listener.call(this, ev); }\n                  catch (err) {\n                    try {\n                      globalThis.__reeseBridgeErrors.push(\n                        'load_handler:' + String(err && err.message || err)\n                      );\n                    } catch (_) {}\n                  }\n                };\n                return _etAdd.call(this, type, wrapped, options);\n              }\n            }\n            return _etAdd.call(this, type, listener, options);\n          };\n        }\n      } catch (_) {}\n\n      // iframe lifecycle: interrogator creates IFRAME; fire load and patch child realm\n      function patchIframeRealm(win) {\n        if (!win || win.__reesePatched) return;\n        try { win.__reesePatched = true; } catch (_) {}\n        try {\n          // hide host in child if present\n          try { delete win.__iv8__; } catch (_) {}\n          try {\n            if (win.Object && win.Object.getOwnPropertyNames) {\n              const gopn = win.Object.getOwnPropertyNames;\n              win.Object.defineProperty(win.Object, 'getOwnPropertyNames', {\n                configurable: true,\n                writable: true,\n                value: function(obj) {\n                  return gopn(obj).filter(function(k) { return k !== '__iv8__'; });\n                }\n              });\n            }\n          } catch (_) {}\n          // share fetch/XHR bridge into child\n          try { win.fetch = globalThis.fetch; } catch (_) {}\n          try {\n            if (win.XMLHttpRequest && globalThis.XMLHttpRequest) {\n              win.XMLHttpRequest = globalThis.XMLHttpRequest;\n            }\n          } catch (_) {}\n          try {\n            if (!win.chrome && window.chrome) win.chrome = window.chrome;\n          } catch (_) {}\n          try {\n            if (win.navigator && !win.navigator.userAgentData && navigator.userAgentData) {\n              win.navigator.userAgentData = navigator.userAgentData;\n            }\n          } catch (_) {}\n          // permissions wrapper in child realm too\n          try {\n            var childPerms = {\n              query: function(desc) {\n                var name = '';\n                try { name = String((desc && (desc.name || desc)) || ''); } catch (_) {}\n                return Promise.resolve({ state: 'prompt', name: name, onchange: null });\n              }\n            };\n            Object.defineProperty(win.navigator, 'permissions', {\n              configurable: true,\n              enumerable: true,\n              get: function() { return childPerms; },\n              set: function() {}\n            });\n          } catch (_) {}\n        } catch (e) {\n          globalThis.__reeseBridgeErrors.push('iframe_patch:' + String(e));\n        }\n      }\n\n      function armIframe(iframe) {\n        if (!iframe || iframe.__reeseArmed) return;\n        iframe.__reeseArmed = true;\n\n        // Observe native/synthetic load: mark fired so we never double-dispatch.\n        try {\n          var _markLoad = function() {\n            iframe.__reeseLoadFired = true;\n            try { patchIframeRealm(iframe.contentWindow); } catch (_) {}\n          };\n          if (iframe.addEventListener) {\n            iframe.addEventListener('load', _markLoad, true);\n          }\n        } catch (_) {}\n\n        // Wrap element-level handlers for safer challenge callbacks.\n        (function wrapLoadHandlers(el) {\n          try {\n            var origAdd = el.addEventListener && el.addEventListener.bind(el);\n            if (origAdd) {\n              el.addEventListener = function(type, listener, options) {\n                if (String(type) === 'load' && typeof listener === 'function') {\n                  var wrapped = function(ev) {\n                    try { return listener.call(this, ev); }\n                    catch (err) {\n                      try {\n                        globalThis.__reeseBridgeErrors.push(\n                          'iframe_load_handler:' + String(err && err.message || err)\n                        );\n                      } catch (_) {}\n                    }\n                  };\n                  return origAdd(type, wrapped, options);\n                }\n                return origAdd(type, listener, options);\n              };\n            }\n          } catch (_) {}\n          try {\n            var current = null;\n            Object.defineProperty(el, 'onload', {\n              configurable: true,\n              enumerable: true,\n              get: function() { return current; },\n              set: function(fn) {\n                if (typeof fn !== 'function') {\n                  current = fn;\n                  return;\n                }\n                current = function(ev) {\n                  try { return fn.call(this, ev); }\n                  catch (err) {\n                    try {\n                      globalThis.__reeseBridgeErrors.push(\n                        'iframe_onload_prop:' + String(err && err.message || err)\n                      );\n                    } catch (_) {}\n                  }\n                };\n              }\n            });\n          } catch (_) {}\n        })(iframe);\n\n        // Fire load at most once, and only if native load did not already run.\n        const fireLoadOnce = function() {\n          if (iframe.__reeseLoadFired) return;\n          iframe.__reeseLoadFired = true;\n          try {\n            patchIframeRealm(iframe.contentWindow);\n            try {\n              if (typeof Event === 'function') {\n                iframe.dispatchEvent(new Event('load'));\n                return;\n              }\n            } catch (_) {}\n            try {\n              var ev = document.createEvent('Event');\n              ev.initEvent('load', false, false);\n              iframe.dispatchEvent(ev);\n            } catch (__) {}\n          } catch (e) {\n            globalThis.__reeseBridgeErrors.push('iframe_load:' + String(e));\n          }\n        };\n\n        const scheduleFire = function() {\n          if (iframe.__reeseLoadScheduled) return;\n          iframe.__reeseLoadScheduled = true;\n          var tries = 0;\n          var tick = function() {\n            tries += 1;\n            if (iframe.__reeseLoadFired) return;\n            try {\n              var win = iframe.contentWindow;\n              var doc = iframe.contentDocument || (win && win.document);\n              patchIframeRealm(win);\n              var ready = !doc || doc.readyState === 'complete' || doc.readyState === 'interactive';\n              if (ready || tries >= 10) {\n                // Wait for challenge to attach listeners; skip if native load already fired.\n                setTimeout(function() {\n                  if (!iframe.__reeseLoadFired) fireLoadOnce();\n                }, 40);\n                return;\n              }\n            } catch (_) {\n              setTimeout(function() {\n                if (!iframe.__reeseLoadFired) fireLoadOnce();\n              }, 40);\n              return;\n            }\n            setTimeout(tick, 8);\n          };\n          setTimeout(tick, 0);\n        };\n\n        try {\n          var setAttr = iframe.setAttribute ? iframe.setAttribute.bind(iframe) : null;\n          if (setAttr) {\n            iframe.setAttribute = function(name, value) {\n              var r = setAttr(name, value);\n              if (String(name).toLowerCase() === 'src') {\n                iframe.__reeseLoadScheduled = false;\n                scheduleFire();\n              }\n              return r;\n            };\n          }\n        } catch (_) {}\n\n        scheduleFire();\n      }\n\n      try {\n        const ce = document.createElement.bind(document);\n        document.createElement = function(tag) {\n          const el = ce(tag);\n          if (String(tag).toLowerCase() === 'iframe') {\n            armIframe(el);\n          }\n          return el;\n        };\n      } catch (e) {\n        globalThis.__reeseBridgeErrors.push('createElement hook:' + String(e));\n      }\n\n      try {\n        const ap = Node.prototype.appendChild;\n        Node.prototype.appendChild = function(child) {\n          const r = ap.call(this, child);\n          try {\n            if (child && String(child.tagName || '').toLowerCase() === 'iframe') {\n              armIframe(child);\n            }\n          } catch (_) {}\n          return r;\n        };\n      } catch (e) {\n        globalThis.__reeseBridgeErrors.push('appendChild hook:' + String(e));\n      }\n\n      try {\n        const ib = Node.prototype.insertBefore;\n        Node.prototype.insertBefore = function(newNode, ref) {\n          const r = ib.call(this, newNode, ref);\n          try {\n            if (newNode && String(newNode.tagName || '').toLowerCase() === 'iframe') {\n              armIframe(newNode);\n            }\n          } catch (_) {}\n          return r;\n        };\n      } catch (_) {}\n    })();\n    "
    parsed_ch = urlparse(challenge_url)
    path_only = parsed_ch.path or ''
    path_with_query = path_only + (f'?{parsed_ch.query}' if parsed_ch.query else '')
    resource_map = {challenge_url: {'body': challenge_js, 'contentType': 'application/javascript'}, path_only: {'body': challenge_js, 'contentType': 'application/javascript'}, path_with_query: {'body': challenge_js, 'contentType': 'application/javascript'}, urljoin(entry_url, path_only): {'body': challenge_js, 'contentType': 'application/javascript'}, urljoin(entry_url, path_with_query): {'body': challenge_js, 'contentType': 'application/javascript'}}
    script_src = path_with_query if path_with_query else path_only
    if not script_src:
        script_src = challenge_url
    html_for_load = f'''<!doctype html><html><head><meta charset='utf-8'><title>Reese</title><script src="{script_src}"></script></head><body></body></html>'''
    snapshot = {'baseURL': entry_url, 'html': html_for_load, 'headers': {'content-type': 'text/html; charset=utf-8'}, 'resources': resource_map}
    capture_host_js = "\n    (function() {\n      // __iv8__ is a special binding: !!__iv8__ === false and assigning the host\n      // object loses it. Capture FUNCTIONS via property access only.\n      var pageLoad = __iv8__.page.load;\n      var drain = __iv8__.eventLoop.drain;\n      var drainMicrotasks = __iv8__.eventLoop.drainMicrotasks;\n      var sleep = __iv8__.eventLoop.sleep;\n      var pyHttp = __iv8__.data.pyHttp;\n      // capture snapshot object now (cannot rely on __iv8__.data after hide)\n      var snapshotObj = __iv8__.data.snapshot;\n      if (typeof pageLoad !== 'function') throw new Error('iv8.page.load missing');\n      if (typeof drain !== 'function') throw new Error('iv8.eventLoop.drain missing');\n      if (typeof pyHttp !== 'function') throw new Error('iv8.data.pyHttp missing (expose first)');\n      if (!snapshotObj) throw new Error('snapshot missing on __iv8__.data');\n      globalThis.__reeseHostRef = {\n        pageLoad: pageLoad,\n        drain: drain,\n        drainMicrotasks: drainMicrotasks,\n        sleep: sleep,\n        pyHttp: pyHttp,\n        snapshot: snapshotObj\n      };\n      return true;\n    })()\n    "
    hide_host_js = "\n    (function() {\n      // Hide window.__iv8__ from enumeration AFTER host capture.\n      // Do this only after bridge is installed and host members are captured.\n      try { delete window.__iv8__; } catch (_) {}\n      try {\n        const _gopn = Object.getOwnPropertyNames;\n        Object.defineProperty(Object, 'getOwnPropertyNames', {\n          configurable: true,\n          writable: true,\n          value: function(obj) {\n            return _gopn(obj).filter(function(k) { return k !== '__iv8__'; });\n          }\n        });\n      } catch (_) {}\n      return !Object.getOwnPropertyNames(window).includes('__iv8__');\n    })()\n    "
    drive_protection_js = "\n    (function() {\n      try {\n        if (typeof initializeProtection !== 'function') return 'no-init';\n        const p = initializeProtection();\n        globalThis.__prot = p;\n        try { if (typeof p.start === 'function') p.start(); } catch (_) {}\n        try { if (typeof p.startInternal === 'function') p.startInternal(); } catch (_) {}\n        try { if (typeof p.solve === 'function') p.solve(); } catch (_) {}\n        try {\n          if (p.interrogator && typeof p.interrogator.interrogate === 'function') {\n            p.interrogator.interrogate();\n          }\n        } catch (_) {}\n        try {\n          if (typeof p.exportToken === 'function') {\n            p.exportToken(20000).then(function(t) {\n              globalThis.__exportedToken = t;\n              globalThis.__exportDone = true;\n            }).catch(function(e) {\n              globalThis.__exportErr = String(e);\n              globalThis.__exportDone = true;\n            });\n          }\n        } catch (e) {\n          globalThis.__exportErr = String(e);\n        }\n        return 'driven';\n      } catch (e) {\n        globalThis.__reeseBridgeErrors = globalThis.__reeseBridgeErrors || [];\n        globalThis.__reeseBridgeErrors.push('drive:' + String(e));\n        return 'drive-err:' + String(e);\n      }\n    })()\n    "
    perm_config = {}
    try:
        defaults = iv8.JSContext.get_defaults()
        for path, default in defaults.items():
            if not str(path).startswith('config.permissions.'):
                continue
            parts = str(path).split('.')
            if len(parts) < 3:
                continue
            key = parts[2]
            if isinstance(default, str) and default in {'granted', 'denied', 'prompt'}:
                perm_config[key] = default
            else:
                perm_config.setdefault(key, 'prompt')
    except Exception:
        perm_config = {'geolocation': 'prompt', 'notifications': 'prompt', 'camera': 'prompt', 'microphone': 'prompt', 'clipboard-read': 'prompt', 'clipboard-write': 'granted', 'accelerometer': 'granted', 'gyroscope': 'granted'}
    ctx_config = {'timezone': 'UTC', 'permissions': perm_config}
    with iv8.JSContext(environment=env, config=ctx_config, time_mode='system') as ctx:
        ctx.expose(py_http, 'pyHttp')
        ctx.expose(snapshot, 'snapshot')
        try:
            ok_host = ctx.eval(capture_host_js, to_py=True)
            logger.info('host APIs captured={}', ok_host)
        except Exception as e:
            token_state['errors'].append(f'capture_host: {e}')
            raise RuntimeError(f'cannot capture iv8 host APIs: {e}') from e
        ctx.eval(bridge_js)
        try:
            ctx.eval(env_patch_js)
        except Exception as e:
            token_state['errors'].append(f'env_patch: {e}')
        try:
            hidden = ctx.eval(hide_host_js, to_py=True)
            logger.info('host hidden from window GOPN={}', hidden)
        except Exception as e:
            token_state['errors'].append(f'hide_host: {e}')
            logger.info('hide host warn: {}', e)
        try:
            load_result = ctx.eval("\n                (function(){\n                  var bag = globalThis.__reeseHostRef;\n                  if (!bag || typeof bag.pageLoad !== 'function') throw new Error('host bag incomplete');\n                  if (!bag.snapshot) throw new Error('snapshot missing');\n                  return bag.pageLoad(bag.snapshot);\n                })()\n                ", to_py=True)
            logger.info('page.load result={}', load_result)
            try:
                leak = ctx.eval("Object.getOwnPropertyNames(window).includes('__iv8__')", to_py=True)
                logger.info('window.__iv8__ leaked after load={}', leak)
            except Exception:
                pass
        except Exception as e:
            token_state['errors'].append(f'page.load: {e}')
            logger.info('page.load error: {}', e)
            raise
        try:
            drive_ret = ctx.eval(drive_protection_js, to_py=True)
            logger.info('drive protection={}', drive_ret)
        except Exception as e:
            token_state['errors'].append(f'drive: {e}')
            logger.info('drive protection error: {}', e)
        for i in range(MAX_TICKS):
            time.sleep(SLEEP_MS / 1000.0)
            for _ in range(12):
                try:
                    ctx.eval('\n                        (function(){\n                          var b = globalThis.__reeseHostRef;\n                          if (b.drainMicrotasks) b.drainMicrotasks();\n                          if (b.drain) b.drain();\n                          if (b.sleep) b.sleep(50);\n                        })()\n                        ')
                except Exception:
                    try:
                        ctx.eval('__iv8__.eventLoop.drainMicrotasks()')
                        ctx.eval('__iv8__.eventLoop.drain()')
                        ctx.eval('__iv8__.eventLoop.sleep(50)')
                    except Exception:
                        pass
            if token_state.get('token'):
                logger.info('token ready at tick={}', i)
                break
            try:
                exported = ctx.eval("globalThis.__exportedToken ? String(globalThis.__exportedToken) : ''", to_py=True)
                if isinstance(exported, str) and exported.startswith('3:') and (len(exported) > 40):
                    token_state['token'] = exported
                    token_state['cookieDomain'] = token_state.get('cookieDomain') or 'bangkokair.com'
                    logger.info('captured exported token len={}', len(exported))
                    break
            except Exception:
                pass
            if i % 5 == 4:
                try:
                    errs = ctx.eval('globalThis.__reeseBridgeErrors || []', to_py=True)
                    if errs:
                        token_state['errors'].extend([str(x) for x in list(errs)[-5:]])
                        logger.info('bridge errors sample: {}', list(errs)[-3:])
                except Exception:
                    pass
                try:
                    st = ctx.eval('\n                        ({\n                          count: globalThis.__prot && globalThis.__prot.scriptInterrogationCount,\n                          running: globalThis.__prot && globalThis.__prot.running,\n                          currentToken: globalThis.__prot && globalThis.__prot.currentToken,\n                          exportErr: globalThis.__exportErr || null,\n                          exportDone: !!globalThis.__exportDone\n                        })\n                        ', to_py=True)
                    logger.info('prot state={}', st)
                except Exception:
                    pass
                logger.info('tick={} exchanges={} token={}', i, len(token_state['exchanges']), bool(token_state.get('token')))
        try:
            errs = ctx.eval('globalThis.__reeseBridgeErrors || []', to_py=True)
            if errs:
                token_state['errors'].extend([str(x) for x in list(errs)[-20:]])
        except Exception:
            pass
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        ch_sha = hashlib.sha256(challenge_js.encode('utf-8', errors='ignore')).hexdigest()
        safe_exchanges = [{'method': e.get('method'), 'url': e.get('url'), 'status': e.get('status'), 'req_len': e.get('req_len'), 'resp_len': e.get('resp_len')} for e in token_state['exchanges'][-15:]]
        meta = {'challenge_url': challenge_url, 'challenge_sha256': ch_sha, 'challenge_size': len(challenge_js), 'token_len': len(token_state['token'] or ''), 'renewInSec': token_state.get('renewInSec'), 'cookieDomain': token_state.get('cookieDomain'), 'exchange_count': len(token_state['exchanges']), 'exchanges': safe_exchanges, 'errors': token_state['errors'][-20:]}
        (cache_dir / 'last_l2_meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    if not token_state.get('token'):
        raise RuntimeError(f"L2 failed: no reese token captured; exchanges={len(token_state['exchanges'])} errors={token_state['errors'][-8:]}")
    return {'token': token_state['token'], 'renewInSec': token_state.get('renewInSec'), 'cookieDomain': token_state.get('cookieDomain') or 'bangkokair.com', 'exchanges': token_state['exchanges'], 'errors': token_state['errors'], 'challenge_url': challenge_url, 'challenge_sha256': hashlib.sha256(challenge_js.encode('utf-8', errors='ignore')).hexdigest()}
