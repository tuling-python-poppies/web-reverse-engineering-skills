'use strict'

const { runStreamCodec } = require('./vm_codec')

const DEFAULT_STREAM_KEY = '3e627e1b4c63f913'

function encodeCompressed(compressed, streamKey = DEFAULT_STREAM_KEY) {
  if (typeof compressed !== 'string' || compressed.length === 0) {
    throw new TypeError('compressed must be a non-empty Base64 string')
  }
  if (!/^[0-9a-z]{16}$/.test(streamKey)) {
    throw new TypeError('streamKey must be 16 lowercase alphanumeric characters')
  }
  return runStreamCodec(compressed, streamKey)
}

module.exports = { DEFAULT_STREAM_KEY, encodeCompressed }

if (require.main === module) {
  let body = ''
  process.stdin.setEncoding('utf8')
  process.stdin.on('data', chunk => { body += chunk })
  process.stdin.on('end', () => {
    const request = JSON.parse(body)
    const output = encodeCompressed(request.input, request.key)
    process.stdout.write(JSON.stringify({ output }))
  })
}
