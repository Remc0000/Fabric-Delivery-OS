# Offline registry-bound dispatch

`SQLiteRegistryDispatchStore` is a privileged **single-host four-file coordinator**,
not an authenticated approval service, queue worker, skill manager or cloud runtime.
It joins an already registered private proposal to an already recorded externally
verified grant, maximum spend reservation and inert ready/claim records.
See the [bounded specification](../openspec/changes/build-offline-registry-dispatch/proposal.md)
and [review checklist](../openspec/changes/build-offline-registry-dispatch/tasks.md).

## Supplied state and API

The trusted caller supplies an existing `SQLiteRequestRegistry`,
`SQLiteAuthorizationStore`, `SQLiteSpendStore`, complete `RegistryRequest`,
`ApprovalBinding` and approved `DispatchProfile`. It must configure policy,
budget/prices, freeze the manifest and independently verify/record the human
grant before coordination. This module performs none of that authentication.
Intake receipts, labels, author attribution and Teams actions are not grants.

```python
from fabric_delivery_core import SQLiteRegistryDispatchStore

queue = SQLiteRegistryDispatchStore(
    new_private_outbox_path, registry, authorization, spend,
    clock=trusted_clock,
)
receipt = queue.enqueue(current_registry_request, verified_binding, approved_profile)
claim = queue.claim(fresh_registry_request, reverified_binding, approved_profile)
```

All names other than the imported class are explicit trusted caller inputs.
The fragment performs local bookkeeping only; it invokes no worker. Neither
receipt nor claim is a reusable execution credential. Private `receipt(request_id)`
may expose complete ledger bindings; never publish it or use it as fresh readiness.

## Atomicity and conservative denial

Enqueue locks all four stores before checking the complete proposal/current policy
and existing human-grant/profile/spend bindings. One explicit post-lock timestamp
is shared across preparation checks. Consumption, maximum reservation and a ready
row bound to `RegistryRequest.digest` commit together. Operational, profile or
spend failure rolls back tentative effects; observed valid registry/authorization
drift instead commits its permanent invalidation before surfacing a closed denial.

Claim uses a new common lock-time timestamp, revalidates the registry and checks
the stored full proposal digest plus existing grant/reserve/profile/deadline
bindings. Revocation, changed policy/input or expiry before claim permanently
blocks ready work. The grant stays consumed and reserve stays held; restoring old
content, refunding, zero usage or retries cannot revive that job.

`registry_digest` is **proposal consistency**, not proof of which issue revision
a human approved. Grants bind the complete manifest; its input digest is supplied
independently from the issue capture. Authenticated private input/human scope
linkage remains a separate unimplemented live boundary.

The full manifest includes immutable skill/tool/framework/runtime snapshot
digests. A changed snapshot is denied as changed input, not silently refreshed.
Comparing digests does not resolve, verify or load skills. Required role-specific
Skills for Fabric, approved compatible updates, fixed approved snapshots,
quarantine and attributable guidance remain
[future runtime requirements](../openspec/changes/establish-fabric-delivery-os/specs/skills-and-tools/spec.md).

## Outbox versions and storage

Use a new private version-2 outbox with a required `registry_digest` column.
Legacy [version-1 dispatch](durable-dispatch.md) cannot open it; this coordinator
cannot open a version-1 outbox. Neither API converts or migrates files.
This isolates a coordinated outbox, **not every privileged authorization API**:
direct consumption or another legacy outbox sharing the grant store still belongs
to the trusted-service boundary. Real tool/identity bypass prevention is unproven.

All four files must be distinct physical ordinary files on one reliable local
filesystem, with supported schemas, DELETE journals, FULL synchronization and
foreign keys. Unexpected views/triggers/schema objects are denied. Missing
attached files are not recreated; observed aliases/replacements are rejected
before attachment, after locking and before commit. Do not move or restore one
file independently, use WAL, a mapped network drive or share state with agents.

These checks are not cryptographic protection against privileged coherent rewrites,
historical rollback before a fresh instance or a faulty filesystem. Host ACLs,
private ownership, trustworthy time and real durability/recovery proof remain
external prerequisites. This is not OneLake business-data storage or a distributed
exactly-once external-effect protocol.

## Post-claim accounting and remaining gaps

`cancel` remains pre-claim only. `mark_unknown` conservatively retains the maximum
reservation after ambiguous outcomes. `finish` uses complete trusted final usage
and existing terminal accounting, including excess-cost freeze and late failure.
Registry revocation after a committed claim cannot undo effects or stop a live
worker; it does not prevent normal truthful accounting of an already claimed job.
Unknown outcomes still require separately reviewed reconciliation, not automatic
refund/reclaim. No such recovery endpoint or live cancellation protocol is supplied.

No API/model/source call, identity/approval conversion, worker launch, credential,
Teams connector or deployment is supplied. Existing offline preflight/live blockers
remain unchanged. Synthetic crash/race tests are local evidence, not production
storage certification or permission to activate delivery.
