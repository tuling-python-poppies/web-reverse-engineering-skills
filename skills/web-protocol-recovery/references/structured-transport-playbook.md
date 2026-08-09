# Structured Transport Playbook

Use this reference when:

- the target uses GraphQL instead of plain REST
- the business contract lives in WebSocket frames
- the request or response is gRPC / grpc-web framed
- the body or frame payload is protobuf, msgpack, or another binary envelope
- message IDs, operation names, channels, or opcodes matter as much as the visible business fields

## Core rule

Transport shape is part of the protocol contract.

## Working method

1. identify the transport kind:
   - GraphQL query or mutation
   - WebSocket request-response
   - WebSocket stream
   - gRPC or grpc-web framed body
   - protobuf or msgpack over HTTP
   - custom binary envelope
2. freeze one known-good request or frame sample
3. separate:
   - envelope fields
   - business fields
   - sequencing fields
   - signature or token fields
4. determine what the server assigns versus what the client must rebuild
5. replay one stable sample locally before scaling to streams or pagination

## GraphQL notes

- compare `operationName`, `variables`, and persisted-query hashes
- watch for wrapper headers or origin checks
- confirm whether the query text, hash, or both are required

## WebSocket notes

- fingerprint message types before reading individual frames
- identify auth frames, subscribe frames, heartbeat frames, and business frames
- preserve ordering when the server expects a warm-up sequence

## Binary envelope notes

- freeze raw bytes
- identify field boundaries or parser functions
- confirm whether compression happens before structured decode

## gRPC and grpc-web framing

Treat each message frame as a wire contract:

1. byte 0 is the frame flag
2. bytes 1 through 4 are an unsigned big-endian payload length
3. the next `length` bytes are exactly one message payload
4. repeat until the body or stream is exhausted

Do not treat every nonzero flag as `zlib`. Resolve `grpc-encoding` or the active grpc-web contract from headers and runtime evidence. For grpc-web, distinguish data frames from trailer frames, preserve the transport encoding (`application/grpc-web+proto` versus text/Base64), and parse every frame rather than only the first payload.

Verification gates:

- reject truncated five-byte headers and payload lengths beyond the available bytes
- prove single-frame and multi-frame parsing with fixed bytes
- retain unknown protobuf fields or raw payload bytes when the schema is incomplete
- compare decoded messages and re-encoded frame bytes separately
- use a negative control with a tampered length, flag, or trailer boundary
- do not call HTTP `200` or `grpc-status: 0` sufficient until the intended business message is decoded and consumed

Use `scripts/grpc_frame_inspector.py` for a bounded structural check. By default it emits only flags, kind, length, and offset; it does not print payload bytes, choose a compression codec, or decode protobuf fields. Payload SHA-256 is disabled by default. Enable `--include-payload-sha256` only for task-local correlation, because stable hashes of sensitive payloads are unsafe to publish.

If compression, encryption, or signing wraps the protobuf payload, record the exact order. A common shape is frame parse -> decompress -> protobuf, but captured bytes and the active parser remain authoritative.

## Protobuf payload decode

Once one payload's exact bytes are frozen, decode fields in this preference order:

1. **`protoc --decode_raw`** (schema-free) when `protoc` is on PATH. Best structural output, no `.proto` needed. Feed it the exact payload bytes on stdin.
2. **`protoc --decode <Message>` or the `protobuf` Python package** when a `.proto` or FileDescriptorSet is available. This is the only path that yields real field names and typed values; use it whenever the schema can be recovered from the bundle, a descriptor set, or grpc reflection.
3. **`scripts/protobuf_inspect.py`** as the portable fallback that always runs offline. It emits field number, wire type, and a best-effort value (varint / i32 / i64 hex / string / bytes / nested message) and never invents field names.

Wire-type reminder for manual reads: `0` varint, `1` 64-bit, `2` length-delimited (string / bytes / nested message / packed), `5` 32-bit. A length-delimited field is ambiguous; try nested-message decode first, then UTF-8 string, then keep raw bytes.

Verification gates:

- when the schema is unknown or partial, keep unknown fields and raw length-delimited bytes rather than discarding them
- decode the message and re-encode it separately; compare both against captured bytes, because a lossy raw view can still round-trip wrong
- prove single-field and nested-message decode with fixed bytes, plus one negative control (truncated varint or a length that overruns the buffer)
- do not treat a successful raw decode as semantic success until the intended business field is located and consumed

## Acceptable handoff

The final collector must still be local protocol code:

- HTTP plus GraphQL body
- WebSocket client plus local frame builder or parser
- Python plus local gRPC/grpc-web frame parser, protobuf decoder, or msgpack decoder
