/**
 * Generic Sensor Generator Template - NV8 reference implementation
 *
 * This script is called by Python, which automatically locates Node 24 via:
 * - NVM_HOME environment variable + v24.* directory
 * - FNM-activated node (checks version)
 * - System node in PATH (checks version)
 *
 * Users do NOT need to manually run `nvm use 24` before execution.
 *
 * IMPORTING NV8:
 *   This NV8 package does not re-export EdgeSandbox from the bare package
 *   name (`exports` only exposes the root, fingerprints, protocol and collector).
 *   This template therefore resolves `EdgeSandbox` from the install root:
 *     1. `NV8_ROOT` environment variable (Python sets it), or
 *     2. a project-local `node_modules/nv8/` created by `npm install`.
 *
 * Architecture:
 * 1. Load approved challenge page + sensor script inputs
 * 2. NV8: evaluate sensor -> capture POST/GET body
 * 3. Output JSON for Python to forward via curl_cffi
 *
 * USAGE:
 * Adjust the CONFIG section below for your target site.
 */

import { existsSync, readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// ═══════════════════════════════════════════════════════════════════════════
// Resolve EdgeSandbox from the NV8 install root (see header)
// ═══════════════════════════════════════════════════════════════════════════
const NV8_ROOT = process.env.NV8_ROOT ?? '';

/** @type {string[]} */
const candidates = [];
if (NV8_ROOT) {
  candidates.push(pathToFileURL(resolve(NV8_ROOT, 'src/public/edge-sandbox.js')).href);
}
candidates.push(new URL('./node_modules/nv8/src/public/edge-sandbox.js', import.meta.url).href);
candidates.push(new URL('../node_modules/nv8/src/public/edge-sandbox.js', import.meta.url).href);

let EdgeSandbox = null;
let resolvedFrom = null;
for (const specifier of candidates) {
  try {
    ({ EdgeSandbox } = await import(specifier));
    resolvedFrom = specifier;
    break;
  } catch {
    // try the next candidate
  }
}

if (typeof EdgeSandbox !== 'function') {
  console.error('[sensor] EdgeSandbox could not be resolved from the NV8 install root.');
  console.error('[sensor] Set NV8_ROOT (e.g. D:/develop_software/Nv8) or run: npm install');
  console.error('[sensor] Ensure package.json has: "nv8": "file:<nv8-root>"');
  process.exit(1);
}

console.log(`[sensor] NV8 loaded from: ${resolvedFrom}`);

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

  // Offline inputs prepared by Python delivery after approval and request accounting
  challengeHtmlFile: 'challenge.html',
  sensorScriptFile: 'sensor.js',
  cookiesFile: 'cookies.json',

  // Fingerprint (merged over the default Edge 150 profile)
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
// Step 1: Load Challenge Page Fixture
// ═══════════════════════════════════════════════════════════════════════════
function loadChallengePage() {
  console.log('[sensor] loading approved challenge HTML...');
  const html = readFileSync(resolve(__dirname, CONFIG.challengeHtmlFile), 'utf-8');
  const cookies = JSON.parse(readFileSync(resolve(__dirname, CONFIG.cookiesFile), 'utf-8'));

  // Extract sensor script URL
  const scriptMatch = html.match(CONFIG.sensorScriptPattern);
  const sensorScriptUrl = scriptMatch ? `https://${CONFIG.host}${scriptMatch[1]}` : null;

  console.log(`[sensor] cookies=${Object.keys(cookies).join(',')} sensorScript=${sensorScriptUrl ? 'found' : 'NOT FOUND'}`);

  if (!sensorScriptUrl) {
    throw new Error('Sensor script URL not found in challenge page');
  }

  return { html, cookies, sensorScriptUrl };
}

// ═══════════════════════════════════════════════════════════════════════════
// Step 2: Load Sensor Script Fixture
// ═══════════════════════════════════════════════════════════════════════════
function loadSensorScript() {
  console.log('[sensor] loading approved sensor script...');
  const scriptText = readFileSync(resolve(__dirname, CONFIG.sensorScriptFile), 'utf-8');
  console.log(`[sensor] sensor script fetched: ${(scriptText.length / 1024).toFixed(0)}KB`);
  return scriptText;
}

// ═══════════════════════════════════════════════════════════════════════════
// Step 3: Run Sensor in NV8
// ═══════════════════════════════════════════════════════════════════════════
async function runSensorInNv8(sensorScriptUrl, sensorScript, cookies) {
  console.log('[sensor] creating NV8 sandbox...');

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
    // Seed cookies. `document.cookie` accepts one cookie per assignment
    // ("a=1; Path=/" — everything after the first `;` is treated as attributes),
    // so never join multiple cookies into one string.
    for (const [name, value] of Object.entries(cookies)) {
      try {
        await sandbox.evaluate(
          `document.cookie = ${JSON.stringify(`${name}=${value}; path=/`)}`,
        );
      } catch {
        // Cookie seeding is best-effort; shape checks below catch real misses.
      }
    }

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
  console.log('[sensor] Generic sensor generator (NV8)');

  const { cookies, sensorScriptUrl } = loadChallengePage();
  const sensorScript = loadSensorScript();
  const result = await runSensorInNv8(sensorScriptUrl, sensorScript, cookies);

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
