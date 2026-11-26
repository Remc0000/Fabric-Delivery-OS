## ADDED Requirements

### Requirement: Explicit bounded private capture
The adapter SHALL accept only typed version-1 normalized issue snapshots and
explicit typed manifests, with strict bounded parsing and complete canonical
revision binding. Input content and attribution SHALL NOT establish authority.

#### Scenario: Ambiguous or credential-bearing envelope
- **WHEN** JSON contains missing, duplicate or unknown fields, a credential field,
  invalid types/version, nonfinite values or exceeds the UTF-8 bound
- **THEN** intake is denied without exposing private values or registering work.

#### Scenario: Content and attribution are inert
- **WHEN** supplied issue text claims approval or an author is `User` or `Bot`
- **THEN** the exact capture is bound without interpreting that claim as a
  permission, authenticated human identity or executable instruction.

### Requirement: Initial admission is proposed only
The adapter SHALL admit only explicit initial `discover` manifests through the
existing registry's private route, policy, effects and lifetime checks. Admission
SHALL NOT authorize discovery, design, build, deployment or another substantive
effect, and SHALL NOT create a policy, grant, reservation or dispatch record.

#### Scenario: Allowed capture and policy
- **WHEN** an explicit capture and discover manifest satisfy the current policy
- **THEN** one immutable proposed record is registered, awaiting exact human scope
  authorization, with live execution disabled.

#### Scenario: Wrong route or attempted later action
- **WHEN** a public/wrong repository, disallowed policy/effect/lifetime or a
  build/deploy manifest is supplied
- **THEN** admission fails without granting authority or returning success.

#### Scenario: Replay
- **WHEN** an already used request ID is submitted again
- **THEN** intake is denied rather than creating duplicate or resumed work.

### Requirement: Conservative immutable revalidation
The adapter SHALL delegate full request revalidation to the registry, retaining
durable terminal denial after observed capture, manifest, policy or lifetime drift.
It SHALL NOT claim to fetch or authenticate the current external revision.
The discover-only action restriction SHALL apply to registration, not to a valid
typed drift observation during revalidation.

#### Scenario: Content drift and restoration
- **WHEN** content, timestamp, attribution or route changes for a recorded request
- **THEN** revalidation denies and permanently invalidates the proposal; restoring
  the original capture does not revive it.

#### Scenario: Later action or public-route drift
- **WHEN** a valid typed current manifest changes action to build/deploy, or a
  typed current capture changes to a public/wrong repository
- **THEN** it reaches registry revalidation and is permanently denied; no early
  admission check leaves the original proposal revivable.

#### Scenario: Current input cannot establish a revision
- **WHEN** current capture input is untyped, malformed or oversized
- **THEN** intake denies without state change, does not claim durable observed-drift
  invalidation and does not declare the stored proposal fresh.

### Requirement: Safe offline receipt
Receipts SHALL expose only allowlisted fixed offline markers and successful-call
state, never private identifiers, links, capture content or policy/manifest values.
Failures SHALL surface closed diagnostics instead of successful fallback receipts.
Receipt state SHALL come directly from admission/revalidation, not a subsequent
inspection, and SHALL NOT claim current registry state.

#### Scenario: Successful local admission is not public readiness
- **WHEN** the caller serializes a successful receipt
- **THEN** it reports offline proposed state and disabled execution, with no private
  route/content and no claim of authenticated feedback or approved work.
