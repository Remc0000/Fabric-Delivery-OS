## ADDED Requirements

### Requirement: Trusted typed input and existing authority
The coordinator SHALL require a complete registered `RegistryRequest`, typed
approval/profile and an already recorded externally verified grant. It SHALL NOT
create grants, policies, source rights or execution authority from intake or chat.

#### Scenario: Proposal or receipt without a grant
- **WHEN** a proposal has no recorded grant or an intake receipt is supplied as one
- **THEN** coordination denies without consumption, reservation or ready work.

### Requirement: Four-file atomic preparation
Preparation SHALL revalidate the complete proposal/current policy and consume,
reserve and prepare ready work in one supported local transaction. Successful
rows SHALL bind the complete registry request digest.
That digest SHALL be a proposal-consistency check, not a claim of human approval
of issue content. Authenticated private-input/human linkage remains unsupported.

#### Scenario: Valid synthetic coordination
- **WHEN** registered input, recorded grant and spend/profile bindings are valid
- **THEN** exactly one consumed grant, maximum reservation and digest-bound ready
  row commit together, without launching any worker.

#### Scenario: Spend or operational failure
- **WHEN** preparation fails after tentative consumption or reservation
- **THEN** all tentative effects roll back; no partial or successful result escapes.

#### Scenario: Observed registry or authorization drift
- **WHEN** a valid typed current request or recorded authorization binding drifts
- **THEN** the appropriate durable invalidation commits before denial, with no
  reservation/ready work; restoring original bytes cannot revive that denial.

#### Scenario: Approved skill or tool snapshot changes
- **WHEN** a current manifest supplies a different skill/tool snapshot digest
- **THEN** it is durably denied as changed input, not silently refreshed or treated
  as new authority; no actual skill-loading proof is inferred from the digest.

### Requirement: Registry-bound single claim
Claim SHALL revalidate registered input/current policy and stored registry digest
inside the same transaction as existing claim checks. Pre-claim registry denial
SHALL permanently block ready work while retaining consumed grants/reservations.

#### Scenario: Policy or request revoked after enqueue
- **WHEN** a prepared proposal is revoked, replaced or observed drifted before claim
- **THEN** claim and later restored/replayed attempts fail; the job remains blocked
  and reservation remains held without new effects or automatic refunds.

#### Scenario: Competing claims and crash ambiguity
- **WHEN** competing processes claim or a process dies after claim commit
- **THEN** at most one claim exists and it cannot be requeued/reclaimed; unknown
  outcomes remain visible without claiming worker success.

#### Scenario: Revocation after claim
- **WHEN** registry policy is revoked after the claim already committed
- **THEN** it does not undo effects or refund the reservation; truthful terminal
  accounting remains possible and no live cancellation guarantee is claimed.

### Requirement: Supported storage and legacy isolation
The coordinator SHALL require four distinct supported same-filesystem files,
DELETE journals, full synchronization and lock-time freshness. Missing,
replaced, aliased or foreign files SHALL be denied without recreation/conversion.
Its version-2 outbox SHALL be incompatible with normal legacy version-1 claims.
Enqueue/claim SHALL use one explicit post-lock timestamp across their shared
checks. Schema validation SHALL reject unexpected views/triggers. The outbox
version guard SHALL NOT be described as global privileged API bypass prevention.

#### Scenario: Legacy bypass or unsupported store
- **WHEN** either API opens the other outbox version or a file/journal/schema is unsupported
- **THEN** it fails closed without migration, policy bypass or mutation.

#### Scenario: Expiry while waiting for a lock
- **WHEN** a request/policy/grant expires before the common lock is acquired
- **THEN** the inside-lock check denies and commits applicable permanent invalidation.

### Requirement: Bounded offline proof
The coordinator SHALL preserve existing standalone APIs and conservative terminal
accounting. Synthetic checks SHALL NOT clear live preflight or activation blockers.

#### Scenario: Recovery and regression evidence
- **WHEN** offline tests cover rollback/restart and an inert lifecycle completes
- **THEN** existing APIs retain behavior and live identity/evidence/worker/storage
  acceptance remains separate, with execution activation disabled.
