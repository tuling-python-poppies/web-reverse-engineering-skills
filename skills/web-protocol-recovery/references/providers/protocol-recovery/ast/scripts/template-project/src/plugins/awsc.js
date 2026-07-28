const { applyVisitors, reparse } = require('../lib/core')
const runCommon = require('./common')

const awscVoid = require('../visitors/awsc-void')
const awscLogicalToIf = require('../visitors/awsc-logical-to-if')
const awscConditionalToIf = require('../visitors/awsc-conditional-to-if')
const awscNormalizeBlocks = require('../visitors/awsc-normalize-blocks')

module.exports = function runAwsc(ast, options = {}) {
  const visitors = [
    awscVoid,
    awscConditionalToIf,
    awscLogicalToIf
  ]
  if (options.aggressive) visitors.push(awscNormalizeBlocks)
  applyVisitors(ast, visitors)
  return runCommon(reparse(ast))
}
