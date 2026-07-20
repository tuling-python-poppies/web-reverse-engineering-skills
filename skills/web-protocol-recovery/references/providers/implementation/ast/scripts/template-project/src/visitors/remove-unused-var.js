const t = require('@babel/types')

function isSafeUnusedInitializer(node) {
  if (!node) return true
  if (
    t.isStringLiteral(node) ||
    t.isNumericLiteral(node) ||
    t.isBooleanLiteral(node) ||
    t.isNullLiteral(node) ||
    t.isBigIntLiteral(node) ||
    t.isRegExpLiteral(node) ||
    t.isFunctionExpression(node) ||
    t.isArrowFunctionExpression(node)
  ) {
    return true
  }
  if (t.isUnaryExpression(node)) {
    return ['!', 'void', 'typeof'].includes(node.operator) && isSafeUnusedInitializer(node.argument)
  }
  if (t.isTemplateLiteral(node)) {
    return node.expressions.length === 0
  }
  if (t.isArrayExpression(node)) {
    return node.elements.every((element) => element === null || (!t.isSpreadElement(element) && isSafeUnusedInitializer(element)))
  }
  if (t.isObjectExpression(node)) {
    return node.properties.every((property) =>
      t.isObjectProperty(property) && !property.computed && isSafeUnusedInitializer(property.value)
    )
  }
  return false
}

module.exports = {
  VariableDeclarator(path) {
    if (!t.isIdentifier(path.node.id)) return
    const binding = path.scope.getBinding(path.node.id.name)
    if (!binding || binding.referenced || !binding.constant) return
    if (binding.scope.path.isProgram()) return
    const declaration = path.parentPath
    const parent = declaration.parentPath
    if (parent.isProgram()) return
    if (!isSafeUnusedInitializer(path.node.init)) return
    if (t.isForInStatement(parent?.node) || t.isForOfStatement(parent?.node)) return
    if (declaration.node.declarations.length === 1) {
      declaration.remove()
      declaration.scope.crawl()
      return
    }
    path.remove()
    path.scope.crawl()
  }
}
