## Context

See `proposal.md` for scope and `specs/` for the behavior contract. The selected
deployment model uses GitHub Free with two public repositories and private
solutions. Native required reviewers are available on public control runs;
this does not add native protection to private solution branches.

The broader design remains proposed. Explicit human authorization on 2026-11-17
permits only the bounded framework authorization-core build described below.
No executable workflow, model, identity, tenant change, or Fabric resource is
authorized by these documents themselves.

### Implemented bounded core

`fabric-delivery-core` implements version-1 frozen SHA-256-bound manifests and a
private local-file SQLite store. It records externally verified approval bindings,
uses write transactions to consume each grant once, persists claim receipts,
and permanently denies replay, revocation, expiry, and observed binding drift.
This is the immutable-request portion of decision 4, not the complete dispatcher
of decision 2. See [the implementation guide](../../../docs/authorization-core.md).

SQLite is an explicit single-host library backend, not a selection of Azure
storage or worker infrastructure. Native gate/identity/federation verification
must happen in an external trusted adapter. The core does not assert that a
caller-created approval object proves a human decision.

One protected repository/run/attempt/gate tuple may bind only one request.
The lifecycle is pending -> authorized -> consumed, with permanent revocation
or consume-time invalidation before consumption. Time is checked after obtaining
the write lock. Drift cannot be reverted to resurrect a grant. A crash after a
claim commits burns the grant; no atomic worker launch/outbox is claimed.
The existing requirement for atomic consumption plus safe scheduling still
requires integration work before any worker dispatch is enabled.

### Read-only native approval observation

The explicitly authorized continuation provides an optional Requests-based
GitHub.com REST observer. A trusted private registry binds one manifest and
reviewed policy snapshot to the actual numeric repository/workflow/run/attempt
and environment identities. The observer reads native history and current
reviewer/ref/branch/environment policy, verifies workflow bytes at the pinned
commit, compares two observations, and returns typed bound evidence.

The documented history lacks per-review timestamps and attempt attribution:
only first attempts are supported, and age is conservatively bounded by run
creation time. The documented environment schema omits administrative bypass.
The observer does not infer a bypass setting, authenticate OIDC/JWKS, or prove
human credential provenance; those are explicit execution blockers. Conversion
of observations to an ApprovalBinding is unsupported and always denied.
See [the verifier guide](../../../docs/native-approval-verifier.md). This is
read-only evidence validation, not native-gate replacement or production proof.

## Goals / Non-Goals

**Goals**

- Put authorization outside agent control and make each meaningful grant
  traceable to immutable inputs.
- Keep solution processing private even though the approval surface is public.
- Use adopter-owned Azure compute for agents and Foundry for model access.
- Deliver a complete but bounded batch analytics reference chain.
- Support one human holding all permitted roles without requiring that policy
  for organizations that prohibit it.

**Non-goals for the first release**

- Complete support for every Fabric workload or arbitrary external sources.
- A centrally hosted multi-customer service.
- GitHub Copilot as the initial agent runtime or billing source for model calls.
- Making private GitHub Free branches natively protected.
- Automatic framework/control-plane upgrades or self-approved agent evolution.
- A full capability encyclopedia, scenario-bundle marketplace, or metadata catalog.

## Decisions

### 1. Separate framework, installation control, and private solution

The public framework publishes versioned reusable assets. Each adopter owns a
separate public control repository that pins an approved framework revision.
Private repositories own user issues, solution OpenSpec, implementation, and
delivery evidence. Their runtime configuration is not copied into public files.

Alternatives: a private Free control repository lacks the required native gate;
Enterprise is not selected; a custom service deciding human approvals adds
unnecessary responsibility. A private caller of a public reusable workflow
still executes in the caller's context and is not the selected architecture.

### 2. Use native gates plus a small private request dispatcher

GitHub remains the human interface. A GitHub App-backed request adapter accepts
private issues/events, validates installation membership, freezes a private
execution manifest, and publishes a private review summary linking to the
public control run. Only a random opaque request ID goes to the public run.

The public control repository owns native environments for build and individual
stage deployments. Required reviewers contain the authorized humans. Trusted
refs and disabled administrative bypass are prerequisites. Agents cannot write
control code, change those settings, or access the reviewer's credentials.

After the gate, fixed orchestration authenticates to an Azure dispatcher using
workload identity federation. Federation must bind to the actual immutable
repository identity and approved environment/context; no wildcard acceptance of
solution repositories or arbitrary workflow refs is allowed.

The dispatcher validates the request, environment, state, policy, workflow
revision, and artifact binding, then atomically consumes the grant and starts
the proper worker. It is not a custom replacement for GitHub's human reviewer
decision. It does supply private state, anti-replay, and safe worker scheduling,
which native approval alone does not provide.

Proposed Azure components are a small request/dispatch API, private durable
request/evidence storage, secret storage, and isolated job workers. Final SKUs,
region, and APIs must pass onboarding. No resources are provisioned now.

### 3. Keep private work off the public Actions runner

The proposed public job is a minimal, clean GitHub-hosted dispatcher job. It
does not check out solution code, invoke the model, execute generated code, or
collect worker output. Agent compute remains in the adopter's Azure environment.
This intentionally avoids registering a generally privileged Azure runner on
a public repository. A different control-runner placement requires equivalent
isolation and a reviewed installation decision.

Azure workers use separate execution profiles. A trusted harness mediates model
and tool calls; generated code runs in a separate sandbox without harness,
source, or deployment credentials. Production deployment uses reviewed fixed
logic in a separate worker/identity, never a free-form agent shell.

A container alone is not assumed to establish this boundary. Metadata identity
endpoints, host sockets, storage, network egress, and cross-job persistence must
be verified before the selected worker substrate is accepted. If the proposed
job service cannot enforce the contract, implementation stops for a revised
design rather than weakening the contract.

### 4. Use a typed immutable execution envelope

The private manifest records installation and solution IDs, a unique request
ID, requested action and effects, specification/input revision or artifact
digest, target baseline/environment, policy revision, framework/control runtime
revision, relevant skill/tool snapshot, and validity/revocation state.

Model deployment and region are part of the execution profile. GitHub run ID,
attempt, environment, and approval evidence are linked when a grant is used.
The dispatcher atomically transitions a pending request to one execution.
Duplicate callbacks and old workflow reruns cannot start another mutation.

Each development, test, production, destructive-data, or recovery attempt gets
the required fresh request. A failed operation records partial effects and does
not convert a retry into an implicit permission.

Private review summaries must be generated from the frozen manifest, not from
mutable issue text. Changing accepted inputs produces a new request.

### 5. Separate bootstrap, human authority, and workloads

An approved bootstrap plan creates or reuses the GitHub App, Azure identities,
Fabric grants, trusted workflows, and policy assignments. Bootstrap authority
is not available to ordinary workers. Azure authentication does not imply
Fabric access; each endpoint's actual identity support is checked.

The GitHub App key and installation tokens remain in trusted integration code.
Agents request bounded repository operations through a tool boundary. Roles
share identities only when their effective authority is equivalent; deployment
identities are separated by environment.

Separate the solution-writing GitHub App installation from control-dispatch
authority. A control dispatcher needs no permission to edit control contents
or settings, and the solution writer has no installation access to the control
repository. Do not grant the union of both permission sets to a broad token.

One-person operation is supported by explicitly allowing the same human in
multiple roles. GitHub's "prevent self-review" setting concerns the initiating
user, not whether an AI did the work. For a solo installation that human may
initiate and approve a run; agents still have no human credentials or reviewer
membership. Stricter organizations enforce different-human rules.

### 6. Start with a Python agent harness using Foundry models

Python with Microsoft Agent Framework is the initial design candidate because
it supplies model/tool primitives without making the LLM the process engine.
The dependency version and actual provider/tool behavior must be confirmed
before an approved manifest is introduced. Do not build a custom agent loop
where an established library meets the contract.

Private execution state is authoritative. GitHub displays the request state and
evidence links; interrupted workers do not infer progress from chat memory.
Financial limits can be explicitly unset, but finite iteration/time/retry
limits remain required. Foundry and Azure compute costs are separate from
GitHub AI credits.

### 7. Refresh skills without changing permission or approved inputs

Resolve approved skill sources for each new request, verify and snapshot the
content, and record compatibility. Routine compatible updates become available
automatically. Incompatible updates are quarantined; a visible last-known-good
selection is permitted by policy.

Approved requests retain their snapshot. Downloads cannot add tools, install
packages, run setup scripts, broaden egress, or change permissions without the
applicable bootstrap/policy approval. Framework and control code updates use
reviewed releases, not this skill-refresh channel.

Initial source candidates are Microsoft's Azure skills, Skills for Fabric,
Rayfin for app tasks, Foundry guidance, Microsoft Learn MCP, GitHub MCP, and the
Azure/Fabric/GitHub CLIs where applicable. These are dependency categories to
verify, not a blanket installation list or a promise of format compatibility.

### 8. Separate private processing from model and public output

The request adapter keeps repository/workspace mappings and detailed manifests
private. Public workflow inputs, job names, summaries, errors, annotations,
caches, and artifacts use an output allowlist. Do not depend solely on secret
masking; private identifiers and code are not necessarily GitHub secrets.

All tool responses pass classification before entering model context. Source
records are denied by default, including values embedded in errors, samples,
screenshots, and aggregates. Data checks run in the permitted data environment
and return only approved control results. Model endpoints and telemetry follow
the same policy.

Public run timing, workflow shape, GitHub-visible approval actors, and opaque
request IDs remain observable. This disclosure is a prerequisite accepted
during installation, not something redaction can eliminate.

### 9. Use module contracts, not hardcoded solution generation

Each module supports inventory, impact planning, artifact production, validation,
parameterized deployment, and honest recovery limits. Start with the necessary
batch ingestion, Lakehouse medallion, semantic-model, and report modules.
Exact item formats, APIs, source connections, and application identity support
are capability checks, not assumptions.

Workspace and capacity selection are configuration. The reference convention
uses development/test suffixes and no production suffix. Test deployment and
data baseline stay frozen while a human accepts the release. Code promotion is
by digest; environment-specific connection values do not regenerate code.

## Risks / Trade-offs

- **Public metadata is observable** -> disclose it; prohibit confidential
  control inputs and reject incompatible installations.
- **Private branches lack native Free enforcement** -> agents cannot obtain
  authority from a push/merge alone; immutable requests and external execution
  identity restrictions govern delivery. Human admins remain trusted roots.
- **Native approval is not full end-to-end authorization** -> verify manifest
  binding, current policy, single use, isolation, and federation separately.
- **Public self-hosted runners could expose Azure** -> use a minimal clean
  public dispatcher and isolate all private work in Azure.
- **Automatic skill updates can regress** -> record snapshots, validate,
  quarantine incompatibilities, and support visible rollback.
- **Source/API limits vary by tenant and item** -> capability-driven preflight
  blocks unsupported modules before a claim of delivery.
- **Data rollback differs from code rollback** -> enumerate partial effects
  and require a separately authorized recovery plan.

## Verification and Rollout Plan

1. Human review of these drafts and the installation-control test scope.
2. Implement only the approved synthetic approval smoke test: no source access,
   model usage, Fabric operations, or Azure provisioning.
3. Demonstrate waiting, human approval/rejection, and exclusion of agent actors.
4. Approve bootstrap separately, then test federation, private manifests,
   replay prevention, public-output filtering, and isolated workers using
   synthetic payloads.
5. Only after these checks, authorize the complete private reference solution.

OpenSpec validation or a gate-only demo must not be reported as proof of the
whole platform. On capability or security failure, leave execution disabled.

## Deferred Reference Ideas

A bounded review of the public
[earlier framework](https://github.com/Remc0000/Fabric-Engineering-OS/tree/6115b2a641c9cedbaa1e33f1b03d6329333b80c3)
identified useful next-version candidates:

- Formal [Fabric Decision Records](https://github.com/Remc0000/Fabric-Engineering-OS/blob/6115b2a641c9cedbaa1e33f1b03d6329333b80c3/decision-records/README.md)
  for alternatives, consequences, evidence, and named approval.
- [Scenario bundles](https://github.com/Remc0000/Fabric-Engineering-OS/blob/6115b2a641c9cedbaa1e33f1b03d6329333b80c3/agent-bundles/README.md)
  such as incidents, release management, and metadata-driven ELT.
- A [machine-readable discovery catalog and freshness metadata](https://github.com/Remc0000/Fabric-Engineering-OS/blob/6115b2a641c9cedbaa1e33f1b03d6329333b80c3/metadata/README.md)
  with stable capability IDs and validated links.
- A broader [capability decision catalog](https://github.com/Remc0000/Fabric-Engineering-OS/blob/6115b2a641c9cedbaa1e33f1b03d6329333b80c3/capabilities/README.md)
  and golden paths rather than one default architecture for every request.

No reference code or governing instructions were copied. The older Copilot
runtime and its operational permissions do not override this proposal.

## Documentation References

- [GitHub environments and protection availability](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- [Reusable workflow execution context](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations)
- [Azure workload federation for Actions](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-azure)
- [Actions security and runner isolation](https://docs.github.com/en/actions/reference/security/secure-use)
- [Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/overview/)

## Installation Inputs Not Yet Resolved

The region, exact model/CLI/package versions, capacity/resource IDs, private
source location, and installed GitHub App identifiers must be resolved during
the approved preflight. They do not authorize a change in the architecture or
requirements. An incompatible outcome requires a revised proposal.
