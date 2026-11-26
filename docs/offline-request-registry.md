# Offline private request/policy registry

The human-authorized 2026-11-26 slice adds a standard-library local registry.
It is an offline library component, **not a GitHub/Teams issue adapter, human
approval service, released installation, cloud state store or execution grant**.
See its [OpenSpec contract](../openspec/changes/build-offline-request-registry/specs/offline-request-registry/spec.md)
and [implementation/review checklist](../openspec/changes/build-offline-request-registry/tasks.md).

## What is bound

| Record | Explicit bindings |
| --- | --- |
| `RequestRule` | One action and its allowed admission effects |
| `RequestPolicy` | Installation/solution, unique policy version, numeric private repository ID, rules, validity and canonical digest |
| `IssueRevision` | Numeric repository/issue identity, observed private visibility and exact private issue-scope snapshot digest |
| `RegistryRequest` | The existing complete ExecutionManifest and the issue revision |
| `RegistrySnapshot` | Frozen record, last stored proposed/invalidated/revoked state and closed denial reason |

The manifest's `policy_digest` must equal the entire `RequestPolicy.digest`.
Its `input_digest` can bind a compound specification/input snapshot; it does not
have to equal the separately bound issue revision digest. All manifest fields,
including effects, target, profile, framework, tools and skills, retain their
existing immutable meaning.

Action/effect rules constrain **admission**, not permission to perform an action.
A discover rule does not admit build effects. Admitted records always remain
proposed, even when submitted by a human. There is no approver field, grant
conversion, model/source access, worker launch or automatic issue ingestion.

## Trusted caller API

Import the records and `SQLiteRequestRegistry` from `fabric_delivery_core`.
The trusted application must already have authentic current private input
snapshots and explicitly authorized configuration. These library calls cannot
prove where a policy, issue revision or claimed private visibility came from.

- `register_policy(policy)` retains the immutable version, makes it current
  and atomically invalidates older proposals for that installation/solution.
- `register(request)` checks current policy, private route, action-specific
  effects and current request lifetime; returns the registry digest only.
- `revalidate(current_request)` checks actual newly observed bindings after
  locking, returning proposed local consistency or committing permanent denial.
- `revoke(request_id)` permanently revokes a proposal, not an execution grant.
- `revoke_policy(policy_digest)` removes the current policy and invalidates its
  proposals while retaining immutable policy/request history.
- `inspect(request_id)` reads private **last-recorded** state. It does not check
  current expiry or external state and is never authorization/readiness evidence.

Request IDs and policy versions cannot be reused, including after revocation.
Fresh revisions require a new request ID and applicable separate human decision.
Multiple distinct requests can reference one issue; there is no automatic
Teams-event idempotency or lifecycle scheduler here.

The API and file belong only to a privileged trusted service. Agents, arbitrary
issue text and public callbacks must not register policy, call these methods or
modify the file. Do not store credentials, private records or raw logs in these
metadata records. Real configuration and registry files stay out of public Git,
Actions logs and model prompts.

## State and failure behavior

Registration yields `proposed`. A privileged policy replacement/revocation or
observed binding/expiry failure leads to `invalidated`; explicit proposal
revocation leads to `revoked`. These terminal states cannot be restored by
reverting bytes or rewinding a clock. Closed errors are `RegistryDenied` with
generic codes, never supplied identifiers, values, paths or provider errors.

Revalidation commits denial before raising it, so restart cannot resurrect the
proposal. Policy version/current-pointer/proposal-invalidation writes share one
transaction; a storage failure rolls them back together.

Policy administration is not native human authorization. A previously admitted
proposal is not atomically linked to another store's grant/dispatch transaction.
Real policy administration, request revalidation at execution time, cancellation
and cross-component transaction/recovery semantics still require an independently
reviewed trusted live adapter.

## Storage boundary

Use one dedicated private local file with an existing parent, reliable SQLite
locks/fsync, DELETE journal support, FULL synchronous transactions and protected
backups. Different installation data files must not be shared with agents.
Authorization, spend and outbox files are separate schemas; passing one as the
registry is rejected, not converted.

Schema version, application ID, complete table/constraint definitions and loaded
canonical record/digest bindings are checked. Unsupported journals/schemas fail
without reconfiguration. Ordinary operations open only an existing file and
never recreate lost state. An existing instance rejects observed file-identity
replacement.

These checks are not cryptographic protection against a malicious file owner,
coherently rewritten state, backup rollback or replacement before a new instance
starts. Host ownership/access controls and verified restore/recovery remain
operator responsibilities. This is not a multi-host/cloud database choice.
It stores request metadata and local admission state, not Bronze tables or a
solution's notebook/data files. No OneLake or other cloud storage is provisioned.

## Offline verification

From a reviewed checkout, with existing Python dependencies:

```powershell
$env:PYTHONPATH = 'src'
$env:TEMP = 'D:\Temp'
$env:TMP = 'D:\Temp'
python -m unittest discover -s tests -p test_request_registry.py -v
```

Tests use synthetic inputs and fresh disposable local files, including competing
process registration, rollback, lock-time expiry, policy/revision drift,
corruption, missing/replaced files and unrelated-schema denial. They do not use
GitHub/Teams/Fabric APIs, source records, secrets or model calls.
Existing operator preflight continues to report live execution unsupported;
passing this registry's tests does not remove any live blocker.
