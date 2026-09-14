#!/usr/bin/env node
/**
 * NV8 Node.js version diagnostic tool
 *
 * NV8 runtime support matrix:
 * - Node >= 18.18.0 is the supported floor (matrix covers 18 / 20 / 22 / 24).
 * - Node 22+ is ADVISORY for fingerprint-order-sensitive work (Window global
 *   enumeration order); it does not gate execution.
 * - Node 24.x is this Provider's preferred baseline.
 *
 * Python scripts prefer Node 24 via NVM_HOME/FNM/PATH,
 * so users do not need to run this manually in normal workflows.
 *
 * Use this for troubleshooting:
 *   node node-version-check.js
 */

const nodeVersion = process.version;
const match = nodeVersion.match(/^v(\d+)\.(\d+)\.(\d+)$/);

if (!match) {
  console.error('Cannot parse Node.js version:', nodeVersion);
  process.exit(1);
}

const [, majorRaw, minorRaw] = match.map(Number);

if (majorRaw < 18 || (majorRaw === 18 && minorRaw < 18)) {
  console.error('NV8 requires Node.js 18.18.0 or newer');
  console.error(`Current version: ${nodeVersion}`);
  console.error('');
  console.error('Install a supported Node version:');
  console.error('  NVM:    nvm install 24');
  console.error('  FNM:    fnm install 24');
  console.error('  Manual: https://nodejs.org/ (LTS 24.x)');
  console.error('');
  console.error('Python scripts auto-detect Node 24 via the NVM_HOME environment variable.');
  process.exit(1);
}

console.log(`Node.js ${nodeVersion} (supported)`);
if (majorRaw < 22) {
  console.warn('NOTE: advisory — Node 22+ is better for Edge-equivalent Window global order.');
}
if (majorRaw !== 24) {
  console.warn('NOTE: this Provider prefers Node 24.x when available.');
}
console.log(`  NVM_HOME: ${process.env.NVM_HOME || 'not set'}`);
process.exit(0);
