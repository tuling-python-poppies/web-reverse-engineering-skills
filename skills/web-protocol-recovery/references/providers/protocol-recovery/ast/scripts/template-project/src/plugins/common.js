const { applyVisitors } = require('../lib/core')

const deleteExtra = require('../visitors/delete-extra')
const foldBinary = require('../visitors/fold-binary')
const foldBoolean = require('../visitors/fold-boolean')
const mergeStrings = require('../visitors/merge-strings')
const normalizeMember = require('../visitors/normalize-member')
const splitSequence = require('../visitors/split-sequence')
const removeEmpty = require('../visitors/remove-empty')

module.exports = function runCommon(ast) {
  return applyVisitors(ast, [
    deleteExtra,
    foldBinary,
    foldBoolean,
    mergeStrings,
    normalizeMember,
    splitSequence,
    removeEmpty
  ])
}
