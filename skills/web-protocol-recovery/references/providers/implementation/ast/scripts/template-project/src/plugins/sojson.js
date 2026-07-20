const vm = require('vm')
const traverse = require('@babel/traverse').default
const generator = require('@babel/generator').default
const t = require('@babel/types')

const { reparse } = require('../lib/core')
const runCommon = require('./common')

function getDecryptFunctionName(statement) {
  if (t.isFunctionDeclaration(statement) && t.isIdentifier(statement.id)) {
    return statement.id.name
  }
  if (!t.isVariableDeclaration(statement) || statement.declarations.length !== 1) return null
  const declaration = statement.declarations[0]
  if (!t.isIdentifier(declaration.id)) return null
  if (t.isFunctionExpression(declaration.init) || t.isArrowFunctionExpression(declaration.init)) {
    return declaration.id.name
  }
  return null
}

function isPrimitive(value) {
  return value === null || ['string', 'number', 'boolean'].includes(typeof value)
}

function isBootstrapLike(statement) {
  if (t.isVariableDeclaration(statement) || t.isFunctionDeclaration(statement)) return true
  if (!t.isExpressionStatement(statement)) return false
  return (
    t.isCallExpression(statement.expression) ||
    t.isAssignmentExpression(statement.expression) ||
    t.isSequenceExpression(statement.expression)
  )
}

function getCandidateNames(statement) {
  const names = []
  if (t.isFunctionDeclaration(statement) && t.isIdentifier(statement.id)) {
    names.push(statement.id.name)
  }
  if (t.isVariableDeclaration(statement)) {
    for (const declaration of statement.declarations) {
      if (t.isIdentifier(declaration.id)) {
        names.push(declaration.id.name)
      }
    }
  }
  return names
}

function getMostLikelyDecryptName(ast, bootstrapEnd) {
  const candidates = []
  for (let index = 0; index <= bootstrapEnd; index += 1) {
    candidates.push(...getCandidateNames(ast.program.body[index]))
  }

  let best = null
  traverse(ast, {
    Program(path) {
      for (const name of candidates) {
        const binding = path.scope.getBinding(name)
        if (!binding || binding.referencePaths.length === 0) continue
        const callRefs = binding.referencePaths.filter((refPath) => refPath.parentPath.isCallExpression() && refPath.key === 'callee').length
        const memberRefs = binding.referencePaths.filter((refPath) => refPath.parentPath.isMemberExpression() && refPath.key === 'object').length
        const score = callRefs * 3 + memberRefs
        if (!best || score > best.score) {
          best = { name, score }
        }
      }
      path.stop()
    }
  })

  if (best && best.score > 0) return best.name
  return null
}

function getBootstrapInfo(ast) {
  const body = ast.program.body
  if (body.length < 3) return null

  const bootstrap = []
  let bootstrapEnd = -1

  for (let index = 0; index < Math.min(body.length, 8); index += 1) {
    const statement = body[index]
    if (!isBootstrapLike(statement)) break
    bootstrap.push(statement)
    bootstrapEnd = index

    const directName = getDecryptFunctionName(statement)
    if (directName) {
      const nextStatement = body[index + 1]
      if (!nextStatement || !t.isExpressionStatement(nextStatement)) {
        break
      }
    }
  }

  if (bootstrap.length < 2) return null

  let decryptName = null
  for (let index = 0; index <= bootstrapEnd; index += 1) {
    decryptName = getDecryptFunctionName(body[index]) || decryptName
  }
  decryptName = getMostLikelyDecryptName(ast, bootstrapEnd) || decryptName

  if (!decryptName) return null
  return { bootstrap, decryptName }
}

function createSandbox(bootstrapAst) {
  const code = generator({
    type: 'Program',
    sourceType: 'script',
    body: bootstrapAst
  }, {
    comments: false,
    jsescOption: { minimal: true }
  }).code

  const sandbox = {
    console: { log() {}, warn() {}, error() {}, info() {} },
    window: {},
    globalThis: {}
  }
  sandbox.window = sandbox
  sandbox.globalThis = sandbox
  vm.createContext(sandbox)
  vm.runInContext(code, sandbox, { timeout: 1000 })
  return sandbox
}

function restoreDecryptCalls(ast, decryptName, sandbox) {
  let decryptBinding = null
  traverse(ast, {
    Program(path) {
      decryptBinding = path.scope.getBinding(decryptName)
      path.stop()
    }
  })
  if (!decryptBinding) return

  traverse(ast, {
    CallExpression(path) {
      if (!t.isIdentifier(path.node.callee, { name: decryptName })) return
      if (path.scope.getBinding(decryptName) !== decryptBinding) return
      const evaluation = path.get('arguments').every((argPath) => argPath.evaluate().confident)
      if (!evaluation) return
      try {
        const expressionCode = generator(path.node, { comments: false, jsescOption: { minimal: true } }).code
        const value = vm.runInContext(expressionCode, sandbox, { timeout: 200 })
        if (isPrimitive(value)) {
          path.replaceWith(t.valueToNode(value))
        }
      } catch {}
    },
    MemberExpression(path) {
      if (!t.isIdentifier(path.node.object, { name: decryptName })) return
      if (path.scope.getBinding(decryptName) !== decryptBinding) return
      if (!path.node.computed) return
      if (!t.isStringLiteral(path.node.property) && !t.isNumericLiteral(path.node.property)) return
      try {
        const expressionCode = generator(path.node, { comments: false, jsescOption: { minimal: true } }).code
        const value = vm.runInContext(expressionCode, sandbox, { timeout: 200 })
        if (isPrimitive(value)) {
          path.replaceWith(t.valueToNode(value))
        }
      } catch {}
    }
  })
}

module.exports = function runSojson(ast, options = {}) {
  const info = getBootstrapInfo(ast)
  if (info && options.executeBootstrap && options.trustedBootstrap) {
    try {
      const sandbox = createSandbox(info.bootstrap)
      restoreDecryptCalls(ast, info.decryptName, sandbox)
    } catch {}
    ast = reparse(ast)
  }

  return runCommon(ast)
}
