const t = require('@babel/types')

module.exports = {
  BinaryExpression: {
    exit(path) {
      if (path.node.operator !== '+') return
      if (!t.isStringLiteral(path.node.left) || !t.isStringLiteral(path.node.right)) return
      path.replaceWith(t.stringLiteral(path.node.left.value + path.node.right.value))
    }
  }
}
