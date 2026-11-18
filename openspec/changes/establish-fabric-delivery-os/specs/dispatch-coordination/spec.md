## Purpose

Coordinate authorized work, conservative spend and one local worker attempt
without implying native approval, cloud readiness or exactly-once external effects.

## Implementation status

The explicit 2026-11-18 software authorization implements a trusted-caller
single-host SQLite outbox and inert disposable self-test. Real native/OIDC
approval joining, App/federation proof, authenticated private-input adapters,
isolated workers, live storage/recovery validation and Fabric modules remain
unsupported. No live execution follows from this implementation.

## ADDED Requirements

### Requirement: Grant consumption and ready work commit with the cost reservation
The local coordinator SHALL reuse the authorization and spend checks in one
durable transaction that consumes one grant, reserves the computed maximum and
creates exactly one ready outbox entry. No worker SHALL be invoked in that
transaction. Cost/configuration/storage failures SHALL roll back all three
writes. Authorization drift/expiry SHALL retain the existing permanent
invalidation behavior instead of rolling it back when reporting denial.

#### Scenario: A grant is valid but no headroom remains
- **WHEN** preparing work fails its maximum-cost reservation
- **THEN** no consumed grant, reservation or ready entry is committed
- **AND** no external effect starts

#### Scenario: The service terminates before the ready transaction commits
- **WHEN** the process stops after writing grant/reservation changes but before commit
- **THEN** recovery observes neither a consumed grant nor a partial reservation/ready entry
- **AND** storage recovery failure blocks execution rather than resetting the files

#### Scenario: Drift denial is returned
- **WHEN** current trusted input, target, policy or profile differs from the grant
- **THEN** permanent authorization invalidation is committed
- **AND** restoring the original observation cannot resurrect the request

### Requirement: Dispatch binds exact approved worker and cost snapshots
The immutable manifest execution-profile digest SHALL bind the complete dispatch
profile: reviewed worker/runtime configuration digest, budget and price digests,
operation/version, currency/month, token/call limits and positive runtime bound.
Reservation snapshots MUST equal that profile. A mutable worker path, command,
label or agent-selected callable MUST NOT substitute for a reviewed worker.

#### Scenario: A profile reuses a version label with different rates
- **WHEN** the ledger budget or price content digest differs from the approved profile
- **THEN** enqueue is denied and all preparation writes roll back

### Requirement: A ready job has one non-reclaimable worker claim
Claiming SHALL revalidate exact fresh trusted manifest/approval/profile bindings,
authorization/reservation consistency, installation freeze and validity under
the write lock. At most one claim may commit. The claim deadline SHALL not
exceed request/approval/price/month expiry or the approved runtime bound.
Changed or expired ready work SHALL become permanently blocked.

#### Scenario: A ready transaction survives restart before any worker claim
- **WHEN** one ready entry is durable but no worker claim was committed
- **THEN** it may receive its first claim only after fresh verification before expiry
- **AND** neither the grant nor its reserve is duplicated

#### Scenario: Competing workers claim a job
- **WHEN** claimants contend for the same ready entry
- **THEN** only one committed claim is returned
- **AND** all other claim attempts are denied

#### Scenario: The process stops after a worker claim commits
- **WHEN** worker launch or its response is ambiguous after the claim
- **THEN** restart, lease expiry and receipt inspection cannot requeue or relaunch it
- **AND** the consumed grant and reservation remain available for private reconciliation

### Requirement: Cancellation and uncertain outcomes never create a refund or retry
A ready job MAY be cancelled by the trusted service without restoring its grant
or releasing reserved cost. A claimed job with unknown outcome SHALL remain
visibly ambiguous, unclaimable and outstanding. No automatic expiry refund,
lease reclaim, reauthorization, reset or unfreeze SHALL be supplied by this slice.

#### Scenario: A ready job is cancelled before a worker claims it
- **WHEN** cancellation commits before claim
- **THEN** claim is denied and the job remains cancelled
- **AND** no new execution permission or automatic credit is produced

#### Scenario: A worker times out without complete final usage
- **WHEN** the trusted service records an unknown outcome
- **THEN** no zero/partial settlement is invented
- **AND** the job cannot be claimed again

### Requirement: Terminal evidence and trusted usage commit together
Complete final trusted usage and terminal state/result digest SHALL commit in
one transaction. A breach SHALL atomically record actual usage, the installation
freeze and a failed breach state before raising denial. Late completion MUST
record actual usage but MUST NOT report success. A real worker adapter SHALL
enforce bounds and cancellation during execution; this store is not that adapter.

#### Scenario: Terminal persistence fails after usage was written
- **WHEN** the transaction cannot commit its terminal record
- **THEN** both usage settlement and terminal state roll back
- **AND** the worker effect is not retried

#### Scenario: Final usage exceeds its reservation
- **WHEN** trusted reported cost, tokens or calls exceed approved bounds
- **THEN** breach evidence and installation freeze commit before the error is surfaced

### Requirement: Unsupported storage or synthetic evidence cannot enable live work
The local coordinator SHALL require distinct durable files on one supported
local filesystem, exact known database identities and DELETE rollback journals,
using full synchronous attached-file transactions. Unsupported modes, missing
attached files and unrelated schemas SHALL fail closed without reconfiguration
or recreation. The synthetic CLI exercise SHALL accept no installation files,
credentials or worker inputs, use only fresh disposable stores and always
report live execution unsupported, including on exit 0.

#### Scenario: An operator supplies a WAL or missing ledger
- **WHEN** the coordinator opens its trusted store set
- **THEN** it refuses without converting journals or recreating a missing attached file

#### Scenario: The disposable cycle succeeds
- **WHEN** the self-test enqueues, claims, completes and denies replay
- **THEN** its output states that only the inert local cycle passed
- **AND** no human identity proof, real cost, active worker or deployment readiness follows
