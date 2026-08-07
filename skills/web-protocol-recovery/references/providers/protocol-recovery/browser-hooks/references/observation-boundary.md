# Observation Boundary

Use this reference only when the work order already names a concrete hook target but the exact observation surface is still ambiguous. Canonical executable templates remain under `../scripts/`; topic-specific examples are indexed in `index.md`.

## Choose The Smallest Surface

1. Prefer the final observable boundary: URL-filtered `fetch`/XHR, one header setter, one cookie/storage key, one crypto API, one DOM/canvas/export boundary, one event registration, one known object property/method, one known module loader/chunk global, one dynamic-code boundary, or one message type.
2. Hook a wrapper such as `$.ajax`, SDK interceptors, Worker, `MessagePort`, `postMessage`, Blob/object URL, or timer APIs only when initiator evidence shows that wrapper owns the mutation or schedule.
3. Use page-main-world injection only when isolated-world globals differ from the target world. Otherwise return the Console/Snippets script.
4. Do not install broad `window`, `document`, `navigator`, all-XHR, all-fetch, or proxy-style probes to discover an unknown entry. Return to reconnaissance instead.

## Log Contract

Every log entry should identify the target and event before showing data:

```text
target=<fetch|xhr|cookie|storage|crypto|websocket|worker|messagePort|event|property|module>
event=<open|send|set-header|write|read|call|message|register|load>
method/url/key/api/field/moduleId=<bounded identifier when available>
value=<type + length + hash or redacted marker by default>
stack=<only when it answers the acceptance test>
```

Default to type, length, field names, hashes, and `<redacted>`. Full cookie, token, Authorization, request body, response body, ArrayBuffer, Blob, canvas/dataURL, or storage values require an explicit approved raw-field policy.

## Restore And Idempotence

1. Preserve original descriptors/functions before installing the hook.
2. Keep `this`, arguments, return values, thrown errors, and Promise behavior identical to the original call.
3. Install idempotently: refuse duplicate wrappers or require calling the named restore function first.
4. Expose exactly one restore function for the hook family, and remove task-owned hooks before returning `complete`.
5. If target code cached native references before injection, return a timing blocker instead of adding broader hooks.

## When To Stop

Return a blocker to web-protocol-recovery when:

1. the requested boundary is not yet known;
2. the hook changes request timing, signature output, verifier behavior, or page state;
3. integrity/native checks detect the hook;
4. only a sibling writer is observed and the canonical mutation point remains unknown;
5. the next step requires browser navigation, live replay, raw artifact save, mutation, or collection scale outside the work order.
