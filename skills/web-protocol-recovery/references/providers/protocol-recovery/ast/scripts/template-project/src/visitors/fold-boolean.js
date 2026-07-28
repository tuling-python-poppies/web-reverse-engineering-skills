const t = require('@babel/types')

module.exports = {
  UnaryExpression(path) {
    if (path.node.operator !== '!') return
    const arg = path.node.argument
    if (t.isArrayExpression(arg) && arg.elements.length === 0) {
      path.replaceWith(t.booleanLiteral(false))
      return
    }
    if (!t.isUnaryExpression(arg, { operator: '!' })) return
    const nested = arg.argument
    if (t.isArrayExpression(nested) && nested.elements.length === 0) {
      path.replaceWith(t.booleanLiteral(true))
    }
  }
}
