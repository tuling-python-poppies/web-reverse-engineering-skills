# Async Export Job Playbook

Use this playbook when the business path creates a report, export, download, or batch task and completion arrives later.

## Core Rule

An export collector is a state machine. HTTP 200 is not create success, the newest task row is not automatically this run's task, and a readable file is not automatically complete.

## State Machine

1. run read-only count, field-catalog, permission, and filter probes
2. snapshot existing task IDs when task history is visible
3. submit first-create with the exact method, query/body placement, serialization, and content type
4. prove that a new task exists and matches this run's filters and selected fields
5. poll only that task ID with bounded attempts and explicit terminal states
6. run download precheck
7. acquire fresh secondary verification material when required
8. download bytes
9. decrypt or unpack when required
10. parse records
11. apply artifact and field-completeness gates before persistence
12. refresh session state only on an explicit authentication failure and with a bounded retry

## Create Acceptance

Accept create only when the response returns a new task ID or the post-create task set contains an ID absent from the pre-create snapshot. The chosen task must also match the requested time range, report type, file type, and selected field set.

Reject:

- a success envelope with no new task
- the first or newest task row without identity proof
- a completed task created before this run
- regenerate/retry evidence used as proof of first-create
- signer input built from a different method, body, or serialization

## Polling And Side Channels

Keep the isolated task ID through the whole poll loop. Do not re-query and silently switch rows.

For mailbox, SMS, webhook, queue, or callback material:

1. record a cursor, message ID, or timestamp baseline before triggering send
2. trigger the exact scene
3. accept only material newer than the baseline
4. validate scene-specific sender, shape, and binding

## Artifact Gates

Before persistence verify:

- magic bytes or expected content type
- archive/decryption success
- requested field count versus parsed column count
- required business keys
- row-count sanity against the read-only probe when available

Fail closed when a file opens but contains fewer fields than requested.

## Local Control

`scripts/tools/practice_lab.py --self-test` includes empty-create, wrong-task selection, and thin-field negative controls. It does not contact an external service.

## Completion Gate

Require explicit states, new-task proof, condition match, bounded polling, fresh side-channel baselines, artifact validation, completeness checks, and bounded out-of-band session refresh. Python owns all live HTTP.
