# Delivery Templates

Use this reference after fixed-vector behavior is known and the Provider must package a stable local helper. Templates are skeletons for the task project, not proof that env-patch succeeded.

## Files

Copy only the needed skeletons from Provider-local `../templates/` into the approved project root:

1. `../templates/mod.js`: root environment installer.
2. `../templates/main.js`: callable JS entry that loads `mod.js` and prints JSON.
3. `../templates/main.py`: Python owner for live HTTP and JS helper execution.

Do not edit or execute templates inside the installed skill tree.

## Promotion Rules

1. Keep target scripts, fixture runners, browser evidence, and diagnosis output under `js_reverse_cache/`.
2. Keep root `mod.js` minimal: only verified stable env patches and profile handling.
3. Keep root `main.js` stdout JSON-only; diagnostics go to stderr or cache files.
4. Keep root `main.py` as the only live HTTP owner after web-protocol-recovery approves live replay.
5. Re-run fixed vectors after copying from cache to root files.

## Required Result Fields

Return these fields to web-protocol-recovery:

```text
artifact.mod=<path + sha256>
artifact.mainJs=<path + sha256>
artifact.mainPy=<path + sha256 when written>
acceptanceTest=<fixed vector or browser evidence name>
result=<pass|fail + first divergence>
runtime=<node version and modules used>
residualAssumptions=<bounded list>
```

If only a local proof was requested, omit `main.py` unless the work order explicitly asked for a Python replay skeleton.
