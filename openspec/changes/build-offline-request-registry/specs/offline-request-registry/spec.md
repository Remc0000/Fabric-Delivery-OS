## Purpose

Persist bounded private issue/request and policy admission state offline without
claiming human authentication or issuing execution authority.

## ADDED Requirements

### Requirement: Registry records are immutable and strictly bound
The registry SHALL store versioned canonical private policies and frozen issue
revision/ExecutionManifest pairs. It SHALL reject malformed, duplicate, unknown
or missing JSON fields and invalid typed identities, intervals and action/effect
rules. The complete policy digest SHALL bind the manifest; the complete issue
and manifest bytes SHALL bind each registry record.

#### Scenario: A frozen record is reopened
- **WHEN** a valid registry is opened by another trusted local instance
- **THEN** the same policy/request bytes, digests and recorded state are preserved
- **AND** a reused request ID or policy version is rejected rather than replaced

#### Scenario: Stored bytes or lookup bindings are corrupted
- **WHEN** payload, canonical digest or duplicated registry identities disagree
- **THEN** the operation is denied with a closed corruption code
- **AND** corrupt state is not silently defaulted or repaired

### Requirement: Admission is private, policy-bound and proposed only
Only trusted callers SHALL register policies and requests. Admission SHALL
verify the current installation/solution policy, numeric private repository
identity, action-specific effects and current validity. Requests MUST NOT
outlive their policy. Admitted requests SHALL remain proposed; admission,
inspection, labels, author identity or caller assertions MUST NOT create grants.

#### Scenario: An agent-filed proposal has an allowed route
- **WHEN** a trusted adapter registers a valid issue revision and manifest
- **THEN** the registry stores proposed state without approval or execution
- **AND** initial discovery, build and deployment still need their separate human gates

#### Scenario: A proposed request changes target or authority
- **WHEN** the request uses a public/wrong repository, unknown policy,
  wrong installation/solution, disallowed action/effects or invalid lifetime
- **THEN** registration is denied without an executable record

### Requirement: Policy changes permanently invalidate affected proposals
Policy versions SHALL be immutable. Privileged registration of a new version
SHALL atomically make it current and invalidate existing proposed requests for
that installation/solution. Privileged current-policy revocation SHALL remove
its current binding and invalidate proposals while retaining frozen history.
Previously registered policy versions MUST NOT be reactivated.

#### Scenario: A policy is replaced or revoked
- **WHEN** the trusted configuration operation commits
- **THEN** affected proposals are invalidated in the same local transaction
- **AND** a restored old policy/request value cannot revive them

### Requirement: Revalidation checks fresh bindings after acquiring the lock
Revalidation SHALL check complete current issue/request bindings, current policy
and validity after transaction locking. Changed issue scope/visibility,
manifest inputs/effects/target/profile or other revisions, expiry and invalid
time SHALL permanently invalidate the old proposal. Its denial SHALL commit
before the closed error is raised. Revocation SHALL be permanent.

#### Scenario: Issue scope changes and is later reverted
- **WHEN** the trusted current snapshot first differs from the frozen request
- **THEN** revalidation commits invalidated state
- **AND** later supplying the original bytes still cannot restore proposed state

#### Scenario: A proposal expires while waiting for a write lock
- **WHEN** revalidation acquires its transaction at or after expiry
- **THEN** it records an expired invalidation rather than returning a valid snapshot

### Requirement: Local persistence fails closed without recreating lost state
The registry SHALL use a dedicated versioned local file, schema/constraint
checks, serialized transactions and supported DELETE-journal durability.
Unknown schemas, unrelated databases and unsupported journals SHALL be denied
without conversion. Ordinary operations MUST NOT recreate a missing registry.
An instance SHALL deny observed file replacement. Storage failures SHALL be
explicit; private input values MUST NOT appear in diagnostic codes.

#### Scenario: Two processes register one request
- **WHEN** competing trusted processes insert the same request ID
- **THEN** exactly one local registration commits
- **AND** other deliveries are denied without replacing the first record

#### Scenario: A file is deleted, replaced or belongs to another store
- **WHEN** a registry operation observes the missing/replaced file or incompatible schema
- **THEN** it fails closed rather than initializing a success-shaped empty registry
- **AND** authoritative recovery requires separate trusted operator verification

### Requirement: Offline checks are not live provenance or authorization
The registry MUST NOT fetch GitHub/Teams/Fabric, inspect source records, handle
credentials, authenticate humans, record ApprovalBinding, consume grants or
schedule workers. All metadata/policy inputs and file access SHALL remain
privileged. Hashes and local identity checks MUST NOT be described as proof of
live policy authenticity, trusted restored state, cloud durability or readiness.

#### Scenario: A coherent snapshot passes local revalidation
- **WHEN** the caller supplies matching current private records
- **THEN** the result means only proposed local binding consistency
- **AND** native human evidence, input provenance and all live execution gates remain unresolved
