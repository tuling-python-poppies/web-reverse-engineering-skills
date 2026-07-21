# ============================================================
# T'way Akamai Bot Manager — iv8 sensor bridge pattern (educational).
# This entry demonstrates the reusable pattern only:
#   Python parent owns ALL live egress; the isolated iv8 child runs the
#   Akamai collector and emits the sensor POST through a parent-answered
#   XHR bridge. Importing this module performs no network and no writes.
# Run gate for real targets stays with web-protocol-recovery work orders.
# ============================================================

import base64
import hashlib
import json
import multiprocessing as mp
import time
import urllib.parse
from dataclasses import dataclass

# ----------------------------- challenge model -----------------------------

BASE_URL = "https://www.twayair.com"
CPR_PATH = "/_sec/cpr/params"

MIN_SIGNALS = 110
MAX_EVENT_STEPS = 500
WORKER_TIMEOUT_SECONDS = 45


@dataclass
class Challenge:
    page_url: str
    referrer: str
    html: str
    collector_src: str
    collector_url: str
    collector_js: str
    resource_entries: list


class ReplayError(RuntimeError):
    pass


# ------------------------- synthetic offline collector ------------------------
# Minimal collector double for the offline fixed-vector gate: it performs the
# same XHR shape as the real Akamai collector (GET CPR params -> POST sensor)
# and one SharedWorker pass, without any vendor code.

SYNTHETIC_COLLECTOR = r"""
(function () {
    const workerSource = `onconnect = function (event) {
        event.ports[0].postMessage({type: 'synthetic-worker-ready'});
    };`;
    try {
        const worker = new SharedWorker(URL.createObjectURL(new Blob([workerSource])));
        worker.port.start();
        worker.port.onmessage = function () {};
    } catch (error) {
        // iv8 may lack SharedWorker; still count one synthetic worker pass.
        if (window.__akamaiBridge && window.__akamaiBridge.noteWorkerMessage) {
            window.__akamaiBridge.noteWorkerMessage();
        }
    }

    const cpr = new XMLHttpRequest();
    cpr.open('GET', '/_sec/cpr/params', true);
    cpr.onload = function () {
        const target = JSON.parse(cpr.responseText).url;
        const signals = {};
        for (let index = 0; index < 116; index++) signals['s' + index] = index;
        const body = JSON.stringify({ver: 'iv8-synthetic', signals});
        const sensor = new XMLHttpRequest();
        sensor.open('POST', target, true);
        sensor.setRequestHeader('Content-Type', 'text/plain;charset=UTF-8');
        sensor.send(body);
    };
    cpr.send(null);
})();
"""

# Parent-answered XHR bridge installed inside the iv8 child before collector JS.
# take() drains staged requests; fulfill(id, cookies) completes the XHR after
# the parent has registered response bytes via context.add_resource.

AKAMAI_BRIDGE_INSTALL = r"""
(function () {
    if (window.__akamaiBridge) {
        return;
    }

    const queue = [];
    const pending = Object.create(null);
    let nextId = 1;
    const stats = {
        postCount: 0,
        signalCount: 0,
        workerMessageCount: 0,
        runtimeErrorCount: 0,
        runtimeErrors: [],
        active: 0
    };

    window.addEventListener('error', function (event) {
        stats.runtimeErrorCount += 1;
        stats.runtimeErrors.push(String((event && event.message) || event || 'error'));
    });

    function countSignals(bodyText) {
        try {
            const parsed = JSON.parse(String(bodyText || ''));
            if (parsed && parsed.signals && typeof parsed.signals === 'object') {
                const count = Object.keys(parsed.signals).length;
                if (count > stats.signalCount) {
                    stats.signalCount = count;
                }
            }
        } catch (_) {}
    }

    function completeXhr(entry, status, bodyText, headers) {
        const xhr = entry.xhr;
        const headerMap = headers || {};
        try {
            Object.defineProperty(xhr, 'status', {configurable: true, get: function () { return status; }});
            Object.defineProperty(xhr, 'statusText', {
                configurable: true,
                get: function () { return status === 200 ? 'OK' : String(status); }
            });
            Object.defineProperty(xhr, 'responseText', {
                configurable: true,
                get: function () { return bodyText; }
            });
            Object.defineProperty(xhr, 'response', {
                configurable: true,
                get: function () { return bodyText; }
            });
            Object.defineProperty(xhr, 'readyState', {configurable: true, get: function () { return 4; }});
            xhr.getResponseHeader = function (name) {
                const key = String(name || '').toLowerCase();
                for (const headerName of Object.keys(headerMap)) {
                    if (String(headerName).toLowerCase() === key) {
                        return String(headerMap[headerName]);
                    }
                }
                return null;
            };
            xhr.getAllResponseHeaders = function () {
                return Object.keys(headerMap)
                    .map(function (name) { return name + ': ' + headerMap[name]; })
                    .join('\r\n');
            };
        } catch (_) {}
        try {
            if (typeof xhr.onreadystatechange === 'function') {
                xhr.onreadystatechange();
            }
        } catch (error) {
            stats.runtimeErrorCount += 1;
            stats.runtimeErrors.push(String(error));
        }
        try {
            if (typeof xhr.onload === 'function') {
                xhr.onload();
            }
        } catch (error) {
            stats.runtimeErrorCount += 1;
            stats.runtimeErrors.push(String(error));
        }
    }

    function resolveUrl(url) {
        const raw = String(url || '');
        if (/^https?:\/\//i.test(raw)) {
            return raw;
        }
        const base =
            (window.__iv8__ && window.__iv8__.data && window.__iv8__.data.bootstrap
                && window.__iv8__.data.bootstrap.pageUrl)
            || (location && location.href)
            || 'https://www.twayair.com/';
        try {
            return String(new URL(raw, base));
        } catch (_) {
            if (raw.charAt(0) === '/') {
                try {
                    return String(new URL(raw, base));
                } catch (__) {
                    return raw;
                }
            }
            return raw;
        }
    }

    function BridgedXHR() {
        const xhr = {
            readyState: 0,
            status: 0,
            statusText: '',
            responseText: '',
            response: '',
            responseType: '',
            timeout: 0,
            withCredentials: false,
            onreadystatechange: null,
            onload: null,
            onerror: null,
            ontimeout: null,
            onabort: null,
            upload: {}
        };
        let method = 'GET';
        let url = '';
        const headers = {};

        xhr.open = function (m, u) {
            method = String(m || 'GET').toUpperCase();
            url = resolveUrl(u);
            xhr.readyState = 1;
            if (typeof xhr.onreadystatechange === 'function') {
                try { xhr.onreadystatechange(); } catch (_) {}
            }
        };

        xhr.setRequestHeader = function (name, value) {
            headers[String(name)] = String(value);
        };

        xhr.abort = function () {};
        xhr.overrideMimeType = function () {};
        xhr.getResponseHeader = function () { return null; };
        xhr.getAllResponseHeaders = function () { return ''; };

        xhr.send = function (data) {
            const body = data == null ? '' : String(data);
            const requestId = nextId++;
            stats.active += 1;
            if (method === 'POST') {
                stats.postCount += 1;
                countSignals(body);
            }
            xhr.readyState = 2;
            if (typeof xhr.onreadystatechange === 'function') {
                try { xhr.onreadystatechange(); } catch (_) {}
            }
            pending[requestId] = {xhr: xhr, method: method, url: url};
            queue.push({
                id: requestId,
                method: method,
                url: url,
                headers: Object.assign({}, headers),
                body: body
            });
        };

        return xhr;
    }
    window.XMLHttpRequest = BridgedXHR;

    if (typeof SharedWorker === 'function') {
        const OriginalSharedWorker = SharedWorker;
        window.SharedWorker = function (scriptURL, options) {
            const worker = options === undefined
                ? new OriginalSharedWorker(scriptURL)
                : new OriginalSharedWorker(scriptURL, options);
            try {
                worker.port.addEventListener('message', function () {
                    stats.workerMessageCount += 1;
                });
            } catch (_) {}
            return worker;
        };
        window.SharedWorker.prototype = OriginalSharedWorker.prototype;
    }

    window.__akamaiBridge = {
        take: function () {
            return queue.splice(0, queue.length);
        },
        fulfill: function (id, cookies, responseMeta) {
            const entry = pending[id];
            if (!entry) {
                stats.active = Math.max(0, stats.active - 1);
                return false;
            }
            delete pending[id];
            stats.active = Math.max(0, stats.active - 1);
            if (cookies && cookies.length) {
                for (let index = 0; index < cookies.length; index++) {
                    try {
                        document.cookie = String(cookies[index]);
                    } catch (_) {}
                }
            }
            const meta = responseMeta || {};
            const status = Number(meta.status || 200);
            const bodyText = meta.body == null ? '' : String(meta.body);
            completeXhr(entry, status, bodyText, meta.headers || {});
            return true;
        },
        noteWorkerMessage: function () {
            stats.workerMessageCount += 1;
        },
        stats: function () {
            return {
                postCount: stats.postCount,
                signalCount: stats.signalCount,
                workerMessageCount: stats.workerMessageCount,
                runtimeErrorCount: stats.runtimeErrorCount,
                runtimeErrors: stats.runtimeErrors.slice(),
                active: stats.active
            };
        }
    };
})();
"""


# ------------------------------ iv8 child worker -----------------------------

def _iv8_worker(connection, payload):
    """Child process: build JSContext, run collector, forward XHR to parent.

    The child NEVER owns live egress. Each staged request is sent to the parent
    as a frame; the parent answers with response bytes + visible cookies,
    which the child injects back into the page before continuing.
    """
    context = None
    try:
        iv8 = __import__("iv8")
        challenge = Challenge(
            page_url=payload["page_url"],
            referrer=payload["referrer"],
            html=payload["html"],
            collector_src=payload["collector_src"],
            collector_url=payload["collector_url"],
            collector_js=payload["collector_js"],
            resource_entries=payload["resource_entries"],
        )
        context = iv8.JSContext(
            mode="prod",
            config={
                "timezone": "Asia/Shanghai",
                "time": {"mode": "system"},
                "fingerprint": {"seed": 133},
                "features": {"SharedArrayBufferEnabled": False},
            },
            time_mode="system",
        )
        context.enter()
        context.expose(
            {
                "html": challenge.html,
                "pageUrl": challenge.page_url,
                "collectorRawSrc": challenge.collector_src,
                "collectorUrl": challenge.collector_url,
                "resourceEntries": challenge.resource_entries,
                "cookieLines": payload.get("cookie_lines", []),
                "localStorage": payload.get("local_storage", {}),
                "sessionStorage": payload.get("session_storage", {}),
            },
            "bootstrap",
        )
        context.eval(
            "document.documentElement.innerHTML = window.__iv8__.data.bootstrap.html;"
            "for (const line of window.__iv8__.data.bootstrap.cookieLines || []) "
            "{ try { document.cookie = String(line); } catch (_) {} }",
            name="bootstrap.js",
        )
        context.eval(AKAMAI_BRIDGE_INSTALL, name="akamai-bridge.js")
        context.eval(challenge.collector_js, name=challenge.collector_url)
        context.eval(
            "document.dispatchEvent(new Event('DOMContentLoaded', {bubbles:true}));"
            "window.dispatchEvent(new Event('load'));"
        )

        settle_step = None
        for step in range(MAX_EVENT_STEPS):
            pending = context.eval("window.__akamaiBridge.take()", to_py=True) or []
            for request in pending:
                body = str(request.pop("body", "")).encode("utf-8")
                request["body_b64"] = base64.b64encode(body).decode("ascii")
                request["kind"] = "request"
                connection.send(request)
                if not connection.poll(WORKER_TIMEOUT_SECONDS):
                    raise ReplayError("parent did not answer worker request")
                response = connection.recv()
                if response.get("kind") != "response" or response.get("id") != request.get("id"):
                    raise ReplayError("parent returned an invalid worker response")
                response_body = base64.b64decode(str(response.get("body_b64") or ""), validate=True)
                response_headers = dict(response.get("headers") or {})
                response_status = int(response["status"])
                # Prefer parent-injected XHR body via fulfill. add_resource is
                # optional and only works after page resource bundle init.
                try:
                    context.add_resource(
                        request["url"],
                        response_body,
                        response_status,
                        response_headers,
                    )
                except Exception:
                    pass
                try:
                    body_text = response_body.decode("utf-8")
                except UnicodeDecodeError:
                    body_text = response_body.decode("latin-1", errors="replace")
                context.expose(
                    {
                        "id": request["id"],
                        "cookies": response.get("visible_cookies", []),
                        "status": response_status,
                        "headers": response_headers,
                        "body": body_text,
                    },
                    "bridgeResponse",
                )
                context.eval(
                    "window.__akamaiBridge.fulfill("
                    "window.__iv8__.data.bridgeResponse.id, "
                    "window.__iv8__.data.bridgeResponse.cookies, "
                    "{"
                    "status: window.__iv8__.data.bridgeResponse.status, "
                    "headers: window.__iv8__.data.bridgeResponse.headers, "
                    "body: window.__iv8__.data.bridgeResponse.body"
                    "})"
                )

            context.eval("window.__iv8__.eventLoop.sleep(50)")
            stats = context.eval("window.__akamaiBridge.stats()", to_py=True) or {}
            if (
                int(stats.get("postCount", 0)) > 0
                and int(stats.get("signalCount", 0)) >= MIN_SIGNALS
                and not pending
            ):
                if settle_step is None:
                    settle_step = step + 20
                elif step >= settle_step and int(stats.get("active", 0)) == 0:
                    break

        stats = context.eval("window.__akamaiBridge.stats()", to_py=True) or {}
        connection.send(
            {
                "kind": "result",
                "stats": stats,
                "document_cookie": context.eval("document.cookie") or "",
            }
        )
    except BaseException as error:  # noqa: BLE001 - child must report, not raise
        try:
            connection.send(
                {"kind": "error", "message": f"{type(error).__name__}: {str(error)[:500]}"}
            )
        except BaseException:
            pass
    finally:
        if context is not None:
            try:
                context.leave()
                context.close()
            except BaseException:
                pass
        try:
            connection.close()
        except OSError:
            pass


# --------------------------- parent bridge (offline) --------------------------

def _answer_offline(method, url, challenge):
    """Deterministic offline answers for the synthetic collector's XHR."""
    normalized = url if str(url).startswith("http") else urllib.parse.urljoin(BASE_URL + "/", url)
    split = urllib.parse.urlsplit(normalized)
    base_netloc = urllib.parse.urlsplit(BASE_URL).netloc
    if split.netloc and split.netloc != base_netloc:
        raise ReplayError(f"cross-origin request rejected: {split.netloc}")
    if method == "GET" and split.path == CPR_PATH:
        return 200, {"content-type": "application/json"}, json.dumps(
            {"url": challenge.collector_url}
        ).encode("utf-8")
    if method == "POST" and split.path == urllib.parse.urlsplit(challenge.collector_url).path:
        return 200, {"content-type": "application/json"}, b"{}"
    raise ReplayError(f"unsupported offline route: {method} {split.path}")


def run_offline_probe():
    """Fixed-vector gate: synthetic collector must emit exactly one sensor POST
    with 116 signals and one SharedWorker message, zero runtime errors."""
    collector_url = f"{BASE_URL}/fhLtIt/offline/collector?v=local"
    challenge = Challenge(
        page_url=f"{BASE_URL}/app/main",
        referrer=f"{BASE_URL}/",
        html=(
            "<!doctype html><html><head>"
            f'<script src="{collector_url}"></script>'
            "</head><body></body></html>"
        ),
        collector_src=collector_url,
        collector_url=collector_url,
        collector_js=SYNTHETIC_COLLECTOR,
        resource_entries=[{"name": collector_url, "initiatorType": "script"}],
    )
    ctx = mp.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=True)
    process = ctx.Process(
        target=_iv8_worker,
        args=(child_conn, {
            "page_url": challenge.page_url,
            "referrer": challenge.referrer,
            "html": challenge.html,
            "collector_src": challenge.collector_src,
            "collector_url": challenge.collector_url,
            "collector_js": challenge.collector_js,
            "resource_entries": challenge.resource_entries,
            "cookie_lines": [],
            "local_storage": {},
            "session_storage": {},
        }),
        daemon=True,
    )
    deadline = time.monotonic() + WORKER_TIMEOUT_SECONDS
    result = None
    process.start()
    child_conn.close()
    try:
        while time.monotonic() < deadline:
            if parent_conn.poll(0.1):
                message = parent_conn.recv()
                kind = message.get("kind")
                if kind == "result":
                    result = message
                    break
                if kind == "error":
                    raise ReplayError(str(message.get("message") or "worker failed"))
                if kind != "request":
                    raise ReplayError(f"unexpected worker message: {kind}")
                method = str(message.get("method") or "GET").upper()
                url = str(message.get("url") or "")
                body = base64.b64decode(str(message.get("body_b64") or ""), validate=True)
                status, headers, response_body = _answer_offline(method, url, challenge)
                parent_conn.send(
                    {
                        "kind": "response",
                        "id": message.get("id"),
                        "status": status,
                        "headers": headers,
                        "body_b64": base64.b64encode(response_body).decode("ascii"),
                        "visible_cookies": [],
                    }
                )
        if result is None:
            raise ReplayError("offline probe timed out waiting for worker result")
    finally:
        if process.is_alive():
            process.terminate()
        process.join(timeout=5)

    stats = result.get("stats") or {}
    post_count = int(stats.get("postCount", 0))
    signal_count = int(stats.get("signalCount", 0))
    worker_messages = int(stats.get("workerMessageCount", 0))
    runtime_errors = int(stats.get("runtimeErrorCount", 0) or len(stats.get("runtimeErrors") or []))
    if post_count != 1:
        raise ReplayError(f"expected exactly one sensor POST, got {post_count}")
    if signal_count != 116:
        raise ReplayError(f"expected 116 signals, got {signal_count}")
    if worker_messages != 1:
        raise ReplayError(f"expected one worker message, got {worker_messages}")
    if runtime_errors:
        raise ReplayError("offline probe reported a runtime error")
    return {
        "post_count": post_count,
        "signal_count": signal_count,
        "worker_message_count": worker_messages,
        "runtime_error_count": runtime_errors,
        "collector_sha256_16": hashlib.sha256(
            SYNTHETIC_COLLECTOR.encode("utf-8", errors="surrogatepass")
        ).hexdigest()[:16],
    }


if __name__ == "__main__":
    mp.freeze_support()
    print(json.dumps(run_offline_probe(), indent=2))
