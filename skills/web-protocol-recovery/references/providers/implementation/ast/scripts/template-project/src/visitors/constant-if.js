const t = require('@babel/types')

function cloneStatements(statements) {
  return statements.map((statement) => t.cloneNode(statement, true))
}

function containsHoistedDeclaration(node, isRoot = true) {
  if (!node) return false
  if (t.isFunctionDeclaration(node) || t.isVariableDeclaration(node, { kind: 'var' })) return true
  if (!isRoot && t.isFunction(node)) return false
  const keys = t.VISITOR_KEYS[node.type] || []
  return keys.some((key) => {
    const child = node[key]
    if (Array.isArray(child)) return child.some((item) => containsHoistedDeclaration(item, false))
    return containsHoistedDeclaration(child, false)
  })
}

module.exports = {
  IfStatement(path) {
    const evaluation = path.get('test').evaluate()
    if (!evaluation.confident) return
    if (evaluation.value) {
      if (containsHoistedDeclaration(path.node.alternate)) return
      if (t.isBlockStatement(path.node.consequent)) {
        path.replaceWith(t.cloneNode(path.node.consequent, true))
      } else {
        path.replaceWith(path.node.consequent)
      }
      return
    }
    if (containsHoistedDeclaration(path.node.consequent)) return
    if (!path.node.alternate) {
      path.remove()
      return
    }
    if (t.isBlockStatement(path.node.alternate)) {
      path.replaceWith(t.cloneNode(path.node.alternate, true))
    } else {
      path.replaceWith(path.node.alternate)
    }
  }
}
