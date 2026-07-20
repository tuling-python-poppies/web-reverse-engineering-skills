const t = require('@babel/types')

module.exports = {
  UnaryExpression(path) {
    if (path.node.operator !== 'void') return
    if (!path.parentPath.isExpressionStatement()) return
    if (t.isSequenceExpression(path.node.argument)) return
    const evaluation = path.get('argument').evaluate()
    if (evaluation.confident && typeof evaluation.value === 'string') return
    path.replaceWith(path.node.argument)
  }
}
