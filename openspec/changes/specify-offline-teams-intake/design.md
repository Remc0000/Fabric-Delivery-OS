## Context and boundary

This is a specification-only refinement of
[`add-teams-experience-layer`](../add-teams-experience-layer/design.md).
The human's 2026-11-26 split permits these documents, not a Teams integration or
simulation described as one. GitHub remains the work/change system of record;
immutable private requests and policy/evidence retain their existing authority.
Teams is an optional experience layer, never an approval or execution ledger.
GitHub-only operation remains independent.

The frozen main-owned
[`build-offline-github-intake` contract](../build-offline-github-intake/design.md)
defines synthetic normalized capture and proposed-only admission. Its future
integration link is main's responsibility; this worker edits no shared document.
The offline adapter neither creates an issue nor authenticates the latest API
metadata, Teams sender, GitHub actor, account/license, OAuth or human approval.

## Goals / Non-Goals

**Goals:** define intent/capture separation, permitted private routing, truthful
receipts, safe feedback/review navigation and observable fail-closed outcomes.

**Non-goals:** implement either Teams route, authenticate identities, design a new
authorization join/decision bridge or live durable coordinator, install apps,
collect private data, call models, approve work or demonstrate deployment readiness.
All live eligibility and integration proofs below remain outstanding.

## Contract decisions

### 1. Separate four objects and their trust

| Object | Permitted meaning | Never evidence of |
| --- | --- | --- |
| Intent candidate | Minimal already supplied text, selected message revision and optional source reference; untrusted and private | Route selection, source access, human identity or scope permission |
| Trusted intake eligibility | Separately authenticated current source-collection authority, exact installation route, repository identity/private visibility/access, permitted content and recipient audience | Discovery/build/deployment approval |
| Immutable GitHub capture | Exact normalized private issue revision from a separately permitted capture path | Current authenticated API state or immutable execution manifest |
| Proposed registry request | Explicit trusted-caller manifest bound independently to capture; awaiting exact human scope | Execution grant, account entitlement or human acceptance |

These are semantic contracts, not a new Teams wire schema, authentication service
or executable coordinator. Candidate attribution records claimed initiator apart
from app/agent issue author; neither is promoted to verified human identity.
Missing source-collection authority blocks collection, even if text is already
visible in a chat. Links/attachments confer no permission to fetch history,
logs, Fabric metadata or additional source records. Model-based clarification
is not assumed: any model input requires its own authenticated private audience,
input-policy and provider-handling proof before transmission.

The exact destination comes only from trusted private installation configuration.
Intent may express a solution need, not select an arbitrary repository. A later
explicit user destination/content review confirms the configured route; it cannot
override policy. Check actual current repository identity, private visibility and
write access independently of user claims, prefilled values or capture flags.
Author permission is not audience permission: check source, target issue audience,
confirmation destination and model recipients separately, before each write/send.
Unknown or failing scope, visibility, content or audience blocks the operation;
post-leakage redaction is not a control.

### 2. Preserve the offline handoff without widening it

For a separately authorized future issue creation/capture path, the normalized
`GitHubIssueSnapshot` version-1 fields remain exactly `schema_version`,
`repository_id`, `repository_private`, `issue_number`, `title`, `body`,
`author_id`, `author_type`, `updated_at`. The GitHub contract owns strict types,
bounded canonical parsing and complete capture digest. Do not inject Teams IDs,
tokens, links-as-authority, approval fields or extra envelope fields into it.
A permitted source link, if intentionally retained in issue body, is private
untrusted provenance and never a fetch permission.

`User`/`Bot` attribution proves no human; an integer timestamp proves no fresh
API observation; a private flag proves no current visibility. Capture digest
binds all capture fields, not source authenticity. The execution manifest input
digest is independently bound, not assumed equal to capture digest. The explicit
initial `discover` manifest admits only a proposed request; it does not start
discovery. No request ID, policy or permission comes from issue/chat text.
Privileged caller state is not an agent tool. The first substantive exact human
scope/revision gate remains later and external, as do specification/build,
implementation review/merge, Dev/Test/production and acceptance decisions.

Private correlation may associate installation, source event/message revision,
tenant/channel/thread, capture/request revision and confirmed issue outcome.
Those mappings stay private; correlation is deduplication context, not identity,
authorization, request approval or public framework metadata.

### 3. Optional paths are separate products, not authority

**Standard GitHub Teams app:** documented create/edit-prefill, comments,
close/reopen, subscriptions and previews are candidate experience features.
The Create an Issue dialog copies message content and a conversation link and
prefills the last-used channel repository. Review the exact configured private
route and minimal permitted content; never silently reuse the channel default.
The documented channel confirmation card itself is an output risk. If creation,
automatic confirmation, notifications or unfurls cannot enforce all recipient
and content checks before output, leave that surface disabled; only a separately
permitted private/manual route is eligible, not an unchecked fallback.

**Channel Agent/GitHub MCP:** public documentation establishes GitHub read
examples, not GitHub issue-write support. Exact supported write tool, scopes,
tenant availability and entitlement remain unknown. Jira/Asana writes do not
prove GitHub writes. Channel membership, assigned Copilot subscription, IT
connected-app permission, active app account and OAuth are prerequisites, not
proof this installation satisfies them or approval to execute.

GitHub Teams documentation separately describes Copilot cloud-agent sessions.
They are not the selected private Azure/Microsoft Agent Framework/Foundry runtime
and stay disabled/outside intake. Block a route if it cannot isolate them.
No invented native Delivery OS approval cards: any future "View GitHub Issue" or
"Review request" control is navigation only. GitHub documents native Actions
approval/rerun controls, but this contract does not enable them, treat them as a
Delivery OS decision bridge or invoke human approval access.

### 4. Feedback is minimal by default, withheld until audience proof

An offline adapter receipt is fixed offline markers and last-recorded state with
`execution_enabled: false`, not a fresh GitHub receipt or authenticated feedback.
Local admission may be described as proposed/awaiting scope only. Actual
"issue created" requires separately verified external creation; running or
delivered states require authoritative current evidence, never inference.

The default projection excludes private repository/issue IDs, title/body, source
detail, model output, URLs/digests, diagnoses and raw errors. A closed allowlist
may report proposed/awaiting scope, blocked, failed, unknown, stale or
reconciliation-required, explicitly identifying whether it is last-recorded or
freshly verified. It carries no private correlation mapping. Status alone is not
permission to publish: safe statuses/references cannot be automatically posted
publicly or to unchecked Teams guests/shared channels.

Public control, if separately permitted, receives only opaque non-authorizing
references and allowlisted status, never private details or mappings. A public
opaque reference is not a Teams correlation ID, private route digest or resolvable
private deep link. This task creates no public receipt or publication mechanism.

Detailed feedback or review links require separate current authenticated private
audience, content/model-input proof and safe preview behavior before delivery.
Check every recipient, including guest/shared-channel members; a sender's GitHub
access or OAuth grant cannot prove that. Failed proof withholds the whole
operation before writing, not automatic "safe" fallback publication. Navigation
grants no access; GitHub/trusted review must independently check current access,
revision and applicable authority. No click, card, comment, emoji, label, author,
agent output/review or consent authorizes discovery, build or deployment.

### 5. Reconciliation is an outcome contract, not implemented coordination

| Condition | Required observable outcome at permitted private operator surface |
| --- | --- |
| Duplicate event/correlation for same frozen intent | Reconcile existing confirmed outcome; no second issue/request, no work replay |
| Replayed correlation with different content/route | Conflict/blocked; do not overwrite mapping or reuse approval |
| Creation timeout/failure after possible write | Unknown/reconciliation-required; no blind resubmit or false success |
| GitHub write confirmed but feedback fails | Preserve confirmed GitHub outcome; expose pending feedback reconciliation, not create again |
| Disconnected feedback/current metadata unavailable | Explicit last-recorded/unknown state; no current-success claim |
| Older/reordered capture or feedback | Cannot replace newer/terminal state; stale/reconciliation-required |
| Changed message/issue/manifest/policy | New proposed revision requires applicable fresh review; terminally invalidated registry proposal cannot revive |

Operator visibility itself obeys private audience/content rules and closed
diagnostics. Retry feedback only after fresh eligibility checks; notification
failure never reruns discovery/build/deployment. If safe correlation/provenance
or order cannot be established, pause and require reconciliation. This specifies
neither storage, transactions, API lookup protocol nor a live recovery service.
The offline registry's replay denial is not a durable Teams deduplication proof.

## Official capability evidence and remaining proof

Public official pages fetched on 2026-11-26; these are bounded product assertions,
not target-tenant verification, installation consent or a working demonstration.
The original M365 chat idea is conceptual and supplies no capability evidence.

- https://docs.github.com/en/integrations/tutorials/teams/create-issues
  Documents standard-app Create an Issue, signed-in GitHub/access prerequisites,
  editable message-derived description plus conversation link, last-used channel
  repository prefill, and a channel confirmation card. These defaults do not
  establish private route/content/audience compatibility.
- https://docs.github.com/en/integrations/tutorials/teams/manage-issues
  Documents standard-app issue comments, close/reopen and PR comments, requiring
  sign-in and relevant repository permissions. They are mutable actions, not grants.
- https://docs.github.com/en/integrations/how-tos/teams/customize-notifications
  Documents event subscriptions, default issue/comment and other events, optional
  reviews/workflows, and separate notification versus agent-session repository
  settings. Subscription availability is channels/personal app, not group chats.
  Native workflow approval/rerun notifications exist but are outside this scope.
- https://docs.github.com/en/integrations/how-tos/teams/use-github-in-teams
  Documents issue/PR thread feedback and resource link previews. Its private-link
  sign-in/app-access conditions do not prove access for all recipients. Also
  documents separate cloud-agent investigation/planning/implementation sessions:
  not enabled here. Use the more specific customization page for subscriptions.
- https://support.microsoft.com/en-us/teams/chat-channels/use-channel-agent-with-jira-asana-and-github
  Documents GitHub MCP read examples (PR comments and completed tasks), OAuth
  consent and channel posting, and prerequisites: assigned Microsoft Copilot
  subscription, channel membership, IT app permission and active connected
  accounts. **Unknown:** GitHub issue-create/write tools and exact eligible SKU;
  this page's Jira/Asana write examples do not establish either.

Also unproven: actual app/tool version and isolation, current metadata/source
authenticity, audience enforcement for automatic outputs/unfurls, human identity
and exact scope evidence, model-input handling, live reconciliation and delivery.
Unknown evidence blocks the dependent feature. No new runtime milestone is done.

## Handoff and validation

Main should link this proposal/design/requirements from the existing Teams change
and the GitHub intake change, and add any shared overview link itself. No main
file is edited here. Validate only this change using the already installed
OpenSpec CLI; validation checks document structure, not live eligibility.
