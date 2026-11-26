## Why

The human explicitly authorized parallel specification, build and synthetic
testing of local request-registry/authorization/spend/outbox coordination on
2026-11-26. PR #17 was human-merged before this continuation.

Separate successful registry revalidation and outbox calls leave a race where
policy or input changes between the check and consumption/claim. The offline
slice must join these checks under the same four-file transaction without
creating approval authority or allowing the legacy claim API to bypass it.

## What Changes

- Add a trusted-caller `SQLiteRegistryDispatchStore` with atomic registry
  revalidation, existing grant consumption, maximum reservation and ready record.
- Revalidate registry input/policy again inside the one-attempt claim transaction.
  Pre-claim revocation/drift blocks the ready job without refund or grant restoration.
- Bind the complete registry request digest into a dedicated version-2 outbox.
  Legacy version-1 dispatch APIs cannot open this outbox; no automatic migration.
- Reuse existing transaction-level checks and terminal accounting; preserve
  standalone registry, authorization, spend and version-1 dispatch behavior.
- Verify rollback, durable denial, competing processes, expiry after lock,
  abrupt-process recovery and legacy bypass refusal using synthetic stores only.

## Capabilities

### New Capabilities

- `offline-registry-dispatch`: Four-file private single-host coordination of
  previously registered requests and externally verified grants.

### Modified Capabilities

None. Related pending proposals retain their complete live integration scope.

## Impact

One coordinator, minimal shared helper extraction, exports, guides and synthetic
tests. No live GitHub/Teams capture, identity verification, evidence-to-grant
conversion, model call, worker launch, credential, deployment or CLI activation.
Successful local claims are inert records, not proof an external effect occurred.
