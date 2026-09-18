#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const vm = require("node:vm");
const { spawnSync } = require("node:child_process");

const sha256 = value => crypto.createHash("sha256").update(value).digest("hex");
let parser, traverse, t;
function loadBabel() {
  parser = require("@babel/parser");
  traverse = require("@babel/traverse").default;
  t = require("@babel/types");
}
function parse(source) {
  return parser.parse(source, { sourceType: "unambiguous", errorRecovery: false });
}
function literal(node) {
  if (t.isStringLiteral(node) || t.isNumericLiteral(node) || t.isBooleanLiteral(node)) return { value: node.value };
  if (t.isNullLiteral(node)) return { value: null };
  if (t.isUnaryExpression(node) && ["+", "-"].includes(node.operator) && t.isNumericLiteral(node.argument)) {
    return { value: node.operator === "-" ? -node.argument.value : node.argument.value };
  }
  return null;
}
function inside(p, root) {
  return p.node.start >= root.node.start && p.node.end <= root.node.end;
}
function selfAssigned(fn) {
  const binding = fn.scope.parent.getBinding(fn.node.id.name);
  return binding.constantViolations.length > 0 && binding.constantViolations.every(p => inside(p, fn));
}

function inspect(source, noRotation = false, selectors = {}) {
  const ast = parse(source);
  let program;
  traverse(ast, { Program(p) { program = p; p.stop(); } });
  const functions = [];
  program.traverse({
    FunctionDeclaration(p) {
      if (p.node.id) functions.push(p);
    }
  });
  const arrays = functions.filter(fn => {
    let found = false;
    fn.traverse({ ArrayExpression(p) {
      if (p.node.elements.length >= 16 && p.node.elements.filter(n => t.isStringLiteral(n)).length >= 16) found = true;
    } });
    return found && selfAssigned(fn);
  });
  let candidates = [];
  for (const decoder of functions.filter(selfAssigned)) {
    for (const array of arrays) {
      if (decoder === array) continue;
      const arrayBinding = array.scope.getBinding(array.node.id.name);
      let callsArray = false;
      let indexOffset = false;
      decoder.traverse({
        CallExpression(p) {
          if (p.get("callee").isIdentifier() && p.scope.getBinding(p.node.callee.name) === arrayBinding) callsArray = true;
        },
        AssignmentExpression(p) {
          const { left, right } = p.node;
          if (t.isIdentifier(left) && ((t.isBinaryExpression(right, { operator: "-" }) &&
              t.isIdentifier(right.left, { name: left.name }) && t.isNumericLiteral(right.right)) ||
              (p.node.operator === "-=" && t.isNumericLiteral(right)))) indexOffset = true;
        }
      });
      if (callsArray && indexOffset) candidates.push({ decoder, array });
    }
  }
  candidates = candidates.filter(({ decoder, array }) =>
    (!selectors.decoder || decoder.node.id.name === selectors.decoder) &&
    (!selectors.array || array.node.id.name === selectors.array));
  if (candidates.length !== 1) throw new Error(candidates.length ?
    "ambiguous decoder/array pairs: " + candidates.map(x => `${x.decoder.node.id.name}/${x.array.node.id.name}`).join(",") :
    selectors.decoder || selectors.array ? "selected decoder/array pair not found" : "unsupported decoder/array shape");
  const { decoder, array } = candidates[0];
  const rootBinding = decoder.scope.getBinding(decoder.node.id.name);
  const arrayBinding = array.scope.getBinding(array.node.id.name);

  function alias(binding, use, seen = new Set()) {
    if (!binding || seen.has(binding)) return false;
    if (binding === rootBinding) return true;
    if (!binding.constant || !binding.path.isVariableDeclarator()) return false;
    const init = binding.path.get("init");
    if (!init.isIdentifier() || binding.path.node.end > use.node.start) return false;
    seen.add(binding);
    return alias(init.scope.getBinding(init.node.name), init, seen);
  }

  const rotations = [];
  for (const statement of program.get("body").filter(p => p.isExpressionStatement())) {
    statement.traverse({ CallExpression(p) {
      if (!p.get("callee").isFunctionExpression() && !p.get("callee").isArrowFunctionExpression()) return;
      if (!p.get("arguments").some(arg => arg.isIdentifier() && arg.scope.getBinding(arg.node.name) === arrayBinding)) return;
      let loop = false, decoderRef = false;
      p.get("callee").traverse({
        Loop() { loop = true; },
        ReferencedIdentifier(ref) { if (alias(ref.scope.getBinding(ref.node.name), ref)) decoderRef = true; }
      });
      if (loop && decoderRef) rotations.push({ call: p, statement });
    } });
  }
  if (rotations.length > 1) throw new Error("ambiguous rotation IIFEs");
  if (!rotations.length && !noRotation) throw new Error("rotation not proved; use --no-rotation only after reviewing the initialization");
  if (rotations.length && noRotation) throw new Error("--no-rotation contradicts observed rotation");
  const rotation = rotations[0];
  const protectedPaths = [array, decoder, ...(rotation ? [rotation.call] : [])];

  const dependencies = new Map();
  for (const root of [array, decoder, ...(rotation ? [rotation.call] : [])]) {
    root.traverse({ ReferencedIdentifier(ref) {
      const binding = ref.scope.getBinding(ref.node.name);
      if (!binding || binding === rootBinding || binding === arrayBinding || inside(binding.path, root)) return;
      if (!binding.path.isVariableDeclarator() || binding.scope !== program.scope) throw new Error("unsupported bootstrap dependency: " + ref.node.name);
      const value = literal(binding.path.node.init);
      if (!value || binding.path.node.end > root.node.start ||
          binding.constantViolations.some(p => p.node.start < (rotation ? rotation.call.node.end : root.node.end))) {
        throw new Error("nonliteral or mutable bootstrap dependency: " + ref.node.name);
      }
      dependencies.set(ref.node.name, value.value);
    } });
  }
  const bootstrap = [...dependencies].map(([name, value]) => `var ${name}=${JSON.stringify(value)};`).join("\n") +
    "\n" + source.slice(array.node.start, array.node.end) + "\n" + source.slice(decoder.node.start, decoder.node.end) +
    (rotation ? "\n(" + source.slice(rotation.call.node.start, rotation.call.node.end) + ");" : "");
  const calls = [];
  const pairs = new Map();
  let protectedCalls = 0, unresolvedCalls = 0;
  program.traverse({ CallExpression(p) {
    if (!p.get("callee").isIdentifier() || !alias(p.scope.getBinding(p.node.callee.name), p)) return;
    if (protectedPaths.some(root => inside(p, root))) { protectedCalls++; return; }
    const args = p.node.arguments.map(literal);
    if (![1, 2].includes(args.length) || args.some(a => !a) || !Number.isSafeInteger(args[0].value) ||
        (args.length === 2 && typeof args[1].value !== "string")) { unresolvedCalls++; return; }
    const values = args.map(a => a.value);
    const key = JSON.stringify(values);
    pairs.set(key, values);
    calls.push({ start: p.node.start, end: p.node.end, key });
  } });
  if (!calls.length) throw new Error("no supported business decoder calls");
  if (pairs.size > 2000) throw new Error("call budget exceeded (2000 distinct inputs)");
  return {
    bootstrap, decoder: decoder.node.id.name, array: array.node.id.name,
    rotation: Boolean(rotation), calls, pairs: [...pairs], protectedCalls, unresolvedCalls,
    protectedRanges: protectedPaths.map(p => ({ start: p.node.start, end: p.node.end }))
  };
}

function decodeWorker(payload) {
  function batch(pairs) {
    const context = vm.createContext(Object.create(null), { codeGeneration: { strings: false, wasm: false } });
    vm.runInContext("globalThis.window=globalThis;globalThis.self=globalThis;", context, { timeout: 100 });
    vm.runInContext(payload.bootstrap, context, { timeout: 5000 });
    const results = new Map();
    for (const [key, args] of pairs) {
      const expression = `${payload.decoder}(...${JSON.stringify(args)})`;
      const value = vm.runInContext(expression, context, { timeout: 200 });
      if (typeof value !== "string" || value.length > 65536) throw new Error("decoder must return a bounded primitive string");
      results.set(key, value);
    }
    return results;
  }
  const first = batch(payload.pairs);
  const reverse = batch([...payload.pairs].reverse());
  for (const [key, value] of first) {
    if (reverse.get(key) !== value) throw new Error("decoder output depends on evaluation order: " + key);
  }
  return [...first];
}
function runWorker(plan) {
  const env = {};
  for (const name of ["SystemRoot", "WINDIR", "NODE_PATH"]) if (process.env[name]) env[name] = process.env[name];
  const result = spawnSync(process.execPath, ["--max-old-space-size=128", __filename, "--worker"], {
    input: JSON.stringify({ bootstrap: plan.bootstrap, decoder: plan.decoder, pairs: plan.pairs }),
    encoding: "utf8", timeout: 30000, maxBuffer: 2 * 1024 * 1024, windowsHide: true, env
  });
  if (result.error) throw new Error("bounded worker failed: " + result.error.code);
  let value;
  try { value = JSON.parse(result.stdout); } catch { throw new Error("invalid worker response"); }
  if (result.status !== 0 || value.error) throw new Error(value.error || "decoder worker failed");
  return new Map(value.values);
}
function transform(source, plan, values) {
  let output = source;
  for (const call of [...plan.calls].sort((a, b) => b.start - a.start)) {
    if (!values.has(call.key)) throw new Error("missing decoder value");
    const replacement = JSON.stringify(values.get(call.key)).replace(/\u2028/g, "\\u2028").replace(/\u2029/g, "\\u2029");
    output = output.slice(0, call.start) + replacement + output.slice(call.end);
  }
  parse(output);
  return output;
}
function validatePaths(input, outputs) {
  const key = p => process.platform === "win32" ? path.resolve(p).toLowerCase() : path.resolve(p);
  const keys = new Set([key(input)]);
  for (const p of outputs) {
    if (keys.has(key(p))) throw new Error("input/output paths must be disjoint");
    keys.add(key(p));
    if (fs.existsSync(p)) throw new Error("refusing to overwrite existing artifact: " + p);
  }
}
function publish(file, value) {
  const directory = path.dirname(path.resolve(file));
  fs.mkdirSync(directory, { recursive: true });
  const normalize = s => process.platform === "win32" ? s.toLowerCase() : s;
  if (normalize(fs.realpathSync.native(directory)) !== normalize(directory)) throw new Error("refusing output through a symlink/junction");
  fs.writeFileSync(file, value, { encoding: "utf8", flag: "wx" });
}
function parseArgs(argv) {
  const out = {};
  const flags = { "--execute-target-code": "execute", "--trusted": "trusted", "--no-rotation": "noRotation", "--self-test": "selfTest" };
  const values = { "-i": "input", "--input": "input", "-o": "output", "--output": "output", "--dump": "dump", "--report": "report", "--decoder": "decoder", "--array": "array" };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    const name = flags[arg] || values[arg];
    if (!name || out[name] !== undefined) throw new Error("unknown or duplicate argument: " + arg);
    if (flags[arg]) out[name] = true;
    else {
      if (!argv[i + 1] || argv[i + 1].startsWith("-")) throw new Error("missing value for " + arg);
      out[name] = argv[++i];
    }
  }
  return out;
}
function main(argv) {
  const args = parseArgs(argv);
  if (args.selfTest) return require("./string_table_recover.test.js").run();
  if (!args.input || !args.execute || !args.trusted) throw new Error("requires -i INPUT --execute-target-code --trusted after execution approval");
  const destinations = [args.output, args.dump, args.report].filter(Boolean);
  validatePaths(args.input, destinations);
  const bytes = fs.readFileSync(args.input);
  if (bytes.length > 2 * 1024 * 1024) throw new Error("input exceeds 2 MiB");
  const source = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  const report = { status: "failed", inputSha256: sha256(bytes), toolSha256: sha256(fs.readFileSync(__filename)),
    outputMode: "readable-only", semanticEquivalence: "not-proven", targetCodeExecuted: false };
  let phase = "inspect";
  try {
    loadBabel();
    const plan = inspect(source, args.noRotation, { decoder: args.decoder, array: args.array });
    phase = "execute";
    report.targetCodeExecuted = true;
    const values = runWorker(plan);
    phase = "reparse";
    const output = transform(source, plan, values);
    Object.assign(report, { status: "ok", parse: "ok", arrayFunction: plan.array, decoder: plan.decoder,
      rotationFound: plan.rotation, protectedCalls: plan.protectedCalls, unresolvedCalls: plan.unresolvedCalls,
      protectedRanges: plan.protectedRanges, pairs: plan.pairs.length, replaced: plan.calls.length,
      orderCheck: "forward-reverse-match", bootstrapSha256: sha256(plan.bootstrap), outputSha256: sha256(output) });
    phase = "publish";
    if (args.output) publish(args.output, output);
    if (args.dump) publish(args.dump, JSON.stringify({ format: "argument-array-key-v1", values: [...values] }, null, 2) + "\n");
  } catch (error) {
    report.status = "failed";
    report.phase = phase;
    report.error = String(error.message).slice(0, 500);
  }
  if (args.report) publish(args.report, JSON.stringify(report, null, 2) + "\n");
  console.log(JSON.stringify(report));
  return report.status === "ok" ? 0 : 4;
}
module.exports = { main, loadBabel, inspect, transform, runWorker, parseArgs, validatePaths, decodeWorker };
if (require.main === module) {
  if (process.argv.length === 3 && process.argv[2] === "--worker") {
    try {
      const input = fs.readFileSync(0, "utf8");
      if (input.length > 3 * 1024 * 1024) throw new Error("worker input too large");
      console.log(JSON.stringify({ values: decodeWorker(JSON.parse(input)) }));
    } catch (error) {
      console.log(JSON.stringify({ error: String(error.message).slice(0, 500) }));
      process.exitCode = 4;
    }
  } else {
    try { process.exitCode = main(process.argv.slice(2)); }
    catch (error) { console.error(String(error.message)); process.exitCode = 2; }
  }
}
