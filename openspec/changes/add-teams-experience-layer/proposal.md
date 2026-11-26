## Why

People report Fabric problems where they collaborate, not necessarily in GitHub.
Teams can make the existing specification-first, human-governed lifecycle
accessible without creating a second delivery engine or approval authority.

On 2026-11-26 the human requested this specification update only. This proposal
does not authorize integration builds, app installation, OAuth grants, channel
subscriptions, agent activation, model calls, or deployments. The existing
framework is still a bounded offline package, not a runnable delivery platform.

## What Changes

- Propose Teams as an optional conversational experience layer: capture intent,
  create a correctly routed GitHub issue, show policy-approved progress, and
  guide the human to the applicable review/approval checkpoint.
- Keep GitHub issues as work-contract anchors and pull requests as change-contract
  anchors. Immutable requests and detailed evidence remain in the existing
  private installation boundary, linked from GitHub.
- Distinguish the standard GitHub Teams app from the Teams Channel Agent with
  GitHub MCP. Neither integration is assumed to implement Delivery OS gates.
- Route solution incidents to an allowed private solution repository, not the
  public framework. Public framework proposals require sanitization.
- Return revision-linked analysis, proposed fixes, impact, checks, and delivery
  outcomes only to an authorized Teams audience; no notification grants access.
- Preserve initial discovery authorization, specification review, explicit build
  authorization, implementation review, separate Dev/Test/production approvals,
  and functional acceptance.
- Make approval cards a proposed custom UX, not a claim about standard app
  functionality. Initially they lead to trusted review; Teams clicks cannot
  create grants or replace native public-control approvals.
- Require route-specific capability, licensing, identity, app-consent, audience,
  data-policy, and negative-case verification before any activation.

### Deferred ideas

A custom authenticated Teams decision bridge, turnkey installer, autonomous
Teams-to-Fabric execution, a different delivery runtime, and a complete live demo
are not approved or implemented by this change. The Channel Agent's exact GitHub
write-tool support must be verified; documented GitHub reads do not prove issue
creation in the target tenant.

## Capabilities

### New Capabilities

- `teams-experience`: Optional governed Teams intake, issue linkage, private
  progress feedback, and navigation to revision-bound human decisions.

### Modified Capabilities

None. There are no accepted baseline specifications in `openspec/specs` yet.
This proposal adds constraints alongside the pending `github-lifecycle`,
`human-authorization`, `information-boundaries`, and `onboarding` contracts in
`establish-fabric-delivery-os`; it does not weaken or replace them.

## Impact

Only OpenSpec documents and their reference links change now. Future authorized
implementation would depend on the private issue/request adapter, authenticated
identity mapping, classified notification adapter, installation configuration,
and existing trusted control gates. Teams credentials cannot be handed to the
delivery runtime or used by agents to impersonate human approvers.
