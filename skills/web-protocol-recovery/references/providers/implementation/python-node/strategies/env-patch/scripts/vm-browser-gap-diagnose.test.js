import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const script = path.join(__dirname, 'vm-browser-gap-diagnose.js');

test('diagnoser fails closed without trusted-code acknowledgement', () => {
  const result = spawnSync(process.execPath, [script, 'does-not-need-to-exist.js'], { encoding: 'utf8' });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /--trusted-code/);
  assert.match(result.stderr, /node:vm/);
  assert.doesNotMatch(result.stderr, /目标脚本不存在/);
});

test('diagnoser runs reviewed code with explicit acknowledgement', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-diagnose-'));
  const target = path.join(dir, 'target.js');
  fs.writeFileSync(target, 'globalThis.answer = 42;');
  try {
    const result = spawnSync(process.execPath, [script, '--trusted-code', '--quiet', target], { encoding: 'utf8' });
    assert.equal(result.status, 0, `${result.stderr}\n${result.stdout}`);
    const output = JSON.parse(result.stdout);
    assert.equal(output.success, true);
    assert.deepEqual(output.moduleLoadErrors, []);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('diagnoser preserves undefined-path monitoring after env modules load', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-diagnose-env-'));
  const target = path.join(dir, 'target.js');
  fs.writeFileSync(target, 'void navigator.missingDiagnosticProperty;');
  try {
    const result = spawnSync(
      process.execPath,
      [script, '--trusted-code', '--quiet', '--env', 'bom/navigator-fingerprint.js', target],
      { encoding: 'utf8' },
    );
    assert.equal(result.status, 0, result.stderr);
    const output = JSON.parse(result.stdout);
    assert.equal(output.success, true);
    assert.ok(output.undefinedPaths.includes('navigator.missingDiagnosticProperty'));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('monitored baseline remains available when one env module is selected', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-baseline-with-env-'));
  const target = path.join(dir, 'target.js');
  fs.writeFileSync(target, 'void document.missingDiagnosticProperty;');
  try {
    const result = spawnSync(
      process.execPath,
      [script, '--trusted-code', '--quiet', '--env', 'bom/navigator-fingerprint.js', target],
      { encoding: 'utf8' },
    );
    assert.equal(result.status, 0, result.stderr);
    const output = JSON.parse(result.stdout);
    assert.equal(output.success, true);
    assert.ok(output.undefinedPaths.includes('document.missingDiagnosticProperty'));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('project-local generated env modules resolve from the project root', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-project-env-'));
  const envDir = path.join(dir, 'js_reverse_cache', 'env', 'ai-generated');
  const env = path.join(envDir, 'custom.js');
  const retiredEnvDir = path.join(dir, 'ai-generated');
  const retiredEnv = path.join(retiredEnvDir, 'custom.js');
  const target = path.join(dir, 'target.js');
  fs.mkdirSync(envDir, { recursive: true });
  fs.mkdirSync(retiredEnvDir, { recursive: true });
  fs.writeFileSync(env, 'window.projectLocalPatch = 7;');
  fs.writeFileSync(retiredEnv, 'window.projectLocalPatch = 99;');
  fs.writeFileSync(target, "if (window.projectLocalPatch !== 7) throw new Error('project patch missing');");
  try {
    const result = spawnSync(
      process.execPath,
      [script, '--trusted-code', '--quiet', '--env', 'js_reverse_cache/env/ai-generated/custom.js', target],
      { cwd: dir, encoding: 'utf8' },
    );
    assert.equal(result.status, 0, result.stderr);
    assert.equal(JSON.parse(result.stdout).success, true);

    if (process.platform === 'win32') {
      const windowsResult = spawnSync(
        process.execPath,
        [script, '--trusted-code', '--quiet', '--env', 'js_reverse_cache\\env\\ai-generated\\custom.js', target],
        { cwd: dir, encoding: 'utf8' },
      );
      assert.equal(windowsResult.status, 0, windowsResult.stderr);
      assert.equal(JSON.parse(windowsResult.stdout).success, true);
    }

    const retiredResult = spawnSync(
      process.execPath,
      [script, '--trusted-code', '--quiet', '--env', 'ai-generated/custom.js', target],
      { cwd: dir, encoding: 'utf8' },
    );
    const retiredOutput = JSON.parse(retiredResult.stdout);
    assert.notEqual(retiredResult.status, 0);
    assert.ok(retiredOutput.moduleLoadErrors.some(
      error => error.module === 'ai-generated/custom.js'
        && /must be under js_reverse_cache\/env/.test(error.error),
    ));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('built-in env module names cannot be shadowed by the project cwd', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-builtin-shadow-'));
  const shadowDir = path.join(dir, 'bom');
  const target = path.join(dir, 'target.js');
  fs.mkdirSync(shadowDir, { recursive: true });
  fs.writeFileSync(path.join(shadowDir, 'navigator-fingerprint.js'), "throw new Error('cwd shadow executed');");
  fs.writeFileSync(target, "if (navigator.appName !== 'Netscape') throw new Error('built-in module missing');");
  try {
    const result = spawnSync(
      process.execPath,
      [script, '--trusted-code', '--quiet', '--env', 'bom/navigator-fingerprint.js', target],
      { cwd: dir, encoding: 'utf8' },
    );
    assert.equal(result.status, 0, `${result.stderr}\n${result.stdout}`);
    assert.equal(JSON.parse(result.stdout).success, true);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('project env modules reject symlink or junction escapes', (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-project-link-'));
  const cacheDir = path.join(dir, 'js_reverse_cache');
  const externalEnv = path.join(dir, 'external-env');
  const target = path.join(dir, 'target.js');
  fs.mkdirSync(cacheDir, { recursive: true });
  fs.mkdirSync(externalEnv, { recursive: true });
  fs.writeFileSync(path.join(externalEnv, 'custom.js'), 'window.linkEscapeExecuted = true;');
  fs.writeFileSync(target, "if (window.linkEscapeExecuted) throw new Error('linked module executed');");
  try {
    try {
      fs.symlinkSync(externalEnv, path.join(cacheDir, 'env'), process.platform === 'win32' ? 'junction' : 'dir');
    } catch (error) {
      if (['EPERM', 'EACCES', 'ENOTSUP'].includes(error.code)) {
        t.skip(`symlink/junction creation is unavailable: ${error.code}`);
        return;
      }
      throw error;
    }
    const result = spawnSync(
      process.execPath,
      [script, '--trusted-code', '--quiet', '--env', 'js_reverse_cache/env/custom.js', target],
      { cwd: dir, encoding: 'utf8' },
    );
    const output = JSON.parse(result.stdout);
    assert.notEqual(result.status, 0);
    assert.ok(output.moduleLoadErrors.some(
      error => error.module === 'js_reverse_cache/env/custom.js'
        && /symlink or junction|real path escapes/.test(error.error),
    ));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('selected env modules replace the monitored baseline', () => {
  const cases = [
    [['--env', 'bom/navigator-fingerprint.js'], "if (navigator.appName !== 'Netscape') throw new Error('navigator was not replaced');"],
    [['--env', 'bom/location-url-state.js'], "if (typeof location.assign !== 'function') throw new Error('location was not replaced');"],
    [['--env', 'bom/screen-fingerprint.js'], "if (!screen.orientation) throw new Error('screen was not replaced');"],
    [['--env', 'bom/web-storage.js'], "if (typeof localStorage.getItem !== 'function') throw new Error('storage was not replaced');"],
    [['--env', 'bom/location-url-state.js,bom/history-state.js'], "if (typeof history.pushState !== 'function') throw new Error('history was not replaced');"],
    [['--env', 'dom/event-constructors.js,dom/document-dom-runtime.js'], "if (typeof document.createElement !== 'function') throw new Error('document was not replaced');"],
  ];

  for (const [envArgs, source] of cases) {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-replace-'));
    const target = path.join(dir, 'target.js');
    fs.writeFileSync(target, source);
    try {
      const result = spawnSync(process.execPath, [script, '--trusted-code', '--quiet', ...envArgs, target], { encoding: 'utf8' });
      assert.equal(result.status, 0, `${envArgs.join(' ')}\n${result.stderr}`);
      assert.equal(JSON.parse(result.stdout).success, true);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  }
});

test('profile values survive baseline replacement and proxies are idempotent', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-profile-'));
  const target = path.join(dir, 'target.js');
  const profile = path.join(dir, 'profile.json');
  fs.writeFileSync(profile, JSON.stringify({ navigator: { userAgent: 'web-protocol-recovery-Test-UA' } }));
  fs.writeFileSync(target, `
    if (navigator.userAgent !== 'web-protocol-recovery-Test-UA') throw new Error('profile was ignored');
    if (watch(navigator, 'navigator') !== navigator) throw new Error('proxy was wrapped twice');
  `);
  try {
    const result = spawnSync(
      process.execPath,
      [script, '--trusted-code', '--quiet', '--profile-file', profile, '--env', 'bom/navigator-fingerprint.js', target],
      { encoding: 'utf8' },
    );
    assert.equal(result.status, 0, result.stderr);
    assert.equal(JSON.parse(result.stdout).success, true);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('proxy monitoring evaluates a getter exactly once', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-getter-'));
  const target = path.join(dir, 'target.js');
  fs.writeFileSync(target, `
    let reads = 0;
    const source = {};
    Object.defineProperty(source, 'value', { get() { reads += 1; return 7; } });
    const monitored = watch(source, 'source');
    if (monitored.value !== 7 || reads !== 1) throw new Error('getter evaluated more than once');
  `);
  try {
    const result = spawnSync(process.execPath, [script, '--trusted-code', '--quiet', target], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(JSON.parse(result.stdout).success, true);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('safefunction keeps native source outside reflectable function keys', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-native-shape-'));
  const target = path.join(dir, 'target.js');
  fs.writeFileSync(target, `
    function browserMethod(value) { return value; }
    const before = Reflect.ownKeys(browserMethod);
    safefunction(browserMethod);
    const after = Reflect.ownKeys(browserMethod);
    if (before.length !== after.length || before.some((key, index) => key !== after[index])) {
      throw new Error('safefunction added a reflectable own key');
    }
    if (after.some(key => typeof key === 'symbol')) throw new Error('safefunction leaked a symbol');
    if (Function.prototype.toString.call(browserMethod) !== 'function browserMethod() { [native code] }') {
      throw new Error('native source mismatch');
    }
  `);
  try {
    const result = spawnSync(process.execPath, [script, '--trusted-code', '--quiet', target], { encoding: 'utf8' });
    assert.equal(result.status, 0, `${result.stderr}\n${result.stdout}`);
    assert.equal(JSON.parse(result.stdout).success, true);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('web crypto uses real digest, signature verification, and entropy limits', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-crypto-'));
  const target = path.join(dir, 'target.js');
  fs.writeFileSync(target, `
    (async () => {
      const input = new Uint8Array([97, 98, 99]);
      const digestBuffer = await crypto.subtle.digest('SHA-256', input);
      if (!(digestBuffer instanceof ArrayBuffer)) throw new Error('digest returned a host-realm buffer');
      const digest = new Uint8Array(digestBuffer);
      const hex = Array.from(digest, value => value.toString(16).padStart(2, '0')).join('');
      if (hex !== 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad') {
        throw new Error('fake digest');
      }
      const key = await crypto.subtle.importKey('raw', new Uint8Array([1, 2, 3, 4]), { name: 'HMAC', hash: 'SHA-256' }, true, ['sign', 'verify']);
      if (!(key instanceof CryptoKey)) throw new Error('fake CryptoKey');
      if (key.constructor !== CryptoKey) throw new Error('CryptoKey constructor mismatch');
      if (!(key.algorithm instanceof Object)) throw new Error('CryptoKey algorithm is not local');
      if (!(key.usages instanceof Array)) throw new Error('CryptoKey usages are not local');
      if (!(crypto instanceof Crypto)) throw new Error('Crypto identity mismatch');
      if (!(crypto.subtle instanceof SubtleCrypto)) throw new Error('SubtleCrypto identity mismatch');
      if (Object.prototype.toString.call(crypto.subtle) !== '[object SubtleCrypto]') throw new Error('SubtleCrypto tag mismatch');
      if (Object.keys(crypto.subtle).length !== 0) throw new Error('SubtleCrypto methods must not be own properties');
      if (crypto.subtle.digest.name !== 'digest' || crypto.subtle.digest.length !== 2) throw new Error('digest method shape mismatch');
      if (crypto.getRandomValues.name !== 'getRandomValues' || crypto.getRandomValues.length !== 1) throw new Error('getRandomValues method shape mismatch');
      if (crypto.randomUUID.name !== 'randomUUID' || crypto.randomUUID.length !== 0) throw new Error('randomUUID method shape mismatch');
      const subtleGetter = Object.getOwnPropertyDescriptor(Crypto.prototype, 'subtle').get;
      if (subtleGetter.name !== 'get subtle' || subtleGetter.length !== 0) throw new Error('subtle getter shape mismatch');
      if (!Function.prototype.toString.call(crypto.subtle.digest).includes('[native code]')) throw new Error('SubtleCrypto method source leaked');
      let cryptoBrandRejections = 0;
      try { Object.getOwnPropertyDescriptor(Crypto.prototype, 'subtle').get.call({}); } catch (_) { cryptoBrandRejections += 1; }
      try { crypto.getRandomValues.call({}, new Uint8Array(1)); } catch (_) { cryptoBrandRejections += 1; }
      try { crypto.randomUUID.call({}); } catch (_) { cryptoBrandRejections += 1; }
      if (cryptoBrandRejections !== 3) throw new Error('Crypto accepted an invalid receiver');
      let detachedRejected = false;
      try { await crypto.subtle.digest.call({}, 'SHA-256', input); } catch (_) { detachedRejected = true; }
      if (!detachedRejected) throw new Error('detached SubtleCrypto method accepted an invalid receiver');
      const exported = await crypto.subtle.exportKey('raw', key);
      if (!(exported instanceof ArrayBuffer)) throw new Error('exportKey returned a host-realm buffer');
      const signature = await crypto.subtle.sign('HMAC', key, input);
      const valid = await crypto.subtle.verify('HMAC', key, signature, new Uint8Array([97, 98, 100]));
      if (valid) throw new Error('verification must fail for changed data');
      const pair = await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
      if (!(pair.publicKey instanceof CryptoKey) || !(pair.privateKey instanceof CryptoKey)) throw new Error('key pair was not localized');
      const pairSignature = await crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, pair.privateKey, input);
      if (!await crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }, pair.publicKey, pairSignature, input)) {
        throw new Error('localized key pair did not round-trip');
      }
      let quotaError = false;
      try { crypto.getRandomValues(new Uint8Array(65537)); } catch (error) { quotaError = error.name === 'QuotaExceededError'; }
      if (!quotaError) throw new Error('entropy quota was not enforced');
      let unsupportedError;
      try { await crypto.subtle.digest('web-protocol-recovery-UNSUPPORTED', input); } catch (error) { unsupportedError = error; }
      if (!(unsupportedError instanceof DOMException) || !(unsupportedError instanceof Error)) throw new Error('host rejection leaked realms');
      if (unsupportedError.constructor !== DOMException || unsupportedError.name !== 'NotSupportedError' || unsupportedError.code !== 9) throw new Error('DOMException identity mismatch');
      if (Object.keys(unsupportedError).length !== 0 || Object.hasOwn(unsupportedError, 'name') || Object.hasOwn(unsupportedError, 'message') || Object.hasOwn(unsupportedError, 'code')) {
        throw new Error('DOMException exposed own fields');
      }
      if (DOMException.NOT_SUPPORTED_ERR !== 9 || DOMException.prototype.NOT_SUPPORTED_ERR !== 9) throw new Error('DOMException constants missing');
    })()
  `);
  try {
    const result = spawnSync(
      process.execPath,
      [script, '--trusted-code', '--quiet', '--env', 'bom/web-crypto.js', target],
      { encoding: 'utf8' },
    );
    assert.equal(result.status, 0, `${result.stderr}\n${result.stdout}`);
    assert.equal(JSON.parse(result.stdout).success, true);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('diagnoser waits for host-backed WebCrypto until the configured deadline', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-slow-crypto-'));
  const target = path.join(dir, 'target.js');
  fs.writeFileSync(target, `
    (async () => {
      const material = await crypto.subtle.importKey('raw', new Uint8Array([1, 2, 3, 4]), 'PBKDF2', false, ['deriveBits']);
      const bits = await crypto.subtle.deriveBits({
        name: 'PBKDF2', hash: 'SHA-256', salt: new Uint8Array([5, 6, 7, 8]), iterations: 150000
      }, material, 256);
      if (!(bits instanceof ArrayBuffer) || bits.byteLength !== 32) throw new Error('PBKDF2 result mismatch');
    })()
  `);
  try {
    const result = spawnSync(
      process.execPath,
      [script, '--trusted-code', '--quiet', '--timeout', '5000', '--env', 'bom/web-crypto.js', target],
      { encoding: 'utf8' },
    );
    assert.equal(result.status, 0, `${result.stderr}\n${result.stdout}`);
    assert.equal(JSON.parse(result.stdout).success, true);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('diagnoser still bounds a promise that never settles', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-stalled-promise-'));
  const target = path.join(dir, 'target.js');
  fs.writeFileSync(target, 'new Promise(() => {})');
  try {
    const started = Date.now();
    const result = spawnSync(
      process.execPath,
      [script, '--trusted-code', '--quiet', '--timeout', '30', target],
      { encoding: 'utf8' },
    );
    assert.notEqual(result.status, 0);
    assert.ok(Date.now() - started < 2000);
    assert.match(JSON.parse(result.stdout).error, /timed out/i);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('diagnoser bounds detached host WebCrypto work with a process watchdog', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-detached-crypto-'));
  const target = path.join(dir, 'target.js');
  fs.writeFileSync(target, `
    crypto.subtle.importKey('raw', new Uint8Array([1, 2, 3, 4]), 'PBKDF2', false, ['deriveBits']).then(key =>
      crypto.subtle.deriveBits({
        name: 'PBKDF2', hash: 'SHA-256', salt: new Uint8Array([5, 6, 7, 8]), iterations: 50000000
      }, key, 256)
    );
  `);
  try {
    const started = Date.now();
    const result = spawnSync(
      process.execPath,
      [script, '--trusted-code', '--quiet', '--timeout', '150', '--env', 'bom/web-crypto.js', target],
      { encoding: 'utf8', env: { ...process.env, WPR_DIAGNOSE_INTERNAL_WORKER_TOKEN: 'inherited-stale-value' } },
    );
    assert.notEqual(result.status, 0);
    assert.ok(Date.now() - started < 2000);
    assert.match(JSON.parse(result.stdout).error, /timed out/i);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('monitor wrapping supports configurable getter-only roots', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-getter-root-'));
  const env = path.join(dir, 'getter-root.js');
  const target = path.join(dir, 'target.js');
  fs.writeFileSync(env, `
    Object.defineProperty(globalThis, 'navigator', {
      get() { return { marker: 'getter-root' }; },
      configurable: true,
      enumerable: true
    });
  `);
  fs.writeFileSync(target, `
    'use strict';
    const descriptor = Object.getOwnPropertyDescriptor(globalThis, 'navigator');
    if (typeof descriptor.get !== 'function' || descriptor.set !== undefined) throw new Error('getter descriptor was replaced');
    if (navigator.marker !== 'getter-root') throw new Error('getter root was not wrapped');
    try { globalThis.navigator = {}; } catch (_) {}
    const afterAssignment = Object.getOwnPropertyDescriptor(globalThis, 'navigator');
    if (typeof afterAssignment.get !== 'function' || afterAssignment.set !== undefined || navigator.marker !== 'getter-root') {
      throw new Error('getter-only assignment semantics changed');
    }
  `);
  try {
    const result = spawnSync(
      process.execPath,
      [script, '--trusted-code', '--quiet', '--env', env, target],
      { encoding: 'utf8' },
    );
    assert.equal(result.status, 0, `${result.stderr}\n${result.stdout}`);
    assert.equal(JSON.parse(result.stdout).success, true);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('web crypto rejection follows the active DOMException constructor', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-domexception-order-'));
  const target = path.join(dir, 'target.js');
  fs.writeFileSync(target, `
    (async () => {
      let rejection;
      try { await crypto.subtle.digest('web-protocol-recovery-UNSUPPORTED', new Uint8Array([1])); } catch (error) { rejection = error; }
      if (!(rejection instanceof DOMException) || rejection.constructor !== DOMException) throw new Error('stale DOMException constructor');
      if (rejection.name !== 'NotSupportedError' || rejection.code !== 9) throw new Error('DOMException fields changed');
    })()
  `);
  try {
    const result = spawnSync(
      process.execPath,
      [script, '--trusted-code', '--quiet', '--env', 'bom/web-crypto.js,dom/event-constructors.js,dom/document-dom-runtime.js', target],
      { encoding: 'utf8' },
    );
    assert.equal(result.status, 0, `${result.stderr}\n${result.stdout}`);
    assert.equal(JSON.parse(result.stdout).success, true);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('document runtime installs a browser-shaped DOMException without web crypto', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-document-domexception-'));
  const target = path.join(dir, 'target.js');
  fs.writeFileSync(target, `
    const error = new DOMException('missing', 'NotFoundError');
    if (!(error instanceof DOMException) || !(error instanceof Error) || error.code !== 8) throw new Error('DOMException identity mismatch');
    if (Object.keys(error).length !== 0 || Object.hasOwn(error, 'name') || Object.hasOwn(error, 'message') || Object.hasOwn(error, 'code')) {
      throw new Error('DOMException exposed own fields');
    }
    if (DOMException.NOT_FOUND_ERR !== 8 || DOMException.prototype.NOT_FOUND_ERR !== 8) throw new Error('DOMException constants missing');
  `);
  try {
    const result = spawnSync(
      process.execPath,
      [script, '--trusted-code', '--quiet', '--env', 'dom/event-constructors.js,dom/document-dom-runtime.js', target],
      { encoding: 'utf8' },
    );
    assert.equal(result.status, 0, `${result.stderr}\n${result.stdout}`);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('console output serializes BigInt values', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-bigint-log-'));
  const target = path.join(dir, 'target.js');
  fs.writeFileSync(target, 'console.log(1n, { nested: 2n });');
  try {
    const result = spawnSync(process.execPath, [script, '--trusted-code', '--quiet', target], { encoding: 'utf8' });
    assert.equal(result.status, 0, `${result.stderr}\n${result.stdout}`);
    assert.deepEqual(JSON.parse(result.stdout).consoleOutput, [['log', '1n', { nested: '2n' }]]);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('console output remains bounded and valid JSON', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-large-log-'));
  const target = path.join(dir, 'target.js');
  fs.writeFileSync(target, "console.log('x'.repeat(17 * 1024 * 1024));");
  try {
    const result = spawnSync(process.execPath, [script, '--trusted-code', '--quiet', target], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
    const output = JSON.parse(result.stdout);
    assert.equal(output.success, true);
    assert.match(output.consoleOutput[0][1], /\[truncated\]$/);
    assert.ok(result.stdout.length < 2 * 1024 * 1024);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('proxy monitoring preserves non-configurable property invariants', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-proxy-invariant-'));
  const target = path.join(dir, 'target.js');
  fs.writeFileSync(target, `
    const source = {};
    Object.defineProperty(source, '__isProxy__', { value: false, configurable: false, writable: false });
    if (watch(source, 'source').__isProxy__ !== false) throw new Error('proxy invariant changed');
  `);
  try {
    const result = spawnSync(process.execPath, [script, '--trusted-code', '--quiet', target], { encoding: 'utf8' });
    assert.equal(result.status, 0, `${result.stderr}\n${result.stdout}`);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('window globals do not fabricate crypto when the crypto module is absent', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vm-gap-no-fake-crypto-'));
  const target = path.join(dir, 'target.js');
  fs.writeFileSync(target, "if (typeof crypto !== 'undefined') throw new Error('fake crypto installed');");
  try {
    const result = spawnSync(
      process.execPath,
      [script, '--trusted-code', '--quiet', '--env', 'bom/window-global-apis.js', target],
      { encoding: 'utf8' },
    );
    assert.equal(result.status, 0, result.stderr);
    assert.equal(JSON.parse(result.stdout).success, true);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
