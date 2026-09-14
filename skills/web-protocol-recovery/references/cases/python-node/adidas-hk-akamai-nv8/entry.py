#!/usr/bin/env python3
"""Offline NV8 executor entry for the adidas-hk-akamai-nv8 case.

Two layers, both offline:

1. Fixed vectors (always): sensor endpoint derivation, redacted sensor request
   shape, SFCC product parsing, live-egress refusal.
2. NV8 executor chain (when an NV8 install + a supported Node runtime
   are available): run the synthetic Akamai-shape sensor inside an NV8
   ``EdgeSandbox``, capture the sensor POST at the offline network boundary,
   and validate the narrow artifact.

This entry performs no live HTTP and persists nothing. Live egress belongs to
the python-collector delivery Provider. The real adidas HK sensor JavaScript is
sensitive material and is intentionally NOT part of this case; the synthetic
sensor reproduces only the documented observable contract.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

CASE_ID = "adidas-hk-akamai-nv8"
CASE_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = CASE_DIR / "fixtures"
RUNNER_PATH = CASE_DIR / "sensor_runner.mjs"
TARGET_URL = "https://www.adidas.com.hk/zh/summer_cs_promotion_2"
BUSINESS_ENDPOINT = (
    "https://www.adidas.com.hk/on/demandware.store/"
    "Sites-adidas-HK-Site/zh_HK/Search-UpdateGrid"
)
ARTIFACT_BEGIN = "===== NV8 SENSOR ARTIFACT ====="
ARTIFACT_END = "===== END ====="
MIN_BODY_BYTES = 4000
MIN_NODE_VERSION = (18, 18)
FINGERPRINT_ORDER_ADVISORY_VERSION = (22, 0)


def _reject_live_egress(action: str = "live HTTP") -> None:
    raise RuntimeError(
        f"case entry refuses {action}: offline-only. "
        "Use a project collector for approved live egress."
    )


def file_sha256(path: Path) -> str:
    import hashlib

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
    if int(body_shape.get("observedBytesApprox") or 0) < MIN_BODY_BYTES:
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


def _node_executable() -> str:
    return "node.exe" if os.name == "nt" else "node"


def _node_candidates() -> list[Path]:
    candidates: list[Path] = []

    explicit = os.environ.get("NV8_NODE")
    if explicit:
        candidates.append(Path(explicit))

    nvm_home = os.environ.get("NVM_HOME")
    if nvm_home:
        versions = sorted(
            Path(nvm_home).glob("v24.*"),
            key=lambda path: path.name,
            reverse=True,
        )
        candidates.extend(version / _node_executable() for version in versions)

    on_path = shutil.which("node")
    if on_path:
        candidates.append(Path(on_path))

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).lower()
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def locate_node() -> tuple[Path, tuple[int, int]] | None:
    """Prefer Node 24 (provider baseline); accept >= 18.18 (NV8 floor)."""

    best: tuple[Path, tuple[int, int]] | None = None
    for candidate in _node_candidates():
        if not candidate.is_file():
            continue
        try:
            completed = subprocess.run(
                [str(candidate), "--version"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        match = re.match(r"v(\d+)\.(\d+)\.", completed.stdout.strip())
        if match is None:
            continue
        version = (int(match.group(1)), int(match.group(2)))
        if version < MIN_NODE_VERSION:
            continue
        if version[0] == 24:
            return candidate, version
        if best is None or version > best[1]:
            best = (candidate, version)
    return best


def resolve_nv8_root(explicit: str | None = None) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    env_root = os.environ.get("NV8_ROOT")
    if env_root:
        candidates.append(Path(env_root))
    candidates.append(CASE_DIR / "node_modules" / "nv8")

    for candidate in candidates:
        entry = candidate / "src" / "public" / "edge-sandbox.js"
        package = candidate / "package.json"
        if entry.is_file() and package.is_file():
            try:
                metadata = json.loads(package.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if metadata.get("name") == "nv8":
                return candidate
    return None


def nv8_availability(explicit_root: str | None = None) -> tuple[bool, str]:
    nv8_root = resolve_nv8_root(explicit_root)
    if nv8_root is None:
        return False, "NV8 install not found (set NV8_ROOT or run npm install)"
    node = locate_node()
    if node is None:
        return False, "supported Node runtime not found (NV8 supports Node >= 18.18)"
    node_path, version = node
    detail = f"node={node_path} nv8={nv8_root}"
    if version < FINGERPRINT_ORDER_ADVISORY_VERSION:
        detail += (
            " (advisory: Node 22+ is recommended for Edge-equivalent Window global order;"
            " the executor itself runs on 18.18+)"
        )
    return True, detail


def _parse_runner_artifact(stdout: str) -> dict[str, Any]:
    begin = stdout.find(ARTIFACT_BEGIN)
    end = stdout.find(ARTIFACT_END, begin + 1)
    if begin == -1 or end == -1:
        raise RuntimeError("sensor runner did not emit an artifact")
    payload = stdout[begin + len(ARTIFACT_BEGIN): end].strip()
    artifact = json.loads(payload)
    if not isinstance(artifact, dict):
        raise RuntimeError("sensor runner artifact is not an object")
    return artifact


def run_nv8_chain(
    explicit_root: str | None = None,
    pump_ms: int = 1500,
) -> dict[str, Any]:
    """Run the synthetic sensor through NV8 and validate the narrow artifact."""

    nv8_root = resolve_nv8_root(explicit_root)
    if nv8_root is None:
        raise RuntimeError("NV8 install not found (set NV8_ROOT or run npm install)")
    node = locate_node()
    if node is None:
        raise RuntimeError("supported Node runtime not found")

    node_path, version = node
    request_sample = load_fixture("request.sample.json")
    script_url = request_sample["challenge"]["sensorScriptUrlShape"]
    expected_endpoint = sensor_endpoint_from_script_url(script_url)

    completed = subprocess.run(
        [
            str(node_path),
            str(RUNNER_PATH),
            "--nv8-root",
            str(nv8_root),
            "--target-url",
            TARGET_URL,
            "--challenge",
            str(FIXTURE_DIR / "challenge.html"),
            "--sensor",
            str(FIXTURE_DIR / "pomCpnC-sensor.synthetic.js"),
            "--cookies",
            str(FIXTURE_DIR / "cookies.json"),
            "--pump-ms",
            str(pump_ms),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "sensor runner failed: "
            + (completed.stderr.strip().splitlines() or ["unknown error"])[-1]
        )

    artifact = _parse_runner_artifact(completed.stdout)

    if artifact.get("method") != "POST":
        raise AssertionError("NV8 artifact: sensor request must be POST")
    if artifact.get("sensorEndpoint") != expected_endpoint:
        raise AssertionError("NV8 artifact: endpoint does not match the derived rule")
    if artifact.get("contentType") != "application/json":
        raise AssertionError("NV8 artifact: content-type must be application/json")
    if artifact.get("bodyJsonKeys") != ["body"]:
        raise AssertionError("NV8 artifact: body JSON keys must be ['body']")
    if int(artifact.get("bodyByteLength") or 0) < MIN_BODY_BYTES:
        raise AssertionError(f"NV8 artifact: body is below {MIN_BODY_BYTES} bytes")

    return {
        "status": "executed",
        "node": f"{version[0]}.{version[1]}",
        "nv8Root": str(nv8_root),
        "sensorEndpoint": artifact.get("sensorEndpoint"),
        "method": artifact.get("method"),
        "contentType": artifact.get("contentType"),
        "bodyJsonKeys": artifact.get("bodyJsonKeys"),
        "bodyByteLength": artifact.get("bodyByteLength"),
        "body": artifact.get("body"),
        "outcome": artifact.get("outcome"),
        "nodeAdvisory": (
            None
            if version >= FINGERPRINT_ORDER_ADVISORY_VERSION
            else "Node 22+ recommended for Edge-equivalent Window global order"
        ),
    }


def run(*, live: bool = False, with_nv8: bool = True, nv8_root: str | None = None) -> dict[str, Any]:
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

    result: dict[str, Any] = {
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

    if with_nv8:
        available, detail = nv8_availability(nv8_root)
        if available:
            try:
                result["nv8"] = run_nv8_chain(nv8_root)
            except Exception as error:  # keep vector data printable on chain failure
                result["nv8"] = {"status": "failed", "reason": str(error)}
        else:
            result["nv8"] = {"status": "unavailable", "reason": detail}

    return result


def _print_report(result: dict[str, Any], print_body: bool = False) -> None:
    """Human-readable console report: exactly the data this case produces."""

    sensor = result.get("sensor") or {}
    nv8 = result.get("nv8") or {}
    products = result.get("products") or []

    line = "=" * 72
    print(line)
    print("adidas-hk-akamai-nv8 · NV8 离线执行链数据")
    print(line)

    print("\n[1] 向量校验（离线）")
    print(f"    推导的 sensor 端点 : {result.get('derivedSensorEndpoint')}")
    print(
        "    sensor 请求形状    : "
        f"{sensor.get('method')} {sensor.get('contentType')} "
        f"observed≈{sensor.get('observedBytesApprox')}B"
    )
    print(f"    业务端点          : {result.get('businessEndpoint')}")

    print("\n[2] NV8 sensor 工件")
    status = nv8.get("status")
    if status == "executed":
        print(f"    状态              : executed (node {nv8.get('node')})")
        print(f"    捕获端点          : {nv8.get('sensorEndpoint')}")
        print(
            "    请求              : "
            f"{nv8.get('method')} {nv8.get('contentType')} "
            f"keys={nv8.get('bodyJsonKeys')}"
        )
        print(f"    body 字节 / 结果  : {nv8.get('bodyByteLength')} / {nv8.get('outcome')}")
        body = nv8.get("body") or ""
        if print_body:
            print(f"    body（完整）      : {body}")
        else:
            preview = body if len(body) <= 240 else body[:240] + " ..."
            print(f"    body（前 240 字符）: {preview}")
            print("    （加 --print-body 打印完整 body）")
        if nv8.get("nodeAdvisory"):
            print(f"    提示              : {nv8.get('nodeAdvisory')}")
    elif status == "unavailable":
        print(f"    状态              : unavailable")
        print(f"    原因              : {nv8.get('reason')}")
        print("    修复              : 在本目录执行 npm install，或设置 NV8_ROOT 指向 NV8 安装根目录")
    else:
        print(f"    状态              : {'skipped' if not nv8 else status}")
        if nv8.get("reason"):
            print(f"    原因              : {nv8.get('reason')}")

    print(f"\n[3] 业务数据（离线 fixture 解析，共 {len(products)} 条）")
    for index, product in enumerate(products, start=1):
        print(
            f"    [{index}] {product.get('sku')}  {product.get('name')}  "
            f"{product.get('price')}"
        )
        print(f"         url: {product.get('url')}")
        print(f"         img: {product.get('image')}")

    acceptance = result.get("acceptance") or {}
    print("\n[4] 验收")
    print(
        "    offlineProductCount={0}  rejectsLiveEgress={1}  "
        "requiresCurrentLiveVerification={2}".format(
            acceptance.get("offlineProductCount"),
            acceptance.get("rejectsLiveEgress"),
            acceptance.get("requiresCurrentLiveVerification"),
        )
    )
    print("    说明：本 case 不发起真实 HTTP；live egress 由 python-collector 负责。")
    print(line)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="refused by design")
    parser.add_argument("--nv8-root", default=None, help="NV8 install root")
    parser.add_argument("--skip-nv8", action="store_true", help="vector checks only")
    parser.add_argument("--print-body", action="store_true", help="print the full captured sensor body")
    parser.add_argument("--json", action="store_true", help="print the full result as JSON")
    args = parser.parse_args()

    try:
        result = run(live=args.live, with_nv8=not args.skip_nv8, nv8_root=args.nv8_root)
    except RuntimeError as error:
        print(json.dumps({"status": "error", "caseId": CASE_ID, "error": str(error)}, ensure_ascii=False))
        raise SystemExit(1)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    _print_report(result, print_body=args.print_body)


if __name__ == "__main__":
    main()
