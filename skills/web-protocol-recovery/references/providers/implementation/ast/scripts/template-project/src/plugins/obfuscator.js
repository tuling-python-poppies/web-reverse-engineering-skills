const { applyVisitors, reparse } = require('../lib/core')
const runCommon = require('./common')

const mergeObject = require('../visitors/merge-object')
const inlineDispatcher = require('../visitors/inline-dispatcher')
const whileSwitchUnpack = require('../visitors/while-switch-unpack')
const normalizeMember = require('../visitors/normalize-member')

module.exports = function runObfuscator(ast, options = {}) {
  const visitors = options.aggressive
    ? [mergeObject, inlineDispatcher, whileSwitchUnpack, normalizeMember]
    : [normalizeMember]
  applyVisitors(ast, visitors)
  return runCommon(reparse(ast))
}
