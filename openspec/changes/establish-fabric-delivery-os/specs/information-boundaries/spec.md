## Purpose

Keep private solution information outside public control surfaces and restrict
what models can receive, including indirect tool and diagnostic output.

## ADDED Requirements

### Requirement: Public processing uses an explicit output allowlist
The public framework and control repositories SHALL contain only intended
public material. Public runs MUST NOT receive private source identifiers,
repository mappings, code, prompts, model output, data, manifests, or raw worker
logs. They SHALL use opaque request references and allowlisted status fields.

#### Scenario: A worker error includes a private source name
- **WHEN** the error is published to the public control run
- **THEN** only an approved generic status is emitted and the diagnostic remains private

### Requirement: Public operational metadata is disclosed
Onboarding SHALL explain that public control workflow definitions, run
existence, timing, actor information exposed by GitHub, and stage labels can
be visible. An installation whose policy forbids these disclosures MUST NOT
activate this architecture.

#### Scenario: A company requires private control metadata
- **WHEN** its policy disallows public run timing or approval actor exposure
- **THEN** the three-repository Free architecture is reported as incompatible

### Requirement: AI source-record access is denied by default
Each solution SHALL define model-input policy. The default MUST deny source
records, samples, raw query output, unclassified aggregates, screenshots,
exceptions, and logs containing business data. Structural metadata also MUST
be subject to an explicit allowed schema or field policy.

#### Scenario: A metadata query unexpectedly returns sample values
- **WHEN** the response is prepared for the model
- **THEN** the response is withheld or sanitized according to policy
- **AND** no unclassified values are passed through as ordinary tool text

### Requirement: Data processing and model access remain distinct
Authorized Fabric operations SHALL be able to process source data without
returning that data to an agent. The model SHALL receive only policy-approved
check results. Broader AI access MUST be explicitly authorized per solution
and MUST NOT exceed organization policy.

#### Scenario: A reconciliation check operates on source records
- **WHEN** the check finishes inside the approved data environment
- **THEN** the agent receives only the permitted control result, not the underlying rows

### Requirement: Private configuration and secrets remain separate
Repository and workspace mappings, capacity choices, role assignments, policy,
and detailed evidence SHALL remain in the private installation boundary.
Secrets SHALL be stored in approved secret services and referenced rather
than committed. Worker/model telemetry MUST follow the same classification
rules as tool outputs.

#### Scenario: A configuration includes an access token
- **WHEN** it is prepared for storage in any repository
- **THEN** it is rejected and redirected to approved secret storage

### Requirement: Model routing is an explicit data decision
The installation SHALL record approved model providers, deployments, regions,
and relevant data-handling constraints. Running on an Azure worker MUST NOT
be represented as proof that all downstream tools or model calls stay inside
the same tenant or geography.

#### Scenario: A configured model route changes jurisdiction
- **WHEN** the route no longer satisfies the approved data policy
- **THEN** affected agent calls are blocked pending an approved configuration change
