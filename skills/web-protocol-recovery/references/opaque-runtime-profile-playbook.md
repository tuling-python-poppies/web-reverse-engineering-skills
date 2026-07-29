# Opaque Runtime Profile Playbook

Use this playbook when an opaque signer, telemetry sidecar, verifier payload, or packed request is assembled through several runtime stages and complete captured input sets work while mixed fragments fail.

Do not route here merely because code is obfuscated. First prove the public input/output boundary, authoritative state write, or request egress.

## Delivery Classes

Report exactly one class:

| Class | Meaning | Required proof |
|---|---|---|
| `algorithmic` | current explicit inputs generate a fresh artifact without a captured final artifact or captured opaque profile | deterministic stage parity plus repeated fresh acceptance |
| `profile-driven` | recovered transforms run locally but require one complete captured runtime profile | atomic-profile selection, scope, freshness, and no-fragment-splice controls |
| `artifact-pool` | a previously accepted final artifact is selected | provenance, reuse/scope limits, exhaustion behavior, and a clear non-generation statement |

Browser-free and runtime-free are separate properties. Record both independently.

## Workflow

1. Freeze one coherent accepted run. Record asset hash, runtime version, route, request slot, session scope, moving-input policy, final artifact hash, and semantic acceptance anchor.
2. Prove the outer boundary: public helper input, wrapper return, state write, egress mutation, and final consumer. Stop if that boundary is sufficient.
3. When needed, trace stable stage boundaries such as dispatcher modes, serializers, packers, or transform tables. Avoid opcode-wide logging until a stage boundary is demonstrably insufficient.
4. Build a segment map from observed stage lengths, prefixes, delimiters, length fields, and framing. Keep unexplained bytes opaque.
5. Build one atomic profile. Preserve all correlated environment, config, opaque blocks, random policy, asset version, session scope, and expected artifact hash from the same run.
6. Port one transform at a time and fix the first divergent stage.
7. Run splice and tamper negative controls. Do not combine blocks from separate accepted runs unless a controlled test proves independence.
8. Separate deterministic proof inputs from live-generation inputs. Refresh only fields whose writers and variability are proven.
9. Test freshness, second-use behavior, session transfer, route scope, and the first business consumer.

## Stage Trace

Use this minimal shape:

```json
{
  "traceVersion": 1,
  "source": {"artifactSha256": "...", "runtime": "..."},
  "stages": [
    {
      "name": "normalize",
      "input": {"encoding": "base64", "data": "..."},
      "output": {"length": 96, "sha256": "..."}
    }
  ]
}
```

Compare traces with:

```text
python scripts/transform_trace_diff.py accepted-trace.json local-trace.json --json
```

Raw descriptors are allowed only in the approved private task namespace. Reviewable reports should use length and SHA-256 descriptors.

## Cross-Runtime Checks

Check these before compensating in a later stage:

- custom Base64 alphabet, padding, and byte-to-text conversion
- UTF-8 versus UTF-16 code units
- signed shifts, integer overflow, and endianness
- JavaScript number precision and rounding
- varint, TLV, compact JSON, and length prefixes
- key order and normalization
- returned transformed bytes versus mutated source arrays

## Completion Gate

Require the outer boundary, stable trace order, deterministic stage parity, final composition parity, negative controls, fresh semantic acceptance when approved, explicit scope, truthful delivery class, and final browser-free status. A high artifact-pool acceptance rate does not prove generation.
