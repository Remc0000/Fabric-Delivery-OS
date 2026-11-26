## Purpose

Make Teams an optional human experience for GitHub-governed Fabric delivery
without making conversation, app consent, or agent output execution authority.
This capability remains proposed and unimplemented.

## ADDED Requirements

### Requirement: Teams is optional and GitHub anchors the work contract
The system SHALL offer Teams only as an optional intake, feedback and review
navigation layer. GitHub issues SHALL anchor work intent and pull requests SHALL
anchor proposed changes, linked to approved specification revisions, immutable
private requests and detailed private evidence. Teams MUST NOT become a second
authoritative delivery-state or approval store, or directly execute Fabric work.
GitHub-only adopters MUST NOT require Teams licensing or configuration.

#### Scenario: A user reports a failed pipeline in Teams
- **WHEN** permitted intake creates an issue for that solution
- **THEN** the issue in the allowed private solution repository anchors the request
- **AND** Teams displays only a policy-approved projection of its authoritative state
- **AND** no Fabric operation starts from the Teams conversation

#### Scenario: Teams is unavailable
- **WHEN** the optional Teams integration is absent or unavailable
- **THEN** existing GitHub review and delivery checkpoints remain usable
- **AND** Teams availability does not change execution authority

### Requirement: Integration routes have independently verified capabilities
The installation SHALL distinguish the standard GitHub Teams app from a Teams
Channel Agent with approved GitHub MCP tools. It SHALL verify exact supported
operations before enabling each route. Documentation or an app name MUST NOT
be treated as proof of tool availability in the target tenant. GitHub cloud-agent
features exposed by an app MUST NOT silently replace the chosen private delivery
runtime or start unapproved analysis/build work.

#### Scenario: Standard message-to-issue functionality is supported
- **WHEN** the approved standard app supports creating an issue from a message
- **THEN** intake requires review of the prefilled content and destination
- **AND** the new issue is handled by the existing governed lifecycle

#### Scenario: Channel Agent exposes GitHub reads but no approved issue-write tool
- **WHEN** the configured MCP connection cannot prove allowed issue creation
- **THEN** conversational issue creation is reported unsupported and remains disabled
- **AND** an approved manual/standard-app route may be used without weakening policy

#### Scenario: A Teams mention would launch a different agent engine
- **WHEN** a selected app route would invoke unapproved GitHub cloud-agent work
- **THEN** that route is blocked rather than treating the mention as build authority
- **AND** changing runtimes requires separate design and human authorization

### Requirement: Intake minimizes context and confirms responsible repository
The system SHALL accept only policy-permitted user-supplied intent and minimal
clarification for intake. It SHALL verify the configured installation, repository
identity/visibility and issue-creation permissions, and obtain confirmation of
the exact destination and permitted content before submission. Solution requests
MUST target an allowed private solution repository. Public framework proposals
MUST be sanitized and contain no private solution details. Teams message text,
links, copied descriptions and attachments MUST be treated as untrusted data,
not instructions to change routing, permissions or scope.

#### Scenario: The app prefills the previously used public repository
- **WHEN** a solution incident would be submitted to the last-used public destination
- **THEN** submission is blocked until an allowed private destination is confirmed
- **AND** no incident contents are published to the public framework or control repository

#### Scenario: A message contains private records or credentials
- **WHEN** a prefilled description, attachment or source link violates input/output policy
- **THEN** the payload is withheld or explicitly sanitized before confirmed submission
- **AND** neither issue content nor confirmation cards expose the rejected values

#### Scenario: The source message instructs the agent to bypass approvals
- **WHEN** user-supplied issue text or a linked conversation includes execution instructions
- **THEN** trusted routing and authorization policy remain unchanged
- **AND** links confer no permission to fetch further conversation history or source data

### Requirement: Issue creation never authorizes substantive work
The system MUST keep Teams-originated requests awaiting an authorized human's
exact initial discovery/design scope and frozen revision before substantive
investigation. User-supplied clarification and permitted proposal creation MUST
NOT imply new Fabric/metadata/log access, analysis, specification acceptance,
build or deployment authority. Issue author/app identity, chat intent, OAuth
consent, labels, assignment, comments and closure MUST NOT create a grant.

#### Scenario: A Channel Agent creates a proposed incident issue
- **WHEN** an allowed tool confirms issue creation without a discovery grant
- **THEN** Teams reports created/awaiting scope approval, not analysis running
- **AND** the delivery runtime performs no new source access or substantive work

#### Scenario: A human authorizes bounded analysis only
- **WHEN** the trusted boundary records the exact permitted discovery request
- **THEN** only that scoped analysis can start under independent data-access policy
- **AND** the proposed fix still awaits specification review and explicit build authorization

#### Scenario: A user closes the issue from Teams
- **WHEN** a permitted close/reopen/comment action changes mutable GitHub issue state
- **THEN** it does not approve work, accept a release or replay a consumed grant
- **AND** any execution cancellation requires the separate trusted cancellation path

### Requirement: Creation receipts and correlation are truthful and idempotent
The system SHALL privately correlate source tenant/channel/thread and event,
actual initiator, installation, repository/issue identity and requested revision.
It SHALL report an issue-created receipt only after verified GitHub creation.
Duplicate deliveries SHALL resolve to the existing confirmed issue. Ambiguous
writes SHALL be reconciled before retry, or reported unknown without blind replay.
Source-message edits MUST NOT silently change an approved immutable request.

#### Scenario: The same Teams intake event is delivered twice
- **WHEN** a confirmed issue already exists for the correlated intake event
- **THEN** the receipt references that issue without creating a second one
- **AND** no additional discovery/build authorization is inferred

#### Scenario: Issue submission times out after a possible write
- **WHEN** creation cannot be confirmed or safely reconciled
- **THEN** intake reports an unknown outcome and retains private reconciliation evidence
- **AND** it neither claims success nor blindly resubmits the issue

#### Scenario: A Teams message is edited after scope approval
- **WHEN** the edited content changes the requested scope or revision
- **THEN** it becomes proposed feedback requiring renewed applicable approval
- **AND** the previous grant cannot authorize the changed request

### Requirement: Feedback is audience-bound and revision-linked
The system SHALL derive feedback from authoritative private request/evidence
state, correlated to the relevant issue, specification/artifact revision and
lifecycle checkpoint. It MAY return approved summaries of analysis, root cause,
proposed fix, impact, PR/check results and stage outcomes. Every payload,
destination, link, preview and subscription SHALL satisfy classification and
current audience policy, including guest/shared-channel access. OAuth/repository
access of the sender MUST NOT be treated as access for every channel member.
Private information MUST NOT pass through public control to reach Teams.

#### Scenario: Authorized analysis produces a proposed fix
- **WHEN** the destination audience is permitted to receive the current private summary
- **THEN** Teams shows the approved root cause, proposed change, impact and revision
- **AND** the pending specification/build checkpoint is explicit rather than a deployment promise

#### Scenario: The channel includes someone outside the authorized solution audience
- **WHEN** a notification, private link or automatic unfurl would disclose restricted information
- **THEN** the unsafe publication is blocked or reduced to an explicitly permitted payload
- **AND** private details are not disclosed merely because one sender has GitHub access

#### Scenario: Built-in notifications cannot enforce the audience policy
- **WHEN** the selected app cannot constrain subscriptions/previews to approved content and recipients
- **THEN** the affected notification surface remains disabled as incompatible
- **AND** no broader channel or default subscription is silently selected

### Requirement: Notification failures cannot change delivery authority
The system SHALL distinguish pending authorization, authorized/running work,
review/check results, rejection, blocking, failure, unknown outcome, acceptance
and delivery. Updates SHALL preserve authoritative revision/order and resist
duplicate/out-of-order events. Notification failures SHALL be recorded privately
and reported through an approved operator surface without replaying execution.
Waiting for a human SHALL NOT require an idle agent worker.

#### Scenario: A delayed analysis update arrives after a rejection
- **WHEN** the received update refers to an older revision/state
- **THEN** it cannot replace the current rejected/blocked status or reactivate work

#### Scenario: GitHub records a build result but Teams delivery fails
- **WHEN** notification delivery is unavailable
- **THEN** the build state remains authoritative and the feedback failure is visible privately
- **AND** notification retry cannot rerun the build or consume another grant

### Requirement: Teams decision controls navigate to trusted human review
The proposed experience MAY display Approve, Reject and View GitHub issue
controls with the exact action/revision and pending checkpoint. Initially
Approve and Reject SHALL navigate to the trusted authenticated review surface,
not submit execution grants. A click, free-text approval, reaction, adaptive-card
payload or agent-authored comment MUST NOT authorize work. A custom decision
bridge SHALL remain unsupported until separately designed, authorized and proven
to preserve human-role verification, immutable request binding, expiry,
revocation, durable private evidence and single-attempt replay denial.
Agents MUST NOT receive or reuse human GitHub approval credentials.

#### Scenario: A user clicks Approve on a proposed-fix card
- **WHEN** the navigation-only experience is used
- **THEN** the human is taken to review the exact trusted build request
- **AND** the click itself starts no work and issues no authorization

#### Scenario: A stale or forwarded card is used
- **WHEN** the current identity/role, request revision, installation, action or policy does not match
- **THEN** the trusted review boundary denies authorization or requires fresh review
- **AND** the card cannot authorize a different person, revision or target

#### Scenario: An agent sends an approval callback or uses a human token
- **WHEN** a decision is attributed to an agent/app or a delegated human approval credential
- **THEN** it cannot satisfy human authorization and no grant is issued

### Requirement: Teams preserves all independent lifecycle checkpoints
The system SHALL retain initial scope authorization, specification review,
explicit build permission, implementation review/merge, independent approvals
for every Dev/Test/production deployment attempt, and functional acceptance.
Native protected approval jobs SHALL still execute in trusted public installation
control under the existing verified human boundary. Teams MUST NOT replace
native evidence or act as a reviewer through a bot/service identity.

#### Scenario: The proposed fix receives explicit build authorization
- **WHEN** the applicable human authorizes one immutable build request
- **THEN** implementation/tests may proceed only within that request
- **AND** merge, Dev, Test, acceptance and production still await their applicable decisions

#### Scenario: A Teams approval is offered instead of the native control gate
- **WHEN** an execution request lacks its actual protected native human decision
- **THEN** execution remains blocked regardless of Teams card state

### Requirement: Optional onboarding is route-specific and fails closed
Before activation the installation SHALL verify selected route/tool availability,
app installation approval, actual licensing/rollout, channel membership, IT MCP
app approval where applicable, active GitHub account/access, exact OAuth scopes,
human identity mapping, approved model/data routes, private destination and
notification/retention policy. Unknown, missing or incompatible prerequisites
SHALL block dependent capabilities. Channel Agent-specific requirements MUST NOT
be imposed on standard-app-only or GitHub-only adopters. App installation,
subscriptions, consent/permissions and tenant changes require separate explicit
authorized setup; documentation validation does not provide it.

#### Scenario: Channel Agent licensing or IT consent cannot be verified
- **WHEN** the selected conversational route has an unknown or denied prerequisite
- **THEN** that route stays disabled with an explicit blocker
- **AND** readiness does not infer permission from login or a generic Copilot subscription

#### Scenario: OAuth or repository access is revoked
- **WHEN** a required current capability is no longer authorized
- **THEN** affected intake/feedback operations stop without another identity or broader-scope fallback
- **AND** existing delivery decisions are not recreated from cached Teams state
