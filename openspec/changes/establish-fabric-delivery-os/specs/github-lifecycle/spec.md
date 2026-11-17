## Purpose

Keep user intent, approved specifications, delivery work, and feedback linked in
GitHub without allowing process automation to replace human decisions.

## ADDED Requirements

### Requirement: Issues belong to the responsible product
The system SHALL accept solution requests in the private solution repository and
framework defects or improvements in the framework repository. It MUST preserve
links between related work without copying private details into public issues.

#### Scenario: A solution exposes a framework defect
- **WHEN** a private solution task identifies a reusable framework defect
- **THEN** a proposed public issue contains only sanitized framework information
- **AND** the private issue retains the detailed reproduction and linkage

### Requirement: Discovery precedes implementation
The system SHALL discover relevant source metadata, existing artifacts, code,
dependencies, and policies before proposing OpenSpec changes. It MUST ask for
missing intent and distinguish observations, assumptions, and proposed business
definitions. Drafting a specification MUST NOT start implementation.

#### Scenario: Business meaning is unknown
- **WHEN** column names suggest a metric without an approved definition
- **THEN** the agent proposes a definition and records its assumptions for review
- **AND** it does not treat the proposal as an accepted business rule

### Requirement: Human checkpoints govern the lifecycle
The system SHALL track specification review, authorized building, implementation
review, separately authorized deployments, functional acceptance, and delivery.
Human approval of a specification SHALL explicitly identify whether it also
authorizes the corresponding build request. It MUST NOT authorize deployment.

#### Scenario: Specifications are approved without a build grant
- **WHEN** the current specifications are accepted but no build request is authorized
- **THEN** implementation remains blocked and GitHub shows the missing authorization

### Requirement: Review and feedback remain attached to a revision
The system SHALL link implementation pull requests to their issue and approved
specification revision. Agents MUST NOT approve or merge their own work.
Rejected specifications or acceptance results SHALL return the task to the
appropriate earlier step without discarding the feedback.

#### Scenario: Acceptance feedback changes the requested behavior
- **WHEN** feedback requires behavior outside the approved specification
- **THEN** the specification is revised and returned for human approval
- **AND** the old approval does not authorize the changed build

### Requirement: Evidence distinguishes progress from authorization
The system SHALL record request state, approved inputs, artifact digests,
framework and skill versions, model deployment, checks, actors, and stage
outcomes in private evidence linked from GitHub. A passed check, completed
OpenSpec artifact, agent recommendation, or issue closure MUST NOT be an approval.

#### Scenario: Document validation passes
- **WHEN** a specification passes structural validation
- **THEN** the issue reports validation separately from its human approval state
- **AND** the platform does not start a build solely because validation passed

### Requirement: Concurrent and resumed work preserves request identity
The system SHALL isolate independent requests and serialize conflicting
mutations of the same target. Resume operations MUST recheck request state,
authorization, and drift. Waiting for human input MUST NOT require an idle
agent worker to remain running.

#### Scenario: A delayed run resumes after its target changed
- **WHEN** a pending request resumes against a different target baseline
- **THEN** the platform stops for impact assessment and renewed authorization
- **AND** it does not silently rebase the approved operation
