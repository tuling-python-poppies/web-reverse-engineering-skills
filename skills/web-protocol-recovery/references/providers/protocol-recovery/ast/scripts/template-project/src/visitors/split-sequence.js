const t = require('@babel/types')

function couldBecomeDirective(path, expression) {
  if (!t.isStringLiteral(expression) || path.key !== 0) return false
  if (path.parentPath.isProgram()) return true
  return path.parentPath.isBlockStatement() && path.parentPath.parentPath.isFunction()
}

module.exports = {
  ExpressionStatement(path) {
    if (!t.isSequenceExpression(path.node.expression)) return
    if (couldBecomeDirective(path, path.node.expression.expressions[0])) return
    path.replaceWithMultiple(path.node.expression.expressions.map((expr) => t.expressionStatement(expr)))
  }
}
