## Purpose

Make human authorization an enforced boundary for building and deployment,
independent of agent instructions and private repository plan limitations.

## ADDED Requirements

### Requirement: Human roles are configurable from the first version
The system SHALL distinguish specification/build approver, implementation
reviewer, development deployment approver, test deployment approver, acceptant,
production deployment approver, and installation administrator. Policy SHALL
control allowed role combinations and required separation of duties.

#### Scenario: One-person pilot
- **WHEN** installation policy explicitly permits one person to hold every human role
- **THEN** that person can perform each separately recorded decision
- **AND** no role is assigned to an agent as a substitute

#### Scenario: An organization requires separation
- **WHEN** a proposed assignment violates mandatory role separation
- **THEN** installation or the affected operation is blocked with an explicit reason

### Requirement: Only authorized humans can approve
The system MUST accept approvals only from configured human identities for the
relevant action and installation. Another agent, a service account, a GitHub App,
an agent review, or a token impersonating a human MUST NOT satisfy this boundary.
Agent runtimes MUST NOT receive human approval credentials.

#### Scenario: Two agents agree
- **WHEN** a builder and a review agent both recommend release
- **THEN** release still waits for the required human decision

### Requirement: Authorization binds an immutable execution request
Every build or deployment request SHALL identify the installation, private
solution, unique request ID, action, input/specification or artifact digests,
target baseline, environment where applicable, policy revision, execution
profile, and applicable framework/tool/skill snapshot. Authorization MUST NOT
follow a mutable branch name or replaceable artifact reference.

#### Scenario: Artifact content changes behind the same label
- **WHEN** an artifact label resolves to different bytes after approval
- **THEN** the execution is rejected as a request mismatch

### Requirement: Native approval jobs execute in trusted public control
On GitHub Free, required-reviewer jobs SHALL execute in the installation's
public control repository. The system MUST verify designated human reviewers,
trusted workflow/ref restrictions, and prevention of administrative bypass
before enabling execution. Agents MUST NOT administer these protections.

#### Scenario: A private caller imports a public workflow
- **WHEN** a private workflow calls a public reusable workflow
- **THEN** this alone does not count as a public control approval gate
- **AND** no worker is authorized without the actual protected control run

#### Scenario: Control protection is weakened
- **WHEN** reviewers, visibility, trusted refs, or bypass settings diverge from policy
- **THEN** affected execution is disabled rather than falling back to an unprotected job

### Requirement: Every stage deployment requires separate permission
Build approval, code review, development approval, test approval, functional
acceptance, and production approval SHALL be distinct decisions. Every
deployment attempt to development, test, or production MUST have an explicit
grant for that action and target. Acceptance alone MUST NOT deploy production.

#### Scenario: Development was approved
- **WHEN** an approved development deployment succeeds
- **THEN** test deployment remains blocked until its own approval is granted

### Requirement: Approval is revocable and cannot be replayed
The system SHALL invalidate affected approvals when approved inputs, target
state, policy, or execution profile change. It MUST atomically claim a grant
for one execution attempt and reject duplicate deliveries, stale callbacks,
revoked requests, and reuse for another action. A retry of a mutation SHALL
require a new request and approval.

#### Scenario: A failed production operation is retried
- **WHEN** a previous production request has already been consumed
- **THEN** retry requires a new explicit production grant
- **AND** rerunning the old workflow cannot reuse its approval

### Requirement: Grants define operational side effects
Requests SHALL distinguish deploying definitions, loading data, scheduling
execution, replacing data, destructive changes, and recovery. The approved plan
MUST explicitly enumerate permitted side effects; deployment permission alone
MUST NOT imply permission to start arbitrary data-changing operations.

#### Scenario: Deployment omitted table replacement
- **WHEN** execution would replace a table outside the authorized effects
- **THEN** it stops and requests authorization for the additional operation

### Requirement: Control changes cannot be self-authorized
Agents MUST NOT change their effective permissions, role assignments, approval
policy, trusted runtime, or control workflows. Proposed framework and control
changes SHALL pass human review and a separately approved upgrade path.

#### Scenario: A solution proposes an alternative deployment workflow
- **WHEN** generated solution code includes a workflow that bypasses the control plane
- **THEN** that workflow has no usable execution credentials or privileged runner path
- **AND** the attempted deviation is reported privately
