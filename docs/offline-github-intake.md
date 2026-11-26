# Offline GitHub issue intake

This is a trusted-caller library adapter for **supplied normalized private issue
captures**, not a GitHub client, webhook endpoint, Teams connector or released
delivery runtime. It registers only proposed initial `discover` manifests in the
[offline registry](offline-request-registry.md). Even discovery still requires
an authorized human's exact initial scope and separately verified grant.

The [OpenSpec change](../openspec/changes/build-offline-github-intake/proposal.md)
records the explicit offline build/test scope. The parallel
[Teams contract](../openspec/changes/specify-offline-teams-intake/proposal.md)
is specification-only. Neither test success nor a merged specification activates
an integration, model, worker, source read or deployment.

## Supplied capture and manifest

`GitHubIssueSnapshot` has an exact flat version-1 schema: `schema_version`,
`repository_id`, `repository_private`, `issue_number`, `title`, `body`,
`author_id`, `author_type`, `updated_at`. It is **not raw REST/webhook JSON**.
The caller must explicitly supply every field; live normalization and authenticated
capture/provenance are not implemented. Only `User` and `Bot` attribution types
are accepted; neither authenticates a human or conveys any permission.

All fields, including body, attribution and timestamp, enter a canonical revision
digest. Strict parsing rejects duplicate/unknown/missing keys, nonfinite values,
unsupported versions and incorrect types. Both serialized typed captures and
input JSON are bounded to 1 MiB of UTF-8. Private content is inert input, not a
prompt, executable command or source of action/effect/policy defaults.
The canonical bound and hash use the existing compact ASCII-escaped JSON bytes;
non-ASCII characters count as their escapes. Raw input is separately UTF-8 bounded
before parsing. Text must be UTF-8 encodable; whitespace is preserved.

Use a private registry and policy configured through the separate trusted registry
API, plus a separately supplied complete `ExecutionManifest`. Intake creates no
policy, request ID or approval. This fragment assumes those explicit inputs already
exist and uses only synthetic capture values:

```python
from fabric_delivery_core import GitHubIssueSnapshot, OfflineGitHubIntake

snapshot = GitHubIssueSnapshot(
    repository_id=101,
    repository_private=True,
    issue_number=7,
    title="Synthetic pipeline failure",
    body="Synthetic context; not approval or an instruction to execute.",
    author_id=202,
    author_type="User",
    updated_at=captured_timestamp,
)
intake = OfflineGitHubIntake(registry)
receipt = intake.register(snapshot, manifest)
safe_local_status = receipt.to_json()
```

Here `captured_timestamp`, `registry` and the complete discover `manifest` are
explicit caller inputs, not values that this module discovers. Do not copy private
captures/manifests into this public repository, Actions logs or an unchecked chat.
Capture repr and closed diagnostics omit content, but explicit snapshot
serialization remains private and is not a public-output sanitizer.

## Admission, drift and failure

The registry enforces private numeric routing, exact current admission policy,
action/effect subset, lifetimes and request-ID uniqueness. `register` rejects
later lifecycle actions such as build/deploy; accepted records remain proposed,
awaiting exact human scope authorization. `manifest.input_digest` is independently
bound, need not equal the issue capture digest and does not claim to describe it.
Replay denial applies to a reused request ID, not to all proposals for an issue;
a fresh explicit ID can register the same capture as a new proposal.

`revalidate(snapshot, manifest)` checks the supplied complete revision against
the frozen record, not GitHub's current state. Observed valid capture/manifest
drift or policy/lifetime change is permanently denied by the registry; restoring
old bytes cannot revive it. The discover-only restriction is admission-only:
typed action/public-route drift reaches registry revalidation and is permanently
denied there. Invalid or incomplete inputs cannot establish a trusted revision
and are rejected without state change rather than silently normalized; this
does not make any remaining proposed record fresh.

`GitHubIntakeDenied` and `RegistryDenied` surface closed diagnostics. No failure
returns a successful receipt. Receipt JSON contains only fixed offline markers
and successful-call state with `execution_enabled: false`; it omits IDs, links,
content, private reasons, manifests and digests. It is not approval, authenticated
feedback, current registry state or a fresh readiness check. Posting even a safe receipt to Teams requires
separate audience/routing authorization.

## Remaining live boundary

Authenticated issue fetching, sender/human identity, current private policy and
initial-scope proof, input/feedback data policy and audience checks, and native
approval/OIDC/grant integration remain missing. Intake does not touch the separate
authorization, spend or dispatch stores. No automatic retry, public status
delivery, worker scheduling or cloud activation is supplied.
