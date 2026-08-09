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
 * Architecture:
 * 1. Fetch challenge page + sensor script
 * 2. EdgeSandbox: evaluate sensor → capture POST/GET body
 * 3. Output JSON for Python to forward via curl_cffi
 * 
 * USAGE:
 * Adjust the CONFIG section below for your target site.
 */

import { EdgeSandbox } from 'file:///D:/develop_software/edge_node_sandbox/src/index.js';
import { readFileSync } from 'node:fs';

// ═══════════════════════════════════════════════════════════════════════════
// CONFIG — Adjust for your target site
// ═══════════════════════════════════════════════════════════════════════════

const CONFIG = {
  // Target URL (protected page)
  targetUrl: 'https://www.example.com/protected-page',
  
  // Host (for constructing absolute URLs)
  host: 'www.example.com',
  
  // User-Agent for HTTP fetch (may differ from sandbox UA)
  fetchUA: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0',
  
  // Regex pattern to extract sensor script URL from challenge HTML
  // Example: src="/akam/.../<hash>.js" or src="/<path>/<hash>.js?v=<uuid>"
  sensorScriptPattern: /src="([^"]*(?:sensor|akam|bot-manager)[^"]*)"/i,
  
  // Fingerprint file path (optional, for real browser export)
  fingerprintPath: './fingerprint.json',
  
  // Locale and timezone for sandbox
  locale: 'en-US',
  timezone: 'America/New_York',
  
  // Expected request method to capture (POST or GET)
  captureMethod: 'POST',
  
  // Event loop pump duration (ms) for async requests
  pumpDurationMs: 10_000,
};

// ═══════════════════════════════════════════════════════════════════════════
// Step 1: Fetch challenge page
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
// Step 2: Fetch sensor script
// ═══════════════════════════════════════════════════════════════════════════

async function fetchSensorScript(url, cookies) {
  console.log(`[sensor] GET sensor script...`);
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
// Step 3: Run sensor in EdgeSandbox
// ═══════════════════════════════════════════════════════════════════════════

async function runSensorInEdgeSandbox(html, sensorScript, cookies) {
  console.log('[sensor] creating EdgeSandbox...');
  
  // Load real fingerprint if available
  let fingerprint = { locale: CONFIG.locale, timezone: CONFIG.timezone };
  try {
    const fp = JSON.parse(readFileSync(CONFIG.fingerprintPath, 'utf-8'));
    fingerprint = {
      locale: fp.locale || CONFIG.locale,
      timezone: fp.timezone || CONFIG.timezone,
      screen: fp.screen || { width: 1920, height: 1080, availWidth: 1920, availHeight: 1040, colorDepth: 24, pixelDepth: 24 },
    };
    console.log('[sensor] loaded real fingerprint');
  } catch (e) {
    console.log('[sensor] fingerprint load failed, using defaults');
  }

  const sandbox = await EdgeSandbox.create({
    page: {
      url: CONFIG.targetUrl,
      html: html, // use full challenge HTML or minimal HTML
      contentType: 'text/html',
    },
    fingerprint,
    networkCapture: {
      enabled: true,
      maxEntries: 100,
      maxBodyBytes: 10 * 1024,
    },
    limits: {
      timeoutMs: 20_000,
      maxHeapBytes: 512 * 1024 * 1024,
      maxSourceBytes: 2 * 1024 * 1024,
    },
  });

  try {
    // Inject cookies
    const cookieStr = Object.entries(cookies).map(([k, v]) => `${k}=${v}`).join('; ');
    try {
      await sandbox.evaluate(`document.cookie = ${JSON.stringify(cookieStr)}`);
    } catch (e) {
      console.log('[sensor] cookie injection failed (non-fatal):', e.message);
    }
    
    // Execute sensor
    console.log('[sensor] evaluating sensor script...');
    await sandbox.evaluate(sensorScript);
    console.log('[sensor] sensor executed OK');
    
    // Keep event loop alive for async POST/GET
    console.log(`[sensor] pumping event loop (${CONFIG.pumpDurationMs}ms) for async requests...`);
    try {
      await sandbox.evaluate(`new Promise(resolve => setTimeout(resolve, ${CONFIG.pumpDurationMs}))`);
    } catch (e) {
      console.log('[sensor] pump ended:', e.message?.slice(0, 60));
    }
    
    // Capture network requests
    const requests = await sandbox.networkRequests();
    console.log(`[sensor] captured ${requests.length} requests`);
    
    const targetRequest = requests.find(r => r.method === CONFIG.captureMethod);
    
    if (!targetRequest) {
      console.log(`[sensor] no ${CONFIG.captureMethod} found`);
      return null;
    }
    
    console.log(`[sensor] ${CONFIG.captureMethod} captured: ${targetRequest.url}`);
    console.log(`[sensor] body size: ${targetRequest.bodyByteLength} bytes`);
    
    return {
      requestUrl: targetRequest.url,
      method: targetRequest.method,
      body: targetRequest.bodyText,
      headers: Object.fromEntries(targetRequest.headers),
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
  
  const { html, cookies, sensorScriptUrl } = await fetchChallengePage();
  const sensorScript = await fetchSensorScript(sensorScriptUrl, cookies);
  const result = await runSensorInEdgeSandbox(html, sensorScript, cookies);
  
  if (!result) {
    console.log('[sensor] sensor request generation failed');
    process.exit(1);
  }
  
  // Derive correct endpoint (strip query params from script URL if needed)
  const sensorEndpoint = new URL(sensorScriptUrl);
  const postEndpoint = `https://${CONFIG.host}${sensorEndpoint.pathname}`;
  
  // Output JSON for Python
  console.log('\n[sensor] ===== SENSOR REQUEST READY =====');
  console.log(JSON.stringify({
    sensorEndpoint: postEndpoint,
    method: result.method,
    body: result.body,
    cookies,
  }, null, 2));
  console.log('[sensor] ===== END =====\n');
}

main().catch(err => {
  console.error('[sensor] fatal error:', err);
  process.exit(1);
});
