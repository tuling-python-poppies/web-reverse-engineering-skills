#!/usr/bin/env node
/**
 * NV8 sensor runner for the adidas-hk-akamai-nv8 executor proof.
 *
 * Runs the (synthetic) Akamai-shape sensor inside an NV8
 * `EdgeSandbox` and prints the captured sensor POST as a narrow JSON artifact
 * delimited by markers, so the Python entry can consume it without touching
 * the network or any global state.
 *
 * Offline by construction:
 *   - the NV8 sandbox has no real network;
 *   - the sensor endpoint is answered by an NV8 `replay` record;
 *   - no file writes, no live egress.
 *
 * Usage (normally invoked by entry.py):
 *   node sensor_runner.mjs --nv8-root <root> --target-url <url> \
 *     --challenge fixtures/challenge.html --sensor fixtures/sensor.synthetic.js \
 *     --cookies fixtures/cookies.json [--pump-ms 1500]
 */

import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const MARKER_BEGIN = '===== NV8 SENSOR ARTIFACT =====';
const MARKER_END = '===== END =====';

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    if (!item.startsWith('--')) continue;
    const key = item.slice(2);
    const value = argv[index + 1];
    if (value === undefined || value.startsWith('--')) {
      args[key] = true;
      continue;
    }
    args[key] = value;
    index += 1;
  }
  return args;
}

function requireString(args, key) {
  const value = args[key];
  if (typeof value !== 'string' || value.length === 0) {
    console.error(`[runner] missing required --${key}`);
    process.exit(2);
  }
  return value;
}

async function loadEdgeSandbox(nv8Root) {
  const entry = resolve(nv8Root, 'src/public/edge-sandbox.js');
  if (!existsSync(entry)) {
    console.error(`[runner] NV8 public entry not found: ${entry}`);
    process.exit(2);
  }
  try {
    const module = await import(pathToFileURL(entry).href);
    if (typeof module.EdgeSandbox !== 'function') {
      console.error('[runner] NV8 module does not export EdgeSandbox');
      process.exit(2);
    }
    return module.EdgeSandbox;
  } catch (error) {
    console.error(`[runner] failed to import NV8 from ${entry}: ${error.message}`);
    process.exit(2);
  }
}

function decodeEntities(value) {
  return value
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#x2f;/gi, '/')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>');
}

function deriveSensorEndpoint(challengeHtml, challengePath) {
  const refs = [...challengeHtml.matchAll(/<script[^>]+src="([^"]+)"/gi)]
    .map((match) => decodeEntities(match[1]))
    .filter((src) => src.startsWith('/') || src.startsWith('https://'));
  // Live shape: the sensor script is the same-origin script whose query
  // carries `v=<uuid>` (variants `&t=<challengeId>` / `&ch=true`).
  let scriptRef = refs.find((src) => /[?&]v=[0-9a-f-]{32,}(?:&|$)/i.test(src));
  if (scriptRef === undefined) {
    scriptRef = refs.find((src) => /[?&](?:t|ch)=/.test(src));
  }
  if (scriptRef === undefined) {
    console.error(`[runner] sensor script (?v=<uuid>) not found in ${challengePath}`);
    process.exit(2);
  }
  const scriptUrl = new URL(scriptRef, 'https://www.adidas.com.hk/');
  // Endpoint = script URL without query data (documented derivation rule).
  scriptUrl.search = '';
  scriptUrl.hash = '';
  return scriptUrl.href;
}

function pathnameOf(url) {
  try {
    return new URL(url).pathname;
  } catch {
    return null;
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const nv8Root = requireString(args, 'nv8-root');
  const targetUrl = requireString(args, 'target-url');
  const challengePath = resolve(requireString(args, 'challenge'));
  const sensorPath = resolve(requireString(args, 'sensor'));
  const cookiesPath = resolve(requireString(args, 'cookies'));
  const pumpMs = Number(args['pump-ms'] ?? 1500);

  const EdgeSandbox = await loadEdgeSandbox(nv8Root);
  const challengeHtml = readFileSync(challengePath, 'utf8');
  const sensorScript = readFileSync(sensorPath, 'utf8');
  const cookies = JSON.parse(readFileSync(cookiesPath, 'utf8'));
  const sensorEndpoint = deriveSensorEndpoint(challengeHtml, challengePath);

  console.error(`[runner] nv8 root     : ${nv8Root}`);
  console.error(`[runner] target url   : ${targetUrl}`);
  console.error(`[runner] sensor       : ${sensorEndpoint}`);

  const sandbox = await EdgeSandbox.create({
    page: {
      url: targetUrl,
      html: challengeHtml,
      contentType: 'text/html',
    },
    fingerprint: { locale: 'zh-HK', timezone: 'Asia/Hong_Kong' },
    // Offline answer for the synthetic sensor POST: keeps the request
    // `replayed` while still being captured by network capture.
    replay: [
      {
        method: 'POST',
        url: sensorEndpoint,
        status: 200,
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ ok: true }),
      },
    ],
    networkCapture: { enabled: true, maxEntries: 50, maxBodyBytes: 64 * 1024 },
    limits: { timeoutMs: 20_000 },
  });

  try {
    for (const [name, value] of Object.entries(cookies)) {
      await sandbox.evaluate(
        `document.cookie = ${JSON.stringify(`${name}=${value}; path=/`)}`,
      );
    }

    await sandbox.evaluate(`globalThis.__SENSOR_ENDPOINT = ${JSON.stringify(sensorEndpoint)}`);
    await sandbox.evaluate(
      `(() => { try { ${sensorScript} } catch (error) { globalThis.__sensorError = String(error && error.message || error); } })()`,
    );

    const sensorError = await sandbox.evaluate('globalThis.__sensorError ?? null');
    if (sensorError.value !== null && sensorError.value !== undefined) {
      console.error(`[runner] synthetic sensor error: ${sensorError.value}`);
    }

    await sandbox.evaluate(`new Promise((resolve) => setTimeout(resolve, ${pumpMs}))`);

    const requests = await sandbox.networkRequests();
    const endpointPath = pathnameOf(sensorEndpoint);
    const post = requests.find(
      (request) => request.method === 'POST' && pathnameOf(request.url) === endpointPath,
    );
    if (post === undefined) {
      console.error(`[runner] no sensor POST captured at ${endpointPath} (requests=${requests.length})`);
      process.exit(1);
    }

    let parsedBody = null;
    try {
      parsedBody = JSON.parse(post.bodyText);
    } catch {
      parsedBody = null;
    }

    const artifact = {
      schemaVersion: 'adidas-hk-akamai-nv8/runner-artifact@1',
      runtime: 'nv8',
      sensorEndpoint,
      method: post.method,
      contentType:
        post.headers.find(([name]) => name.toLowerCase() === 'content-type')?.[1] ?? null,
      bodyJsonKeys: parsedBody !== null && typeof parsedBody === 'object'
        ? Object.keys(parsedBody)
        : null,
      bodyByteLength: post.bodyByteLength,
      outcome: post.outcome,
      body: post.bodyText,
    };

    console.log(MARKER_BEGIN);
    console.log(JSON.stringify(artifact));
    console.log(MARKER_END);
  } finally {
    await sandbox.close();
  }
}

main().catch((error) => {
  console.error(`[runner] fatal: ${error && error.message}`);
  process.exit(1);
});
