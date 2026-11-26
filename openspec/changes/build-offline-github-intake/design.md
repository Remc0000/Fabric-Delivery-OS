## Contract

`GitHubIssueSnapshot` is a frozen normalized capture, not a GitHub REST response or
webhook. Its exact version-1 fields are `schema_version`, `repository_id`,
`repository_private`, `issue_number`, `title`, `body`, `author_id`, `author_type`
and `updated_at`. Numeric identities are positive signed-64-bit integers, not
Booleans; visibility is a strict Boolean; the timestamp is an explicit nonnegative
integer. Title is nonempty text; body is text or null; author type is `User` or
`Bot`. Neither type proves a human identity, authenticated origin or authority.

Canonical capture JSON is at most 1 MiB of the existing compact ASCII-escaped
`_canonical` JSON encoded as UTF-8, including for typed construction. Those exact
bytes are hashed; non-ASCII characters count as their JSON escapes. Raw parsing
input is separately limited to 1 MiB of UTF-8 before decoding JSON. Text must be
UTF-8 encodable; title/body whitespace is preserved rather than trimmed.
Parsing rejects unknown/missing/duplicate fields, nonfinite constants, unsupported
versions and incorrect types. Private content must not appear in errors or repr.
Parser, depth and Unicode errors are closed denials without private exception
chaining or the decoder's private input document.
The digest binds every capture field, without executing or interpreting its text.
Snapshots are privileged private input; this module does not authenticate them.

`OfflineGitHubIntake(registry)` provides `register(snapshot, manifest)` and
`revalidate(snapshot, manifest)`. Both require typed explicit inputs; only
`register` restricts the initial manifest action to `discover`. They construct `RegistryRequest` with
an `IssueRevision` whose digest is the complete capture digest and delegate to the
existing registry. The manifest input digest is independently bound, not assumed
to equal the issue digest and does not claim to describe the capture. No request ID, policy, permission or approval is inferred
from title/body, author, labels, chat intent or defaults. No policy is created.

`GitHubIntakeReceipt.to_json()` returns only fixed offline markers and the
state at the successful call: no IDs, links, content, policy/manifest digests or private
denial reasons. It reports `execution_enabled: false`; proposed state means
awaiting the exact authorized human scope, not permission to start discovery.
The receipt comes directly from successful admission/revalidation, not a second
`inspect` call that could race with policy replacement. It is not current
registry state, authenticated feedback or a fresh external readiness assessment.
Closed intake validation diagnostics and existing closed registry denials remain
visible; failure must never produce a successful receipt.

## Boundaries and persistence

The existing registry enforces private numeric routing, current policy, effect
allowlists, lifetime and one registration per request ID. It does not deduplicate
an issue capture submitted with a fresh explicit ID. Revalidation must pass every
otherwise valid typed snapshot/manifest, including a changed action or public/wrong
route, to the registry before any action/route rejection. Observed typed drift
durably invalidates proposals before surfacing denial; restoring old content cannot revive
them. It cannot establish current GitHub state, authenticate metadata, make an
approval decision or prevent a coherent hostile rewrite by a privileged host.
An untyped, malformed or oversized current capture cannot establish a trusted
revision and is denied without state change. Such denial is not observed valid
drift evidence; any remaining proposed record is still non-fresh.

Only normalized synthetic/private captures enter this API. It never accepts
tokens or fetches URLs, issues, users or source data. It exposes no model-facing
tool, writes no public record, and cannot create issues, grants, spend reservations
or outbox entries. Real API capture/provenance, human identity and scope binding,
model-input policy, feedback audiences and atomic execution joining need separate
design, authorization and proof.

## Parallel ownership

The GitHub worker owns only `github_intake.py` and `test_github_intake.py` in its
isolated worktree. The Teams worker owns only the new Teams OpenSpec change.
Main owns this contract, shared docs/exports and integration. Worker commits are
local handoffs, not human acceptance; publication never merges or activates work.
