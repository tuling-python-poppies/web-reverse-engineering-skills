# Hook Output Samples

Use these as target log shapes when generating one-off hook snippets.

## XHR Hook

```text
[XHR Hook] open: GET https://api.example.com/data?<redacted>
[XHR Hook] setRequestHeader: x-sign = <redacted len=16>
[XHR Hook] send: body=<redacted len=20>
[XHR Hook] readyState: 4, status: 200
  Response: <redacted len=128>
=== Call Stack ===
  at XMLHttpRequest.send (native)
  at api.fetchData (https://domain.com/static/app.chunk.js:2345:12)
  at App.componentDidMount (https://domain.com/static/main.bundle.js:890:5)
```

## Fetch Hook

```text
[Fetch Hook] Request: POST https://api.example.com/login
  Header names: ["content-type","x-token"]
  Body: <redacted len=52>
[Fetch Hook] Response from https://api.example.com/login
  Status: 200
  Header names: ["content-type"]
  Body: <redacted len=96>
=== Call Stack ===
  at fetch (native)
  at loginService.submit (https://domain.com/js/login.v3.js:456:8)
```

## Cookie Write Hook

```text
[Cookie Hook] SET cookie: acw_tc
  Value: <redacted len=64>
  Path: /, Domain: .example.com
=== Call Stack ===
  at Object.defineProperty (native)
  at setCookie (https://domain.com/static/challenge.js:123:5)
  at initProtection (https://domain.com/static/challenge.js:80:3)
```

## Storage Hook

```text
[Storage Hook] localStorage.setItem("token", <redacted>)
  Value length: 192
  Key preview: token
=== Call Stack ===
  at Storage.setItem (native)
  at saveSession (https://domain.com/js/auth.js:234:15)
```

## WebCrypto Hook

```text
[Crypto Hook] crypto.subtle.digest("SHA-256", ArrayBuffer[32])
  Algorithm: SHA-256
  Data length: 32 bytes
  Data: <redacted>
  Result type: ArrayBuffer
  Result length: 32 bytes
  Result: <redacted>
=== Call Stack ===
  at SubtleCrypto.digest (native)
  at signData (https://domain.com/static/crypto-utils.js:67:22)
  at buildRequest (https://domain.com/static/api.js:145:12)
```

## Canvas Fingerprint Hook

```text
[Canvas Hook] getContext("2d") called
  Width: 280, Height: 60
[Canvas Hook] fillText at (2, 20), textLength=31
[Canvas Hook] toDataURL called
  DataURL length: 12034 chars
  DataURL: <redacted>
```

## Event And Property Hooks

```text
[Event Hook] register target=document type=keydown capture=false
=== Call Stack ===
  at EventTarget.addEventListener (native)
  at installProtection (https://domain.com/static/challenge.js:80:3)

[Property Hook] set window._knownState type=object length=1
=== Call Stack ===
  at Object.<anonymous> (https://domain.com/static/challenge.js:123:5)
```

## Module And Timer Hooks

```text
[Webpack Hook] moduleId="12345" chunkIdCount=1
=== Call Stack ===
  at Array.push (native)
  at loadChunk (https://domain.com/static/runtime.js:45:9)

[Timer Hook] id=17 kind=interval delayType=number callbackType=function sourceLength=48
[Timer Cancel] id=17 kind=interval
```

## MessagePort Hook

```text
[MessagePort Hook] send type=challenge length=128
=== Call Stack ===
  at MessagePort.postMessage (native)
  at workerBridge.send (https://domain.com/static/bridge.js:55:7)
```

## Noise Control

High-frequency hooks should start with an explicit config:

```js
const HOOK_CONFIG = {
  FULL_LOG: false,
  MAX_BODY_LENGTH: 0,
  MAX_STACK_DEPTH: 5,
  MAX_HITS: 20,
  URL_FILTER: null,
  EVENT_FILTER: null,
  MODULE_FILTER: null,
  DUPLICATE_SUPPRESS: true,
};
```

## Request Binding Output

When the user asks which request carried a target field:

```text
[Request Binding] target=fetch, event=open, method=POST, url=/api/submit
  Hit fields: header x-sign, body.timestamp
[Request Binding] target=xhr, event=setRequestHeader, header=x-token
  Value: <redacted len=192>
  URL: /api/data/list?<redacted>
```
