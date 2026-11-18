## Purpose

Produce reviewable SQL-to-Bronze artifacts from explicit metadata, preserving
human scope, existing targets and separate source/load authority.

## ADDED Requirements

### Requirement: Contracts are explicit metadata, not inferred schema or credentials
The module SHALL require versioned exact source/table/column metadata, supported
Spark types/nullability, finite row/query bounds, an explicit load mode, narrowly
referenced app identity and distinct development/test/production targets.
Duplicate/unknown fields, inline secret values, ambiguous mappings, unsafe JDBC
properties and unsupported types/modes SHALL fail. The compiler MUST NOT read
source records, log private configuration or treat contract fields as approval.

#### Scenario: An input contains an access token or unknown refresh behavior
- **WHEN** configuration supplies inline credentials or an unsupported load mode
- **THEN** compilation fails without exposing input values or enabling work

### Requirement: Artifacts are deterministic and stage substitutions are frozen
The compiler SHALL produce valid ipynb notebook definitions and explicit
InlineBase64 create payloads for all three configured stages. Worker and
configuration cells SHALL be identical across stages; only approved Lakehouse
dependency metadata may differ. The exact emitted files SHALL be content-hashed
in a release manifest, without regeneration during promotion.

#### Scenario: The same reviewed contract is compiled again
- **WHEN** compiler/runtime source and contract bytes represent the same frozen inputs
- **THEN** the resulting stage artifacts and digests are unchanged
- **AND** compilation does not upload, deploy, execute or schedule anything

### Requirement: Export never overwrites private state or publishes values
The CLI SHALL create only a new output directory under private operator-managed
storage and write the completion manifest last. It MUST NOT overwrite existing
files/directories. A partial manifest write or failed exclusive publication
SHALL NOT leave a completion marker. Failure SHALL be visible without printing configuration,
paths, credentials or provider exceptions. Local success SHALL explicitly
mean compiled-not-deployed, with live execution disabled.

#### Scenario: Export fails after some files were written
- **WHEN** storage fails before release.json is committed
- **THEN** the partial directory has no completion manifest and is not a usable release
- **AND** retry does not silently overwrite it

### Requirement: The initial worker performs only explicitly selected create-only snapshots
The initial supported mode SHALL be explicitly selected create_only_snapshot.
The worker SHALL check all targets before credentials/source reads, use explicit
quoted column projection, TLS certificate validation, finite query timeout and
maximum rows plus one, then verify exact source schema/types and required
nonnull values before writing. Over-limit results SHALL fail, not become
silently truncated snapshots. It SHALL add batch/time/source provenance and
write Delta errorifexists, without source mutations, implicit casts, automatic
schema evolution, overwrites, deletes or row output to models.

#### Scenario: A target already exists
- **WHEN** the worker checks its selected targets
- **THEN** it refuses before fetching source credentials or reading source records
- **AND** it preserves existing tables unchanged

#### Scenario: Metadata, nullability or source limits disagree
- **WHEN** a source read exceeds its row ceiling or violates the declared columns/types/nullability
- **THEN** that table is not written and the cached frame is released
- **AND** no source-row samples or values are printed as evidence

### Requirement: Identity and data-loading authority remain external
The bounded worker SHALL use only the explicitly configured app and runtime
Key Vault secret reference through the documented Spark SQL token route.
It MUST NOT use human/default credentials, invent native Copy headless support,
auto-install packages or change tenant/role settings. Separate stage-specific
definition-deployment and source-read/load grants SHALL bind the exact release,
rendered artifact, policy, target baseline, runtime identity and batch parameter.
A batch UUID or local compiler success MUST NOT supply those grants.

#### Scenario: Definitions were approved but a load was not
- **WHEN** a stage has an approved notebook package but no applicable source/load decision
- **THEN** source reading and notebook execution remain unauthorized

### Requirement: Partial failure and unproven platform behavior remain visible
Each table write SHALL be treated as an independent effect. A later failure
MUST NOT imply rollback of earlier tables, cross-table snapshot consistency,
safe automatic job retry or separately approved recovery. Closed progress
events SHALL contain only frozen table indices and started/created codes.
The trusted host must privately capture/join these signals and reconcile actual
effects; missing completion MUST be treated as ambiguous, not proof of no write.
Progress output MUST NOT be described as a durable evidence ledger. Compiler tests and
synthetic runtime doubles SHALL NOT be described as real Fabric execution,
end-to-end medallion/semantic/report delivery or installation acceptance.

#### Scenario: The second table fails after the first was created
- **WHEN** the job stops with partial target state
- **THEN** progress identifies confirmed versus ambiguous writes by frozen index for private reconciliation
- **AND** no table is deleted/recreated or retried without applicable fresh authorization
