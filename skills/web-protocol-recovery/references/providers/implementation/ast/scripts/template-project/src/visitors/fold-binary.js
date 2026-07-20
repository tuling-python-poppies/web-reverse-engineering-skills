const t = require('@babel/types')

const SAFE_OPERATORS = new Set([
  '+', '-', '*', '/', '%', '**',
  '|', '&', '^', '<<', '>>', '>>>',
  '==', '===', '!=', '!==', '<', '<=', '>', '>='
])

function isPrimitiveLiteral(node) {
  return t.isStringLiteral(node) ||
    t.isNumericLiteral(node) ||
    t.isBooleanLiteral(node) ||
    t.isNullLiteral(node)
}

module.exports = {
  BinaryExpression: {
    exit(path) {
      if (!SAFE_OPERATORS.has(path.node.operator)) return
      if (!isPrimitiveLiteral(path.node.left) || !isPrimitiveLiteral(path.node.right)) return
      const evaluation = path.evaluate()
      if (!evaluation.confident) return
      if (typeof evaluation.value === 'function') return
      if (typeof evaluation.value === 'number' && (!Number.isFinite(evaluation.value) || Object.is(evaluation.value, -0))) return
      path.replaceWith(t.valueToNode(evaluation.value))
    }
  }
}
