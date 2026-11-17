# Read-only GitHub native approval verifier

This bounded continuation depends on the immutable-request core in
[Remc0000/Fabric-Delivery-OS#3](https://github.com/Remc0000/Fabric-Delivery-OS/pull/3).
It observes actual native environment-review history through authenticated
GitHub REST reads. It neither makes human decisions nor enables execution.
Human authorization on 2026-11-17 permits this implementation and tests, not
deployment, self-approval, or merging either pull request.

## What works

The optional `fabric_delivery_core.github_approval` module provides:

- `GitHubReadClient`: a Requests-based, GET-only GitHub.com REST client. TLS is
  required, redirects disabled, connect/read timeouts finite, and responses
  capped at 1 MiB. No netrc, ambient proxy/authentication discovery, shell, `gh`
  credentials, request/response logging, or write endpoints are used.
- `GitHubInstallationToken`: a short-lived secret value excluded from `repr`.
  The trusted caller supplies an App installation-token provider; common
  personal/OAuth/user-token formats are rejected. Prefix validation is **not**
  cryptographic identity verification. Successful authenticated access to
  `/installation/repositories` and membership of the pinned repository are
  additionally required.
- `NativeApprovalPolicy`: a frozen **private registry** snapshot binding
  installation, solution, action, target environment, parent policy digest,
  numeric repository/workflow/environment/protection-rule IDs, full Git commit,
  workflow-content SHA-256 digest, exact trusted branch, enrolled human user
  IDs, self-review policy, environment update time, and finite freshness limits.
- `RegisteredControlRun`: the trusted adapter's private association between one
  frozen request/manifest, policy snapshot, repository, run ID/attempt, and
  pre-dispatch time. This must come from an authoritative durable private
  registry; accepting a constructed record from a caller defeats the boundary.
  Registry persistence and dispatch are not implemented in this slice.
- `GitHubNativeApprovalVerifier.verify`: fetches and cross-checks the current
  repository, workflow, branch head, environment/reviewers, custom branch
  restrictions, run, pending deployments, and native approval history. It
  fetches workflow bytes at the exact pinned commit and verifies their SHA-256
  digest. Relevant API responses are fetched twice and differences denied.
  No mutable public run title, label, login, callback JSON, or caller-provided
  `approved` boolean is used to establish a request association.

The result is `NativeApprovalEvidence`, a frozen private observation bound to
the manifest, registry and policy digests, numeric identities, native reviewer,
observation/expiry times, and a digest of the API snapshot. It intentionally
contains no response bodies or comments. Do not publish even its private
identifiers. The evidence digest is a reproducibility binding, not a signature.
Raw responses are not archived by this library; private audit retention remains
the trusted service's responsibility.

## Fail-closed supported profile

Only a first-attempt `workflow_dispatch` from the exact pinned branch and
commit in the actual public, non-fork, active control repository is supported.
Its numeric workflow ID/path must be active. Reusable workflow references are
not accepted by this bounded verifier. The current branch head must still
match the reviewed commit; moving it requires a reviewed policy/request update.
The reviewed workflow's actual behavior and pinned transitive dependencies
remain a human/code-review responsibility, not a YAML-engine feature here.

The environment must have the pinned numeric ID and update time, exact
individually configured human reviewer IDs and explicit self-review setting,
and exactly one custom deployment branch rule for that branch (no wildcard,
tag, broad protected-branches mode, or extra branch). Teams, extra rule types,
and other policy forms are explicitly unsupported, not approximated.
The frozen environment version must predate dispatch, and the run must not
predate dispatch or the request.

There must be exactly one unambiguous native review record for the pinned
environment ID/name, in state `approved`, by an enrolled `User` identity.
`Bot`/App identities, bot-like logins, unenrolled users, pending/rejected/missing
history, and any pending deployment are denied. A run must be in progress with
no conclusion, or completed successfully; waiting, queued, cancelled, failed,
and skipped runs never satisfy the verifier. Native self-review is allowed
only when the private policy explicitly permits it; stricter policy also
compares both initiating and triggering actors.

Collections are bounded to one page of at most 100 records; next-page links,
truncation, inconsistent counts, missing fields, duplicate JSON keys,
malformed responses, API errors, unavailable permissions, and redirects block
observation. Large installations can narrow the installation token's repository
selection; the verifier never follows arbitrary pagination or response URLs.
Requests exceptions are replaced with closed `AuthorizationDenied.reason`
codes that contain no URLs, credentials, response bodies, or private values.

## Explicit execution blockers

`NativeApprovalEvidence.to_approval_binding()` **always denies** with
`execution_authorization_unsupported`. The result cannot be silently promoted
into the core library's `ApprovalBinding`. There are no override flags or
caller-supplied booleans to clear these blockers:

1. **Administrative bypass is not verified.** The documented REST environment
   schema does not expose a bypass-enabled/disabled field. This implementation
   does not invent one, infer it from success, or treat a smoke run as proof.
   The contract's disabled-administrative-bypass prerequisite remains unmet by
   this API slice.
2. **Federation is not implemented.** No OIDC JWT/JWKS signature validation,
   issuer/audience/subject/repository/environment claim verification, trusted
   workflow-caller authentication, or Azure token exchange is included. No
   home-grown cryptography or acceptance of unverified JWT claims is used.
3. **Human credential provenance is not proven.** GitHub's review history
   identifies an account, not whether a person clicked a button versus a
   program using that account's leaked credential. A service account may also
   have GitHub type `User`. Human enrollment and credential isolation are
   installation security responsibilities. These observations cannot satisfy
   the prohibition on agents impersonating humans by themselves.

GitHub's documented review-history schema also omits a per-review timestamp
and run-attempt association. Consequently **every rerun attempt is rejected**;
retry requires a new request and a newly registered control run, not reuse of
old history. Freshness is conservatively limited by run creation time, request
expiry, and a short observation TTL. No approval timestamp is fabricated from
an environment's timestamps or a collection time.

Two reads are not an atomic GitHub transaction and do not establish complete
historical protection state or rule out transient drift/restoration. Even a
fresh observation cannot authorize a worker. Private registry authenticity,
current manifest/target/policy revalidation, authoritative revocation, actual
disabled bypass, credential separation, federation, atomic one-time
consumption, safe worker scheduling, and target-conflict handling still require
reviewed end-to-end integration. The existing SQLite core retains its unchanged
single-use rules; this module never calls `authorize`, `consume`, or any worker.

## Trusted-service usage and tests

Install the optional `github` extra through the adopter's approved Python
package source, for example `python -m pip install '.[github]'`. The base core
continues to have no runtime dependencies. Requests is an established HTTP/TLS
library; token issuance/key storage must use the installation's separately
approved trusted authentication integration. The provider must not read human
credentials from CLI authentication, browser sessions, environment fallbacks,
or agent inputs, and must restrict permissions to the required read APIs.

```python
from fabric_delivery_core.github_approval import (
    GitHubNativeApprovalVerifier,
    GitHubReadClient,
)

# All three inputs come from authoritative private service state.
# app_installation_token_provider is an approved nonhuman secret provider.
with GitHubReadClient(app_installation_token_provider) as github:
    observation = GitHubNativeApprovalVerifier(github).verify(
        frozen_manifest, registered_control_run, current_private_policy
    )
    assert observation.execution_blockers  # Execution remains disabled.
```

In PowerShell, from this worktree:

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
```

Verifier tests use synthetic API fixtures and the real Requests response/parser
interfaces; no network or credential is needed. If the optional Requests
dependency is absent, only verifier tests are explicitly skipped, while the
standard-library core suite still runs. This implementation has not performed
an installed App/live-service integration test and does not turn the separate
native control smoke cases into production-safety evidence.

## API contract references

- [Review history and workflow runs](https://docs.github.com/en/rest/actions/workflow-runs?apiVersion=2022-11-28#get-the-review-history-for-a-workflow-run)
- [Environment policy fields](https://docs.github.com/en/rest/deployments/environments?apiVersion=2022-11-28#get-an-environment)
- [Deployment branch rules](https://docs.github.com/en/rest/deployments/branch-policies?apiVersion=2022-11-28#list-deployment-branch-policies)
- [App installation repository access](https://docs.github.com/en/rest/apps/installations?apiVersion=2022-11-28#list-repositories-accessible-to-the-app-installation)
- [Official GitHub REST schemas](https://github.com/github/rest-api-description)
- Related installation-control work:
  [Remc0000/Fabric-Delivery-OS-Control](https://github.com/Remc0000/Fabric-Delivery-OS-Control).
  No control or private-solution worktrees are modified by this implementation.
