# GitHub OIDC cryptographic verifier

This software-only continuation is stacked on the read-only native evidence
observer in [Remc0000/Fabric-Delivery-OS#6](https://github.com/Remc0000/Fabric-Delivery-OS/pull/6),
which depends on [Remc0000/Fabric-Delivery-OS#3](https://github.com/Remc0000/Fabric-Delivery-OS/pull/3).
It implements JWT signature and signed workload-context verification, not
human approval, an executable grant, Azure federation provisioning, or a worker.
The human-authorized build does not waive any missing authorization prerequisite.
README and other worktrees are deliberately unchanged.

## Trust and policy

The optional `oidc` extra supplies Requests, PyJWT with its cryptography backend,
and cryptography. Existing installed dependencies may be reused. No JWT signing,
RSA, certificate, or signature-verification algorithm is implemented here.
PyJWT verifies RS256 signatures and standard issuer/audience/subject/time claims;
the module adds strict schema, context, freshness, and private-policy checks.

`GitHubOidcPolicy` requires an **explicit exact subject and audience** and an
explicit issuer equal to `https://token.actions.githubusercontent.com`. There is
no inferred legacy `repo:...` subject, URL normalization, prefix/wildcard subject,
audience array, enterprise issuer, or fallback. New repositories may use immutable
subject formats: onboarding must record the actual configured subject, not a
sample from documentation.

The reviewed private policy also pins:

- The complete `NativeApprovalPolicy` digest, which binds installation, solution,
  action/target, numeric repository identity, workflow path, full Git commit,
  workflow-content digest, exact trusted branch, and native environment policy.
- Canonical immutable repository-owner ID and exact environment node ID. The
  private bootstrap must establish the numeric/node environment association;
  this module does not derive one from a mutable name.
- Maximum token validity window and token age (at most 600 seconds), explicit
  clock skew (0–30 seconds), and maximum HTTP JWKS age (1–300 seconds).

`RegisteredOidcRequest` binds this OIDC policy digest to the existing private
registered run, including its manifest, native-policy digest, run ID and attempt.
These objects must be loaded from authoritative access-controlled private state
registered for the dispatch; never construct them from an untrusted callback.
Their persistence/authentication is not supplied by this library.

## Signed claims actually checked

`GitHubOidcVerifier.verify` requires all of the following signed claims, in
addition to a valid RS256 signature:

| Claims | Verification |
| --- | --- |
| `iss`, `aud`, `sub` | Exact reviewed issuer, one audience string, exact configured subject |
| `exp`, `nbf`, `iat`, `jti` | Required; strict integer NumericDates, bounded lifetime/age/skew, nonempty bounded token ID |
| `repository_id`, `repository_owner_id` | Exact canonical decimal strings matching private immutable IDs |
| `repository`, `repository_owner` | Exact reviewed context names, never the sole identity boundary |
| `repository_visibility` | `public`, matching this control profile |
| `ref`, `ref_type`, `sha` | Exact trusted branch, `branch`, pinned full Git commit |
| `workflow_ref`, `workflow_sha` | Exact reviewed repository/path/ref and immutable workflow commit |
| `run_id`, `run_attempt` | Exact private registered run and attempt, as canonical strings |
| `environment`, `environment_node_id` | Exact configured native gate context and pinned node ID |
| `event_name`, `runner_environment` | `workflow_dispatch`, `github-hosted` |

Reusable-workflow `job_workflow_ref`/`job_workflow_sha` contexts are unsupported
and denied, rather than confusing the caller workflow with reusable code.
Some context claims depend on installation/token claim configuration. Missing
claims deny; environment is never inferred from subject text. The issuer's
public discovery currently advertises `environment_node_id`; actual configured
token delivery must still be proven during the future live bootstrap.

NumericDate booleans, floats, and numeric strings are rejected. The complete
`exp - min(iat, nbf)` validity window must fit the configured maximum; this
explicitly accounts for an issuer backdating `nbf`. Tokens must not predate
registered dispatch beyond permitted skew. Skew allows bounded future `iat`/
`nbf` and issuer/clock differences, but **expiry, maximum age, and request expiry
have no grace**. Signature/time validity is checked after JWKS retrieval, and
private request validity is rechecked then too. A reliable service clock is
required.

Duplicate JSON keys, malformed compact JWTs, missing claims, wrong algorithms,
bad signatures, unknown keys, and any mismatched context deny with closed codes.
Header inspection before signature verification is used only for strict parsing
and selecting a key from the fixed trusted JWKS. It confers no authority.
`actor`/`actor_id` are not treated as a native approver.

## Official JWKS and rotation

`GitHubJwksClient` only GETs
`https://token.actions.githubusercontent.com/.well-known/jwks`. It does not
discover an origin from token claims/headers or follow redirects. TLS verification
is mandatory, ambient proxy/netrc/auth discovery is disabled, timeouts and body
size are bounded, and no credentials are sent.

Each verification fetches anew: there is no memory/disk key cache and no stale or
network-error fallback. Unknown/removed keys deny; a later verification can accept
an explicitly published rotated key. HTTP Date/Age and elapsed retrieval time
must meet the configured freshness bound. No claim is made that the verifier can
detect a revocation before GitHub publishes its changed key set.

Signing keys must have unique bounded `kid` values, RSA type, RS256 algorithm,
signature use, verify-only operations if specified, and 2048–8192-bit public
keys. Private key parameters, duplicate IDs, algorithm confusion, token-provided
`jku`/`jwk`/`x5u`/critical headers, unavailable JWKS, and stale responses deny.
Certificate metadata in official JWKS is not a separate trust source; key
selection comes from the authenticated fixed-origin public JWKS and PyJWT.

## Evidence is not authorization

The result is a frozen `GitHubOidcEvidence` containing private policy/registration
and token/token-ID digests, pinned identities, and bounded observation validity.
No raw JWT, signing key, subject, complete payload, or credential is retained in
the result or logged. Tokens, policy/registry objects and error internals must
not be copied into public logs. Errors expose closed denial codes only.

GitHub does **not** sign `workflow_dispatch` inputs, a private request UUID, or a
private manifest/artifact digest in its supported standard claims. A signed
run/attempt can be associated with an authoritative private registry record,
but that is not a signed input-content assertion. Extra lookalike
`request_id`/`manifest_digest` claims do not clear this missing stage.

`to_approval_binding()` always denies. No supported boolean override turns this
observation into execution authority. Outstanding blockers include:

- Authoritative private request/input binding and revocation enforcement.
- Joining fresh native review evidence and this workload identity to the exact
  request; native review attempt attribution remains limited to first attempts.
  Signed OIDC attempt numbers are independently verifiable but do not repair
  missing per-attempt native approval history.
- Administrative-bypass verification and actual human credential provenance.
- Exact runtime GitHub App/token provenance and least-privilege separation.
- A future **live, human-enabled control token/bootstrap proof**, Azure token
  exchange and identity assignment, safe grant consumption/scheduling, and workers.

This verifier itself is read-only and stateless: the same valid token can be
observed repeatedly. It does not replace the durable one-time grant store,
make a token a one-use credential, or change existing replay rules. The native
observer's own `federation_unverified` blocker remains until a separately
reviewed end-to-end integration actually combines the observations.

## Usage and validation

Install the optional extra through the approved Python package source:
`python -m pip install '.[oidc]'`. Base-core imports still have no runtime
dependencies, and missing optional dependencies explicitly skip their suites.

```python
from fabric_delivery_core.github_oidc import GitHubJwksClient, GitHubOidcVerifier

# These are authoritative private installation/request records, not HTTP inputs.
with GitHubJwksClient() as jwks:
    observation = GitHubOidcVerifier(jwks).verify(
        presented_oidc_jwt, frozen_manifest, registered_oidc_request,
        current_native_policy, current_oidc_policy,
    )
    assert observation.execution_blockers  # No grant or worker activation.
```

Tests generate ephemeral RSA keys **in memory**, sign using PyJWT, and mock the
official JWKS response. They cover real cryptographic verification, context
mismatches, bad algorithms/signatures, malformed signed JSON, age/skew/expiry,
rotation/removal, stale/failed JWKS, and registry/policy drift. They do not obtain
an actual workflow token, use an actual App/user credential, or mutate GitHub.
No live federation test is claimed: the separate control test still requires
human merge/enablement, and a passing native smoke run alone proves no such
federation or production safety.

References:
[GitHub OIDC claims](https://docs.github.com/en/actions/reference/security/oidc),
[official discovery](https://token.actions.githubusercontent.com/.well-known/openid-configuration),
[PyJWT validation API](https://pyjwt.readthedocs.io/en/stable/api.html),
and [Remc0000/Fabric-Delivery-OS-Control](https://github.com/Remc0000/Fabric-Delivery-OS-Control).
