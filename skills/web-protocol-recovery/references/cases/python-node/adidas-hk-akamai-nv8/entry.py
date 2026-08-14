from __future__ import annotations

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


CASE_ID = "adidas-hk-akamai-nv8"
CASE_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = CASE_DIR / "fixtures"
TARGET_URL = "https://www.adidas.com.hk/zh/summer_cs_promotion_2"
BUSINESS_ENDPOINT = (
    "https://www.adidas.com.hk/on/demandware.store/"
    "Sites-adidas-HK-Site/zh_HK/Search-UpdateGrid"
)


def _reject_live_egress(action: str = "live HTTP") -> None:
    raise RuntimeError(
        f"case entry refuses {action}: offline-only. "
        "Use a project collector for approved live egress."
    )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_fixture(name: str) -> dict[str, Any]:
    path = FIXTURE_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def sensor_endpoint_from_script_url(script_url: str) -> str:
    parts = urlsplit(script_url)
    if parts.scheme != "https" or parts.netloc != "www.adidas.com.hk":
        raise ValueError("unexpected sensor script origin")
    if "pomCpnC" not in parts.path:
        raise ValueError("sensor script URL does not contain pomCpnC")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def validate_sensor_request(sample: dict[str, Any]) -> dict[str, Any]:
    sensor = sample.get("sensorPost") or {}
    method = sensor.get("method")
    endpoint = sensor.get("endpoint")
    content_type = (sensor.get("headers") or {}).get("content-type")
    body_shape = sensor.get("bodyShape") or {}

    if method != "POST":
        raise ValueError("sensor request must be POST")
    if not isinstance(endpoint, str) or "pomCpnC" not in endpoint:
        raise ValueError("sensor endpoint marker missing")
    if content_type != "application/json":
        raise ValueError("sensor request content-type must be application/json")
    if body_shape.get("jsonObject") is not True:
        raise ValueError("sensor body must be a JSON object")
    if body_shape.get("keys") != ["body"]:
        raise ValueError("sensor body keys must be ['body']")
    if int(body_shape.get("observedBytesApprox") or 0) < 4000:
        raise ValueError("sensor body size is below the expected floor")

    return {
        "method": method,
        "endpoint": endpoint,
        "contentType": content_type,
        "observedBytesApprox": int(body_shape.get("observedBytesApprox") or 0),
    }


class ProductTileParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.products: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._capture_name = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if "data-pid" in values:
            self._current = {
                "sku": values.get("data-pid", ""),
                "name": values.get("data-product-name", ""),
                "price": values.get("data-price", ""),
                "url": values.get("data-url", ""),
                "image": values.get("data-image", ""),
            }
            return
        if self._current is None:
            return
        classes = set(values.get("class", "").split())
        if tag in {"a", "span", "div"} and classes & {"product-name", "name"}:
            self._capture_name = True
        if tag == "a" and not self._current.get("url"):
            self._current["url"] = values.get("href", "")
        if tag == "img" and not self._current.get("image"):
            self._current["image"] = values.get("src", "") or values.get("data-src", "")

    def handle_data(self, data: str) -> None:
        if self._current is not None and self._capture_name and not self._current.get("name"):
            self._current["name"] = data.strip()

    def handle_endtag(self, tag: str) -> None:
        if self._capture_name and tag in {"a", "span", "div"}:
            self._capture_name = False
        if tag == "div" and self._current is not None:
            if self._current.get("sku") and self._current.get("name"):
                self.products.append(dict(self._current))
            self._current = None
            self._capture_name = False


def parse_products_from_html(html: str) -> list[dict[str, str]]:
    parser = ProductTileParser()
    parser.feed(html)
    seen: set[str] = set()
    products: list[dict[str, str]] = []
    for product in parser.products:
        sku = product.get("sku", "")
        if not sku or sku in seen:
            continue
        seen.add(sku)
        products.append(product)
    return products


def run(*, live: bool = False) -> dict[str, Any]:
    if live:
        _reject_live_egress("run(live=True)")

    request_sample = load_fixture("request.sample.json")
    response_sample = load_fixture("response.sample.json")
    vectors = load_fixture("vectors.json")

    script_url = request_sample["challenge"]["sensorScriptUrlShape"]
    endpoint = sensor_endpoint_from_script_url(script_url)
    sensor = validate_sensor_request(request_sample)
    products = parse_products_from_html(response_sample["html"])

    expected_count = response_sample["expected"]["productCount"]
    if len(products) != expected_count:
        raise AssertionError(f"expected {expected_count} products, got {len(products)}")

    return {
        "status": "offline",
        "caseId": CASE_ID,
        "target": TARGET_URL,
        "businessEndpoint": BUSINESS_ENDPOINT,
        "derivedSensorEndpoint": endpoint,
        "sensor": sensor,
        "productCount": len(products),
        "products": products,
        "acceptance": vectors["acceptance"],
    }


def main() -> None:
    result = run(live=False)
    print(
        json.dumps(
            {
                "status": result["status"],
                "caseId": result["caseId"],
                "productCount": result["productCount"],
                "derivedSensorEndpoint": result["derivedSensorEndpoint"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
