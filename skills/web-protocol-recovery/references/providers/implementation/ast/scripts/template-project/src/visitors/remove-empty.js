module.exports = {
  EmptyStatement(path) {
    if (!path.inList) return
    const isDirectiveContainer = path.parentPath.isProgram() ||
      (path.parentPath.isBlockStatement() && path.parentPath.parentPath.isFunction())
    if (!isDirectiveContainer) path.remove()
  }
}
