# Report Template

Return a Kasada result in this shape. Keep values observed or unverified-labeled; no secrets, no full tokens.

```
kasada-result:
  evidenceSurfaces: [<x-kpsdk-* | KPSDK-bootstrap | double-UUID-path | /tl | KP_UIDz | cdndex-beacon>, ...]
  deploymentShape: <page-embedded-pjs | 429-interstitial | direct-ipsjs>
  scriptRoles:
    pjs: <path | absent>
    ipsjs: <path>            # sensor producer for /tl
  collector:
    scriptPath: /<uuid>/<uuid>/ips.js
    tlSubmission: <observed | reproduced>
  sandboxRun:
    bytecodeAssembled: <yes | no>
    anomalyBeacon: <none | reporting.cdndex.io fired>
    tlPosted: <yes | no>  bodyLen: <n | n/a>
  ctMint:
    value: <present | absent>   # do not paste the token
    signals: { reload: <t/f>, cr: <t/f>, st: <present/absent> }
    sessionBinding: { ip: <exit>, ua: <major>, tls: <profile> }
  cdStatus: <not-in-scope | open-blocker | reproduced-verified>   # per cd-open-problem.md
  business:
    endpoint: <method + path>
    result: <parsed-data | blocked>
    repeatedFreshSession: <yes | no>
  artifacts: [{ path: <projectRoot-relative>, sha256: <hash> }, ...]
  budget: { used: <n>, remaining: <n> }
  residualRisk: <egress-binding | version-rotation | cd-unsolved | none>
```

## Acceptance restatement

- Non-empty `ct` or a `/tl` `200` alone is not success.
- Success is a parsed business response on the same IP/UA/TLS session, repeated fresh.
- An unsolved `cd` is reported as `open-blocker`, never hidden or faked.
- Any recovered cipher/opcode/constant is version-locked; note the captured build.
