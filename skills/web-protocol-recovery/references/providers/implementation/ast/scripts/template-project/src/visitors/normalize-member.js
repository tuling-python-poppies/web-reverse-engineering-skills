const t = require('@babel/types')

function isIdentifierName(value) {
  return /^[A-Za-z_$][0-9A-Za-z_$]*$/.test(value)
}

module.exports = {
  MemberExpression(path) {
    if (!path.node.computed) return
    if (!t.isStringLiteral(path.node.property)) return
    if (!isIdentifierName(path.node.property.value)) return
    path.node.property = t.identifier(path.node.property.value)
    path.node.computed = false
  }
}
