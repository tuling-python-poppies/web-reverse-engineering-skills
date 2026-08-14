# NV8-Based Sensor Execution

Run Bot Manager sensor scripts in a browser-free Edge 150 compatibility sandbox. This reference contains a verified end-to-end implementation.

## When to Use

- Sensor requires full DOM/CSS/Canvas/WebGL APIs that basic env-patch cannot provide.
- Sensor reads navigator, screen, getComputedStyle, Canvas 2D, WebGL parameters.
- Final delivery must be browser-free Python (no Playwright/Camoufox runtime dependency).
- Target sensor is 500KB+ obfuscated JS with deep environment introspection.

## Architecture

```
Python entry (main.py)
  ↓ subprocess.run([node24_path, 'sensor_generator.mjs'])
Node.js NV8 script
  ├── Native fetch (Firefox UA) → GET 403 challenge + sensor script
  ├── EdgeSandbox.create() → NV8 Edge 150 sandbox (1232 Window props)
  ├── sandbox.evaluate(sensorScript) → sensor synchronous execution
  ├── setTimeout pump (10s) → async POST fires
  └── sandbox.networkRequests() → capture POST body + headers
  ↓ stdout JSON { sensorEndpoint, body, cookies }
Python
  ├── Parse sensor POST body + initial cookies
  ├── curl_cffi.post(sensorEndpoint, body) → ak_bmsc / bm_s
  └── curl_cffi.get(business_api, cookies) → products / data
```

## Key Implementation Notes

1. **Sensor POST target**: The sensor internally POSTs to `location.href` (the page URL). In Python, override to the correct endpoint: sensor script URL path without query params.
2. **Async POST**: The sensor schedules POST via `setTimeout`. After `evaluate(sensorScript)`, pump the event loop: `sandbox.evaluate('new Promise(r => setTimeout(r, 10000))')`.
3. **UA split**: Use Firefox UA for HTTP fetches (CDN serves sensor to Firefox); NV8 internally presents Chrome 150 UA (what sensor sees via `navigator.userAgent`).
4. **Cookie injection**: Inject challenge page cookies via `document.cookie = "..."` BEFORE evaluating sensor.
5. **Fingerprint**: The default NV8 Edge 150 profile usually passes. For stricter targets, inject real browser export.

## Verified Node.js Sensor Generator

```javascript
/**
 * Bot Manager sensor generator - NV8
 *
 * Pure protocol: no browser runtime dependency.
 * Called by Python which auto-locates Node 24 via NVM_HOME.
 */

import { EdgeSandbox } from 'nv8';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));

const TARGET = 'https://www.adidas.com.hk/zh/summer_cs_promotion_2';
const HOST = 'www.adidas.com.hk';
const FETCH_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0';

// ─── Load fingerprint ──────────────────────────────────────────────────────────
function loadFingerprint() {
  try {
    const fpPath = join(__dirname, 'fingerprint.json');
    const fp = JSON.parse(readFileSync(fpPath, 'utf-8'));
    return {
      locale: 'zh-Hant-HK',
      timezone: 'Asia/Shanghai',
      screen: {
        width: fp.screen?.width || 1680,
        height: fp.screen?.height || 1050,
        availWidth: fp.screen?.availWidth || 1680,
        availHeight: fp.screen?.availHeight || 1002,
        colorDepth: fp.screen?.colorDepth || 24,
        pixelDepth: fp.screen?.pixelDepth || 24,
      },
    };
  } catch (e) {
    return { locale: 'zh-Hant-HK', timezone: 'Asia/Shanghai' };
  }
}

// ─── Step 1: Fetch challenge page ──────────────────────────────────────────────
async function getChallengePage() {
  console.log('[sensor] GET challenge page...');
  const resp = await fetch(TARGET, {
    method: 'GET',
    headers: {
      'User-Agent': FETCH_UA,
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'zh-HK,zh;q=0.5',
    },
    redirect: 'manual',
  });

  const status = resp.status;
  const body = await resp.text();

  const setCookies = resp.headers.getSetCookie?.() || [];
  const cookies = {};
  for (const sc of setCookies) {
    const [kv] = sc.split(';');
    const [k, ...vParts] = kv.split('=');
    cookies[k.trim()] = vParts.join('=').trim();
  }

  // Pattern: src="/pomCpnC--<random>/.../hash"
  const scriptMatch = body.match(/src="([^"]*pomCpnC[^"]*)"/);
  const sensorScriptUrl = scriptMatch ? `https://${HOST}${scriptMatch[1]}` : null;

  console.log(`[sensor] status=${status} cookies=${Object.keys(cookies).join(',')} script=${sensorScriptUrl ? 'found' : 'NOT FOUND'}`);
  return { status, body, cookies, sensorScriptUrl };
}

// ─── Step 2: Fetch sensor script ───────────────────────────────────────────────
async function getSensorScript(url, cookies) {
  console.log('[sensor] GET sensor script...');
  const cookieStr = Object.entries(cookies).map(([k, v]) => `${k}=${v}`).join('; ');

  const resp = await fetch(url, {
    method: 'GET',
    headers: {
      'User-Agent': FETCH_UA,
      'Accept': '*/*',
      'Accept-Language': 'zh-HK,zh;q=0.5',
      'Referer': TARGET,
      'Cookie': cookieStr,
    },
  });

  const scriptText = await resp.text();
  console.log(`[sensor] script fetched: ${(scriptText.length / 1024).toFixed(0)}KB`);
  return scriptText;
}

// ─── Step 3: Run in NV8 ────────────────────────────────────────────────────────
async function runSensorInNv8(sensorScriptUrl, sensorScript, cookies) {
  console.log('[sensor] creating NV8 sandbox...');

  const fingerprint = loadFingerprint();

  const sandbox = await EdgeSandbox.create({
    page: {
      url: TARGET,
      html: `<!DOCTYPE html><html><head><meta charset="utf-8"><title>page</title></head><body></body></html>`,
      contentType: 'text/html',
    },
    replay: [],
    networkCapture: { enabled: true, maxEntries: 100, maxBodyBytes: 10 * 1024 },
    fingerprint,
    limits: { timeoutMs: 20_000, maxHeapBytes: 512 * 1024 * 1024, maxSourceBytes: 2 * 1024 * 1024 },
  });

  try {
    // Inject cookies
    const cookieStr = Object.entries(cookies).map(([k, v]) => `${k}=${v}`).join('; ');
    try { await sandbox.evaluate(`document.cookie = ${JSON.stringify(cookieStr)}`); } catch(e) {}

    // Execute sensor
    console.log('[sensor] evaluating...');
    await sandbox.evaluate(`(() => { try { ${sensorScript} } catch(e) { window.__err = e.message; } })()`);
    console.log('[sensor] executed OK');

    // Pump event loop for async POST
    console.log('[sensor] pumping event loop (10s)...');
    try { await sandbox.evaluate('new Promise(r => setTimeout(r, 10000))'); } catch(e) {}

    // Capture
    const requests = await sandbox.networkRequests();
    console.log(`[sensor] captured ${requests.length} requests`);

    const sensorPost = requests.find(r => r.method === 'POST');
    if (!sensorPost) { console.log('[sensor] no POST found'); return null; }

    console.log(`[sensor] POST captured: ${sensorPost.url} (${sensorPost.bodyByteLength} bytes)`);
    return { body: sensorPost.bodyText, headers: Object.fromEntries(sensorPost.headers) };
  } finally {
    await sandbox.close();
  }
}

// ─── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  console.log('[sensor] Bot Manager sensor generator (NV8)');

  const { cookies, sensorScriptUrl } = await getChallengePage();
  if (!sensorScriptUrl) { console.log('[sensor] FATAL: script URL not found'); process.exit(1); }

  const sensorScript = await getSensorScript(sensorScriptUrl, cookies);
  const result = await runSensorInNv8(sensorScriptUrl, sensorScript, cookies);
  if (!result) { console.log('[sensor] generation failed'); process.exit(1); }

  // Derive correct POST endpoint (script path without query)
  const postEndpoint = `https://${HOST}${new URL(sensorScriptUrl).pathname}`;

  // Output for Python
  console.log('\n[sensor] ===== SENSOR POST READY =====');
  console.log(JSON.stringify({ sensorEndpoint: postEndpoint, body: result.body, cookies }, null, 2));
  console.log('[sensor] ===== END =====\n');
}

main().catch(err => { console.error('[sensor] fatal:', err); process.exit(1); });
```

## Verified Python Collector

```python
#!/usr/bin/env python3
"""Browser-free collector with NV8 sensor generation."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    print("Missing: curl_cffi (pip install curl-cffi)")
    sys.exit(1)

from bs4 import BeautifulSoup


# ─── NV8 Environment Validation ────────────────────────────────────────────────

HERE = Path(__file__).resolve().parent


def find_node24() -> str:
    """Auto-detect Node 24.x via NVM_HOME, then PATH fallback."""
    nvm_home = os.environ.get('NVM_HOME')
    if nvm_home:
        nvm_root = Path(nvm_home)
        v24_dirs = sorted(nvm_root.glob('v24.*'), reverse=True)
        for v24_dir in v24_dirs:
            node_exe = v24_dir / 'node.exe'
            if node_exe.exists():
                return str(node_exe)

    # Fallback: check system PATH
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=5)
        if result.stdout.strip().startswith('v24.'):
            return 'node'
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    raise RuntimeError(
        "Node.js 24.x not found.\n"
        "Install: nvm install 24 (NVM_HOME must be set)\n"
        "Or: fnm install 24 && fnm use 24\n"
        "Or: Download from https://nodejs.org/ (LTS 24.x)"
    )


def ensure_edge_sandbox(node24_path: str) -> None:
    """Check project-local NV8 npm dependency."""
    result = subprocess.run(
        [node24_path, '-e', 'process.exit(0)'],
        capture_output=True,
        timeout=5,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Node 24 binary not functional: {node24_path}")

    pkg_json = HERE / 'node_modules' / 'nv8' / 'package.json'
    if not pkg_json.exists():
        raise RuntimeError(
            "node_modules/nv8/package.json not found.\n"
            "Declare nv8 in this project's package.json and run npm install."
        )

    print(f"[+] NV8 npm package: {pkg_json.parent}")


# ─── Sensor Generation ─────────────────────────────────────────────────────────

def generate_sensor_post(sensor_script_path: Path, proxy: str = None) -> dict:
    """Call Node.js NV8 to generate sensor POST body."""
    node24 = find_node24()
    print(f"[+] Node 24: {node24}")
    
    ensure_edge_sandbox(node24)

    cmd = [node24, str(sensor_script_path)]
    if proxy:
        cmd.extend(['--proxy', proxy])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding='utf-8', errors='replace')

    # Print log lines
    for line in result.stdout.splitlines():
        if line.startswith('[sensor]') and '=====' not in line:
            print(f"    {line}")

    # Extract JSON
    START = '[sensor] ===== SENSOR POST READY ====='
    END = '[sensor] ===== END ====='
    start_idx = result.stdout.find(START)
    end_idx = result.stdout.find(END)

    if start_idx == -1 or end_idx == -1:
        print("Sensor generation failed (no output markers)")
        if result.stderr:
            print("stderr:", result.stderr[:500])
        sys.exit(1)

    json_start = result.stdout.find('\n', start_idx) + 1
    json_str = result.stdout[json_start:end_idx].strip()
    return json.loads(json_str)


# ─── Forward Sensor POST ───────────────────────────────────────────────────────

TARGET = "https://www.adidas.com.hk/zh/summer_cs_promotion_2"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0"

def forward_sensor_and_get_cookies(sensor_data: dict, proxy: str = None) -> dict:
    """Forward sensor POST to server, collect validated cookies."""
    session = cffi_requests.Session(impersonate="chrome120")

    initial_cookies = sensor_data['cookies']
    for name, value in initial_cookies.items():
        session.cookies.set(name, value, domain=".adidas.com.hk")

    post_url = sensor_data['sensorEndpoint']
    post_body = sensor_data['body']

    print(f"[+] POST {post_url}")
    resp = session.post(
        post_url,
        data=post_body.encode('utf-8'),
        headers={
            "Content-Type": "application/json",
            "User-Agent": UA,
            "Accept": "*/*",
            "Origin": "https://www.adidas.com.hk",
            "Referer": TARGET,
        },
        proxies={"http": proxy, "https": proxy} if proxy else None,
        timeout=15,
    )

    print(f"    Response: {resp.status_code}")

    # Collect all cookies
    all_cookies = dict(initial_cookies)
    for cookie in session.cookies.jar:
        all_cookies[cookie.name] = cookie.value

    new_names = [cookie.name for cookie in session.cookies.jar if cookie.name not in initial_cookies]
    if new_names:
        print(f"    New cookies: {new_names}")

    return all_cookies


# ─── Business Data Collection ──────────────────────────────────────────────────

BASE = "https://www.adidas.com.hk"
SEARCH_PATH = "/on/demandware.store/Sites-adidas-HK-Site/zh_HK/Search-UpdateGrid"
CATEGORY = "summer_cs_promotion_2"
PAGE_SIZE = 48

def parse_products_from_html(html: str) -> list[dict]:
    """Extract products from SFCC Search-UpdateGrid HTML response."""
    soup = BeautifulSoup(html, 'html.parser')
    tiles = soup.select('[data-pid]')

    seen_pids = set()
    products = []

    for tile in tiles:
        pid = tile.get('data-pid', '')
        if not pid or pid in seen_pids:
            continue
        seen_pids.add(pid)

        name_el = tile.select_one('.pdp-link a')
        name = name_el.text.strip() if name_el else ''
        url = name_el.get('href', '') if name_el else ''

        price_el = tile.select_one('.sales .value')
        price = price_el.text.strip() if price_el else ''

        orig_el = tile.select_one('.strike-through .value')
        original_price = orig_el.text.strip() if orig_el else ''

        img_el = tile.select_one('img.tile-image, img')
        image = img_el.get('src', '') if img_el else ''
        if img_el and not image:
            image = img_el.get('data-src', '')

        url_str = url if isinstance(url, str) else ''
        image_str = image if isinstance(image, str) else ''

        products.append({
            'productId': pid,
            'productName': name,
            'url': f"{BASE}{url_str}" if url_str.startswith('/') else url_str,
            'price': price,
            'originalPrice': original_price,
            'image': f"{BASE}{image_str}" if image_str.startswith('/') else image_str,
        })

    return products


def collect_products(cookies: dict, pages: int = 1, proxy: str = None) -> list[dict]:
    """Collect products using validated cookies."""
    session = cffi_requests.Session(impersonate="chrome120")
    for name, value in cookies.items():
        session.cookies.set(name, value, domain=".adidas.com.hk")

    headers = {
        "Accept": "*/*",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": TARGET,
        "User-Agent": UA,
    }

    all_products = []
    for page in range(pages):
        start = page * PAGE_SIZE
        url = f"{BASE}{SEARCH_PATH}?cgid={CATEGORY}&format=ajax&start={start}&sz={PAGE_SIZE}"

        print(f"\n[{page + 1}/{pages}] GET {url}")
        resp = session.get(
            url,
            headers=headers,
            proxies={"http": proxy, "https": proxy} if proxy else None,
            timeout=15,
        )

        print(f"    Status: {resp.status_code}, Size: {len(resp.text) // 1024}KB")
        if resp.status_code != 200:
            print(f"    Body preview: {resp.text[:200]}")
            continue

        products = parse_products_from_html(resp.text)
        print(f"    Products: {len(products)}")
        all_products.extend(products)

        if len(products) == 0:
            break

    return all_products
```

## Verified Results

| Step | Action | Result |
|------|--------|--------|
| 1 | Node 24 + NV8 evaluates 534KB sensor | 4123 bytes POST body generated |
| 2 | curl_cffi forward POST to pomCpnC endpoint | 200 OK, `ak_bmsc` cookie received |
| 3 | Business API with validated cookies | 200 OK, 584KB HTML, 82 products |

## NV8 Advantages

| Surface | env-patch (basic) | iv8 | NV8 |
|---------|-------------------|-----|-------------|
| Window properties | ~200 | ~800 | 1232 (exact Edge 150) |
| Canvas 2D | Stub | Basic stub | Full state machine |
| WebGL | None | Basic params | Full vendor/renderer/extensions |
| getComputedStyle | Partial | No | Full CSS layout |
| Worker/iframe Realms | No | Limited | Full independent Realms |
| Fingerprint control | None | Basic | Configurable (Camoufox export) |
