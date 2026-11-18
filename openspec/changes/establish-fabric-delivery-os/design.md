## Context

See `proposal.md` for scope and `specs/` for the behavior contract. The selected
deployment model uses GitHub Free with two public repositories and private
solutions. Native required reviewers are available on public control runs;
this does not add native protection to private solution branches.

The broader design remains proposed. Explicit human authorization on 2026-11-17
permits the bounded core and later explicitly scoped software continuations below,
not the complete proposed runtime.
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
standalone claim commits burns the grant; that standalone API schedules no work.
The later local outbox below coordinates preparation and one worker claim
without implying atomic external launch or live dispatch readiness.

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

### GitHub OIDC cryptographic observation

The next explicitly authorized continuation uses maintained PyJWT/cryptography
for RS256 verification against fresh fixed-origin official GitHub public JWKS.
It requires an exact explicitly configured subject/audience/issuer, immutable
repository/owner IDs, ref and workflow path/ref/commit, signed run/attempt, and
explicit environment/node context. A registered OIDC policy digest binds these
settings to the existing authoritative private registered run and manifest.
No default legacy subject is guessed; missing signed claims deny.

JWT validity, lifetime, age, bounded skew, JWKS freshness/rotation, algorithm,
key selection, and signed context are verified, but no execution grant follows.
GitHub does not sign private workflow inputs or the private manifest digest.
App provenance, fresh native-review integration, administrative bypass, human
credential provenance, and live installation federation proof remain separate
blockers. No raw JWT/key is logged, no token is exchanged, and no worker starts.
See [the cryptographic verifier guide](../../../docs/github-oidc-verifier.md).

### Integrated offline package and operator

The authorized main-based integration co-packages the core, native/OIDC
observers and separate-file finite spend ledger without replacing the merged
human-governed lifecycle/onboarding documentation. Cross-component tests verify
matching evidence bindings, unsupported grant conversion, ledger replay/breach
and wrong-file rejection; none proves a live identity or atomic coordination.
Authorization rejects spend/unrelated schemas while preserving existing
version-1 authorization databases.

The standard-library offline operator validates bounded local manifest JSON,
current validity, optional exact-schema spend-plan binding/arithmetic, and
supported optional imports. Its maximum-cost calculation is shared with the
ledger, but no ledger is opened or changed. It emits allowlisted values and
explicit live blockers without identifiers, paths or private input values.
Manifest-check exit 0 means only local validity. Preflight exit 3 means offline
checks passed but live execution is unsupported; missing/invalid/unknown local
checks exit 2. No API, credentials, grant, reservation or worker is used.
See [the operator guide](../../../docs/offline-operator.md).

The next boundary remains an authenticated authoritative private request/policy
adapter joining revalidated inputs, actual App provenance, native human evidence,
OIDC and independently inspected bypass/credential policy. Standard GitHub
claims do not sign private workflow inputs. Even after that join, durable
live authorization/reservation/dispatch integration/recovery, the isolated
Agent Framework/Foundry harness, independently approved stage workers and Fabric
modules remain unimplemented. Offline checks are only a partial onboarding implementation.

### Authorized durable local outbox (2026-11-18)

The explicit continuation reuses the authorization and spend checks in one
SQLite attached-file transaction: consume a grant, reserve the exact approved
maximum and persist ready work together. Existing standalone methods retain
their behavior. Permanent authorization invalidation commits before denial;
budget/configuration/storage failures instead roll back all preparation writes.
The profile digest binds the reviewed worker/runtime configuration, immutable
budget/price digests, operation, period/currency and finite token/call/time bounds.

The outbox uses a third distinct private local database with its own identity.
All files require a common reliable local filesystem, DELETE rollback journals,
full synchronous transactions and trusted-service access controls. Unsupported
journal modes and missing/unrelated attached stores fail closed without
conversion or recreation. This uses SQLite super-journal semantics, not an
Azure distributed-storage guarantee; process-crash tests do not certify
power-loss behavior or backups.

Fresh trusted bindings, valid reservation/freeze state and expiry are checked
again before one worker claim. A durable ready job may receive its first claim
after restart. A committed worker claim is never reclaimed, including when
launch is ambiguous. Pre-claim cancellation, permanent ready-state blocking and
unknown outcomes never refund cost or restore grants. Final complete trusted
usage and terminal result commit together; breach/freeze are durable before
error, and late completion cannot report success. No reset/requeue/unfreeze or
unknown-usage reconciliation endpoint is introduced.

The input-free operator self-test exercises this protocol in fresh disposable
synthetic stores, with no external worker or human identity assertion. It
reports live execution unsupported even on local success. The coordinator
exposes no callback, shell command, network endpoint, credentials or scheduler.
Native/OIDC-to-grant joining, actual private-input/App/federation proof,
ongoing cancellation, target-conflict controls, isolated workers and real
storage/recovery acceptance remain separate activation prerequisites.
See [the local dispatch guide](../../../docs/durable-dispatch.md).

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

Agents may file proposal issues using already authorized observations, only
where repository/visibility policy permits; public framework proposals must be
sanitized while solution details stay private. Filing is not an implicit new
discovery/design task or permission to access more sources. An agent-filed issue
starts proposed/awaiting authorized human approval of the exact first substantive
scope/revision and enumerated effects. The trusted adapter must freeze that
decision through the existing private manifest/native human boundary; author
identity, labels, assignments, validation, agent reviews or mutable text alone
are not authority. Bounded discovery/design approval cannot authorize builds or
deployments; later specification/build/stage gates remain separate, and scope
changes invalidate affected approval. This automatic issue adapter is not
implemented and must remain disabled until these checks are enforced outside
the model. No automatic ingestion service is claimed by this package.

The public control repository owns native environments for build and individual
stage deployments. Required reviewers contain the authorized humans. Trusted
refs and disabled administrative bypass are prerequisites. Agents cannot write
control code, change those settings, or access the reviewer's credentials.

After the gate, fixed orchestration authenticates to an Azure dispatcher using
workload identity federation. Federation must bind to the actual immutable
repository identity and approved environment/context; no wildcard acceptance of
solution repositories or arbitrary workflow refs is allowed.

The dispatcher validates the request, environment, state, policy, workflow
revision, and artifact binding, then atomically consumes the grant, reserves
bounded cost and records ready work. A separate one-time claim precedes the
proper worker launch; an ambiguous claimed attempt is never automatically
relaunched. It is not a custom replacement for GitHub's human reviewer
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

#### Authorized local spend guard slice (2026-11-17)

The approved reusable spend slice uses a separate private, single-authority
local SQLite file and standard-library Python. Immutable installation/month
policy defines mandatory finite token/call limits, currency, and cap; immutable
versioned trusted price cards define all-in conservative integer fixed-point
rates and validity. Reserve the computed maximum under `BEGIN IMMEDIATE` before
effects; outstanding plus final settled amounts must fit the monthly cap.
Bind operation-attempt digest, configuration/card digests, currency and UTC
month. Deny missing/stale/unknown prices, incompatible bindings and replay.

Settlement is final and single-use. Excess actual cost or usage is committed as
a visible breach and freezes new reservations across the installation, including
future months; it cannot undo an external bill. Unknown outcomes stay reserved.
There is no automatic refund, expiry release, unfreeze or model call. The
standalone spend API supplies no atomic authorization/dispatch integration;
the later local outbox reuses its checks without supplying a live adapter.
The adapter must enforce usage and the
exclusive deadline (card expiry or UTC month end), authenticate complete final
usage and avoid duplicate dispatch. Delayed reporting uses the original month.
Excess usage freezes even when its reported cost is low. Conservative price
maxima are not minimum actual charges; authenticating complete final cost is an
adapter responsibility, not something this local ledger can prove.

See `docs/spend-guardrails.md` for exact API, fixed 10^-9 currency units, closed
denials and recovery assumptions. Tested local SQLite concurrency is not
distributed accounting or a guarantee of any cloud invoice ceiling; Azure
budget alerts are not hard caps. Infrastructure and other untracked charges
remain outside this library. Real budgets and installation details stay private.
This implementation does not complete the planned runtime/harness integration.

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
