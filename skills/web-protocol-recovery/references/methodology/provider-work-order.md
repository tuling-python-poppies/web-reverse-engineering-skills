# Provider Work Order

web-protocol-recovery owns the reverse task from intake through final acceptance. Internal providers never become a second task owner. They receive one bounded work order, produce evidence or code, clean up runtime resources they created, and return control to web-protocol-recovery.

## Schema

```json
{
  "schemaVersion": "web-protocol-recovery-provider-work-order/v1",
  "workOrderId": "stable-id",
  "provider": "chromium-recon",
  "phase": "reconnaissance",
  "authorization": {
    "authorizationBasis": "public-unauthenticated",
    "allowedHostsAndRoutes": [
      {
        "scopeId": "primary",
        "scheme": "https",
        "host": "example.com",
        "port": 443,
        "routePrefix": "/api",
        "queryPolicy": {"mode": "deny", "allowedKeys": [], "allowedValues": {}}
      }
    ],
    "actionClass": "read-only",
    "accountOrSessionUse": "none",
    "browserReconAllowed": false,
    "browserNavigationSideEffectsApproved": false,
    "liveReplayAllowed": false,
    "requestBudget": {"total": 0, "remaining": 0, "minDelayMs": 0, "concurrency": 1, "automaticObservationStopThreshold": 0, "observedAutomatic": {"total": 0, "byKind": {"redirect": 0, "subresource": 0, "xhrFetch": 0, "beaconPing": 0, "eventSource": 0, "websocket": 0}, "destinations": []}},
    "artifactPolicy": {
      "mode": "metadata-only",
      "approvedRawFields": [],
      "retentionDeadline": "none",
      "repositoryExcluded": true
    },
    "executionPolicy": {
      "targetCodeExecution": "blocked",
      "approvedCodeSha256": [],
      "dependencyInstall": "blocked",
      "approvedCommands": [],
      "approvalEvidence": "none",
      "approvalDeadline": "none"
    }
  },
  "project": {
    "projectRoot": "none",
    "layout": "web-protocol-recovery-simple/v1",
    "writeMode": "no-write",
    "allowedPaths": []
  },
  "inputs": [],
  "requiredOutputs": ["one precise blocker or evidence"],
  "acceptanceTest": "return bounded offline evidence",
  "runtimeCustody": {
    "providerOwnsBrowser": false,
    "providerOwnsWorker": false,
    "providerOwnsLease": false
  },
  "runtimeIds": []
}
```

Unknown authorization, a non-exact scheme/host/port/absolute-route-prefix scope, an empty live-request budget, or an incomplete artifact policy keeps the provider offline. Canonicalize before comparison: lowercase scheme/host, convert host to IDNA ASCII, make the default port explicit, reject userinfo/fragments/control characters/backslashes/invalid or double encoding, reject encoded separators and any raw or once-decoded `.`/`..` segment, uppercase retained percent escapes, decode only RFC 3986 unreserved bytes, and match path prefixes on a segment boundary (`path == prefix` or `path` starts with `prefix + "/"`). Query authorization is separate from route scope. Before every Provider-initiated navigation, HTTP/XHR/fetch request, retry, WebSocket handshake, or sent frame, require one matching scope entry and consume one unit immediately before egress. Categories are mutually exclusive: a retry is only `retry`, not also `request`; once consumed, an attempt is never refunded even when transport fails before response. Where interception exists, block out-of-scope automatic requests and redirects. A Chrome DevTools clean baseline is the explicit exception and requires `browserNavigationSideEffectsApproved=true` plus `automaticObservationStopThreshold >= 1`: this separately authorizes the known inability to pre-intercept automatic browser traffic, not reuse of those destinations. Pre-authorize its exact top-level URL and one navigation unit, carry the prior cumulative `observedAutomatic` object into and out of every work order, record every automatic destination, and stop further actions when its top-level leaves scope or cumulative total reaches the threshold. Cached local reads and received responses/frames consume zero. All budget and limit fields are integers: `total >= 0`, `0 <= remaining <= total`, `minDelayMs >= 0`, `concurrency >= 1`; threshold `0` denies Chrome baseline. Providers enforce delay/concurrency before egress. `requestBudget.total`, `remaining`, and `observedAutomatic` are shared web-protocol-recovery state and cannot reset at handoff. `writeMode=no-write` forbids all work-order files. `cache-only` restricts writes to the listed `js_reverse_cache/` paths. Approved raw writes require exact fields, an absolute allowlisted path, repository exclusion, and a retention deadline. A provider may promote stable files outside the cache only when `writeMode=project` and the exact path is listed. Operational configuration outside the project is never implied by these modes: require a separate explicit confirmation for the exact path, perform it outside the provider work order, and report it as a side effect. A provider with `runtimeCustody.providerOwnsLease=true` may maintain only its documented PID/lease state under the verified external runtime root; it must clean that state on normal release and may not use it to persist unrelated configuration.

Each scope carries its query authorization. `deny` rejects any query; `allow-listed` requires every decoded key in `allowedKeys` and, when a key appears in `allowedValues`, every decoded value in that key's approved list; `allow-all` requires explicit authorization and grants no new host, route, action, or budget. An omitted or malformed query policy fails closed.

Before executing target-supplied code, hash the exact reviewed bytes and require `targetCodeExecution=approved-reviewed-hash`, a matching `approvedCodeSha256`, unexpired approval evidence, and a sandbox whose network/file/process capabilities are denied unless separately authorized. Dependency installation requires `dependencyInstall=approved` and an exact command present in `approvedCommands`; package names alone are not approval.

## Result

```json
{
  "schemaVersion": "web-protocol-recovery-provider-result/v1",
  "workOrderId": "stable-id",
  "provider": "chromium-recon",
  "status": "complete",
  "artifacts": [],
  "verification": {"test": "return bounded offline evidence", "passed": true, "evidence": "offline contract validated"},
  "requestBudget": {"consumed": 0, "remaining": 0, "byKind": {"navigation": 0, "request": 0, "retry": 0, "websocketHandshake": 0, "websocketFrame": 0}, "observedAutomatic": {"total": 0, "byKind": {"redirect": 0, "subresource": 0, "xhrFetch": 0, "beaconPing": 0, "eventSource": 0, "websocket": 0}, "destinations": []}, "minDelayMsApplied": 0, "maxConcurrencyObserved": 1},
  "execution": {"executedCodeSha256": [], "installedCommands": []},
  "runtimeIds": [],
  "diagnostics": [],
  "sideEffects": [],
  "cleanup": {"complete": true, "remainingResources": []},
  "residualRisks": []
}
```

Every browser request, script, frame, target, worker, and WebSocket ID is bound to the exact record fields `resourceId`, `engine`, `contextId`, `targetId`, `navigationEpoch`, `owner`, and `lifecycle` (`live | stale | retained | released`). Every result returns the final record for each incoming ID plus every ID created by the Provider. Identity fields never change; navigation, reload, engine switch, worker stop, lease release, or browser close makes affected IDs stale or released. A retained record also carries nonempty `retention.reason`, `retention.approvalEvidence`, and `retention.releaseDeadline`. Reject work orders/results that omit these fields for an ID; never invent defaults or reuse an ID across boundaries. Save durable redacted artifacts before cleanup.

One budget unit means one Provider-initiated outbound attempt reserved immediately before egress: navigation, initial HTTP/XHR/fetch request, retry attempt, WebSocket handshake, or sent frame. Categories are mutually exclusive and consumed units are never refunded. All `byKind`, `consumed`, and returned `remaining` values are non-negative integers. Budget accounting is conserved: `consumed = sum(byKind)`, `0 <= consumed <= prior remaining <= total`, returned `remaining = prior remaining - consumed`, and no Provider may increase `total`. Automatic observation accounting uses cumulative vectors: for every kind, `delta[kind] = returned.byKind[kind] - prior.byKind[kind] >= 0`; `returned.total = sum(returned.byKind) = prior.total + sum(delta)`; and canonical destination counts sum to `returned.total`. Destinations are bounded scheme/host/port/route/count records, and the Provider stops further actions once cumulative total reaches the threshold without claiming prevention. `minDelayMsApplied >= requested minDelayMs` and `maxConcurrencyObserved <= requested concurrency`. Executed hashes and install commands must be subsets of the approved execution policy. web-protocol-recovery rejects a result that omits or violates these equations.

For `status=complete`, no runtime ID may remain `live`, `cleanup.complete` is true, and `cleanup.remainingResources` equals exactly the IDs with approved `retained` lifecycle. Blocked/failed results still report all IDs and cleanup state; unapproved retained or live task-owned resources remain a blocker.

## Provider Rules

1. Read only the selected provider's `PROVIDER.md`, at most one matching case bundle, and at most one Provider-local reference; each remains subject to its separate read-budget window and the whole-task cap.
2. Do not load another provider implicitly. Return a precise blocker when another capability is required.
3. Do not create a project root, wrapper directory, or alternate cache.
4. Do not overwrite `main.py` or another provider's stable file unless the exact path is assigned.
5. Do not create `collector/`, `analysis/`, `input/`, `logs/`, provider-specific project roots, or any alternate layout; all writes stay inside `web-protocol-recovery-simple/v1` assigned paths.
6. Keep raw secrets out of provider notes, tests, cases, and persistent browser memory.
7. web-protocol-recovery accepts or rejects the result against `acceptanceTest`; a provider's `complete` label is not sufficient.
