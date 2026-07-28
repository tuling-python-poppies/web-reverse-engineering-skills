# River Security Provider

## Select When

- Evidence contains at least two independent observed River Security markers: HTTP `412`, `$_ts.nsd` / `$_ts.cd`, `<script r="m">`, dynamic `_$...()` entry, generated `*T` cookie paired with server `*S`, protected XHR URL/header mutation, or a River Security / RuiShu protection script.
- The task is a challenge-gated Web flow where challenge JavaScript derives replay state such as cookies, URL suffixes, headers, or form admission state.
- A registry case or current artifacts prove a River Security subtype and the next step is subtype classification, local runtime proof, or browser-free Python replay.

## Do Not Select When

- The only evidence is a generic `412`, `403`, reset, or a user hypothesis such as "suspected RuiShu" with no observed product marker.
- The target is Akamai (`_abck`, `bm_*`, `sensor_data`), captcha/verifier, generic WAF cookie challenge, or a normal signer with no River Security markers.
- The user only wants browser automation or a live browser-backed collector.
- The next action would execute target JavaScript, install `sdenv`/Node/native modules, navigate a browser, or send live HTTP without the matching gates.

web-protocol-recovery owns route choice, gates, `projectRoot`, read budget, case selection, provider sequencing, and final acceptance. This Provider owns River Security family classification, subtype selection, historical-case reuse guidance, runtime boundary selection, and River Security-specific acceptance criteria.

## Naming

Use **River Security** in new prose. `RuiShu`, `Ruishu`, and `瑞数` are aliases and historical registry/case tags. Registry aliases such as `alias:ruishu` normalize historical names; they do not count as independent observed product markers. Do not rename existing case IDs only for terminology cleanup.

## First-Turn Rules

1. A user guess is not evidence. `怀疑瑞数 + 412` stays `shape:evidence` and asks for HTML, response headers, `Set-Cookie`, `$_ts`, `r="m"`, and script markers.
2. `route: river-security` requires at least two independent observed River Security markers; alias tags are never part of that marker count. Supplied artifacts or an exact case ID may still use `route: evidence-reuse` for the first read.
3. River Security alone is not a Camoufox criterion. Fresh URL reconnaissance starts with Chromium recon. Use Camoufox only for explicit Camoufox/SpiderMonkey/engine-level wording or a recorded Chromium/Cloak observer-effect blocker.
4. Historical cases are templates unless `selectableAs=proof`. They require fresh current-target verification before live reuse.

## Subtype Router

| Evidence | Subtype | Next owner |
|---|---|---|
| `412` + `$_ts.nsd/cd` + `r="m"` + server `*S` + client `*T` cookie | RS6-style cookie challenge | `python-node` with `strategy: env-patch` or `iv8`; old `sdenv` path only after execution/dependency gates |
| Two-stage cookie and protected XHR rewrites URL suffix | two-stage URL mutation | `iv8` after API-inventory gate |
| Two-stage cookie and protected XHR rewrites URL plus headers | two-stage URL/header mutation | `iv8` after API-inventory gate |
| Generated `*T` cookie then form POST returns HTML fragment | search/form replay | `iv8` -> `python-collector` |
| Cookie writer unclear | cookie provenance | Return blocker for `cookie-provenance-playbook.md` |
| Exact same page works after clean browser but local replay fails | challenge-state envelope | `challenge-state-envelope-playbook.md` or `iv8`, depending on visible boundary |

## Case Discriminators

Load `references/cases/registry.json` first; select at most one case. Stop reuse when the same minimum signal set matches multiple cases.

| Case | Use when | Notes |
|---|---|---|
| `camoufox-jsvmp-ruishu6-cookie-412-sdenv` | RS6-style `412`, `$_ts.nsd/cd`, `r="m"`, server `*S`, client `*T` | Historical evidence template only; no executable entry; old Camoufox/sdenv notes are provenance, not current delivery |
| `iv8-chinatax-ruishu` | `site:chinatax` plus two-stage cookie and XHR suffix | Historical iv8 implementation template; fresh target verification required |
| `iv8-chng-ruishu-announcement` | `site:chng` announcement route plus two-stage cookie and XHR suffix | Historical iv8 implementation template; fresh target verification required |
| `iv8-customs-ruishu` | `site:customs` plus two-stage cookie, URL, and header mutation | Historical iv8 implementation template; fresh target verification required |
| `iv8-cqvip-journal-search` | `site:cqvip`, `412`, `$_ts.nsd/cd`, `r="m"`, generated `*T`, form search replay | Product family confirmed by current evidence; historical iv8 implementation template |

## Runtime Boundary

1. Browser and DevTools are evidence only.
2. `python-node` with `strategy: env-patch` is for a known JS entry with minimal Node/jsdom gaps.
3. `iv8` is for a narrow browser-like artifact generator: cookie, URL suffix, header set, or form-admission state.
4. `sdenv` or other native Node helpers require explicit dependency and target-code execution approval; they are never the final HTTP owner.
5. `python-collector` owns final live egress after the River Security artifact boundary is accepted.

## Acceptance

All applicable checks must pass:

1. Product proof uses observed markers, not a vendor guess.
2. Subtype is named before selecting a case or Provider.
3. One coherent challenge round is preserved: first response, seed cookies, challenge HTML, protection script, generated state, and replay boundary.
4. Historical case reuse records `verificationClass`, `selectableAs`, and current-target verification status.
5. Local runtime produces the exact replay artifact at the canonical mutation boundary.
6. Python replay returns semantic business content; `412` gone, non-empty `*T`, or one HTTP `200` alone is not success.

## Failure Recovery

| Trigger | First fix | Still fails -> stop |
|---|---|---|
| Only `412` or user guess | Ask for HTML, headers, cookies, `$_ts`, `r="m"`, script URL | Do not classify as River Security |
| Multiple River Security cases match | Ask for host/site/subtype discriminator | Do not select by registry order |
| RS6 historical template suggests sdenv live HTTP | Convert to current Provider chain and Python final egress | Do not deliver Node-owned HTTP |
| iv8 generates cookie but business still fails | Diff UA, referer, fetch metadata, stage order, URL/header mutation | Do not scale retries |
| Camoufox requested without criteria | Use Chromium recon first | Escalate only after explicit engine/observer evidence |

## Exit

Return: product evidence, subtype, selected case or no-case reason, current artifact boundary, chosen runtime owner, required gates before execution/live replay, accepted/rejected historical evidence, artifact paths/hashes, cleanup state, and next hub action.
