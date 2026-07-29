# Reese84 Provider

## Select When

- Evidence contains at least one Reese84-native marker: a `reese84` cookie, `x-d-token` projected from that cookie, a challenge script exposing `initializeProtection` / `onProtectionInitialized` / `reeseSkipAutoLoad`, or a solution response carrying `token`, `renewInSec`, and `cookieDomain`.
- A second independent surface corroborates the family: randomized challenge GET/POST traffic, the cookie transition, `/_Incapsula_Resource?SWJIYLWA=`, Imperva interstitial script evidence, or a business request consuming the token.
- The next task is to prove the Reese84 challenge state machine, recover one narrow local challenge artifact, or accept a browser-free Python business replay.

## Do Not Select When

- The only evidence is `403`, error 15, "Pardon Our Interruption", an Imperva label, one `visid_incap_*` / `incap_ses_*` / `nlbi_*` cookie, or a generic randomized path.
- The target is Akamai, River Security, a CAPTCHA/verifier, another Imperva product with no Reese84 marker, or a normal signer with no challenge-cookie transition.
- The user only wants a reversible hook, whole-file deobfuscation, browser automation, or pasted-cookie replay.
- Live replay, account/session use, target-code execution, dependency installation, or writes lack the matching authorization gates.

web-protocol-recovery owns intake, authorization, exact scope, request budget, `projectRoot`, case selection, Provider sequencing, cleanup, and final delivery status. Reese84 owns product-family proof, challenge-state modeling, cookie/header projection, transport coherence, refresh boundaries, and Reese84-specific semantic acceptance. It never owns final live egress.

## First-Turn Rules

1. Require one Reese84-native marker plus one independent corroborating surface before selecting `route: reese84`.
2. A supplied exact case ID may start with `route: evidence-reuse`; loading a template does not prove the current target.
3. Fresh URL reconnaissance starts with `chromium-recon`. Reese84 or Imperva wording alone is not a Camoufox criterion.
4. Keep primary gate `challenge`; record `session` and `transport` only as secondary gates when current evidence proves those blockers.
5. Unknown Imperva products return to evidence/recon instead of being forced into Reese84.

## Canonical State Machine

Preserve one coherent session and record each writer and first consumer:

```text
document request
  -> Imperva session cookies and interstitial
  -> randomized Reese84 challenge script
  -> optional GPC/UTMVC side state
  -> challenge solution POST
  -> response token + renewInSec + cookieDomain
  -> reese84 cookie write
  -> optional x-d-token projection on the business/API host
  -> first semantically accepted business request
```

Do not collapse `Set-Cookie`, JavaScript cookie writes, the stored jar, outbound `Cookie`, and `x-d-token` into one observation. Treat optional `___utmvc`, `visid_incap_*`, `incap_ses_*`, `nlbi_*`, `prxCookie`, `xctrc`, and SWJIYLWA resources as separate state until current evidence proves their role.

## Runtime Boundary

1. Capture the final challenge-script path, solution request body shape, response token writer, cookie transition, and business consumer before choosing an implementation.
2. Use `browser-hooks` only for one known reversible boundary; use `ast` only when whole-source structure blocks that boundary.
3. Use `python-node` with `strategy: env-patch` when a known entry needs a narrow Node/vm/jsdom host surface.
4. Use `iv8` when the challenge needs browser-visible host semantics, iframe realms, event scheduling, or an allowlisted Python HTTP bridge. Reese84 remains the protocol and acceptance owner.
5. Use `python-collector` only after the challenge artifact boundary is accepted. Python owns challenge HTTP, cookie continuity, OAuth/application calls, and final live egress.

Target JavaScript or WASM execution requires the normal reviewed-hash and capability-denied sandbox gates. Browser page `fetch`, browser-cookie export as an operating requirement, and Node-owned business HTTP are not final delivery.

## Transport And Session Coherence

- Keep UA, Client Hints, TLS impersonation profile, proxy exit, challenge cookies, and business-request headers coherent within one session.
- Treat transport as secondary until cookie projection, request bytes, and session continuity are ruled out as the first divergence.
- Use `transport-pre-gate-playbook.md` before native transport profiling. Do not implement TLS or HTTP/2 from scratch.
- Prove refresh behavior from `renewInSec`, expiry, a fresh challenge round, or a named server rejection. Do not hardcode a captured `reese84`.
- If `x-d-token` is observed, prove whether it equals the current `reese84` value and where that projection is written.

## Case Use

`iv8-bangkokair-reese84-booking` is template evidence. It may identify Reese84 markers, the challenge/business boundary, and an implementation shape, but it supplies no current executable entry. Current-target evidence must re-establish the route, state chain, implementation boundary, and semantic acceptance before live delivery.

## Acceptance

All applicable checks must pass:

1. Family proof contains one Reese84-native marker plus one independent corroborating surface.
2. One coherent challenge round records document response, challenge asset, solution request, token response, cookie write, and first business consumer.
3. The token is fresh for the tested round; any `x-d-token` projection and business-host cookie behavior match current wire evidence.
4. A local implementation reproduces the accepted challenge artifact at the canonical boundary without pasted reusable state.
5. The first business request returns the expected application data shape. Challenge disappearance, token length, OAuth success, or one HTTP `200` alone is insufficient.
6. A collector claim requires a second clean session or another approved refresh/reuse test that proves the declared scope and lifetime.
7. Final delivery is browser-free, Python-owned, bounded by the work order, and leaves no unapproved runtime resources.

## Failure Recovery

| Trigger | First fix | Still fails -> stop |
|---|---|---|
| Only generic Imperva/interstitial/cookie evidence | Capture challenge script, solution POST, token response, or business token consumption | Do not select Reese84 |
| Token exists but business request is rejected | Diff cookie/header projection, session continuity, UA/Client-Hints, transport, and optional UTMVC state | Do not claim challenge success |
| iv8 runs but no solution token appears | Verify challenge version, iframe/event lifecycle, HTTP bridge, and first divergent stage | Return a bounded implementation blocker |
| OAuth or bootstrap works but business payload is blocked | Validate the first business consumer and transport/session coherence | Do not accept an intermediate `200` |
| Template code appears reusable | Extract only current verified facts through a new work order | Do not import or execute template references |
| Another Imperva product is present without Reese84 markers | Return to evidence/recon | Do not broaden this Provider |

## Exit

Return: Reese84 evidence surfaces, primary/secondary gates, challenge asset and solution boundary, cookie/header transition, optional side-state decision, selected implementation Provider or blocker, transport/session tuple, business acceptance result, artifact paths/hashes, request budget, cleanup state, and residual freshness/egress risk.
