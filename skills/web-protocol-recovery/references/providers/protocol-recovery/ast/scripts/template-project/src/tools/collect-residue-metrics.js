const fs = require("fs");
const path = require("path");
const parser = require("@babel/parser");
const traverse = require("@babel/traverse").default;
const generator = require("@babel/generator").default;
const t = require("@babel/types");

function countMatches(text, regex) {
  const matches = text.match(regex);
  return matches ? matches.length : 0;
}

function parseText(text) {
  return parser.parse(text, {
    sourceType: "unambiguous",
    plugins: ["jsx"],
  });
}

function printNode(node) {
  return generator(node, {
    compact: true,
    comments: false,
    jsescOption: { minimal: true },
  }).code;
}

function isLiteralLike(node) {
  return (
    t.isStringLiteral(node) ||
    t.isNumericLiteral(node) ||
    t.isBooleanLiteral(node) ||
    t.isNullLiteral(node) ||
    t.isBigIntLiteral(node) ||
    t.isIdentifier(node, { name: "undefined" })
  );
}

function isOpcodeDiscriminant(node) {
  return t.isIdentifier(node) || t.isMemberExpression(node);
}

function getOpcodeIfDescriptor(node) {
  if (!t.isIfStatement(node) || node.alternate) return null;
  const test = node.test;
  if (!t.isBinaryExpression(test) || !["==", "===", "!=", "!=="].includes(test.operator)) {
    return null;
  }
  if (isLiteralLike(test.left) && isOpcodeDiscriminant(test.right)) {
    return { discriminantKey: printNode(test.right), literalKey: printNode(test.left) };
  }
  if (isLiteralLike(test.right) && isOpcodeDiscriminant(test.left)) {
    return { discriminantKey: printNode(test.left), literalKey: printNode(test.right) };
  }
  return null;
}

function countOpcodeIfChains(ast) {
  const statementLists = [];
  traverse(ast, {
    Program(path) {
      statementLists.push(path.node.body);
    },
    BlockStatement(path) {
      statementLists.push(path.node.body);
    },
    SwitchCase(path) {
      statementLists.push(path.node.consequent);
    },
  });

  let count = 0;
  statementLists.forEach((statements) => {
    for (let index = 0; index < statements.length; index += 1) {
      const first = getOpcodeIfDescriptor(statements[index]);
      if (!first) continue;
      const seenLiterals = new Set([first.literalKey]);
      let chainLength = 1;
      let cursor = index + 1;
      while (cursor < statements.length) {
        const next = getOpcodeIfDescriptor(statements[cursor]);
        if (!next || next.discriminantKey !== first.discriminantKey) break;
        seenLiterals.add(next.literalKey);
        chainLength += 1;
        cursor += 1;
      }
      if (chainLength >= 2 && seenLiterals.size >= 2) {
        count += chainLength;
        index = cursor - 1;
      }
    }
  });
  return count;
}

function getReturnArgument(fnNode) {
  if (t.isArrowFunctionExpression(fnNode) && !t.isBlockStatement(fnNode.body)) return fnNode.body;
  if (!t.isFunctionExpression(fnNode) && !t.isArrowFunctionExpression(fnNode)) return null;
  if (!t.isBlockStatement(fnNode.body) || fnNode.body.body.length !== 1) return null;
  const [statement] = fnNode.body.body;
  return t.isReturnStatement(statement) ? statement.argument : null;
}

function collectReferencedParameterNames(node) {
  const names = new Set();
  if (!node) return names;
  traverse(t.file(t.program([t.expressionStatement(t.cloneNode(node, true))])), {
    noScope: true,
    Identifier(path) {
      if (path.isReferencedIdentifier()) names.add(path.node.name);
    },
  });
  return names;
}

function isThinWrapperFunction(fnNode) {
  const returnArgument = getReturnArgument(fnNode);
  if (!returnArgument) return false;
  const paramNames = new Set(fnNode.params.filter((param) => t.isIdentifier(param)).map((param) => param.name));
  if (paramNames.size === 0) return false;
  const referencedNames = collectReferencedParameterNames(returnArgument);
  for (const name of referencedNames) {
    if (!paramNames.has(name)) return false;
  }
  if (t.isBinaryExpression(returnArgument) || t.isLogicalExpression(returnArgument)) return true;
  if (t.isUnaryExpression(returnArgument) && t.isIdentifier(returnArgument.argument)) return true;
  if (t.isCallExpression(returnArgument)) return t.isIdentifier(returnArgument.callee) || t.isMemberExpression(returnArgument.callee);
  return false;
}

function countDispatcherWrappers(ast) {
  let count = 0;
  traverse(ast, {
    ObjectExpression(path) {
      let thinWrapperCount = 0;
      let literalPropertyCount = 0;
      path.get("properties").forEach((propertyPath) => {
        if (!propertyPath.isObjectProperty()) return;
        const valuePath = propertyPath.get("value");
        if (valuePath.isStringLiteral() || valuePath.isNumericLiteral() || valuePath.isBooleanLiteral() || valuePath.isNullLiteral()) {
          literalPropertyCount += 1;
          return;
        }
        if (isThinWrapperFunction(valuePath.node)) thinWrapperCount += 1;
      });
      if (thinWrapperCount >= 2 || (thinWrapperCount >= 1 && literalPropertyCount >= 2)) {
        count += thinWrapperCount;
      }
    },
  });
  return count;
}

function collectMetrics(text) {
  let opcodeIfChainCount = countMatches(text, /if\s*\(\s*(?:0x[\da-f]+|\d+|["'][^"'\\]*(?:\\.[^"'\\]*)*["'])\s*={2,3}\s*[A-Za-z_$][\w$]*\s*\)/gi);
  let dispatcherWrapperCount = countMatches(text, /:\s*function\s*\([^)]*\)\s*\{\s*return\b/g);

  try {
    const ast = parseText(text);
    opcodeIfChainCount = countOpcodeIfChains(ast);
    dispatcherWrapperCount = countDispatcherWrappers(ast);
  } catch (error) {
    // Keep regex fallback for non-parseable files.
  }

  return {
    lineCount: text.split(/\r?\n/).length,
    splitPipeCount: countMatches(text, /\.split\(\s*["']\|["']\s*\)/g),
    loopSwitchCount: countMatches(text, /(?:while|for)\s*\([^)]*\)\s*\{[\s\S]{0,120}?switch\s*\(/g),
    opcodeIfChainCount,
    dispatcherWrapperCount,
    hexIdentifierCount: countMatches(text, /\b_0x[a-f0-9]+\b/gi),
  };
}

function collectMetricsFromFile(filePath) {
  const text = fs.readFileSync(filePath, "utf8");
  return {
    filePath: path.resolve(filePath),
    ...collectMetrics(text),
  };
}

function writeExclusive(outputPath, content) {
  const resolved = path.resolve(outputPath);
  const directory = path.dirname(resolved);
  const canonicalDirectory = fs.realpathSync.native(directory);
  const normalize = value => process.platform === "win32" ? value.toLowerCase() : value;
  if (normalize(canonicalDirectory) !== normalize(path.resolve(directory))) {
    throw new Error(`refusing output through a symlink or junction: ${directory}`);
  }
  const temporary = path.join(
    directory,
    `.${path.basename(resolved)}.${process.pid}.${process.hrtime.bigint()}.tmp`,
  );
  const sameFile = (left, right) => left.dev === right.dev && left.ino === right.ino;
  const unlinkIfSame = (file, expected) => {
    try {
      if (sameFile(fs.lstatSync(file), expected)) fs.unlinkSync(file);
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
    }
  };
  let descriptor;
  let temporaryIdentity;
  let published = false;
  try {
    descriptor = fs.openSync(temporary, "wx", 0o600);
    temporaryIdentity = fs.fstatSync(descriptor);
    if (normalize(path.dirname(fs.realpathSync.native(temporary))) !== normalize(canonicalDirectory)) {
      throw new Error(`temporary output escaped the approved directory: ${temporary}`);
    }
    fs.linkSync(temporary, resolved);
    const outputIdentity = fs.lstatSync(resolved);
    if (!sameFile(outputIdentity, temporaryIdentity) ||
        normalize(path.dirname(fs.realpathSync.native(resolved))) !== normalize(canonicalDirectory)) {
      throw new Error(`published output escaped the approved directory: ${resolved}`);
    }
    fs.writeFileSync(descriptor, content, "utf8");
    fs.fsyncSync(descriptor);
    if (!sameFile(fs.lstatSync(resolved), temporaryIdentity)) {
      throw new Error(`published output was replaced during write: ${resolved}`);
    }
    published = true;
  } finally {
    if (descriptor !== undefined) fs.closeSync(descriptor);
    if (!published && temporaryIdentity) unlinkIfSame(resolved, temporaryIdentity);
    if (temporaryIdentity) unlinkIfSame(temporary, temporaryIdentity);
  }
}

function main() {
  const [, , inputPath, outputPath = ""] = process.argv;
  if (!inputPath) {
    console.error("Usage: node src/tools/collect-residue-metrics.js <input.js> [output.json]");
    process.exit(1);
  }
  const result = collectMetricsFromFile(inputPath);
  const json = JSON.stringify(result, null, 2);
  if (outputPath) writeExclusive(outputPath, json);
  else process.stdout.write(`${json}\n`);
}

if (require.main === module) main();

module.exports = {
  collectMetrics,
  collectMetricsFromFile,
  writeExclusive,
};
