#!/usr/bin/env node
/**
 * gap-log-module-advisor.js
 *
 * Map Proxy / diagnostic gap logs onto the current env-patch module tree
 * (bom/dom/webapi/core/encoding/timer paths under env/).
 *
 * Usage:
 *   node gap-log-module-advisor.js <gap-log.json>
 *
 * Accepts:
 *   - { logs: [{ type, path, ... }, ...] }
 *   - [{ type, path, ... }, ...]
 *   - { missingPaths, undefinedPaths, descriptorAccess, prototypeAccess, invocationErrors }
 *
 * Prints JSON with recommendedModules as paths relative to env/.
 */

import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

/** Lower index = preferred when scores tie. Paths match env-modules.md. */
const MODULE_PRIORITY = [
  "core/proxy-access-monitor.js",
  "core/minimal-proxy-browser-env.js",
  "core/profile-seed-manager.js",
  "core/classified-env-monitor.js",
  "core/element-mock-monitor.js",
  "bom/window-global-apis.js",
  "bom/navigator-fingerprint.js",
  "bom/location-url-state.js",
  "bom/history-state.js",
  "bom/screen-fingerprint.js",
  "bom/web-storage.js",
  "bom/web-crypto.js",
  "bom/performance-timing.js",
  "bom/observer-constructors.js",
  "bom/console-log-buffer.js",
  "dom/event-constructors.js",
  "dom/document-dom-runtime.js",
  "dom/html-element-constructors.js",
  "webapi/fetch-request-response.js",
  "webapi/xml-http-request.js",
  "webapi/blob-file-formdata.js",
  "webapi/url-search-params.js",
  "webapi/network-mock-recorder.js",
  "webapi/web-audio-fingerprint.js",
  "webapi/webrtc-peerconnection.js",
  "webapi/worker-messaging.js",
  "timer/timeout-interval-scheduler.js",
  "encoding/base64-codec.js",
  "encoding/text-codec.js",
];

function toArray(value) {
  if (Array.isArray(value)) return value;
  if (value && Array.isArray(value.logs)) return value.logs;
  return [];
}

function unique(values) {
  return Array.from(new Set(values));
}

function extractPathList(input, key, type) {
  if (Array.isArray(input[key])) return unique(input[key].filter((v) => typeof v === "string"));
  return unique(
    toArray(input)
      .filter((item) => item && item.type === type && typeof item.path === "string")
      .map((item) => item.path),
  );
}

/**
 * Infer env/ module paths from an observed property/API path string.
 * Returns paths relative to env/. Native/prototype pressure that modules
 * cannot fix is reported as advisory nextActions, not fake module names.
 */
function isNativePressureOnly(path) {
  const value = String(path || "");
  // Known API.prototype.method paths are module targets, not native-engine blockers.
  if (/XMLHttpRequest|HTMLElement|Element\.|Node\.|EventTarget|Document\.|Window\.|Storage\.|Worker|MessagePort|RTCPeer|AudioContext|fetch|Request|Response|Headers|FormData|URLSearchParams|TextEncoder|TextDecoder/.test(value)) {
    return false;
  }
  if (/getOwnPropertyDescriptor|defineProperty|propertyIsEnumerable|ownKeys|__proto__/.test(value)) return true;
  if (/Function\.prototype\.toString|\.toString\b/.test(value) && !/navigator|document|location/.test(value)) return true;
  if (/\bprototype\b|\bconstructor\b/.test(value) && !/XMLHttpRequest|HTML|Element|Node|Event|Document|Window/.test(value)) return true;
  if (/\bcaller\b|\barguments\b/.test(value)) return true;
  return false;
}

function inferModulesFromPath(path) {
  const modules = [];
  const value = String(path || "");

  if (isNativePressureOnly(value)) {
    return modules;
  }

  if (/navigator|plugins|mimeTypes|webdriver|userAgentData|getBattery|permissions|mediaDevices|serviceWorker|hardwareConcurrency|deviceMemory/.test(value)) {
    modules.push("bom/navigator-fingerprint.js");
  }
  if (/\blocation\b|location\.href|location\.protocol|location\.host/.test(value)) {
    modules.push("bom/location-url-state.js");
  }
  if (/\bhistory\b|history\.pushState|history\.replaceState|scrollRestoration/.test(value)) {
    modules.push("bom/history-state.js");
  }
  if (/\bscreen\b|availWidth|availHeight|colorDepth|pixelDepth|isExtended/.test(value)) {
    modules.push("bom/screen-fingerprint.js");
  }
  if (/localStorage|sessionStorage|StorageEvent|\bStorage\b/.test(value)) {
    modules.push("bom/web-storage.js");
  }
  if (/\bcrypto\b|msCrypto|getRandomValues|subtle/.test(value)) {
    modules.push("bom/web-crypto.js");
  }
  if (/\bperformance\b|PerformanceObserver|timeOrigin|now\(\)/.test(value)) {
    modules.push("bom/performance-timing.js");
  }
  if (/MutationObserver|ResizeObserver|IntersectionObserver|PerformanceObserver/.test(value)) {
    modules.push("bom/observer-constructors.js");
  }
  if (/\bconsole\b/.test(value)) {
    modules.push("bom/console-log-buffer.js");
  }
  if (
    /innerWidth|innerHeight|outerWidth|outerHeight|devicePixelRatio|visualViewport|requestAnimationFrame|cancelAnimationFrame|matchMedia|getComputedStyle|indexedDB|trustedTypes|caches|\bCSS\b|Notification|Clipboard|scheduler|postMessage/.test(
      value,
    )
  ) {
    modules.push("bom/window-global-apis.js");
  }

  if (/document\.all/.test(value)) {
    modules.push("dom/document-dom-runtime.js");
  } else if (/\bdocument\b|createElement|querySelector|cookie|getElementById|documentElement|body|head/.test(value)) {
    modules.push("dom/document-dom-runtime.js");
  }
  if (/HTMLElement|HTMLDivElement|HTMLCanvasElement|HTMLIFrameElement|Element\.prototype|Node\.prototype/.test(value)) {
    modules.push("dom/html-element-constructors.js");
  }
  if (/\bEvent\b|CustomEvent|MouseEvent|KeyboardEvent|addEventListener|dispatchEvent|EventTarget/.test(value)) {
    modules.push("dom/event-constructors.js");
  }

  if (/\bfetch\b|\bRequest\b|\bResponse\b|Headers\b|AbortController|AbortSignal/.test(value)) {
    modules.push("webapi/fetch-request-response.js");
  }
  if (/XMLHttpRequest|xhr\./i.test(value)) {
    modules.push("webapi/xml-http-request.js");
  }
  if (/\bBlob\b|\bFile\b|FormData|FileReader/.test(value)) {
    modules.push("webapi/blob-file-formdata.js");
  }
  if (/URLSearchParams|\bURL\b/.test(value) && !/location/.test(value)) {
    modules.push("webapi/url-search-params.js");
  }
  if (/AudioContext|OfflineAudioContext|Oscillator|Analyser|AudioBuffer/.test(value)) {
    modules.push("webapi/web-audio-fingerprint.js");
  }
  if (/RTCPeerConnection|RTCDataChannel|RTCIceCandidate|RTCSessionDescription|webkitRTCPeerConnection/.test(value)) {
    modules.push("webapi/webrtc-peerconnection.js");
  }
  if (/\bWorker\b|SharedWorker|MessagePort|BroadcastChannel|MessageChannel/.test(value)) {
    modules.push("webapi/worker-messaging.js");
  }

  if (/setTimeout|setInterval|clearTimeout|clearInterval|queueMicrotask/.test(value)) {
    modules.push("timer/timeout-interval-scheduler.js");
  }
  if (/\batob\b|\bbtoa\b/.test(value)) {
    modules.push("encoding/base64-codec.js");
  }
  if (/TextEncoder|TextDecoder/.test(value)) {
    modules.push("encoding/text-codec.js");
  }

  if (/canvas|webgl|getContext|toDataURL|WebGLRenderingContext/.test(value)) {
    modules.push("bom/window-global-apis.js");
    modules.push("dom/html-element-constructors.js");
  }

  return unique(modules);
}

function scoreEvidence(entry) {
  if (!entry || !entry.type) return 1;
  if (entry.type === "invoke-error" || entry.type === "error") return 5;
  if (entry.type === "missing" || entry.type === "undefined") return 4;
  if (entry.type === "descriptor" || entry.type === "prototype") return 3;
  return 1;
}

function collectAllPaths(input) {
  const paths = [];
  for (const key of ["missingPaths", "undefinedPaths", "descriptorAccess", "prototypeAccess", "invocationErrors"]) {
    paths.push(...extractPathList(input, key, key.replace(/Paths?$/, "").replace(/Access$/, "").replace(/Errors$/, "")));
  }
  for (const entry of toArray(input)) {
    if (entry && typeof entry.path === "string") paths.push(entry.path);
  }
  return unique(paths);
}

export function analyzeGapLog(input = {}) {
  const logs = toArray(input);
  const allPaths = collectAllPaths(input);
  const groupedByModule = Object.create(null);
  const unmatchedPaths = [];
  const nativePressurePaths = [];

  function addModule(modulePath, score, evidencePath) {
    if (!groupedByModule[modulePath]) {
      groupedByModule[modulePath] = { score: 0, evidence: [] };
    }
    groupedByModule[modulePath].score += score;
    if (evidencePath) groupedByModule[modulePath].evidence.push(evidencePath);
  }

  for (const entry of logs) {
    const path = entry && entry.path;
    if (typeof path !== "string") continue;
    const modules = inferModulesFromPath(path);
    if (!modules.length) {
      if (isNativePressureOnly(path)) nativePressurePaths.push(path);
      else unmatchedPaths.push(path);
      continue;
    }
    for (const moduleName of modules) {
      addModule(moduleName, scoreEvidence(entry), path);
    }
  }

  for (const path of allPaths) {
    if (logs.some((e) => e && e.path === path)) continue;
    const modules = inferModulesFromPath(path);
    if (!modules.length) {
      if (isNativePressureOnly(path)) nativePressurePaths.push(path);
      else unmatchedPaths.push(path);
      continue;
    }
    for (const moduleName of modules) {
      addModule(moduleName, 2, path);
    }
  }

  const recommendedModules = Object.keys(groupedByModule).sort((left, right) => {
    const leftScore = groupedByModule[left].score;
    const rightScore = groupedByModule[right].score;
    if (rightScore !== leftScore) return rightScore - leftScore;
    const leftPriority = MODULE_PRIORITY.indexOf(left);
    const rightPriority = MODULE_PRIORITY.indexOf(right);
    const lp = leftPriority === -1 ? 999 : leftPriority;
    const rp = rightPriority === -1 ? 999 : rightPriority;
    return lp - rp;
  });

  const nextActions = [];
  if (recommendedModules.length) {
    nextActions.push(
      "Load recommendedModules in env-modules.md order (core baseline first, then bom/dom/webapi) via --env paths relative to env/.",
    );
  }
  if (nativePressurePaths.length) {
    nextActions.push(
      "Native/prototype/descriptor/toString pressure detected; env modules cannot fully model this. Read references/node-detection.md, then path-upgrade-checklist.md for iv8 escalation or blocker.",
    );
  }
  if (unmatchedPaths.length) {
    nextActions.push(
      "Unmatched paths: write minimal project patches under js_reverse_cache/env/ai-generated/<name>.js and load with --env.",
    );
  }
  if (!recommendedModules.length && !nativePressurePaths.length && !unmatchedPaths.length) {
    nextActions.push("No actionable gap paths; re-run diagnosis with proxy monitoring or supply undefinedPaths.");
  }

  return {
    recommendedModules,
    byModule: groupedByModule,
    unmatchedPaths: unique(unmatchedPaths),
    nativePressurePaths: unique(nativePressurePaths),
    nextActions,
    moduleTree: "env/ (bom|dom|webapi|core|encoding|timer)",
  };
}

function main() {
  const args = process.argv.slice(2);
  if (!args.length || args[0] === "-h" || args[0] === "--help") {
    console.error("Usage: node gap-log-module-advisor.js <gap-log.json>");
    process.exit(args.length ? 0 : 1);
  }
  const raw = readFileSync(args[0], "utf8");
  let input;
  try {
    input = JSON.parse(raw);
  } catch (err) {
    console.error(`Invalid JSON: ${err.message}`);
    process.exit(1);
  }
  const result = analyzeGapLog(input);
  console.log(JSON.stringify(result, null, 2));
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main();
}
