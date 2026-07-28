module.exports = {
  StringLiteral(path) {
    delete path.node.extra
  },
  NumericLiteral(path) {
    delete path.node.extra
  }
}
