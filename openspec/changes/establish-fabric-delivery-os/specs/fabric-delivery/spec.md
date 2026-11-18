## Purpose

Deliver reviewable Fabric changes for both new and existing solutions while
preserving stage isolation, data correctness, and explicit operational authority.

## Implementation status

The separately authorized 2026-11-18 `build-sql-bronze-module` change supplies
the first bounded offline artifact compiler and fixed create-only Bronze Spark
worker source. It does not complete this broader capability: real metadata,
identities, deployed/runtime verification, existing-table changes, Silver/Gold,
semantic models/reports and live stage/load acceptance remain outstanding.

## ADDED Requirements

### Requirement: New and existing targets are both supported
The system SHALL plan creation for new targets and bounded changes for existing
ones. It MUST inventory relevant dependencies, source-controlled definitions,
runtime drift, and downstream impact before modification. Existing unrelated
artifacts MUST NOT be replaced merely because a template lacks them.

#### Scenario: A target workspace already contains reports
- **WHEN** an issue changes a model used by those reports
- **THEN** the plan identifies affected reports and compatibility requirements
- **AND** preserves unrelated content

### Requirement: Modules publish verifiable delivery contracts
Each supported module SHALL declare discovery, planning, artifact production,
validation, deployment, environment parameterization, and recovery behavior.
Unsupported item types or API/identity combinations MUST be reported before
provisioning. A listed skill alone MUST NOT imply implemented workload support.

#### Scenario: A report format cannot be safely deployed with the available APIs
- **WHEN** planning selects the reporting module
- **THEN** it blocks that delivery scope rather than claiming the report was delivered

### Requirement: Three environments have separate responsibilities
The first release SHALL support development, test, and production workspaces.
Naming SHALL be configurable, with the solution name used without a production
suffix in the reference convention. Test acceptance SHALL be bound to a stable
release and suitable data snapshot or documented watermark.

#### Scenario: New development occurs during acceptance
- **WHEN** another approved build is produced
- **THEN** it does not overwrite the release or data baseline under acceptance
- **AND** replacing that test baseline requires a separately approved deployment

### Requirement: Promotion preserves the reviewed artifact
Deployment SHALL promote the approved artifact digest and explicitly allowed
environment parameters rather than regenerate code at each stage. The system
MUST verify dependencies, capacity compatibility, permissions, and drift
before applying effects.

#### Scenario: Production requires a code fix after test acceptance
- **WHEN** the proposed package differs from the accepted package
- **THEN** it returns through the necessary build and test approvals
- **AND** the previous acceptance cannot authorize the modified package

### Requirement: Data and business correctness have acceptance evidence
Plans SHALL define table grain, keys, relationships, transformation rules,
reconciliation, data-quality expectations, semantic measures, report behavior,
and repeat-run checks relevant to the requested solution. Business definitions
MUST be proposed for human approval rather than inferred as facts.

#### Scenario: A semantic measure reconciles incorrectly
- **WHEN** its agreed acceptance check fails
- **THEN** delivery remains failed or blocked with private evidence
- **AND** a visually successful report cannot override the failed check

### Requirement: Failures and recovery do not hide data loss
Deployments SHALL be idempotent where supported and record partial effects.
Recovery SHALL distinguish item-definition restoration, data restoration,
reprocessing, and irreversible operations. Recovery mutations require explicit
authorization and MUST NOT be described as guaranteed data rollback.

#### Scenario: Deployment fails after creating some items
- **WHEN** the platform prepares recovery
- **THEN** it lists completed effects and proposes an approved repair or rollback
- **AND** it does not silently delete or recreate resources
