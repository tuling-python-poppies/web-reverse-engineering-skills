/**
 * Generic Sensor Generator Template — EdgeSandbox reference implementation
 * 
 * This script is called by Python, which automatically locates Node 24 via:
 * - NVM_HOME environment variable + v24.* directory
 * - FNM-activated node (checks version)
 * - System node in PATH (checks version)
 * 
 * Users do NOT need to manually run `nvm use 24` before execution.
 * 
 * INSTALLATION:
 * EdgeSandbox is installed as a local npm dependency:
 *   1. Add to package.json: "edge-sandbox": "file:<path-to-edge-sandbox>"
 *   2. Run: npm install
 *   3. Import: import { EdgeSandbox } from 'edge-sandbox';
 * 
 * Architecture:
 * 1. Fetch challenge page + sensor script
 * 2. EdgeSandbox: evaluate sensor → capture POST/GET body
 * 3. Output JSON for Python to forward via curl_cffi
 * 
 * USAGE:
 * Adjust the CONFIG section below for your target site.
 */

import { existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// ═══════════════════════════════════════════════════════════════════════════
// Verify edge-sandbox is installed via npm
// ═══════════════════════════════════════════════════════════════════════════
const edgeSandboxPkg = resolve(__dirname, 'node_modules', 'edge-sandbox', 'package.json');
const parentEdgeSandboxPkg = resolve(__dirname, '..', 'node_modules', 'edge-sandbox', 'package.json');
if (!existsSync(edgeSandboxPkg) && !existsSync(parentEdgeSandboxPkg)) {
  console.error('[sensor] edge-sandbox not found in node_modules.');
  console.error('[sensor] Run: npm install');
  console.error('[sensor] Ensure package.json has: "edge-sandbox": "file:<path-to-edge-sandbox>"');
  process.exit(1);
}

const { EdgeSandbox } = await import('edge-sandbox');

// ═══════════════════════════════════════════════════════════════════════════
// CONFIG — Adjust for your target site
// ═══════════════════════════════════════════════════════════════════════════

const CONFIG = {
  // Target URL (protected page)
  targetUrl: 'https://www.example.com/protected-page',
  
  // Target host
  host: 'www.example.com',
  
  // Regex pattern to find sensor script URL in challenge HTML
  sensorScriptPattern: /src="([^"]*sensor-path[^"]*)"/,
  
  // User-Agent for HTTP requests (fetching challenge + sensor)
  fetchUA: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0',
  
  // Fingerprint (default EdgeSandbox profile or custom)
  fingerprint: {
    locale: 'en-US',
    timezone: 'America/New_York',
  },
  
  // Sandbox timeout (ms) — increase for large sensors
  timeoutMs: 30_000,
  
  // Event loop pump duration (ms) — time to wait for async POST
  pumpMs: 10_000,
};

// ═══════════════════════════════════════════════════════════════════════════
// Step 1: Fetch Challenge Page
// ═══════════════════════════════════════════════════════════════════════════
async function fetchChallengePage() {
  console.log('[sensor] GET challenge page...');
  const resp = await fetch(CONFIG.targetUrl, {
    method: 'GET',
    headers: {
      'User-Agent': CONFIG.fetchUA,
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    },
    redirect: 'manual',
  });

  const status = resp.status;
  const html = await resp.text();
  
  // Parse Set-Cookie
  const setCookies = resp.headers.getSetCookie?.() || [];
  const cookies = {};
  for (const sc of setCookies) {
    const [kv] = sc.split(';');
    const [k, ...vParts] = kv.split('=');
    cookies[k.trim()] = vParts.join('=').trim();
  }

  // Extract sensor script URL
  const scriptMatch = html.match(CONFIG.sensorScriptPattern);
  const sensorScriptUrl = scriptMatch ? `https://${CONFIG.host}${scriptMatch[1]}` : null;

  console.log(`[sensor] status=${status} cookies=${Object.keys(cookies).join(',')} sensorScript=${sensorScriptUrl ? 'found' : 'NOT FOUND'}`);
  
  if (!sensorScriptUrl) {
    throw new Error('Sensor script URL not found in challenge page');
  }

  return { status, html, cookies, sensorScriptUrl };
}

// ═══════════════════════════════════════════════════════════════════════════
// Step 2: Fetch Sensor Script
// ═══════════════════════════════════════════════════════════════════════════
async function fetchSensorScript(url, cookies) {
  console.log('[sensor] GET sensor script...');
  const cookieStr = Object.entries(cookies).map(([k, v]) => `${k}=${v}`).join('; ');
  
  const resp = await fetch(url, {
    method: 'GET',
    headers: {
      'User-Agent': CONFIG.fetchUA,
      'Accept': '*/*',
      'Referer': CONFIG.targetUrl,
      'Cookie': cookieStr,
    },
  });

  const scriptText = await resp.text();
  console.log(`[sensor] sensor script fetched: ${(scriptText.length / 1024).toFixed(0)}KB`);
  return scriptText;
}

// ═══════════════════════════════════════════════════════════════════════════
// Step 3: Run Sensor in EdgeSandbox
// ═══════════════════════════════════════════════════════════════════════════
async function runSensorInEdgeSandbox(sensorScriptUrl, sensorScript, cookies) {
  console.log('[sensor] creating EdgeSandbox...');

  // Minimal HTML — sensor only needs location, document.cookie, navigator, screen
  const sensorPath = new URL(sensorScriptUrl).pathname;
  const cleanHtml = `<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Target</title></head>
<body><main></main><script src="${sensorPath}"></script></body>
</html>`;

  const sandbox = await EdgeSandbox.create({
    page: {
      url: CONFIG.targetUrl,
      html: cleanHtml,
      contentType: 'text/html',
    },
    fingerprint: CONFIG.fingerprint,
    networkCapture: {
      enabled: true,
      maxEntries: 100,
      maxBodyBytes: 10 * 1024,
    },
    limits: {
      timeoutMs: CONFIG.timeoutMs,
      maxHeapBytes: 512 * 1024 * 1024,
      maxSourceBytes: 2 * 1024 * 1024,
    },
  });

  try {
    // Inject cookies
    const cookieStr = Object.entries(cookies).map(([k, v]) => `${k}=${v}`).join('; ');
    try {
      await sandbox.evaluate(`document.cookie = ${JSON.stringify(cookieStr)}`);
    } catch (e) {}

    // Execute sensor script (wrapped in try-catch for error capture)
    console.log('[sensor] evaluating sensor script...');
    const wrappedScript = `
      (() => {
        try { ${sensorScript} }
        catch(e) { window.__sensorError = e.message + '\\n' + (e.stack || '').slice(0, 500); }
      })()
    `;

    try {
      await sandbox.evaluate(wrappedScript);
      console.log('[sensor] sensor executed OK');
    } catch (e) {
      console.log(`[sensor] sensor execution error: ${e.message?.slice(0, 150)}`);
    }

    // Keep event loop alive for async POST
    console.log(`[sensor] pumping event loop (${CONFIG.pumpMs/1000}s) for async POST...`);
    try {
      await sandbox.evaluate(`new Promise(resolve => setTimeout(resolve, ${CONFIG.pumpMs}))`);
    } catch (e) {
      console.log(`[sensor] pump ended: ${e.message?.slice(0, 60)}`);
    }

    // Capture network requests
    const requests = await sandbox.networkRequests();
    console.log(`[sensor] captured ${requests.length} requests`);

    const sensorPost = requests.find(r => r.method === 'POST');

    if (!sensorPost) {
      console.log('[sensor] no POST found');
      return null;
    }

    console.log(`[sensor] POST captured: ${sensorPost.url}`);
    console.log(`[sensor] body size: ${sensorPost.bodyByteLength} bytes`);

    return {
      postUrl: sensorPost.url,
      body: sensorPost.bodyText,
      headers: Object.fromEntries(sensorPost.headers),
    };
  } finally {
    await sandbox.close();
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// Main
// ═══════════════════════════════════════════════════════════════════════════
async function main() {
  console.log('[sensor] Generic sensor generator (EdgeSandbox)');

  const { cookies, sensorScriptUrl } = await fetchChallengePage();
  const sensorScript = await fetchSensorScript(sensorScriptUrl, cookies);
  const result = await runSensorInEdgeSandbox(sensorScriptUrl, sensorScript, cookies);

  if (!result) {
    console.log('[sensor] sensor POST generation failed');
    process.exit(1);
  }

  // Derive POST endpoint (strip query params from script URL)
  const sensorEndpoint = new URL(sensorScriptUrl);
  const postEndpoint = `https://${CONFIG.host}${sensorEndpoint.pathname}`;

  // Output JSON for Python
  console.log('\n===== SENSOR POST READY =====');
  console.log(JSON.stringify({
    sensorEndpoint: postEndpoint,
    body: result.body,
    cookies,
  }, null, 2));
  console.log('===== END =====\n');
}

main().catch(err => {
  console.error('[sensor] fatal:', err);
  process.exit(1);
});
