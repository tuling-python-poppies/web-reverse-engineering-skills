# Line-Ending Gate Status

This file records retained line-ending verification for the hash-bound
`web-protocol-recovery` surfaces. It is not a trigger benchmark acceptance
artifact.

## Repository Mechanism

- `.gitattributes` pins `skills/web-protocol-recovery` text surfaces to LF.
- `validate_architecture.py` reads raw bytes and fails on CRLF in checked text
  suffixes.
- `build_case_registry.py` writes `registry.json` with `newline="\n"`; this exact
  writer is covered by `test_eval_integrity.py`.

## Latest Clone Matrix

Run date: 2026-07-30, Windows local temp clones.

Run base: `28466cf863ea142f5c3f4f5047b7f330b0a36729`.

Command shape:

```cmd
git -c core.autocrlf=<mode> clone --no-hardlinks C:\Users\poppies\.agents <temp>
python -B <temp>\skills\web-protocol-recovery\scripts\verify_case_hashes.py
python -B <temp>\skills\web-protocol-recovery\scripts\preflight.py --strict
```

| `core.autocrlf` | `verify_case_hashes.py` | `preflight.py --strict` |
|---|---|---|
| `false` | `cases=22 checks_ok=247 mismatches=0`; `PASS` | `failures=0 warnings=0 legacy_warnings=0 strict=True`; `PASS` |
| `input` | `cases=22 checks_ok=247 mismatches=0`; `PASS` | `failures=0 warnings=0 legacy_warnings=0 strict=True`; `PASS` |
| `true` | `cases=22 checks_ok=247 mismatches=0`; `PASS` | `failures=0 warnings=0 legacy_warnings=0 strict=True`; `PASS` |

The matrix above verifies the line-ending mechanism at the recorded base commit.
After editing this status file, rerun `python -B scripts/preflight.py --strict` in
the skill root so the raw-byte line-ending scan also covers the new file.
