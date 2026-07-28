'use strict';

const fs = require('fs');
const path = require('path');
const { installEnv } = require('./mod');

function readJsonArg() {
  const raw = process.argv[2] || '{}';
  try {
    return JSON.parse(raw);
  } catch (error) {
    return { url: raw };
  }
}

function loadTarget() {
  const targetPath = path.join(__dirname, 'js_reverse_cache', 'target', 'raw.js');
  if (fs.existsSync(targetPath)) require(targetPath);
}

function getEncryptedParams(input) {
  installEnv(input.profile || undefined);
  loadTarget();

  // Replace this with the verified target entry call. Keep stdout JSON-only.
  return {
    url: input.url || '',
    sign: '',
  };
}

if (require.main === module) {
  try {
    process.stdout.write(JSON.stringify(getEncryptedParams(readJsonArg())));
  } catch (error) {
    process.stderr.write(error && error.stack || String(error));
    process.exit(1);
  }
}

module.exports = getEncryptedParams;
