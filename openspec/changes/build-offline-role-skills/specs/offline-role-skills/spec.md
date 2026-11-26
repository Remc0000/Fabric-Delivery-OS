## ADDED Requirements

### Requirement: Explicit editable role policy
The resolver SHALL accept strict typed/local profile, source policy and catalog
records, select only explicit allowed references and enforce required skills.
Manual revision pins SHALL identify immutable full object IDs, not mutable refs.
Every selected reference SHALL resolve or deny the whole operation; unresolved
required or explicit optional selections SHALL NOT be silently omitted.

#### Scenario: Human changes the selected skills
- **WHEN** a profile adds an allowed skill or changes its explicit revision pin
- **THEN** local resolution creates a new immutable snapshot, never an approval
  or an in-place update of an existing authorized task.

#### Scenario: Missing mandatory or expanded selection
- **WHEN** a required reference is absent or a profile requests an unallowed skill
- **THEN** resolution denies without silently loading everything or granting rights.

#### Scenario: Malformed manual input
- **WHEN** input has unknown/missing/duplicate fields, invalid types/version,
  nonfinite values, ambiguous candidates or exceeds the declared bounds
- **THEN** it fails with closed diagnostics without exposing private text or URLs.

### Requirement: Supplied candidate compatibility and visible quarantine
The resolver SHALL compare approved origin, actual UTF-8 content hash and declared
format/dependency/runtime interface before admitting a candidate. It SHALL select
the highest eligible supplied release sequence for an unpinned reference.

#### Scenario: Incompatible or unverifiable update
- **WHEN** a typed candidate has wrong origin/hash/interface/format/dependency type
- **THEN** it is visibly quarantined for the resolution, never executed or admitted.

#### Scenario: Newest eligible local material
- **WHEN** the supplied catalog includes newer eligible material for an unpinned skill
- **THEN** a future-task snapshot selects it without fetching upstream or claiming
  authenticated freshness, real runtime compatibility or human approval.

### Requirement: Explicit constrained last-known-good fallback
Fallback SHALL require an explicit valid snapshot with matching full profile/policy
digests and eligible pinned artifacts. Its use SHALL be visible and digest-bound.
Pinned selection SHALL retain the identical revision. Mixed current/fallback
results SHALL record exact per-reference fallback provenance in profile order.

#### Scenario: Approved policy removed a source
- **WHEN** fallback belongs to another profile/policy or violates a current selection
- **THEN** it is denied rather than restoring obsolete knowledge or authority.

#### Scenario: No current eligible candidate
- **WHEN** matching explicit fallback material is supplied for an unavailable skill
- **THEN** a new result records fallback use and its prior snapshot digest; it does
  not mutate the old snapshot or claim actual approval.

### Requirement: Immutable run binding and no execution authority
Snapshots SHALL freeze complete profile/policy, ordered exact artifacts and catalog/
fallback digests. Resolution SHALL perform no network, ledger or execution effect.
Valid deserialization SHALL mean local self-consistency only, not authenticated
catalog/history/source evidence. Role/interface labels SHALL confer no IAM/tool
rights. Pure policy edits SHALL NOT be described as automatic grant revocation.

#### Scenario: Catalog or instructions change after authorization
- **WHEN** new resolution changes the manifest's skill snapshot digest
- **THEN** existing registry/authorization gates deny the changed run; restoring
  old input does not revive an already committed denial.

#### Scenario: Guidance asks for additional permissions
- **WHEN** skill text asks for installation, credentials or privileged model/tool calls
- **THEN** it remains inert data and cannot create or consume grants or new rights.

#### Scenario: Offline proof does not install a runtime
- **WHEN** local snapshots and synthetic integration tests succeed
- **THEN** actual source authentication, skill loading, UI/hosting and every live
  permission remain separately gated and unproven.
