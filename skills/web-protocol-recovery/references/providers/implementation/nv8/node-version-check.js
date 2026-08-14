#!/usr/bin/env node
/**
 * NV8 Node.js version diagnostic tool
 *
 * NV8 requires Node.js 24.x due to VM module APIs
 * and explicit resource management support.
 *
 * Python scripts automatically find Node 24 via NVM_HOME/FNM/PATH,
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

const [_, major, minor, patch] = match.map(Number);

if (major !== 24) {
  console.error(`NV8 requires Node.js 24.x`);
  console.error(`Current version: ${nodeVersion}`);
  console.error('');
  console.error('Install Node 24:');
  console.error('  NVM:    nvm install 24');
  console.error('  FNM:    fnm install 24');
  console.error('  Manual: https://nodejs.org/ (LTS 24.x)');
  console.error('');
  console.error('Python scripts auto-detect Node 24 via NVM_HOME environment variable.');
  process.exit(1);
}

console.log(`Node.js ${nodeVersion} (compatible)`);
console.log(`  NVM_HOME: ${process.env.NVM_HOME || 'not set'}`);
process.exit(0);
