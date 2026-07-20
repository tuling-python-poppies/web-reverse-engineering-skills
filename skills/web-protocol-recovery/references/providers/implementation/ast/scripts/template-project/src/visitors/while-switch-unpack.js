const t = require('@babel/types')

function isForeverLoop(test) {
  return (
    t.isBooleanLiteral(test, { value: true }) ||
    (t.isUnaryExpression(test, { operator: '!' }) && t.isNumericLiteral(test.argument, { value: 0 }))
  )
}

function getOrderFromInit(init) {
  if (
    t.isCallExpression(init) &&
    t.isMemberExpression(init.callee) &&
    t.isStringLiteral(init.callee.object) &&
    t.isIdentifier(init.callee.property, { name: 'split' }) &&
    init.arguments.length === 1 &&
    t.isStringLiteral(init.arguments[0], { value: '|' })
  ) {
    return init.callee.object.value.split('|')
  }

  if (t.isArrayExpression(init)) {
    const values = []
    for (const element of init.elements) {
      if (!element) return null
      if (!t.isStringLiteral(element) && !t.isNumericLiteral(element)) return null
      values.push(String(element.value))
    }
    return values
  }

  return null
}

function getCaseKey(test) {
  if (t.isStringLiteral(test) || t.isNumericLiteral(test)) {
    return String(test.value)
  }
  return null
}

function cloneStatements(statements) {
  return statements.map((statement) => t.cloneNode(statement, true))
}

function flattenCaseStatements(statements) {
  const flattened = []
  for (const statement of statements) {
    if (t.isBlockStatement(statement)) {
      flattened.push(...flattenCaseStatements(statement.body))
      continue
    }
    flattened.push(statement)
  }
  return flattened
}

function stripTrailingControl(statements) {
  const out = cloneStatements(flattenCaseStatements(statements))
  while (out.length) {
    const last = out[out.length - 1]
    if (t.isContinueStatement(last) || t.isBreakStatement(last)) {
      out.pop()
      continue
    }
    break
  }
  return out
}

function isSimpleIndexReference(node, indexName) {
  return t.isIdentifier(node, { name: indexName })
}

function getDiscriminantInfo(discriminant) {
  if (!t.isMemberExpression(discriminant) || !t.isIdentifier(discriminant.object)) {
    return null
  }

  const orderName = discriminant.object.name
  let indexName = null
  let updatesInline = false

  if (t.isUpdateExpression(discriminant.property) && t.isIdentifier(discriminant.property.argument)) {
    indexName = discriminant.property.argument.name
    updatesInline = true
  } else if (isSimpleIndexReference(discriminant.property, discriminant.property.name)) {
    indexName = discriminant.property.name
  }

  if (!indexName) return null
  return { orderName, indexName, updatesInline }
}

function removeBindingArtifacts(path, bindingName) {
  const binding = path.scope.getBinding(bindingName)
  if (!binding) return
  if (binding.path.isVariableDeclarator()) {
    const declaration = binding.path.parentPath
    if (declaration.node.declarations.length === 1) {
      declaration.remove()
    } else {
      binding.path.remove()
    }
    path.scope.crawl()
  }
}

function isInsidePath(path, ancestorPath) {
  return path === ancestorPath || Boolean(path.findParent((parent) => parent === ancestorPath))
}

function bindingOnlyUsedByLoop(binding, loopPath, extraPath = null) {
  return binding.referencePaths.every((referencePath) =>
    isInsidePath(referencePath, loopPath) || (extraPath && isInsidePath(referencePath, extraPath))
  )
}

function findStandaloneIndexUpdate(path, indexName) {
  const parentBody = path.parentPath
  if (!parentBody.isBlockStatement()) return null

  const siblings = parentBody.get('body')
  const selfIndex = siblings.findIndex((item) => item.node === path.node)
  if (selfIndex === -1 || selfIndex + 1 >= siblings.length) return null

  const next = siblings[selfIndex + 1]
  if (!next.isExpressionStatement()) return null
  const expr = next.node.expression
  if (!t.isUpdateExpression(expr)) return null
  if (!t.isIdentifier(expr.argument, { name: indexName })) return null
  return next
}

function buildCaseMap(cases) {
  const caseMap = new Map()
  let inheritedConsequent = null

  for (let index = cases.length - 1; index >= 0; index -= 1) {
    const switchCase = cases[index]
    const key = getCaseKey(switchCase.test)
    if (key === null) continue

    if (switchCase.consequent.length === 0 && inheritedConsequent) {
      caseMap.set(key, inheritedConsequent)
      continue
    }

    inheritedConsequent = switchCase
    caseMap.set(key, switchCase)
  }

  return caseMap
}

module.exports = {
  WhileStatement: {
    exit(path) {
      if (!isForeverLoop(path.node.test)) return

      const body = path.node.body
      if (!t.isBlockStatement(body) || body.body.length === 0) return

      const first = body.body[0]
      const second = body.body[1]
      if (!t.isSwitchStatement(first)) return
      if (body.body.length > 1 && second && !t.isBreakStatement(second)) return

      const discInfo = getDiscriminantInfo(first.discriminant)
      if (!discInfo) return

      const orderBinding = path.scope.getBinding(discInfo.orderName)
      if (!orderBinding || !orderBinding.path.isVariableDeclarator()) return

      const order = getOrderFromInit(orderBinding.path.node.init)
      if (!order || order.length === 0) return

      const caseMap = buildCaseMap(first.cases)

      const flattened = []
      for (const key of order) {
        const switchCase = caseMap.get(String(key))
        if (!switchCase) return

        const chunk = stripTrailingControl(switchCase.consequent)
        flattened.push(...chunk)

        const last = chunk[chunk.length - 1]
        if (last && (t.isReturnStatement(last) || t.isThrowStatement(last))) {
          break
        }
      }

      if (flattened.length === 0) return

      const standaloneIndexUpdate = !discInfo.updatesInline
        ? findStandaloneIndexUpdate(path, discInfo.indexName)
        : null

      const indexBinding = path.scope.getBinding(discInfo.indexName)
      if (!indexBinding || !bindingOnlyUsedByLoop(indexBinding, path, standaloneIndexUpdate)) return
      const removeOrderBinding = bindingOnlyUsedByLoop(orderBinding, path)

      if (standaloneIndexUpdate) {
        standaloneIndexUpdate.remove()
      }

      path.replaceWithMultiple(flattened)
      if (removeOrderBinding) removeBindingArtifacts(path, discInfo.orderName)
      removeBindingArtifacts(path, discInfo.indexName)
      path.scope.crawl()
    }
  }
}
