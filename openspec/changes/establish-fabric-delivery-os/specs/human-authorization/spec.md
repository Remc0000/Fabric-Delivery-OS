## Purpose

Make human authorization an enforced boundary for first substantive work, building and deployment,
independent of agent instructions and private repository plan limitations.

## Implementation status

The human-authorized 2026-11-17 builds implement frozen manifest binding,
durable local single-use consumption, and a read-only native GitHub evidence
observer. Approval objects remain privileged trusted-adapter inputs. The observer
checks authenticated API history against a private registry but cannot convert
its observations into execution grants. A further dependent verifier now checks
official-JWKS OIDC signatures and exact configured signed workload context using
maintained JWT/crypto libraries, not inferred/default subjects. Its observations
also cannot issue grants: signed private inputs, native-review/grant integration,
exact runtime App provenance, and live installation federation are unproven.
Complete native protection verification
(including administrative bypass), reviewer credential provenance, identity
separation, federation, cloud state, worker scheduling, and per-deployment
integration remain required and are not proven by these tests.
Agent-proposal ingestion/authorization is not implemented; no automated issue
adapter may be enabled until the first-substantive-scope boundary below is enforced.

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
Every substantive request, including initial discovery/design on an agent-filed
proposal and later build/deployment requests, SHALL identify the installation, private
solution, unique request ID, action, input/specification or artifact digests,
target baseline, environment where applicable, policy revision, execution
profile, and applicable framework/tool/skill snapshot. Authorization MUST NOT
follow a mutable branch name or replaceable artifact reference.
An authorized human's initial decision SHALL identify the exact requested scope,
revision and enumerated effects, frozen through the same trusted private request
boundary. Issue author identity, labels, assignment, structural validation,
agent reviews and mutable issue text alone MUST NOT provide that decision.
Approval of bounded discovery/design MUST NOT imply build or deployment
authority, and changed scope or revision SHALL invalidate affected prior grants.

#### Scenario: Proposed issue has no human decision
- **WHEN** an agent-created issue requests investigation or implementation without an authorized human decision
- **THEN** new source access, discovery, design, build and deployment are denied
- **AND** permitted proposal creation alone does not move the request into an executable state

#### Scenario: Initial approval covers discovery but not building
- **WHEN** an authorized human approves one exact bounded discovery revision
- **THEN** the grant applies only to its frozen scope and permitted effects
- **AND** specification acceptance, building and each deployment still require their applicable decisions

#### Scenario: An approved proposal is edited to widen access
- **WHEN** requested sources, scope, revision or effects differ from the approved immutable request
- **THEN** affected execution is denied and renewed applicable human approval is required
- **AND** the original issue approval cannot authorize the edited request

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

#### Scenario: An empty pending queue is mistaken for approval
- **WHEN** a run has no pending deployments but no matching approved native environment history
- **THEN** the read-only verifier rejects it rather than inferring a human decision from run success

#### Scenario: A mutable public name points to different authority
- **WHEN** a repository, workflow, environment, reviewer, branch, or revision differs from the private registered binding
- **THEN** native evidence is rejected even if display names or public request labels look unchanged

#### Scenario: Review history cannot identify the execution attempt
- **WHEN** the current native history does not attribute reviews to the requested rerun attempt
- **THEN** the bounded verifier rejects reruns and requires a newly registered run and request

#### Scenario: An API cannot prove a mandatory protection
- **WHEN** administrative bypass, reviewer credential provenance, or federation cannot be verified
- **THEN** read-only observations do not become an execution grant
- **AND** no caller-provided boolean clears that unsupported boundary

#### Scenario: A valid GitHub signature has the wrong installation context
- **WHEN** a signed token has the wrong configured audience/subject, immutable repository/owner ID, workflow revision, ref, run/attempt, or environment context
- **THEN** workload identity verification is denied rather than accepting a generic GitHub-signed JWT

#### Scenario: Token or signing-key evidence cannot be trusted
- **WHEN** a JWT has an unsupported algorithm, invalid signature, invalid validity interval, unknown key, or stale/unavailable official JWKS
- **THEN** verification fails closed without a cached, token-provided, or alternate-origin key fallback

#### Scenario: A newer repository uses a different subject format
- **WHEN** installation policy has not explicitly recorded the actual exact subject
- **THEN** verification is blocked instead of guessing a legacy default subject

#### Scenario: Workload identity is mistaken for input or human authorization
- **WHEN** a token signs a registered run and environment but not the private manifest or native human decision
- **THEN** identity observations do not become an execution grant or private input-content proof
- **AND** native human provenance and one-time request consumption remain independently required

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

#### Scenario: Concurrent callbacks claim one grant
- **WHEN** separate processes consume the same authorized request concurrently
- **THEN** at most one durable execution claim is committed
- **AND** the other callbacks are denied even after the store is reopened

#### Scenario: Approval expires while waiting for the store
- **WHEN** a callback acquires the claim lock at or after approval or request expiry
- **THEN** it commits no execution claim and permanently invalidates the request

#### Scenario: An observed change is reverted
- **WHEN** current trusted input, policy, target, or profile observations invalidate a grant
- **THEN** restoring the old observation does not restore that grant
- **AND** renewed authorization requires a new request

#### Scenario: A service stops after consuming a grant
- **WHEN** a claim commits but execution does not start
- **THEN** restarting the service cannot consume the old request again
- **AND** recovery requires reconciliation and a separately authorized request

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
