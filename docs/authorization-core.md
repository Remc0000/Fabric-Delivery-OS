# Authorization core, version 0.1

## Scope and trust boundary

This reusable library implements the immutable-request and one-attempt portion
of the [human-authorization contract](../openspec/changes/establish-fabric-delivery-os/specs/human-authorization/spec.md).
Human authorization on 2026-11-17 permits this bounded build, not a deployment
or a claim that the complete dispatcher is implemented.

The dependent [read-only native approval verifier](native-approval-verifier.md)
can now observe authenticated GitHub API evidence against a private registry
snapshot. It cannot issue an `ApprovalBinding`: administrative-bypass state,
federation, and reviewer credential provenance remain explicit blockers.

The further dependent [GitHub OIDC verifier](github-oidc-verifier.md) validates
official-JWKS signatures and pinned signed workload claims. It also cannot issue
an execution grant: signed private inputs, native-review integration, App
provenance, and live installation federation remain unproven.

Only a trusted service may construct manifests from private inputs, record
approval bindings, revoke requests, or consume grants. Agents must have neither
access to these methods nor write access to the database. These are Python
primitives, **not an authentication boundary between mutually untrusted callers**.

Before calling `authorize` or `consume`, an external adapter must verify the
native GitHub human decision, configured identities/roles, gate protections,
trusted immutable control repository/workflow identity, environment, run and
attempt, federation, current installation policy, and revocation/cancellation
signals. The authorization module does not call GitHub or verify signatures;
the optional evidence modules do not remove this trusted-adapter requirement.
`ApprovalBinding` records the resulting private evidence digest, not a
self-authenticating assertion. Never accept its fields directly from an agent or
an unauthenticated callback. A new run attempt needs fresh verified approval;
changing `run_attempt` on a Python object cannot establish that approval.

## Manifest and binding

`ExecutionManifest` is a frozen dataclass with strict version-1 JSON parsing:
unknown, missing, and duplicate keys are rejected. Its canonical JSON uses sorted
keys, compact separators, ASCII escaping, and integer Unix seconds. SHA-256
digests use `sha256:` followed by 64 lowercase hex characters. Hash actual bytes;
never hash only a mutable label and call that artifact verification.

The manifest includes an opaque UUID4 request ID, installation/solution IDs,
action, input and optional artifact digest, target baseline digest, optional
environment, policy and execution-profile digests, framework/control-workflow
digests, tool/skill snapshot digests, explicit ordered unique effect tokens, and
creation/expiry times. `deploy` requires an artifact digest and environment.
Other action/effect names are policy-defined; the library does not invent an
action vocabulary or infer that deployment permits loading/replacing data.

An input digest may identify a compound frozen input/specification bundle. The
execution-profile snapshot must include configured model deployment, region,
permissions, and execution bounds. Full private snapshots and mappings live
outside the public repository. All fields, including validity and effects, are
bound by the manifest digest. Any accepted change needs a new request ID.

Approval binding records the exact manifest/workflow digests, immutable control
repository ID, protected run ID/attempt/environment, private approval-evidence
digest, approval time, and expiry. Gate environment names need not equal worker
target names; their policy mapping is verified by the external adapter. Approval
expiry cannot outlive request expiry. Both use an exclusive upper time bound.

## Lifecycle and durability

1. `freeze(manifest)` inserts a new `pending` request. An existing request ID
   cannot be replaced, even with identical bytes or after failure.
2. `authorize(request_id, binding)` records an externally verified gate and
   transitions `pending` to `authorized`. One control repository/run/attempt/gate
   tuple cannot authorize multiple requests, including after revocation.
3. Before `consume`, the trusted adapter rehashes actual inputs/artifacts, reads
   current policy, baseline, and runtime snapshots, rechecks approval and
   protections, and constructs the current candidate manifest.
4. `consume(current_manifest, binding)` obtains a SQLite write transaction,
   checks time/state and exact binding, and atomically records `consumed` with
   one durable execution UUID and timestamp. Concurrent processes cannot both
   claim the grant. `receipt(request_id)` reads that claim after restart.
5. `revoke` makes an unconsumed request unusable, including one still pending.
   The caller must translate external cancellation/revocation into this state
   and recheck cancellation before worker effects. A committed claim is never
   undone by revocation, failure, retry, or restart.

Changed policy, baseline, or execution profile produce `policy_changed`,
`target_changed`, or `execution_profile_changed`. Other manifest drift produces
`request_mismatch`; altered callback evidence produces `approval_mismatch`.
Expired requests produce `expired`. These consume-time denials durably
invalidate the old request; reverting the observed value does not resurrect it.
Revocation gives `revoked`, and any second claim gives `consumed`.
`AuthorizationDenied.reason` contains a closed code without private values.
Invalid input schemas raise `ValueError`; storage failures propagate and must
block execution. Do not copy storage exceptions or manifests into public logs.

The SQLite backend uses a real file, separate connections, `BEGIN IMMEDIATE`,
`synchronous=FULL`, and database identity/schema checks. Authorization and spend
files cannot be substituted; unrelated user tables are rejected before creating
authorization state. Existing version-1 authorization files remain supported.
It is supported only on a trusted,
persistent **local filesystem with functioning locks and fsync**, not a network
share, ephemeral container filesystem, or multi-host distributed store.
Provision private directory/file ACLs, encryption, backup protection, reliable
time, and a single authoritative database outside this library. The clock
override exists for deterministic tests and must not be caller-controlled.
Rolling back/restoring old storage can restore old authorization state: offline
recovery must revoke/reconcile outstanding grants before enabling consumption.
The digest consistency check detects accidental stored-manifest changes, not a
host/database administrator rewriting both bytes and hashes.

There is deliberately **no atomic worker scheduling/outbox integration**.
A crash after commit burns the grant even if no worker starts; issue a fresh,
separately approved request after private reconciliation. A receipt is not a
credential and must never be treated as permission to relaunch an execution.
Target-conflict locking, partial-effect records, ongoing cancellation,
distributed storage, and approval/dispatch adapters remain future work.

## Minimal trusted-service usage

This excerpt assumes that a trusted adapter has already constructed `manifest`
and externally verified `binding`; it intentionally supplies no fake approval
factory, credentials, or public endpoint:

```python
from pathlib import Path
from fabric_delivery_core import SQLiteAuthorizationStore

# Use an existing access-controlled private directory, not the public checkout.
store = SQLiteAuthorizationStore(Path(private_state_directory) / "requests.sqlite3")
store.freeze(manifest)
# Only after the protected native human gate and all adapter checks:
store.authorize(manifest.request_id, binding)
# After independent revalidation/rehashing against the current authoritative state:
claim = store.consume(current_manifest, reverified_binding)
# Persisted claim identity for private reconciliation, not worker-launch credentials.
assert store.receipt(manifest.request_id) == claim
```

Do not run solution code with database access. This library includes no model
loop, Azure resources, source queries, identities, or deployment credentials.
Related installation-control work is tracked in
[Remc0000/Fabric-Delivery-OS-Control](https://github.com/Remc0000/Fabric-Delivery-OS-Control);
no private solution configuration or evidence belongs here.
