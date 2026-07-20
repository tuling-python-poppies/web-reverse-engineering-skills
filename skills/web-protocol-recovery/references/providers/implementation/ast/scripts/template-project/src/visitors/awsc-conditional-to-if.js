const t = require('@babel/types')

module.exports = {
  ConditionalExpression(path) {
    if (!path.parentPath.isExpressionStatement()) return
    path.parentPath.replaceWith(
      t.ifStatement(
        path.node.test,
        t.blockStatement([t.expressionStatement(path.node.consequent)]),
        t.blockStatement([t.expressionStatement(path.node.alternate)])
      )
    )
  }
}
