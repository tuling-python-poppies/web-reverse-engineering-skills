const t = require('@babel/types')

function getPropertyKey(node) {
  if (t.isIdentifier(node)) return node.name
  if (t.isStringLiteral(node)) return node.value
  return null
}

module.exports = {
  VariableDeclarator(path) {
    const { id, init } = path.node
    if (!t.isIdentifier(id) || !t.isObjectExpression(init)) return

    const binding = path.scope.getBinding(id.name)
    if (!binding) return

    const knownKeys = new Set()
    for (const property of init.properties) {
      if (!t.isObjectProperty(property)) continue
      const key = getPropertyKey(property.key)
      if (key) knownKeys.add(key)
    }

    const removable = []
    for (const refPath of binding.referencePaths) {
      if (refPath.node.start <= path.node.end) continue
      if (refPath.key !== 'object' || !refPath.parentPath.isMemberExpression()) continue

      const memberPath = refPath.parentPath
      if (memberPath.key !== 'left' || !memberPath.parentPath.isAssignmentExpression({ operator: '=' })) continue

      const propertyKey = getPropertyKey(memberPath.node.property)
      if (!propertyKey || knownKeys.has(propertyKey)) continue

      const assignmentPath = memberPath.parentPath
      init.properties.push(t.objectProperty(t.valueToNode(propertyKey), t.cloneNode(assignmentPath.node.right, true)))
      knownKeys.add(propertyKey)
      removable.push(assignmentPath.parentPath.isExpressionStatement() ? assignmentPath.parentPath : assignmentPath)
    }

    if (removable.length === 0) return

    for (const target of removable) {
      target.remove()
    }
    path.scope.crawl()
  }
}
