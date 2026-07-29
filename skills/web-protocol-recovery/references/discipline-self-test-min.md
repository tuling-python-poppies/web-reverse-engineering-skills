# Discipline Self-Test (Minimal)

Run these prompts (or mental checks) after skill edits that touch layout, gates, cases, or scaffold. Full suite: `official-self-test-task-suite.md`. Offline gate: `python scripts/preflight.py`.

| ID | Prompt / check | Must |
|---|---|---|
| D1 | First file write on a protocol task | Path under approved `projectRoot/js_reverse_cache/**` (or stable `main.py`/`utils/`) — never OS temp as primary |
| D2 | Scaffold with `--cache` only | No pre-created empty recon/source/ast/env/iv8/akamai/samples/private unless `--cache-namespace` named |
| D3 | iv8 delivery skeleton | `utils/iv8_silent.py` + `utils/logger.py`; progress via logger |
| D4 | Non-empty h5st/token but business 403 | Do not claim complete; prefer live bundle / env / cookie refresh diagnosis |
| D5 | Expired reese84 / browser_state | Fail closed with refresh path under `js_reverse_cache/private/` |
| D6 | Protocol task first reply | Four-line header (`shape`/`route`/`nextAsk`/`nextRead`) |
| D7 | chrome-devtools missing | Report missing paired-pass half; do not invent baseline proof |
| D8 | Case writeback commit | Prefer case+registry only; keep darwin `results.tsv` in separate chore when possible |
| D9 | After case file hash edit | `python scripts/preflight.py` exit 0; `--strict` fails only on remaining WARN/LEGACY_WARN |
| D10 | JD h5st frozen-only path | Documented as often 403 on recommend; live bundle is default |
| D11 | Historical case entry import | import of entry must not open network, mkdir, or start iv8; live path only under `main()`; alias/from-import requests and unguarded side-effect helpers must be caught by preflight AST scan; `--skip-tests` must still run `scripts/test_preflight.py` |
| D12 | River Security / 瑞数 first turn | `route:river-security` requires >=2 independent observed markers; alias tags do not count; a user guess or `412` alone never routes; River Security alone does not trigger Camoufox |
| D13 | Reese84 first turn | `route:reese84` requires one Reese84-native marker plus independent corroboration; generic Imperva/interstitial/error 15/incap cookie evidence stays evidence first; Reese84 alone does not trigger Camoufox |

Map recurring shortcuts to `references/anti-patterns-playbook.md` rather than inventing a new exception.
