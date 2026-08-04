# Provider Work Order

web-protocol-recovery owns the reverse task from intake through final acceptance. Internal providers never become a second task owner. They receive one bounded work order, produce evidence or code, clean up runtime resources they created, and return control to web-protocol-recovery.

## Schema

```json
{
  "schemaVersion": "web-protocol-recovery-provider-work-order",
  "workOrderId": "stable-id",
  "shape": "evidence",
  "gateFamily": "signer",
  "secondaryGates": [],
  "canonicalMutationPoint": "request query parameter: h5st",
  "activeProvider": {
    "id": "chromium-recon",
    "role": "reconnaissance",
    "strategy": null,
    "profile": null
  },
  "protocolOwner": null,
  "implementation": null,
  "deliveryProvider": null,
  "caseId": null,
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
    "actionApproval": "standing-read-only",
    "accountOrSessionUse": "none",
    "browserReconAllowed": true,
    "browserNavigationSideEffectsApproved": true,
    "liveReplayAllowed": true,
    "requestBudget": {"total": 10, "remaining": 10, "minDelayMs": 0, "concurrency": 1, "automaticObservationStopThreshold": 200, "observedAutomatic": {"total": 0, "byKind": {"redirect": 0, "subresource": 0, "xhrFetch": 0, "beaconPing": 0, "eventSource": 0, "websocket": 0}, "destinations": []}},
    "artifactPolicy": {
      "mode": "allowlisted-raw",
      "approvedRawFields": ["redacted-request", "source", "screenshot", "net-log"],
      "retentionDeadline": "task",
      "repositoryExcluded": true,
      "rawSecretHandling": "blocked"
    },
    "executionPolicy": {
      "targetCodeExecution": "blocked",
      "approvedCodeSha256": [],
      "dependencyInstall": "blocked",
      "approvedCommands": [],
      "approvalEvidence": "none",
      "approvalDeadline": null
    }
  },
  "project": {
    "projectRoot": "C:/absolute/project-root",
    "layout": "web-protocol-recovery-simple",
    "writeMode": "create-only",
    "allowedPaths": ["js_reverse_cache/recon/chrome/**"]
  },
  "readPlan": {
    "window": "handoff",
    "required": ["references/providers/reconnaissance/chromium-recon/PROVIDER.md"],
    "optional": []
  },
  "inputs": [],
  "requiredOutputs": ["one precise blocker or evidence"],
  "acceptanceTest": "return one bounded request/initiator evidence record",
  "runtimeCustody": {
    "providerOwnsBrowser": true,
    "providerOwnsWorker": false,
    "providerOwnsLease": false
  },
  "runtimeIds": []
}
```

The JSON block is illustrative; resolve `projectRoot` to the task's real absolute path before issuing it. Never send `cwd-default`, `none`, or another sentinel to a Provider. Generate the smallest `allowedPaths` for the active Provider and shape: the reconnaissance example above may write only its assigned Chrome cache path, not stable delivery files.

Standing approval (SKILL Non-Negotiables item 7) applies only inside the selected shape. For routine work, record `actionClass=read-only`, or `verifier-submit` only when a protocol-needed verifier round is the selected action; auto-record browser flags, `liveReplayAllowed=true`, one positive request budget, redacted/nonsecret cache artifact fields, supplied-session use, and the resolved absolute cwd when unset.

`actionApproval` states how that class was authorized and is bound to it in both directions: `read-only`/`none` pairs only with `standing-read-only`, `verifier-submit` only with `standing-verifier-submit` (or `user-confirmed-mutation` when the round also mutates business state), and `mutation-submit` only with `user-confirmed-mutation`. A routine order may not carry a mutation approval, and a mutating order may not understate itself as standing. Never auto-promote to `mutation-submit`, a larger shape/budget, raw-secret handling, or case writeback. Keep local target-code execution and dependency installation blocked until their exact `executionPolicy` confirmation.

A missing or non-exact scheme/host/port/absolute-route-prefix scope keeps live egress offline until the target is known. Canonicalize before comparison: lowercase scheme/host, convert host to IDNA ASCII, make the default port explicit, reject userinfo/fragments/control characters/backslashes/invalid or double encoding, reject encoded separators and any raw or once-decoded `.`/`..` segment, uppercase retained percent escapes, decode only RFC 3986 unreserved bytes, and match path prefixes on a segment boundary (`path == prefix` or `path` starts with `prefix + "/"`). Query authorization is separate from route scope.

Before every Provider-initiated navigation, HTTP/XHR/fetch request, retry, WebSocket handshake, or sent frame, require one matching scope entry and consume one unit immediately before egress. Categories are mutually exclusive: a retry is only `retry`, not also `request`; once consumed, an attempt is never refunded even when transport fails before response. Where interception exists, block out-of-scope automatic requests and redirects. A Chrome DevTools clean baseline requires exact top-level scope, one navigation unit, prior cumulative `observedAutomatic`, enabled browser flags, and `automaticObservationStopThreshold >= 1`; record every automatic destination and stop further actions when its top-level leaves scope or cumulative total reaches the threshold.

All budget and limit fields are integers: `total >= 0`, `0 <= remaining <= total`, `minDelayMs >= 0`, `concurrency >= 1`; threshold `0` denies Chrome baseline. The hub chooses `requestBudget.total` once before first egress. `total`, `remaining`, and `observedAutomatic` are shared task state: route handoffs cannot reset them, and neither hub nor Provider may replenish/increase `total` without `scope-expansion` confirmation. Providers enforce delay/concurrency before egress.

`writeMode=no-write` forbids all work-order writes. `create-only` permits only new files matching `allowedPaths`; `modify-allowlisted` permits new or existing files only at the exact allowlisted paths and never weakens the no-overwrite rules owned by project layout. Routine redacted/nonsecret cache writes may be recorded internally. `artifactPolicy.rawSecretHandling=confirmed` is required for raw-secret writes, alongside `raw-secret-handling` confirmation with exact fields, an absolute allowlisted path, repository exclusion, and a retention deadline. Operational configuration outside the project requires a separate exact-path confirmation and is reported as a side effect. A provider with `runtimeCustody.providerOwnsLease=true` may maintain only its documented PID/lease state under the verified external runtime root; it must clean that state on normal release and may not use it to persist unrelated configuration.

Stateful delivery templates that reserve budget across process launches carry `requestBudget.budgetLedgerId=sha256(workOrderId)` and the exact canonical `requestBudget.ledgerPath` `js_reverse_cache/private/gt4-ledgers/<budgetLedgerId>/ledger.sqlite3`. Its parent subtree is the one terminal `project.allowedPaths` `/**` entry and uses `modify-allowlisted`; it records reservations before egress and never refunds them. A later process must reopen the same ledger, not copy `requestBudget.remaining` into a new in-memory counter or choose a new ledger path.

Each scope carries its query authorization. `deny` rejects any query; `allow-listed` requires every decoded key in `allowedKeys` and, when a key appears in `allowedValues`, every decoded value in that key's approved list; `allow-all` requires explicit authorization and grants no new host, route, action, or budget. An omitted or malformed query policy fails closed.

Before executing target-supplied code, hash the exact reviewed bytes and require `targetCodeExecution=approved-reviewed-hash`, a matching `approvedCodeSha256`, unexpired approval evidence, and a declared `executionPolicy.sandbox` with a reviewed capability-denied adapter identity, adapter hash, and capability evidence. `node:vm` and a work-order supplied argv are not security boundaries. A template that has no bundled reviewed adapter must fail closed rather than invoke a user-declared command. Dependency installation requires `dependencyInstall=approved` and an exact command present in `approvedCommands`; package names alone are not approval.

## Result

```json
{
  "schemaVersion": "web-protocol-recovery-provider-result",
  "workOrderId": "stable-id",
  "provider": {
    "id": "chromium-recon",
    "role": "reconnaissance",
    "strategy": null,
    "profile": null
  },
  "protocolOwner": null,
  "shape": "evidence",
  "gateFamily": "signer",
  "status": "complete",
  "artifactBoundary": null,
  "artifacts": [],
  "verification": {"fixedVectorPass": true, "liveReplayPass": false, "semanticSuccess": true, "firstDivergence": null},
  "requestBudget": {"total": 10, "priorRemaining": 10, "consumed": 0, "remaining": 10, "byKind": {"navigation": 0, "request": 0, "retry": 0, "websocketHandshake": 0, "websocketFrame": 0}, "observedAutomatic": {"total": 0, "byKind": {"redirect": 0, "subresource": 0, "xhrFetch": 0, "beaconPing": 0, "eventSource": 0, "websocket": 0}, "destinations": []}, "minDelayMsApplied": 0, "maxConcurrencyObserved": 1},
  "execution": {"targetCodeExecution": "blocked", "executedCodeSha256": [], "installedCommands": []},
  "runtimeIds": [],
  "diagnostics": [],
  "sideEffects": [],
  "cleanup": {"complete": true, "remainingResources": []},
  "residualRisks": []
}
```

Every browser request, script, frame, target, worker, and WebSocket ID is an object with exact `resourceId`, `engine`, `contextId`, `targetId`, `navigationEpoch`, `owner`, and `lifecycle` (`live | stale | retained | released`) fields. Every result returns the final record for each incoming ID plus every ID created by the Provider. Identity fields never change; navigation, reload, engine switch, worker stop, lease release, or browser close makes affected IDs stale or released. A retained record also carries nonempty `retention.reason`, `retention.approvalEvidence`, and `retention.releaseDeadline`. Reject work orders/results that omit these fields for an ID; never invent defaults or reuse an ID across boundaries. Save durable redacted artifacts before cleanup.

One budget unit means one Provider-initiated outbound attempt reserved immediately before egress: navigation, initial HTTP/XHR/fetch request, retry attempt, WebSocket handshake, or sent frame. Categories are mutually exclusive and consumed units are never refunded. All `byKind`, `consumed`, and returned `remaining` values are non-negative integers. Budget accounting is conserved: `consumed = sum(byKind)`, `0 <= consumed <= prior remaining <= total`, returned `remaining = prior remaining - consumed`, and no Provider may increase `total`. Automatic observation accounting uses cumulative vectors: for every kind, `delta[kind] = returned.byKind[kind] - prior.byKind[kind] >= 0`; `returned.total = sum(returned.byKind) = prior.total + sum(delta)`; and canonical destination counts sum to `returned.total`. Destinations are bounded scheme/host/port/route/count records, and the Provider stops further actions once cumulative total reaches the threshold without claiming prevention. `minDelayMsApplied >= requested minDelayMs` and `maxConcurrencyObserved <= requested concurrency`. Executed hashes and install commands must be subsets of the approved execution policy. web-protocol-recovery rejects a result that omits or violates these equations.

For `status=complete`, no runtime ID may remain `live`, `cleanup.complete` is true, and `cleanup.remainingResources` equals exactly the IDs with approved `retained` lifecycle. Blocked/failed results still report all IDs and cleanup state; unapproved retained or live task-owned resources remain a blocker.

## Provider Rules

1. Read only the selected provider's `PROVIDER.md`, at most one matching case bundle, and at most one Provider-local reference; each remains subject to its separate read-budget window and the whole-task cap.
2. Do not load another provider implicitly. Return a precise blocker when another capability is required.
3. Do not create a project root, wrapper directory, or alternate cache.
4. Do not overwrite `main.py` or another provider's stable file unless the exact path is assigned.
5. Do not create `collector/`, `analysis/`, `input/`, `logs/`, provider-specific project roots, or any alternate layout; all writes stay inside `web-protocol-recovery-simple` assigned paths.
6. Keep raw secrets out of provider notes, tests, cases, and persistent browser memory.
7. web-protocol-recovery accepts or rejects the result against `acceptanceTest`; a provider's `complete` label is not sufficient.
