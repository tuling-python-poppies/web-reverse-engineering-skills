const t = require('@babel/types')

module.exports = {
  LogicalExpression(path) {
    if (path.node.operator !== '&&') return
    if (!path.parentPath.isExpressionStatement()) return
    path.parentPath.replaceWith(
      t.ifStatement(path.node.left, t.blockStatement([t.expressionStatement(path.node.right)]))
    )
  }
}
