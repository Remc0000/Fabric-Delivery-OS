## Purpose

Run bounded agent tasks on adopter-owned Azure compute while keeping model
reasoning, authorization, and deterministic deployment separate.

## ADDED Requirements

### Requirement: Agent roles use explicit execution profiles
The system SHALL provide bounded discovery/specification, building, and review
profiles with explicit models, skills, tools, inputs, and output contracts.
Model access SHALL use configured Foundry deployments rather than assume that
GitHub AI credits pay for direct model calls.

#### Scenario: A role has no usable model deployment
- **WHEN** its configured deployment is inaccessible or unsupported
- **THEN** the task is blocked without silently changing provider or deployment

### Requirement: Workers have no ambient authority
Agent tasks SHALL run in isolated, clean execution environments without human
tokens, control-plane credentials, deployment credentials, inherited host
identities, shared privileged sockets, or reusable secrets from earlier jobs.
Untrusted generated code MUST NOT execute on a privileged control runner.

#### Scenario: Generated code tries to access production credentials
- **WHEN** a build task inspects its environment, host metadata, or shared storage
- **THEN** it cannot obtain a production or control-plane credential
- **AND** access attempts are recorded in private operational evidence

### Requirement: Tools enforce scope outside the model
The system SHALL validate tool requests against the role, request, resource,
and data policy in a trusted layer outside agent control. Repository writes
SHALL be mediated without exposing broad GitHub installation tokens to agents.
Prompt instructions and tool descriptions MUST NOT be the authorization boundary.

#### Scenario: An agent requests an out-of-scope repository write
- **WHEN** a tool call targets a control repository or an unrelated solution
- **THEN** the trusted tool boundary refuses it regardless of the model's rationale

### Requirement: Deployment is not an autonomous agent action
Deployment SHALL use fixed, reviewed orchestration with a separate identity per
target environment. It MUST consume only the approved package and permitted
parameters, and MUST NOT evaluate arbitrary solution or skill scripts with its
deployment credentials.

#### Scenario: A package contains an executable install hook
- **WHEN** that hook is not part of reviewed deployment orchestration
- **THEN** the deployment worker refuses to execute it with privileged access

### Requirement: Execution has visible bounds and failures
The system SHALL enforce configured finite time, tool-call, iteration, and
retry bounds and configurable cost/token controls. No financial cap SHALL be a
supported explicit configuration, not permission for unbounded loops.
Exhausted bounds and tool/model failures MUST produce a visible blocked or
failed state rather than success-shaped output.

#### Scenario: An agent repeatedly fails a validation
- **WHEN** its configured iteration bound is reached
- **THEN** it stops with evidence and the unresolved issue instead of looping indefinitely

### Requirement: Execution is reproducible and cancellable
Workers SHALL record their input and runtime snapshots and support cancellation
before additional effects. Completed or cancelled workers MUST NOT leave
credentials or persistent execution paths available for later requests.

#### Scenario: A request is cancelled while waiting to execute
- **WHEN** a queued worker claims the request
- **THEN** it observes cancellation and performs no authorized mutation
