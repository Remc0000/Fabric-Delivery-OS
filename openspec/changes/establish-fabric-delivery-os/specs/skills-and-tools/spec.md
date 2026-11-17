## Purpose

Give agents current Fabric expertise and task-appropriate tools without
letting downloaded guidance change authorization or installation policy.

## ADDED Requirements

### Requirement: Role profiles select relevant expertise
Fabric engineering profiles SHALL include applicable Skills for Fabric.
Profiles SHALL select Azure, Foundry, GitHub/OpenSpec, and testing guidance as
needed. Fabric app profiles SHALL also consult the Microsoft Rayfin repository
and relevant Rayfin skills. Skills, MCP connections, CLIs, and model endpoints
MUST be represented as distinct dependency types.

#### Scenario: A Foundry skills endpoint is supplied
- **WHEN** onboarding classifies the dependency
- **THEN** it verifies the endpoint's actual integration model instead of treating it as a local skill package

### Requirement: Approved skill sources update automatically
The system SHALL check and acquire newer compatible skills from approved
sources automatically for future tasks, without a separate human review for
each ordinary knowledge update. It MUST record origin, immutable revision,
content digest, and compatibility results.

#### Scenario: A compatible update is available
- **WHEN** a new task resolves its skill set
- **THEN** it selects the updated approved skill and records the exact snapshot

### Requirement: Updates do not change an authorized run
A running or approved execution SHALL use its recorded skill snapshot.
Discovering an update MUST NOT replace that snapshot midway through the task.
A request using a different snapshot SHALL obtain any affected build or
deployment authorization again.

#### Scenario: A skill changes after build approval
- **WHEN** the worker starts the already approved request
- **THEN** it uses the approved snapshot or stops if that snapshot is unavailable
- **AND** it does not silently run the newer instructions

### Requirement: Failed or expanded updates are contained
An unverifiable or incompatible update SHALL be quarantined with an explicit
status. Using a last-known-good snapshot MUST be visible. New sources,
capabilities, script execution permissions, or credentials MUST require the
applicable human-approved policy change.

#### Scenario: An updated skill asks for tenant administration
- **WHEN** its role previously had no tenant administration rights
- **THEN** the update cannot grant or exercise those rights

### Requirement: Scripts and package operations follow approved channels
Skills SHALL be treated as untrusted input at the authorization boundary.
Package installations, CLI changes, and setup scripts MUST follow the
installation's approved sources, feeds, and bootstrap permissions. A skill
instruction MUST NOT cause an unapproved install or bypass a blocked feed.

#### Scenario: A setup script would fetch from an unapproved package feed
- **WHEN** the dependency check detects that requirement
- **THEN** it reports a blocker instead of fetching from another public endpoint

### Requirement: Product guidance has attributable evidence
Material product claims SHALL link to current official documentation or
explicitly marked assumptions. Microsoft Learn MCP SHALL be available to
applicable profiles, while GitHub CLI or MCP SHALL be selected according to
installation policy rather than copied from an unrelated agent runtime.

#### Scenario: Skill advice conflicts with current product documentation
- **WHEN** the conflict affects the proposed implementation
- **THEN** the agent records it and seeks resolution instead of inventing compatibility
