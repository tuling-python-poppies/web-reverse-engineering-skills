# Report Template

```markdown
## Startup Gate
- Authorization/scope:
- Akamai evidence:
- Family (`_abck` / `bm_*` / mixed):
- Recon browser (Edge / Chrome / Camoufox):
- Local fingerprint source (host-captured / foreign rejected):
- Delivery intent:

## Recon
- Final page URL:
- Collector URL discovery rule:
- Pixel URL discovery rule:
- Sensor POST count and body-size sequence:
- Mutation initiator:
- Observer effect:

## Cookie Provenance
- Initial server seeds:
- Sensor stage transitions (`bm_s` / `_abck` rotate?):
- Pixel transition:
- Route-local transition:
- Final outbound authority:

## Transport
- curl_cffi profile:
- UA / Client Hints / sensor major:
- HTTP version:
- Proxy policy and exit IP:
- Reset/rate behavior:

## Business Contract
- Endpoint/method:
- Server context / CSRF / queue sources:
- Required headers:
- Query/body serialization vs browser success pack:
- Response envelope / parser output:

## Delivery
- Collector path:
- Dynamic cache path:
- Output path:
- Pure Python or Python + IV8:
- Browser dependency: none

## Verification
- Fresh successful runs:
- Multi-stage sensor checks:
- Host-local fingerprint checks:
- Unit/syntax tests:
- Known instability:
```
