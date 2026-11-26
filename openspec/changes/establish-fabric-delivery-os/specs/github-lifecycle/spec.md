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

### Requirement: Agent-created issues are proposals, not work authorization
An agent MAY create proposal issues from observations already authorized for
its current work, without a build grant for the proposed work, only where
repository/visibility policy permits issue creation. Public framework proposals
SHALL contain sanitized reusable information; solution details SHALL remain in
the allowed private solution repository. Proposal creation MUST NOT grant new
source access, discovery, design, implementation or deployment authority.
New agent-filed requests SHALL remain proposed/awaiting approval until an
authorized human approves the exact first substantive requested scope and
revision through the existing immutable human-authorization boundary.
Author identity, labels, assignment, validation, another agent's review and
mutable issue text alone MUST NOT be interpreted as approval.

#### Scenario: An agent proposes an improvement
- **WHEN** an agent files an allowed issue from already authorized observations
- **THEN** the issue remains proposed/awaiting approval with no execution started
- **AND** no new metadata/source access, investigation or design is performed for that proposal

#### Scenario: The agent labels its proposal approved
- **WHEN** an agent adds an approved label, assigns itself or receives another agent's approval
- **THEN** the trusted boundary still denies substantive work without the authorized human decision
- **AND** mutable issue status cannot create an execution grant

#### Scenario: A trusted caller admits a proposal into the offline registry
- **WHEN** immutable local policy, private issue revision and manifest checks pass
- **THEN** the record remains proposed and no execution grant or new source access follows
- **AND** local storage does not prove authenticated issue ingestion, current private inputs or a human decision

#### Scenario: A private observation motivates a public proposal
- **WHEN** an agent has permission to file a reusable framework improvement
- **THEN** it includes only sanitized public information in the permitted repository
- **AND** it does not copy private source details or discover more data to strengthen the proposal

### Requirement: Discovery precedes implementation
Only within an applicable human-authorized discovery/design scope and existing
data-access policy, the system SHALL discover relevant source metadata, existing artifacts, code,
dependencies, and policies before proposing OpenSpec changes. It MUST ask for
missing intent and distinguish observations, assumptions, and proposed business
definitions. Drafting a specification MUST NOT start implementation.

#### Scenario: Business meaning is unknown
- **WHEN** column names suggest a metric without an approved definition
- **THEN** the agent proposes a definition and records its assumptions for review
- **AND** it does not treat the proposal as an accepted business rule

### Requirement: Human checkpoints govern the lifecycle
The system SHALL track first substantive scope authorization, specification review, authorized building, implementation
review, separately authorized deployments, functional acceptance, and delivery.
Human approval of a specification SHALL explicitly identify whether it also
authorizes the corresponding build request. It MUST NOT authorize deployment.
Initial proposal approval SHALL NOT waive the later specification, build,
implementation-review or independent stage-deployment decisions.

#### Scenario: A human approves bounded discovery only
- **WHEN** an authorized human approves the exact frozen revision for a bounded metadata investigation
- **THEN** only that investigation and its enumerated effects may execute under applicable access policy
- **AND** implementation and deployment remain blocked pending their separate applicable approvals

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
