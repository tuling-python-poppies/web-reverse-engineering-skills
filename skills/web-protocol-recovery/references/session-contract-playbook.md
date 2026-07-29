# Session Contract Playbook

Use this reference when:

- the page mentions `sessionid`, login, or per-user answers
- different accounts see different sums, rows, or submit results
- fetch and submit must happen under the same account state
- one authenticated session can still switch current tenant, shop, org, locale, or workspace context without a fresh login

## Core rule

Session state is part of the protocol contract, not a side note.

Account authentication and active business context are separate acceptance gates. A successful login does not prove that the intended tenant, shop, organization, role, locale, workspace, or data range is active.

## Working method

1. verify whether the data request depends on login, submission depends on login, or both
2. test with the real session, no session, and an invalid session when safe
3. record whether the answer is account-bound
4. make the relevant cookie or token explicit in the collector arguments
5. keep fetch and submit under the same account when required
6. separate identity session from active business context:
   - which field authenticates the user
   - which field chooses the current tenant, shop, org, locale, or workspace
   - whether switching context rotates the whole session or only mutates one active-context value
7. resolve operator-facing labels through the current authorization or enumeration response:
   - require exactly one label match
   - submit the returned protocol ID, not the display label
   - stop on zero or multiple matches
8. after activation, reread identity from an authoritative final surface such as session introspection, a business-page bootstrap object, or the first business response:
   - compare every required context layer to task configuration
   - do not trust only the switch/update response envelope
   - fail closed on missing, default, previous, or ambiguous context
9. keep short-lived handoff tickets, continuation URLs, and cross-domain transfer tokens on the same session chain, but do not store them as durable collector credentials
10. before collection with a reused session, run one cheap identity probe and refuse collection on mismatch
11. decide concurrency rules before scaling:
   - one session per concurrent context when the active context is single-valued
   - one shared session only when repeated proof shows contexts do not overwrite each other

## Common traps

- assuming login is irrelevant because one endpoint works once without it
- collecting with one account and submitting with another
- treating per-account answers as signer bugs
- treating two cookie jars as independent sessions when they only differ by one mutable context field
- assuming injected cookies can recreate a once-only intermediate UI state that originally depended on a transient ticket or post-auth redirect
- accepting a context-switch HTTP 200 without a final identity reread
- submitting a localized display label where the protocol requires a current authorization ID
- sharing one mutable active context across concurrent workers

## Delivery rule

The collector should expose the required session inputs and document whether the result is account-bound.
It should also document whether active tenant, shop, org, or workspace context is independent per session or single-active-per-session.
Completion requires both account authentication and final business-context reread to match the intended configuration.
