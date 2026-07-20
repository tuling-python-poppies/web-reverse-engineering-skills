const assert = require('assert')
const fs = require('fs')
const os = require('os')
const path = require('path')
const { spawnSync } = require('child_process')
const vm = require('vm')

const core = require('../src/lib/core')
const runAwsc = require('../src/plugins/awsc')
const runCommon = require('../src/plugins/common')
const runObfuscator = require('../src/plugins/obfuscator')
const runSojson = require('../src/plugins/sojson')

function normalizeValue(value) {
  if (typeof value === 'number') {
    if (Number.isNaN(value)) return '<NaN>'
    if (Object.is(value, -0)) return '<-0>'
    if (!Number.isFinite(value)) return value > 0 ? '<Infinity>' : '<-Infinity>'
  }
  if (Array.isArray(value)) return Array.from(value, normalizeValue)
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, normalizeValue(value[key])]))
  }
  return value
}

function execute(code) {
  const trace = []
  const sandbox = {
    trace,
    console: { log: (...args) => trace.push(['log', ...args]) },
    registerHook: () => trace.push('registerHook'),
    sideEffect: () => trace.push('sideEffect'),
    standaloneEffect: () => trace.push('standaloneEffect'),
    use: value => trace.push(['use', value])
  }
  let completion
  let thrown = null
  try {
    completion = vm.runInNewContext(code, sandbox)
  } catch (error) {
    thrown = { name: error.name, message: error.message }
  }
  const globals = {}
  for (const key of ['count', 'done', 'result', 'shadow', 'strictThisKind', 'value']) {
    if (Object.prototype.hasOwnProperty.call(sandbox, key)) globals[key] = normalizeValue(sandbox[key])
  }
  return {
    completion: completion === undefined || ['string', 'number', 'boolean'].includes(typeof completion) ? completion : typeof completion,
    trace: normalizeValue(trace),
    globals,
    thrown
  }
}

function assertEquivalent(original, transformed) {
  assert.deepStrictEqual(execute(transformed), execute(original))
}

const obfuscatorCode = `
var _0xabc = ['0|1'];
var _0xdef = { 'call': function (fn, value) { return fn(value); } };
var _0x123 = '0|1'.split('|');
var _0x456 = 0;
while (true) {
  switch (_0x123[_0x456++]) {
    case '0': _0xdef['call'](console.log, 'ok'); continue;
    case '1': break;
  }
  break;
}`

const sojsonV7Code = `
var _0xabc = ['x'];
function _0xdef(index) { return _0xabc[index]; }
setInterval(function () {}, 1000);
console.log(_0xdef(0));`

assert.strictEqual(core.detectFamily(obfuscatorCode), 'obfuscator')
assert.strictEqual(core.detectFamily(sojsonV7Code), 'sojsonv7')
assert.strictEqual(core.detectFamily("const parts = 'a|b'.split('|')"), 'common')
assert.strictEqual(core.detectFamily('void 0; void 0; void 0; void 0; void 0; void 0;'), 'common')
assert.throws(() => core.parseCode('let duplicate; let duplicate;'))

const semanticCode = `
var externallyVisible = 1;
{ var blockGlobal = 2; }
function demo() {
  const unused = registerHook();
  const pureUnused = 3;
  const throwingUnused = 'x' in 0;
  const templateUnused = \`\${{ toString: function () { sideEffect(); return 'x'; } }}\`;
  const tdzSensitive = later;
  const later = 1;
  const result = void sideEffect();
  void standaloneEffect();
  return result + tdzSensitive;
}`
const commonOutput = core.generateCode(runCommon(core.parseCode(semanticCode)))
assert.match(commonOutput, /registerHook\(\)/)
assert.match(commonOutput, /pureUnused/)
assert.match(commonOutput, /const tdzSensitive = later/)
assert.match(commonOutput, /const result = void sideEffect\(\)/)
assert.match(commonOutput, /["']x["'] in 0/)
assert.match(commonOutput, /templateUnused/)

const directiveCode = `
function demo() {
  ("use strict", globalThis.strictThisKind = this === undefined ? "undefined" : "object");
}
demo();`
const directiveOutput = core.generateCode(runCommon(core.parseCode(directiveCode)))
assert.match(directiveOutput, /"use strict",/)
assertEquivalent(directiveCode, directiveOutput)

const emptyBeforeDirectiveCode = `
function demo() {
  ;
  ("use strict", globalThis.strictThisKind = this === undefined ? "undefined" : "object");
}
demo();`
const emptyBeforeDirectiveOutput = core.generateCode(runCommon(core.parseCode(emptyBeforeDirectiveCode)))
assert.match(emptyBeforeDirectiveOutput, /^\s*function demo\(\) \{\s*;/)
assertEquivalent(emptyBeforeDirectiveCode, emptyBeforeDirectiveOutput)

const emptyBodyCode = 'globalThis.count = 0; while (globalThis.count++ < 1); globalThis.done = true;'
const emptyBodyOutput = core.generateCode(runCommon(core.parseCode(emptyBodyCode)))
assert.match(emptyBodyOutput, /while/)
assertEquivalent(emptyBodyCode, emptyBodyOutput)

const directEvalCode = `
function reveal() {
  const hidden = 42;
  return eval('hidden');
}
globalThis.value = reveal();`
const directEvalOutput = core.generateCode(runCommon(core.parseCode(directEvalCode)))
assert.match(directEvalOutput, /const hidden = 42/)
assertEquivalent(directEvalCode, directEvalOutput)

const nonFiniteCode = 'globalThis.result = [1 / 0, 0 / 0, 0 / -1];'
const nonFiniteOutput = core.generateCode(runCommon(core.parseCode(nonFiniteCode)))
assert.match(nonFiniteOutput, /1 \/ 0/)
assert.match(nonFiniteOutput, /0 \/ 0/)
assert.match(nonFiniteOutput, /0 \/ -1/)
assertEquivalent(nonFiniteCode, nonFiniteOutput)

const awscCode = 'globalThis.result = void trace.push("x"); trace.push(String(globalThis.result));'
const awscOutput = core.generateCode(runAwsc(core.parseCode(awscCode)))
assert.match(awscOutput, /void trace\.push/)
assertEquivalent(awscCode, awscOutput)

const obfuscatorOutput = core.generateCode(runObfuscator(core.parseCode(obfuscatorCode)))
assert.match(obfuscatorOutput, /while \(true\)/)
assertEquivalent(obfuscatorCode, obfuscatorOutput)

const sojsonCode = `
var _0xarr = ['restored'];
function _0xdec(index) { return _0xarr[index]; }
function shadow() {
  function _0xdec() { return 'shadowed'; }
  return _0xdec(0);
}
globalThis.shadow = shadow();
globalThis.value = _0xdec(0);`
const conservativeSojsonOutput = core.generateCode(runSojson(core.parseCode(sojsonCode)))
assert.match(conservativeSojsonOutput, /globalThis\.value = _0xdec\(0\)/)
const trustedSojsonOutput = core.generateCode(runSojson(core.parseCode(sojsonCode), {
  executeBootstrap: true,
  trustedBootstrap: true
}))
assert.match(trustedSojsonOutput, /return _0xdec\(0\)/)
assert.match(trustedSojsonOutput, /globalThis\.value = ["']restored["']/)
assertEquivalent(sojsonCode, trustedSojsonOutput)

const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ast-deob-regression-'))
const inputFile = path.join(tempDir, 'input.js')
const outputFile = path.join(tempDir, 'output.js')
const mainScript = path.resolve(__dirname, '../src/main.js')

fs.writeFileSync(inputFile, 'console.log("review first");')
for (const args of [
  ['--execute-bootstrap']
]) {
  const run = spawnSync(process.execPath, [mainScript, ...args, '-i', inputFile, '-o', outputFile], { encoding: 'utf8' })
  assert.notStrictEqual(run.status, 0)
  assert.strictEqual(fs.existsSync(outputFile), false)
}

// --aggressive is gated but supported: it must run and unfold a dispatcher.
fs.writeFileSync(
  inputFile,
  "var _0x123 = '0|1'.split('|'); var _0x456 = 0; while (true) { switch (_0x123[_0x456++]) { case '0': console.log('a'); continue; case '1': console.log('b'); break; } break; }"
)
const aggressiveRun = spawnSync(process.execPath, [mainScript, '--aggressive', '-i', inputFile, '-o', outputFile], { encoding: 'utf8' })
assert.strictEqual(aggressiveRun.status, 0, aggressiveRun.stderr)
const aggressiveOutput = fs.readFileSync(outputFile, 'utf8')
assert.doesNotMatch(aggressiveOutput, /while\s*\(\s*true\s*\)/)
assert.match(aggressiveOutput, /console\.log\(["']a["']\)/)
fs.unlinkSync(outputFile)

fs.writeFileSync(inputFile, 'let duplicate; let duplicate;')
const invalidRun = spawnSync(process.execPath, [mainScript, '-i', inputFile, '-o', outputFile], { encoding: 'utf8' })
assert.notStrictEqual(invalidRun.status, 0)
assert.strictEqual(fs.existsSync(outputFile), false)

fs.writeFileSync(inputFile, 'globalThis.value = 1;')
const successfulRun = spawnSync(process.execPath, [mainScript, '-i', inputFile, '-o', outputFile], { encoding: 'utf8' })
assert.strictEqual(successfulRun.status, 0, successfulRun.stderr)
const firstOutput = fs.readFileSync(outputFile, 'utf8')
const overwriteRun = spawnSync(process.execPath, [mainScript, '-i', inputFile, '-o', outputFile], { encoding: 'utf8' })
assert.notStrictEqual(overwriteRun.status, 0)
assert.strictEqual(fs.readFileSync(outputFile, 'utf8'), firstOutput)

const samePathRun = spawnSync(process.execPath, [mainScript, '-i', inputFile, '-o', inputFile], { encoding: 'utf8' })
assert.notStrictEqual(samePathRun.status, 0)
assert.strictEqual(fs.readFileSync(inputFile, 'utf8'), 'globalThis.value = 1;')

const metricsScript = path.resolve(__dirname, '../src/tools/collect-residue-metrics.js')
const compareScript = path.resolve(__dirname, '../src/tools/compare-with-reference.js')
const metricsOutput = path.join(tempDir, 'metrics.json')
const compareOutput = path.join(tempDir, 'compare.json')
fs.writeFileSync(metricsOutput, 'metrics sentinel')
fs.writeFileSync(compareOutput, 'compare sentinel')

const metricsOverwriteRun = spawnSync(process.execPath, [metricsScript, inputFile, metricsOutput], { encoding: 'utf8' })
assert.notStrictEqual(metricsOverwriteRun.status, 0)
assert.strictEqual(fs.readFileSync(metricsOutput, 'utf8'), 'metrics sentinel')

const metricsSamePathRun = spawnSync(process.execPath, [metricsScript, inputFile, inputFile], { encoding: 'utf8' })
assert.notStrictEqual(metricsSamePathRun.status, 0)
assert.strictEqual(fs.readFileSync(inputFile, 'utf8'), 'globalThis.value = 1;')

const compareOverwriteRun = spawnSync(
  process.execPath,
  [compareScript, inputFile, inputFile, compareOutput, 'regression'],
  { encoding: 'utf8' }
)
assert.notStrictEqual(compareOverwriteRun.status, 0)
assert.strictEqual(fs.readFileSync(compareOutput, 'utf8'), 'compare sentinel')

const newMetricsOutput = path.join(tempDir, 'new-metrics.json')
const metricsRun = spawnSync(process.execPath, [metricsScript, inputFile, newMetricsOutput], { encoding: 'utf8' })
assert.strictEqual(metricsRun.status, 0, metricsRun.stderr)
assert.strictEqual(JSON.parse(fs.readFileSync(newMetricsOutput, 'utf8')).filePath, inputFile)

const outsideDirectory = path.join(tempDir, 'outside')
const aliasedDirectory = path.join(tempDir, 'approved-alias')
fs.mkdirSync(outsideDirectory)
if (process.platform === 'win32') {
  const junctionRun = spawnSync('cmd.exe', ['/c', 'mklink', '/J', aliasedDirectory, outsideDirectory], { encoding: 'utf8' })
  assert.strictEqual(junctionRun.status, 0, junctionRun.stderr || junctionRun.stdout)
} else {
  fs.symlinkSync(outsideDirectory, aliasedDirectory, 'dir')
}
const aliasOutput = path.join(aliasedDirectory, 'escaped.json')
const aliasRun = spawnSync(process.execPath, [metricsScript, inputFile, aliasOutput], { encoding: 'utf8' })
assert.notStrictEqual(aliasRun.status, 0)
assert.strictEqual(fs.existsSync(path.join(outsideDirectory, 'escaped.json')), false)
const aliasMainOutput = path.join(aliasedDirectory, 'escaped-main.js')
const aliasMainRun = spawnSync(process.execPath, [mainScript, '-i', inputFile, '-o', aliasMainOutput], { encoding: 'utf8' })
assert.notStrictEqual(aliasMainRun.status, 0)
assert.strictEqual(fs.existsSync(path.join(outsideDirectory, 'escaped-main.js')), false)

fs.rmSync(tempDir, { recursive: true, force: true })
console.log('WPR AST provider regressions ok')
