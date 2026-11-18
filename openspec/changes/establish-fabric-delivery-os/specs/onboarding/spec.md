## Purpose

Establish prerequisites and least-privilege installation state explicitly,
without turning a readiness check into permission to alter an environment.

## ADDED Requirements

### Requirement: Preflight reports actual readiness
The system SHALL check applicable CLI versions, skill/tool availability,
authentication, repository features, identities, model access, and Fabric
capabilities. Results SHALL distinguish ready, missing, incompatible,
unauthorized, unknown, and not applicable. Unknown MUST NOT mean permitted.

#### Scenario: A policy cannot be inspected
- **WHEN** the caller lacks access to a required policy
- **THEN** preflight reports the uncertainty and blocks dependent operations
- **AND** it does not infer permission from a successful login

### Requirement: Offline input checks never assert live authorization
The bounded offline operator SHALL validate strict local frozen manifest input,
current validity, optional private spend-plan binding and conservative arithmetic,
and supported Python dependency imports without credentials, API calls, ledger
writes or worker effects. It SHALL expose only allowlisted diagnostic codes,
without echoing private input identifiers, values, paths or raw exceptions.
Missing or unknown local requirements SHALL NOT be reported as passed.
Full installation readiness and execution authorization remain unsupported.

#### Scenario: All supplied offline inputs are valid
- **WHEN** a current manifest, compatible local spend plan and supported imports pass
- **THEN** preflight reports offline checks passed but live execution unsupported
- **AND** it exits with the live-blocked code rather than a successful deployment signal

#### Scenario: The caller mistakes local bounds for available budget
- **WHEN** a supplied prospective maximum fits its local policy cap
- **THEN** offline checks do not claim ledger headroom, authentic pricing or operation authority
- **AND** no reservation, approval or dispatch occurs

#### Scenario: Invalid arguments or private files contain sensitive values
- **WHEN** offline parsing or validation fails
- **THEN** output contains generic failure codes without the supplied values or paths

### Requirement: Tooling checks are task specific
Preflight SHALL assess Azure CLI, Fabric CLI, GitHub CLI/MCP, Microsoft Learn
MCP, and task-specific tooling where required. Rayfin tooling SHALL be checked
for Fabric app work rather than required for every data task. Product names,
authentication methods, and supported versions MUST be verified against current
official documentation before installation.

#### Scenario: A data pipeline task needs no Fabric app tooling
- **WHEN** the selected modules do not use Fabric apps
- **THEN** absent Rayfin tooling is marked not applicable rather than blocking the task

### Requirement: Provisioning and rights require an approved bootstrap plan
The system SHALL propose creation or reuse of GitHub, Azure, Foundry, and Fabric
identities and exact least-privilege grants. A human-authorized bootstrap
identity SHALL perform approved setup. Agents MUST NOT increase their own
rights, register alternate credentials, or reuse interactive human sessions.

#### Scenario: The deployment identity lacks a permission
- **WHEN** a worker encounters a missing grant
- **THEN** it stops and proposes a scoped permission change for human approval

### Requirement: Tenant changes require an explicit instruction
Enabling Fabric MCP exposure, Fabric apps, Rayfin-related capabilities, or
other tenant functions SHALL require both an explicit requested change and
approval by an authorized administrator. Discovery of a missing feature MUST
NOT automatically enable it.

#### Scenario: A tenant feature is disabled
- **WHEN** a task discovers that its required feature is unavailable
- **THEN** it reports the dependency and waits for an approved administrator operation

### Requirement: Workspace capacity is chosen by the adopter
The system SHALL collect and validate capacity selection for each workspace,
allow shared or distinct capacities, and preserve the user's choice. It MUST
check accessibility and workload compatibility before provisioning and MUST
NOT silently choose another capacity or assume a trial.

#### Scenario: All three workspaces use the same selected capacity
- **WHEN** the capacity supports the required workloads and is accessible
- **THEN** the installation can retain that mapping without demanding three capacities

### Requirement: Approval capability is verified before activation
Onboarding SHALL verify the actual target control repository's visibility,
reviewer support, role restrictions, trusted execution context, and Azure
federation. Account membership, repository admin access, and an empty
environment list MUST NOT be considered proof that a protected job can run.

#### Scenario: GitHub rejects the reviewer rule
- **WHEN** the API refuses a required protection for licensing or policy reasons
- **THEN** the installation stays inactive and reports the exact blocker
- **AND** it does not create an unprotected substitute
