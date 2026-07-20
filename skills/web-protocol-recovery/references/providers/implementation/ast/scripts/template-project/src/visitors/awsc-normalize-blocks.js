const t = require('@babel/types')

module.exports = {
  IfStatement(path) {
    if (!t.isBlockStatement(path.node.consequent)) {
      path.node.consequent = t.blockStatement([path.node.consequent])
    }
    if (path.node.alternate && !t.isBlockStatement(path.node.alternate) && !t.isIfStatement(path.node.alternate)) {
      path.node.alternate = t.blockStatement([path.node.alternate])
    }
  },
  BlockStatement(path) {
    const nextBody = []
    let changed = false
    for (const statement of path.node.body) {
      if (t.isBlockStatement(statement)) {
        changed = true
        nextBody.push(...statement.body)
      } else {
        nextBody.push(statement)
      }
    }
    if (changed) {
      path.node.body = nextBody
    }
  }
}
