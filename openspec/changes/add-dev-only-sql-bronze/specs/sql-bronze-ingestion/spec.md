## MODIFIED Requirements

### Requirement: Contracts are explicit metadata, not inferred schema or credentials
The module SHALL require versioned exact source/table/column metadata, supported
Spark types/nullability, finite row/query bounds, an explicit load mode and
narrowly referenced app identity. Version 1 SHALL require distinct development,
test and production targets. Explicit version 2 SHALL require exactly one
development target and SHALL NOT accept later-stage mappings or infer scope
from omitted targets. Duplicate/unknown fields, inline secret values, ambiguous
mappings, unsafe JDBC properties and unsupported types/modes/versions SHALL
fail. The compiler MUST NOT read source records, log private configuration or
treat contract fields as approval.

#### Scenario: A version-1 contract omits Test and production
- **WHEN** a version-1 contract contains only a development target
- **THEN** validation fails rather than implicitly selecting development-only scope

#### Scenario: A development-only contract includes a later stage
- **WHEN** explicit version 2 includes a Test or production target
- **THEN** validation fails before export without fabricating or provisioning targets

#### Scenario: An input contains an access token or unknown refresh behavior
- **WHEN** configuration supplies inline credentials or an unsupported load mode
- **THEN** compilation fails without exposing input values or enabling work

### Requirement: Artifacts are deterministic and stage substitutions are frozen
The compiler SHALL produce valid ipynb notebook definitions and explicit
InlineBase64 create payloads for the stages permitted by the selected contract
version. Version 1 SHALL produce all three configured stages with unchanged
legacy contract digests, notebook/payload bytes and completion-manifest shape
and bytes for unchanged inputs/runtime. Version 2 SHALL produce development
only with a version-2 manifest marking `release_scope: "development_only"` and
`promotion_supported: false`. Worker and configuration cells SHALL remain
identical for identical source/identity/table inputs; only approved Lakehouse
dependency metadata may differ between stages. The exact emitted files SHALL
be content-hashed in a release manifest. A development-only release MUST NOT
be treated as a promotable three-stage release; later delivery requires a
separately reviewed full contract and newly bound release.

#### Scenario: The same reviewed contract is compiled again
- **WHEN** compiler/runtime source and contract bytes represent the same frozen inputs
- **THEN** the resulting stage artifacts and digests are unchanged
- **AND** compilation does not upload, deploy, execute or schedule anything

#### Scenario: An explicit development-only contract is exported
- **WHEN** a valid version-2 contract is compiled and export completes
- **THEN** only development notebook/payload files and its scoped hashed completion manifest exist
- **AND** live execution remains disabled with separate definition/load effects

#### Scenario: A later environment is requested from the Dev-only release
- **WHEN** a future trusted adapter receives a Test or production request for that release
- **THEN** it must refuse rather than retarget a payload, edit the manifest or infer authorization
