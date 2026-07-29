# Offline-only case entry for unit tests and local proof.
# Historical full implementation is declared by case.json.historicalReferences.
# Final live egress: projectRoot main.py + python-collector work-order.

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


def _reject_case_live_egress(action: str = "live HTTP") -> None:
    raise RuntimeError(
        f"case entry refuses {action}: offline-only. "
        "Historical study references are declared by case.json. "
        "Use project main.py + python-collector for live egress."
    )

CASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = CASE_DIR / "assets"

APP_ID = "2088b"
API_URL = "https://api.m.jd.com/api"
FUNCTION_ID = "recommend_like_m"
APPID = "jd-cphdeveloper-m"
LIVE_JS_URL = (
    "https://storage.360buyimg.com/webcontainer/main/js_security_v3_main.js"
)
DEFAULT_BODY = (
    '{"func":"item_rec","recpos":6163,'
    '"param":"{\\"pagenum\\":1,\\"pagecount\\":20,\\"startpos\\":0,'
    '\\"ptag\\":\\"\\",\\"sku\\":\\"\\",\\"cid1\\":\\"\\",\\"cid2\\":\\"\\",\\"cid3\\":\\"\\"}",'
    '"clientPageId":"","clientVersion":"2.0"}'
)
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/150.0.0.0 Safari/537.36"
)


def body_sha256(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def parse_products(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract compact product rows from recommend_like_m JSON."""
    content = (((payload.get("data") or {}).get("feeds") or {}).get("content") or [])
    products: list[dict[str, Any]] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        sku = item.get("id")
        name = item.get("name")
        if not sku and not name:
            continue
        price = (
            item.get("price")
            or item.get("jdPrice")
            or item.get("oriprice")
            or item.get("plusprice")
            or item.get("newuserprice")
            or ""
        )
        ext_raw = item.get("ext")
        ext = ext_raw if isinstance(ext_raw, dict) else {}
        products.append(
            {
                "sku": str(sku) if sku is not None else "",
                "name": str(name or ""),
                "price": str(price),
                "jdPrice": str(item.get("jdPrice") or ""),
                "oriprice": str(item.get("oriprice") or ""),
                "link": str(item.get("link") or ""),
                "img": f"{item.get('imgprefix') or ''}{item.get('imgbase') or ''}",
                "cate1": ext.get("cate1") if ext else None,
                "cate2": ext.get("cate2") if ext else None,
                "cate3": ext.get("cate3") if ext else None,
                "shopId": ext.get("shopId") if ext else None,
                "brandId": ext.get("brandId") if ext else None,
            }
        )
    return products


def _read_asset(name: str) -> str:
    path = ASSET_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"missing case asset: {path}")
    return path.read_text(encoding="utf-8", errors="ignore")


def _load_sign_materials(*, prefer_live: bool = False) -> tuple[str, str, str]:
    """Return (js_code, html, source_label). Live download is disabled in case library."""
    if prefer_live:
        _reject_case_live_egress("live bundle download")
    return (
        _read_asset("js_security_v3_main.js"),
        _read_asset("jd_index.html"),
        "frozen-assets",
    )


def sign_h5st(
    js_code: str,
    index_html: str,
    body: str,
    *,
    function_id: str = FUNCTION_ID,
    appid: str = APPID,
    app_id: str = APP_ID,
) -> str:
    """Generate h5st in iv8. Import-safe when not called at import time."""
    try:
        from utils.iv8_silent import import_iv8_silent  # type: ignore

        runtime = import_iv8_silent()
    except Exception:
        import iv8 as runtime  # type: ignore

    body_hash = body_sha256(body)
    with runtime.JSContext(
        environment={
            "location": {
                "href": "https://m.jd.com/",
                "origin": "https://m.jd.com",
                "protocol": "https:",
                "host": "m.jd.com",
                "hostname": "m.jd.com",
                "port": "",
                "pathname": "/",
                "search": "",
                "hash": "",
            },
            "navigator": {
                "userAgent": UA,
                "language": "zh-CN",
                "platform": "Win32",
            },
        },
        config={"timezone": "Asia/Shanghai"},
        time_mode="system",
    ) as ctx:
        ctx.eval(
            """
            window.MessageChannel = __iv8__.wrapNative(function() {
                const port1 = { onmessage: null };
                const port2 = { onmessage: null };
                port1.postMessage = function(data) {
                  if (port2.onmessage) setTimeout(() => port2.onmessage({data}), 0);
                };
                port2.postMessage = function(data) {
                  if (port1.onmessage) setTimeout(() => port1.onmessage({data}), 0);
                };
                return { port1, port2 };
            }, 'MessageChannel');
            """
        )
        ctx.eval(f"document.documentElement.innerHTML = {json.dumps(index_html)}")
        ctx.eval(
            js_code,
            name="https://storage.360buyimg.com/webcontainer/main/js_security_v3_main.js",
        )
        for _ in range(5):
            try:
                ctx.eval("__iv8__.eventLoop.drainMicrotasks(); __iv8__.eventLoop.drain();")
            except Exception:
                break
            time.sleep(0.05)

        raw = ctx.eval(
            f"""
            (() => {{
              if (typeof window.ParamsSignMain !== 'function') {{
                return JSON.stringify({{ok:false, err:'ParamsSignMain missing'}});
              }}
              const s = new window.ParamsSignMain({{appId: '{app_id}'}});
              const out = s._$sdnmd({{
                appid: '{appid}',
                functionId: '{function_id}',
                body: '{body_hash}'
              }});
              const h5st = out && out.h5st;
              return JSON.stringify({{
                ok: typeof h5st === 'string' && h5st.length > 20,
                h5st: h5st || null
              }});
            }})()
            """
        )
        data = json.loads(raw) if isinstance(raw, str) else raw
        if not data or not data.get("ok"):
            raise RuntimeError(f"ParamsSignMain failed: {data}")
        return str(data["h5st"])


def run(
    *,
    live: bool = False,
    prefer_live_bundle: bool = False,
    body: str = DEFAULT_BODY,
    function_id: str = FUNCTION_ID,
) -> dict[str, Any]:
    """Offline fixture demo only. live=True is rejected in the case library."""
    if live or prefer_live_bundle:
        _reject_case_live_egress("run(live=True) / prefer_live_bundle")
    sample_path = CASE_DIR / "fixtures" / "response.sample.json"
    if sample_path.exists():
        sample = json.loads(sample_path.read_text(encoding="utf-8"))
        products = parse_products(sample.get("response") or sample)
        return {
            "status": "offline",
            "caseId": "iv8-jd-h5st",
            "product_count": len(products),
            "products": products,
            "note": "offline fixtures only; historical study reference is declared by case.json",
        }
    return {
        "status": "offline",
        "caseId": "iv8-jd-h5st",
        "product_count": 0,
        "products": [],
        "note": "offline fixtures only; historical study reference is declared by case.json",
    }


def main() -> None:
    result = run(live=False)
    print(
        json.dumps(
            {
                "status": result.get("status"),
                "product_count": result.get("product_count"),
                "note": result.get("note"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
