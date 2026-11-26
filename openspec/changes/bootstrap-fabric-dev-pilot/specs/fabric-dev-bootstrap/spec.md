## ADDED Requirements

### Requirement: Exact separately approved bootstrap

Bootstrap SHALL create only the explicitly named new Dev workspace and
schema-enabled Lakehouse on the human-selected existing active capacity.

#### Scenario: Capacity is inactive, changed or not approved

- **WHEN** current capacity metadata differs from the confirmed selection
- **THEN** no capacity is resumed, purchased or substituted and creation stops

#### Scenario: Target unexpectedly already exists

- **WHEN** an exact target name is found or ambiguous before creation
- **THEN** no existing resource is modified or deleted and the operator stops

### Requirement: Verified bounded creation

The owner-local bootstrap SHALL verify persisted workspace assignment and
Lakehouse schema metadata, tracking accepted operations without duplicate POSTs.

#### Scenario: Lakehouse creation fails after workspace creation

- **WHEN** a later operation is rejected or its outcome is unknown
- **THEN** the earlier resource is reported privately and retained for human recovery

### Requirement: Installation proof is not delivery authority

Private mappings and tokens SHALL stay out of public artifacts. Bootstrap SHALL
NOT authorize notebook jobs, source records, role/identity changes or later stages.

#### Scenario: Resources are created successfully

- **WHEN** workspace and Lakehouse readbacks match the selected scope
- **THEN** only bounded resource creation is proven; source/runtime/deploy/load gates remain
