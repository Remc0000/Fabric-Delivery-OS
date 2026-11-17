## Purpose

Let independent adopters install and evolve the same framework with their own
repositories, identities, policies, and Azure/Fabric environments.

## ADDED Requirements

### Requirement: Every installation owns its control boundary
The framework SHALL support a public framework source, a separate public
control repository per installation, and private solution repositories.
Adopters MUST NOT depend on the framework author's tenant, credentials,
control repository, or access to another organization's private state.

#### Scenario: A second organization installs the framework
- **WHEN** it onboards its first solution
- **THEN** its requests and identities are isolated from the original installation

### Requirement: Configuration carries adopter choices
Models, regions, capacities, identities, role combinations, modules, skill
sources, and execution/cost limits SHALL be configurable without editing core
runtime code. Configuration changes affecting authority or execution SHALL
require review and invalidate affected requests.

#### Scenario: A user selects a different production capacity
- **WHEN** the configuration change is approved
- **THEN** the platform validates the new mapping before provisioning or deployment
- **AND** existing requests cannot silently use the new target

### Requirement: Module installation is explicit and bounded
The system SHALL support selecting supported modules and their dependencies.
The first release SHALL prove the source-to-Lakehouse-to-semantic-model/report
chain rather than claim complete Fabric workload coverage. Optional app,
streaming, or other modules MUST NOT be silently installed.

#### Scenario: An adopter selects only data engineering modules
- **WHEN** installation calculates requirements
- **THEN** unrelated app or streaming dependencies are excluded

### Requirement: Framework upgrades differ from skill refresh
Framework and control releases SHALL be versioned and pinned per installation.
Their upgrades SHALL be reviewed changes with compatibility and rollback
information. Automatic skill refresh MUST NOT upgrade framework code, control
workflows, authorization policy, or operational permissions.

#### Scenario: A new framework release changes deployment behavior
- **WHEN** it becomes available
- **THEN** an adopter keeps the current version until its upgrade is approved

### Requirement: Product improvement uses governed issues
Framework defects and agent-instruction improvements SHALL use proposed
issues, specification updates, human review, and versioned releases. Agents
MUST NOT silently rewrite their own governing framework based on feedback.
Reference-project ideas SHALL remain deferred until explicitly selected.

#### Scenario: An acceptance failure suggests a better agent strategy
- **WHEN** the improvement affects shared runtime behavior
- **THEN** it becomes a framework proposal rather than an immediate self-modification
