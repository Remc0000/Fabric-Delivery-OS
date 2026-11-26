## Context

This authorized offline slice supplies private policy and issue/request admission
state, not the live trusted adapter described by the broader framework. The
registry, every method and all configuration are privileged trusted-service
inputs. Do not expose them to agents or unauthenticated callbacks.

## Decisions

### 1. Immutable typed records reuse existing manifest semantics

`RequestPolicy` binds installation/solution IDs, a unique version, numeric private
repository ID, explicit action/effect rules and a validity interval.
Its complete canonical JSON digest must equal the manifest's policy digest.
`IssueRevision` binds numeric repository/issue IDs, observed private visibility
and the digest of the privately retained issue scope/revision snapshot.
`RegistryRequest` binds that issue snapshot and the existing ExecutionManifest.
The issue digest need not equal the manifest's input digest, which may represent
compound specifications; both are independently bound.

These values reference immutable bytes; the library does not retrieve those
bytes or prove that a caller's metadata is truthful. A live adapter must obtain
current authoritative inputs outside the model before admission/revalidation.

### 2. Admission is proposed state, not an execution gate

Registration requires the currently registered policy, its action-specific
effect allowlist, private repository identity, installation/solution binding,
and current manifest/policy lifetime. A request cannot outlive its policy.
Every accepted request remains `proposed`. There is no approval object,
human-authorizer assertion, execution-enabled flag, token, worker or grant API.
Multiple separately identified requests may refer to one issue, but an existing
request ID or policy version can never be re-registered.

### 3. Current policy is an explicit privileged update

Policy versions are immutable and retained. Registering a new version makes it
current for its installation/solution and atomically invalidates their existing
proposals. Policy revocation removes the current pointer and invalidates its
proposals without deleting frozen history. Previously registered versions cannot
be activated again. These methods administer admission configuration, not
bootstrap rights or human approval; a live service must protect them separately.

### 4. Revalidation commits permanent denials

Revalidation compares the complete current request with frozen bytes and current
policy inside `BEGIN IMMEDIATE`, checking time after lock acquisition.
Issue content/visibility/repository, manifest inputs/effects, policy, target,
profile and other bound revision changes invalidate the proposal permanently.
Expiry or a backwards clock observation also prevents revival.
A denial is raised only after invalidation commits. Inspection reports the last
stored state; it is not a fresh readiness check and cannot authorize anything.

### 5. Dedicated local storage, not a cloud authority

Use a private local SQLite file with a distinct application ID, schema version,
strict table/constraint definitions, foreign keys, DELETE journals and FULL
synchronous transactions. Unsupported schemas/journals are refused, not repaired.
Every loaded policy/request is strictly parsed and compared with its canonical
digest and duplicated lookup bindings.

Ordinary operations use SQLite `mode=rw` and never recreate a missing file.
An existing instance detects a changed local file identity. New instances still
require operator-verified provenance: checksums cannot authenticate hostile
rewrites, restored backups or replacement by a coherent different registry.
Reliable local locks/fsync, host access controls, backup/recovery and exclusive
trusted ownership remain operator responsibilities. No distributed durability,
cryptographic policy authenticity or exactly-once external effects are claimed.

## Verification

Use only temporary synthetic local state. Cover strict types/serialization,
admission denials, policy replacement/revocation, changed input/effect/route and
expired proposals, revert-after-invalidation, durable reopen, concurrent
registration, clock expiry while waiting for a lock, corrupt schema/content,
missing/replaced files and rejection of other library databases. Preserve the
existing full suite and package imports. No live credentials or network calls
are used.
