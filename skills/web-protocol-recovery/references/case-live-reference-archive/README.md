# Case live-reference archive

Read-only historical implementations restored from Git commit `1e719718a25a52776b28518948715e6238576fe0` before the offline-only case rewrite.

`MANIFEST.json` is the machine-readable integrity boundary. It records every archive path, SHA-256, byte size, exact source commit, and reviewed sensitive literal. `scripts/gates/verify_case_hashes.py` requires disk/manifest parity, byte equality with the declared Git source blob, and explicit review of detected non-empty sensitive literals.

These files are study references only. They are not delivery code, not case entry points, and not active case assets. Read one only through a selected case's hash-bound `historicalReferences` after naming a concrete blocker. Never import or execute archive code, install its historical dependencies, copy it into delivery, or treat its former live result as current acceptance.

Active case entries remain offline-only. Final live egress belongs to a task project `main.py` through the `python-collector` delivery Provider under a validated work order.
