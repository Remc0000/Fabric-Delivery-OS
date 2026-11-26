## ADDED Requirements

### Requirement: Teams remains a specification-only optional experience
The contract SHALL define future Teams intake, feedback and review navigation
only. GitHub SHALL remain the work/change system of record with existing private
immutable request/evidence boundaries. This change MUST NOT authorize a connector,
approval bridge, authorization join, coordinator, setup, live access, model call
or deployment. GitHub-only use SHALL remain independent.

#### Scenario: Documents validate successfully
- **WHEN** this change passes structural validation
- **THEN** only specification structure is verified
- **AND** no runtime, tenant eligibility or human acceptance is claimed

### Requirement: Collection requires source authority and trusted exact private route
Future intake SHALL accept only minimal policy-permitted supplied intent after
current source-collection authority is established. Exact repository identity
SHALL come from trusted private installation configuration, with current private
visibility, access, issue audience and content checks before writing. Confirmation
SHALL review that configured route, never override it. Untrusted intent, message
links, attachments and attribution MUST NOT choose arbitrary repositories,
authorize additional reads or alter policy. Failing or unknown source authority,
scope, visibility, content or audience SHALL block collection/transmission/write.

#### Scenario: Source authority is missing
- **WHEN** a visible message has no verified collection authority
- **THEN** intake collects no message/history/attachment or model input
- **AND** no issue is created and a permitted closed blocker is available privately

#### Scenario: App prefills a last-used or user-requested wrong repository
- **WHEN** a solution request targets a public, wrong or unverified repository
- **THEN** no submission occurs
- **AND** only the reviewed exact trusted private route can become eligible

#### Scenario: Content and all target audiences are permitted
- **WHEN** current source authority, configured private route/access and reviewed minimal content satisfy separate source/issue/output audience checks
- **THEN** the future selected supported route may create the permitted issue
- **AND** the outcome remains proposed and awaits the later exact human scope gate

#### Scenario: Source link or prefilled description would leak
- **WHEN** message content, conversation URL or automatic confirmation violates policy
- **THEN** the affected collection/write/send is blocked before disclosure
- **AND** after-the-fact redaction is not accepted as successful enforcement

### Requirement: Intent and immutable capture do not authenticate or approve work
Intake SHALL distinguish untrusted intent, separately established eligibility,
immutable normalized GitHub capture and explicit proposed registry admission.
The capture SHALL preserve the exact version-1 GitHub contract without Teams or
approval fields; its digest SHALL bind capture fields independently of manifest
input digest. Capture flags/timestamp, claimed Teams sender, GitHub `User`/`Bot`,
proposed registry state, account/license and OAuth MUST NOT be treated as fresh
authenticated API metadata, human identity or human scope approval.
Initial `discover` admission SHALL remain proposed with execution disabled.

#### Scenario: Text claims approval and author type is User
- **WHEN** a supplied chat or captured issue says to start work and attribution is `User`
- **THEN** its text and attribution remain inert private data
- **AND** no discovery, design, build, grant, reservation or dispatch starts

#### Scenario: Offline adapter accepts a normalized capture
- **WHEN** explicit capture and discover manifest satisfy local registry policy
- **THEN** one immutable proposed record may exist with independently bound digests
- **AND** no current GitHub metadata, Teams identity or live readiness is proven

#### Scenario: Message or capture changes after proposal
- **WHEN** source content, issue revision, route, manifest or policy drifts
- **THEN** the changed intent requires a new applicable proposed review
- **AND** a terminally invalidated registry proposal cannot revive by restoring old input

### Requirement: Product paths require separate capability evidence
The installation SHALL distinguish standard GitHub Teams app from Channel
Agent/GitHub MCP. Unknown actual tool, entitlement, account, consent or tenant
support SHALL block dependent features. Documented standard creation SHALL NOT
prove Channel Agent GitHub writes. Channel Agent prerequisites MUST NOT be
imposed on standard-app-only or GitHub-only operation. GitHub cloud-agent
sessions SHALL remain disabled/outside the selected private Azure/Agent
Framework/Foundry runtime; inability to isolate them SHALL block the route.

#### Scenario: Channel Agent read support is the only verified GitHub scope
- **WHEN** documentation or installed capability evidence proves reads but not the required GitHub issue-write tool
- **THEN** Channel Agent issue creation remains unknown/disabled
- **AND** Jira/Asana write examples or a generic Copilot subscription do not satisfy proof

#### Scenario: Standard app automatic outputs cannot be constrained
- **WHEN** creation confirmations, subscriptions or previews lack pre-output policy enforcement
- **THEN** the affected surface remains disabled
- **AND** there is no fallback to a broader channel, identity or cloud-agent session

### Requirement: Default feedback is detail-free and not automatically publishable
Default feedback SHALL contain only closed allowlisted status/offline markers,
with last-recorded versus freshly verified provenance distinguished. It MUST NOT
contain private repository/issue identifiers, title/body, source details, model
output, URLs/digests, diagnoses or raw errors. Even safe status/reference receipts
SHALL require current authorized destination/audience proof before delivery and
MUST NOT be automatically posted publicly or to unchecked guest/shared channels.
Public control MAY receive separately permitted opaque non-authorizing references
and allowlisted status only, never private details or correlation mappings.

#### Scenario: Local registration returns a receipt
- **WHEN** the offline proposed receipt is serialized
- **THEN** only fixed offline markers and last-recorded state with execution disabled are exposed
- **AND** it is not represented as verified external issue creation or authenticated feedback

#### Scenario: Generic receipt targets an unchecked shared channel or public control
- **WHEN** no separate current publication/audience authorization exists
- **THEN** even the detail-free receipt is withheld before sending
- **AND** no private identifier, correlation mapping or safe-looking URL is published

### Requirement: Private details and navigation require separate authenticated audience proof
Detailed feedback, source/model context and private review URLs SHALL require
current separate authenticated private audience, content/model-input and preview
policy proof before transmission. Sender/author repository permission or OAuth
SHALL NOT prove channel/guest/shared audience permission. Unknown or failed proof
SHALL block the send before write, not redact after leakage. A View GitHub Issue
or review-navigation action SHALL grant no access and SHALL NOT approve work.
No Teams card/button/comment/emoji, label, issue author, agent output/review or
OAuth consent SHALL authorize execution or replace existing independent gates.

#### Scenario: A permitted private audience receives a review link
- **WHEN** all current recipient/content/preview proofs and authoritative revision checks pass
- **THEN** only the separately permitted detail and navigation may be sent
- **AND** clicking requires independent GitHub/trusted-review access and starts no work

#### Scenario: Author has access but a guest does not
- **WHEN** the sender can access the repository but any destination recipient is unverified or unauthorized
- **THEN** detail, status, link and unfurl publication is blocked before output
- **AND** no public or wider-channel fallback is automatically attempted

#### Scenario: An approval-looking control or consent is invoked
- **WHEN** a user clicks a card, reacts, comments, changes a label or grants OAuth
- **THEN** no execution grant is issued and no discovery/build/deployment starts
- **AND** later exact human scope, specification/build, merge, stage and acceptance gates remain separate

### Requirement: Correlation and ambiguous outcomes require visible reconciliation
Teams correlation SHALL be private non-authorizing deduplication context, never a
public private-to-control mapping. Duplicate confirmed intake SHALL reconcile
without a second issue/request or work replay. Conflicting/replayed correlation
SHALL block rather than overwrite a frozen mapping. Failure after possible write
SHALL show unknown/reconciliation-required at a permitted private operator surface,
without false success or blind resubmission. This contract SHALL NOT claim the
offline registry implements a live durable Teams coordinator.

#### Scenario: Confirmed intake is replayed
- **WHEN** the same correlated frozen intent is delivered again
- **THEN** the future route resolves the confirmed existing outcome or pauses for reconciliation
- **AND** no second issue/request or resumed execution is created

#### Scenario: Replayed correlation carries altered intent
- **WHEN** a correlation is reused with different content, revision or route
- **THEN** intake reports a private closed conflict/blocker
- **AND** neither private mapping nor previous approval is overwritten or reused

#### Scenario: Creation times out after a possible GitHub write
- **WHEN** external creation cannot be independently confirmed or safely reconciled
- **THEN** the outcome is unknown/reconciliation-required, not created or safely failed
- **AND** there is no blind creation retry or successful fallback receipt

### Requirement: Feedback failure and revision disorder cannot change authority
Feedback SHALL reflect authoritative current revision/state or explicitly marked
last-recorded/unknown state. Stale, reordered or disconnected feedback SHALL NOT
replace newer/terminal state or claim running/delivered success. A confirmed
GitHub write with failed Teams output SHALL retain its outcome with visible
private feedback reconciliation. Retrying feedback SHALL recheck eligibility and
SHALL NOT replay issue creation, discovery, build, grant consumption or deployment.

#### Scenario: Older running update follows rejection or newer revision
- **WHEN** delayed feedback is older than the authoritative terminal or revised state
- **THEN** it is rejected as stale or held for reconciliation
- **AND** it does not resurrect a proposal or replace current status

#### Scenario: Feedback disconnects after confirmed creation
- **WHEN** GitHub creation is verified but Teams delivery fails or freshness cannot be checked
- **THEN** confirmed creation remains recorded privately and feedback is pending/unknown
- **AND** a later eligible feedback retry creates no duplicate issue and claims no fresh success without evidence
