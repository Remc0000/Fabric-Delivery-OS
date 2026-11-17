## Why

Fabric teams need a reproducible path from an issue to a tested data solution
without giving agents authority to approve their own work. The framework must
be independently installable and support GitHub Free without exposing private
solution code or substituting agent judgment for human authorization.

### Current implementation boundary

The original proposal below is broader than the implemented slice. Explicit human
authorization on 2026-11-17 permits the Python immutable-request/authorization
core build. It now provides validated frozen manifests and local-file SQLite
single-use claims with synthetic tests. It does not implement approval identity
verification, federation, worker scheduling, models, or cloud provisioning.
See [the core guide](../../../docs/authorization-core.md). Remaining proposal
work and every deployment still need their applicable human authorization.

The directly dependent, separately authorized continuation adds a read-only
GitHub native-approval evidence observer. It verifies private registry and
API identity/policy/history bindings but issues no execution grant; bypass
state, human credential provenance, and federation remain unsupported.
See [its boundaries](../../../docs/native-approval-verifier.md).

A further directly dependent software slice validates GitHub OIDC signatures
and exact signed workload context using maintained JWT/crypto libraries and
official public JWKS. It does not infer a subject format, sign private inputs,
join native-review evidence into a grant, prove App provenance, or claim live
installation federation. See [the OIDC guide](../../../docs/github-oidc-verifier.md).

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

This is a behavior contract, not by itself implementation authorization. Public
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
sources. The original proposal added specifications and review tasks; the bounded core
build described above is the only framework implementation to date. Installation
control and the private reference solution have separate OpenSpec proposals
that depend on this contract. No dependencies, executable workflows, tenant
settings, credentials, or Fabric resources are installed by this proposal.
