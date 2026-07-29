# Reproducible Evidence Playbook

Use this playbook when two runs reach different acceptance branches, when a result must be reviewable without exposing reusable state, or when a protocol claim needs a deterministic local proof.

## Core Rule

Normalize before comparing. Compare the complete ordered chain before tuning the final request.

A reusable proof package contains:

- ordered request and response steps
- duplicate headers in wire order
- method, URL structure, status, redirects, and state-write surfaces
- body lengths and SHA-256 values, never secret-bearing body bytes
- stable HMAC fingerprints for values that must remain correlatable
- one positive oracle and one decisive negative control

## Evidence Normalization

Run the normalizer only on an approved local capture path. Keep the HMAC key in an environment variable or file outside version control.

```text
python scripts/evidence_normalizer.py input.har output.json --project-root <project-root> --hmac-key-env WPR_EVIDENCE_HMAC_KEY
```

The input and output must stay under the approved project root; the output parent must already exist. The output uses `web-protocol-recovery-evidence/v1`. It preserves names, order, duplicate header positions, lengths, hashes, and state-write surfaces while replacing query values, variable path segments, non-structural header values, and state values with keyed fingerprints.

Do not publish the key or raw input. Store raw captures only in the approved private task namespace.

## First Divergence

Compare two normalized packages with:

```text
python scripts/transcript_diff.py accepted.json rejected.json --json
```

Start at the first reported difference. Inspect that writer and its first consumer before changing later signers, bodies, or verifier fields. A changed redirect, `Set-Cookie`, counter, storage write, or duplicate-header position can explain rejection even when the final body hash matches.

The diff tool prints fingerprints and structural descriptors, not raw changed values.

## Deterministic Practice

Use the local fixture to verify that a proposed implementation rejects plausible shortcuts:

```text
python scripts/practice_lab.py describe
python scripts/practice_lab.py --self-test
```

The fixture covers:

1. exact body bytes, duplicate-header order, and transport slot
2. same-session bootstrap binding
3. ordered response transforms
4. pagination route pivots
5. modified digest behavior
6. business-context activation and final identity reread
7. asynchronous export task isolation and field completeness

It performs no external network request. Passing only a positive path is insufficient; every case includes a negative control.

## Proof Record

Record:

```text
symptom:
decisiveEvidence:
firstDivergentStep:
writer:
firstConsumer:
positiveOracle:
negativeControl:
invariant:
failureBoundary:
artifactPathAndSha256:
```

## Completion Gate

The proof is complete only when:

1. normalized evidence contains no reusable secret value
2. ordered and duplicate fields remain distinguishable
3. the positive oracle passes from a clean local run
4. the negative control fails for the intended reason
5. the first divergence is named or explicitly remains unknown
6. strict preflight executes all bundled diagnostic self-tests
