const parser = require('@babel/parser')
const traverse = require('@babel/traverse').default
const generator = require('@babel/generator').default

function parseCode(code) {
  const ast = parser.parse(code, {
    sourceType: 'unambiguous',
    errorRecovery: true,
    plugins: ['jsx']
  })
  if (ast.errors?.length) {
    const first = ast.errors[0]
    throw new SyntaxError(`Babel recovered ${ast.errors.length} parse error(s); refusing transform: ${first.message}`)
  }
  return ast
}

function generateCode(ast) {
  return generator(ast, {
    comments: false,
    jsescOption: { minimal: true }
  }).code
}

function reparse(ast) {
  return parseCode(generateCode(ast))
}

function applyVisitors(ast, visitors) {
  for (const visitor of visitors) {
    traverse(ast, visitor, undefined, {})
  }
  return ast
}

function countMatches(code, regex) {
  const matches = code.match(regex)
  return matches ? matches.length : 0
}

function detectFamily(code) {
  const ast = parseCode(code)
  const features = {
    hexIdentifiers: 0,
    debuggerStatements: 0,
    setIntervalCalls: 0,
    splitPipeCalls: 0,
    whileSwitchLoops: 0,
    dispatcherTables: 0,
    voidExpressions: 0,
    conditionalExpressions: 0,
    logicalAndExpressions: 0,
    jjencode: 0
  }

  traverse(ast, {
    Identifier(path) {
      if (/^_0x[0-9a-f]+$/i.test(path.node.name)) features.hexIdentifiers++
      if (path.node.name === '$___' || path.node.name.includes('$$$')) features.jjencode = 10
    },
    DebuggerStatement() {
      features.debuggerStatements++
    },
    CallExpression(path) {
      const callee = path.node.callee
      const isSetInterval =
        callee.type === 'Identifier' && callee.name === 'setInterval' ||
        callee.type === 'MemberExpression' && callee.property.type === 'Identifier' && callee.property.name === 'setInterval'
      if (isSetInterval) features.setIntervalCalls++
      if (
        callee.type === 'MemberExpression' &&
        callee.property.type === 'Identifier' &&
        callee.property.name === 'split' &&
        path.node.arguments.length === 1 &&
        path.node.arguments[0].type === 'StringLiteral' &&
        path.node.arguments[0].value === '|'
      ) {
        features.splitPipeCalls++
      }
    },
    WhileStatement(path) {
      const test = path.node.test
      const isForever =
        test.type === 'BooleanLiteral' && test.value === true ||
        test.type === 'UnaryExpression' && test.operator === '!' && test.argument.type === 'NumericLiteral' && test.argument.value === 0
      if (isForever && path.node.body.type === 'BlockStatement' && path.node.body.body.some((node) => node.type === 'SwitchStatement')) {
        features.whileSwitchLoops++
      }
    },
    VariableDeclarator(path) {
      if (path.node.init?.type !== 'ObjectExpression') return
      if (path.node.init.properties.some((property) =>
        property.type === 'ObjectProperty' &&
        (property.value.type === 'FunctionExpression' || property.value.type === 'ArrowFunctionExpression')
      )) {
        features.dispatcherTables++
      }
    },
    UnaryExpression(path) {
      if (path.node.operator === 'void') features.voidExpressions++
    },
    ConditionalExpression() {
      features.conditionalExpressions++
    },
    LogicalExpression(path) {
      if (path.node.operator === '&&') features.logicalAndExpressions++
    }
  })

  const hasHexFamily = features.hexIdentifiers >= 2
  const score = {
    sojson: Number(hasHexFamily) + Number(features.debuggerStatements > 0),
    sojsonv7: Number(hasHexFamily) + Number(features.setIntervalCalls > 0),
    obfuscator:
      Number(hasHexFamily) +
      Number(features.splitPipeCalls > 0) +
      Number(features.whileSwitchLoops > 0) +
      Number(features.dispatcherTables > 0),
    awsc:
      Number(features.voidExpressions > 0) +
      Number(features.conditionalExpressions > 0) +
      Number(features.logicalAndExpressions > 0),
    jjencode: features.jjencode
  }

  if (score.jjencode >= 10) return 'common'
  const matches = [
    ['obfuscator', score.obfuscator >= 2],
    ['sojsonv7', score.sojsonv7 >= 2],
    ['sojson', score.sojson >= 2],
    ['awsc', score.awsc >= 2]
  ].filter(([, matched]) => matched)
  if (matches.length === 1) return matches[0][0]
  return 'common'
}

module.exports = {
  applyVisitors,
  detectFamily,
  generateCode,
  parseCode,
  reparse
}
