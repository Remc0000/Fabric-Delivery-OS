## Public contract

`SQLiteRegistryDispatchStore(path, registry, authorization, spend, *, clock=None)`
uses a separate version-2 outbox with four distinct ordinary local SQLite files.
All state/API/configuration is privileged trusted-service input, never an agent
tool. Constructor accepts typed existing stores; it initializes only an empty
supported outbox, never converts a version-1 or foreign database.

`enqueue(current: RegistryRequest, approval: ApprovalBinding, profile:
DispatchProfile) -> ExecutionReceipt` requires typed explicit inputs, including
an already registered proposal and a grant already recorded by the existing
authorization store from externally verified human evidence. It does not freeze
requests, register policies, authorize grants or interpret intake receipts.

The complete manifest binds `skill_snapshot_digest`, `tool_snapshot_digest` and
framework/runtime profile digests as supplied by the trusted caller. Snapshot
drift is request drift, not permission to refresh an approved run. This does not
resolve, download, authenticate or prove the contents of any skill. Existing
[role/source/update/quarantine requirements](../establish-fabric-delivery-os/specs/skills-and-tools/spec.md)
remain required for the future runtime; no skill manager is built by this slice.

`claim(current: RegistryRequest, approval, profile) -> DispatchClaim` revalidates
the exact registry digest and current policy inside the claim transaction, then
reuses the existing one-attempt binding/reservation/deadline checks. This is not
a worker launch. `cancel`, `mark_unknown`, `finish` and private `receipt` retain
existing conservative cancellation, ambiguity and final-usage behavior.

## Atomic checks and denial semantics

One connection attaches the authorization, spend and registry files to the
version-2 outbox. Supported exact schemas, same-filesystem distinct identities,
DELETE journals, FULL synchronization, foreign keys and `BEGIN IMMEDIATE` are
mandatory. Mode `rw` prevents recreating missing attached files. Instance-observed
file replacement/aliasing is rejected before attach, after acquiring locks and
before committing observed writes.
Enqueue and claim read one coordinator timestamp after the common lock is acquired
and pass it explicitly through registry, authorization, reservation and claim
helpers. Optional helper timestamps default to their existing clocks for legacy
calls; no shared store clock or per-call instance state is mutated. This is a
common lock-time observation, not a promise time cannot pass before commit.
Existing terminal accounting may retain its clocks, still read inside the lock.
Schema validation rejects unexpected views, triggers and executable schema
objects, not merely foreign table names; known constraint autoindexes are allowed.

At enqueue, revalidate the complete registry request first. Only a valid
proposed record can reach existing authorization consumption, maximum reservation
and ready insertion. Bind its full digest in a nonnullable outbox column.
Commit all successful writes together. Spending/storage/profile failure rolls
back consumption/reservation/outbox writes, not a success-shaped fallback.

Registry helpers return a validated snapshot or closed durable denial to the
transaction owner. Observed typed input/route/policy/expiry drift commits the
registry invalidation before denial is raised outside the transaction. Existing
terminal registry denial does not become new work. Authorization drift retains
the existing committed authorization invalidation; no reservation/outbox appears.
Corrupt/unavailable storage is an operational denial, not a valid observation
that can be fabricated into a drift result.
In particular, a validated already invalidated/revoked record returns a durable
denial so a ready row can be blocked and committed. Corrupt state/reasons remain
raised no-effect rollback conditions, not fabricated terminal observations.

At claim, a ready row must bind the same complete registry digest. Registry
revocation/drift/expiry commits any observed registry invalidation and permanently
blocks the ready row in the same transaction, then surfaces a closed denial.
The consumed grant and maximum reservation remain burned/held. No restoring old
bytes, second claim, refund, zero usage or retry can revive it.

Registry state remains proposed/invalidated/revoked, not an authorization ledger.
Registry revocation after a committed claim cannot reverse effects or stop a live
worker. Terminal usage still needs truthful accounting; no later registry check
may prevent conservative settlement of already claimed work. Real per-effect
enforcement, cancellation and worker recovery remain unimplemented.

## Reuse and legacy separation

Extract transaction-level enqueue/claim and registry revalidation helpers instead
of duplicating grant, spend, policy or terminal logic. Existing public APIs,
schema version 1, return values and denial persistence remain compatible.
The new outbox uses the dispatch application family with version 2 and an explicit
required registry digest; its validated schema differs from version 1.

Opening it through legacy `SQLiteDispatchStore` is denied without conversion or
mutation. Opening a legacy version-1 outbox through the coordinator is also denied.
This prevents a normal legacy claim from skipping registry revalidation for a
coordinated job. Privileged host rewrites/backup rollback before a fresh instance,
private ACLs, real storage durability and bypass prevention are still external
trust prerequisites, not authenticated by this library.
Direct privileged authorization consumption or a separate version-1 outbox
sharing the grant store remain possible. The version guard isolates the
coordinated outbox, not every privileged API; real mediated-tool and identity
bypass prevention remains unproven.

`registry_digest` proves consistency with the registered proposal at enqueue,
not that a human approved that issue revision. Existing grants bind the manifest,
whose input digest is independently supplied. Authenticated private-input/human
scope linkage remains a separate live boundary and is not retrofitted here.

## Verification and exclusions

Synthetic externally supplied bindings are test fixtures, never obtained from
intake, author attribution, Teams actions or a model. Verify atomic ready/claim/
settlement, no-grant and receipt misuse denial, durable drift, post-enqueue
revocation, profile/spend rollback, foreign/WAL/missing/replaced/aliased files,
replay/races, lock-time expiry and abrupt crashes before/after commit.

No live capture, credentials, API/model/source access, human identity validation,
native/OIDC/private-input evidence-to-grant conversion, worker activation or
deployment is authorized. Existing offline preflight/live blockers stay enabled.
No distributed/OneLake production storage or exactly-once external effect is proven.

## Parallel ownership

The implementation worker owns the coordinator, minimal shared helper changes
and one focused test file. A second worker owns a separate race/crash test file.
A third reviews this contract read-only. Main owns shared specs/docs/exports,
acceptance records and integration. Local handoffs are not human release acceptance.
