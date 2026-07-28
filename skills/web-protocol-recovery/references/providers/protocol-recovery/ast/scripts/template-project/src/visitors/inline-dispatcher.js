const t = require('@babel/types')

function getKey(node) {
  if (t.isIdentifier(node)) return node.name
  if (t.isStringLiteral(node)) return node.value
  return null
}

function clone(node) {
  return t.cloneNode(node, true)
}

function replaceParams(expression, params, args) {
  const map = new Map()
  params.forEach((param, index) => {
    if (t.isIdentifier(param) && args[index]) {
      map.set(param.name, clone(args[index]))
    }
  })

  function walk(node) {
    if (t.isIdentifier(node) && map.has(node.name)) {
      return clone(map.get(node.name))
    }
    if (Array.isArray(node)) {
      return node.map((item) => walk(item))
    }
    if (!node || typeof node !== 'object') {
      return node
    }
    const next = clone(node)
    for (const key of Object.keys(next)) {
      const value = next[key]
      if (value && typeof value === 'object') {
        next[key] = walk(value)
      }
    }
    return next
  }

  return walk(expression)
}

function getSimpleReturnExpression(value) {
  if (!t.isFunctionExpression(value) && !t.isArrowFunctionExpression(value)) return null
  if (!t.isBlockStatement(value.body) || value.body.body.length !== 1) return null
  const onlyStatement = value.body.body[0]
  if (!t.isReturnStatement(onlyStatement) || !onlyStatement.argument) return null
  return onlyStatement.argument
}

function isSimpleIdentifierList(params) {
  const names = new Set()
  for (const param of params) {
    if (!t.isIdentifier(param) || names.has(param.name)) return false
    names.add(param.name)
  }
  return true
}

function usesUnsafeNodes(expression) {
  let unsafe = false
  function scan(node) {
    if (!node || unsafe) return
    if (Array.isArray(node)) {
      node.forEach(scan)
      return
    }
    if (typeof node !== 'object') return
    if (
      t.isThisExpression(node) ||
      t.isSuper(node) ||
      t.isAssignmentExpression(node) ||
      t.isUpdateExpression(node) ||
      t.isAwaitExpression(node) ||
      t.isYieldExpression(node) ||
      t.isFunction(node) ||
      (t.isIdentifier(node, { name: 'arguments' }))
    ) {
      unsafe = true
      return
    }
    for (const key of Object.keys(node)) {
      scan(node[key])
    }
  }
  scan(expression)
  return unsafe
}

function buildSafeInlineExpression(value, args) {
  const returnExpr = getSimpleReturnExpression(value)
  if (!returnExpr) return null
  if (!isSimpleIdentifierList(value.params)) return null
  if (usesUnsafeNodes(returnExpr)) return null

  if (t.isBinaryExpression(returnExpr) || t.isLogicalExpression(returnExpr)) {
    return replaceParams(returnExpr, value.params, args)
  }

  if (t.isCallExpression(returnExpr) && t.isIdentifier(returnExpr.callee)) {
    return replaceParams(returnExpr, value.params, args)
  }

  if (
    t.isMemberExpression(returnExpr) &&
    t.isIdentifier(returnExpr.object) &&
    (t.isIdentifier(returnExpr.property) || t.isStringLiteral(returnExpr.property) || t.isNumericLiteral(returnExpr.property))
  ) {
    return replaceParams(returnExpr, value.params, args)
  }

  if (t.isConditionalExpression(returnExpr)) {
    return replaceParams(returnExpr, value.params, args)
  }

  return null
}

module.exports = {
  Program: {
    enter(path, state) {
      const dispatchTables = new Map()

      path.traverse({
        VariableDeclarator(innerPath) {
          const { id, init } = innerPath.node
          if (!t.isIdentifier(id) || !t.isObjectExpression(init)) return
          const binding = innerPath.scope.getBinding(id.name)
          if (!binding || !binding.constant) return

          const table = new Map()
          let valid = true
          for (const property of init.properties) {
            if (!t.isObjectProperty(property)) {
              valid = false
              break
            }
            const key = getKey(property.key)
            if (!key) {
              valid = false
              break
            }
            table.set(key, property.value)
          }
          if (valid && table.size > 0) {
            dispatchTables.set(id.name, table)
          }
        }
      })

      state.dispatchTables = dispatchTables
    }
  },

  MemberExpression(path, state) {
    if (!path.node.computed) return
    if (!t.isIdentifier(path.node.object)) return
    if (!t.isStringLiteral(path.node.property)) return

    const table = state.dispatchTables?.get(path.node.object.name)
    if (!table) return
    const value = table.get(path.node.property.value)
    if (!value) return

    if (t.isStringLiteral(value) || t.isNumericLiteral(value) || t.isBooleanLiteral(value) || t.isNullLiteral(value)) {
      path.replaceWith(clone(value))
    }
  },

  CallExpression(path, state) {
    const callee = path.node.callee
    if (!t.isMemberExpression(callee) || !callee.computed) return
    if (!t.isIdentifier(callee.object) || !t.isStringLiteral(callee.property)) return

    const table = state.dispatchTables?.get(callee.object.name)
    if (!table) return
    const value = table.get(callee.property.value)
    if (!value) return

    const replaced = buildSafeInlineExpression(value, path.node.arguments)
    if (!replaced) return
    path.replaceWith(replaced)
  }
}
