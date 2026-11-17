## Why

Fabric teams need a reproducible path from an issue to a tested data solution
without giving agents authority to approve their own work. The framework must
be independently installable and support GitHub Free without exposing private
solution code or substituting agent judgment for human authorization.

## What Changes

- Define three repository responsibilities: a public framework, a public
  installation control plane, and private solutions.
- Define issue-to-specification, approved build, separately approved stage
  deployments, user acceptance, feedback, and delivery evidence.
- Put native required-reviewer jobs in the public control repository and keep
  private execution on isolated Azure workers using Foundry models.
- Define human roles, least-privilege workload identities, immutable requests,
  failure handling, and controls against approval reuse.
- Define onboarding, automatic skill updates, solution-specific data policies,
  modular Fabric delivery, and reviewed framework releases.
- Establish an approval-only smoke test as the first implementation milestone,
  before attempting the complete reference data solution.

This is a draft behavior contract, not implementation authorization. Public
control processing is an explicit architecture choice with public timing and
workflow metadata, not a way to make private GitHub Free features available.

## Capabilities

### New Capabilities

- `github-lifecycle`: Issues, specifications, reviews, feedback, and audit evidence.
- `human-authorization`: Human-only, version-bound build and deployment approval.
- `agent-execution`: Isolated role-based workers, model calls, tools, and limits.
- `onboarding`: Capability checks, identities, workspace choices, and approved setup.
- `skills-and-tools`: Required expertise, automatic updates, and bounded tool access.
- `information-boundaries`: Private solution state and controlled model/public output.
- `fabric-delivery`: New and existing Fabric solutions, stage promotion, and recovery.
- `distribution`: Per-adopter installation, configuration, releases, and evolution.

### Modified Capabilities

None. There are no accepted baseline specifications yet.

## Impact

The future implementation touches GitHub Apps and Actions, Azure worker and
identity infrastructure, Foundry model deployments, Fabric APIs, and skill
sources. This change adds specifications and review tasks only. Installation
control and the private reference solution have separate OpenSpec proposals
that depend on this contract. No dependencies, executable workflows, tenant
settings, credentials, or Fabric resources are installed by this proposal.
