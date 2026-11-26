# Local durable dispatch boundary

The 2026-11-18 authorized software continuation adds a real **single-host
transactional outbox**, not a cloud dispatcher, approval service or worker.
It coordinates the existing authorization and spend stores without weakening
their trusted-caller boundary. No network, provider call, subprocess, generated
code, credentials or Azure resource is used by this module.

This guide describes the legacy version-1 three-file API. The separately
authorized [registry-bound coordinator](offline-registry-dispatch.md) uses a
different version-2 outbox and adds atomic proposal checks at preparation/claim.
The two outbox versions cannot open each other and are not automatically migrated.
Neither API authenticates human-approved private input or launches a worker.

## Try the inert cycle

From an installed, reviewed checkout:

```powershell
fabric-delivery self-test-dispatch
```

This command creates fresh temporary databases, freezes a **synthetic** request,
records a synthetic fixture binding, enqueues once, reopens the outbox, claims
once, computes a fixed inert result, settles synthetic units and checks replay
denial. It accepts no installation paths, approval inputs or worker callbacks.
Its temporary files are removed. Exit 0 means only that this local exercise
passed; output still says `execution_enabled: false` and live execution is
unsupported. It does not authenticate a human, spend money or launch an agent.

## Private trusted-service API

Import `DispatchProfile`, `SQLiteDispatchStore`, `DispatchClaim` and
`DispatchDenied` from `fabric_delivery_core`. Only the privileged service may
access these methods or any of the three files.

```python
queue = SQLiteDispatchStore(private_outbox_path, authorization_store, spend_store)
# The adapter has independently reverified current inputs, policy and the human decision.
receipt = queue.enqueue(current_manifest, reverified_binding, approved_profile)
# A fixed reviewed worker host revalidates the same facts immediately before its first claim.
claim = queue.claim(fresh_manifest, fresh_binding, approved_profile)
# Invoke only the trusted worker selected by the approved worker snapshot, at most once.
# Never retry an external effect after an ambiguous response.
queue.finish(
    claim, succeeded=True, result_digest=trusted_result_digest,
    actual_units=complete_final_cost, actual_tokens=complete_final_tokens,
    actual_calls=complete_final_calls,
)
```

There is deliberately no built-in callback, shell command, executable path,
HTTP endpoint, queue poller or credential flag. The example assumes an
authenticated adapter and a genuinely isolated fixed worker; those components
are **not supplied**. Never turn issue text, a model answer, an observation
object or a caller-provided `ApprovalBinding` into that adapter.

`DispatchProfile` canonically binds `worker_digest`, `budget_digest`,
`price_digest`, `operation`, `price_version`, UTC `period`, `currency`,
`max_tokens`, `max_calls` and positive `max_runtime_seconds`. Its full digest
must equal the manifest's `execution_profile_digest`. `worker_digest` covers
the reviewed implementation **and all its runtime configuration**, including
identity, model/region, tools, permitted targets and isolation profile.
Budget/price digests identify the canonical complete `SpendBudget`/`PriceCard`
snapshots; they must equal the ledger's immutable snapshots, not just version
labels. `budget.digest` and `price_card.digest` expose those canonical bindings.
Real pricing and policy provenance remain external prerequisites.

## State and recovery

| Transition | Durable behavior |
| --- | --- |
| Authorized request -> `ready` | One transaction consumes the grant, reserves the computed maximum and writes the outbox entry. No worker starts. |
| Enqueue denied by budget/config/storage | All three writes roll back; there was no committed execution attempt or effect. |
| Authorization drift/expiry | Permanent authorization invalidation commits before denial, as in the standalone core. |
| `ready` -> `claimed` | One claimant wins. Exact current bindings, reserve/freeze state and validity are checked under the write lock. |
| `ready` -> `blocked` | Changed bindings, expired validity or invalid reservation permanently prevent that job from starting. |
| `ready` -> `cancelled` | Cancellation burns the existing grant; no automatic refund or retry. |
| `claimed` -> `succeeded` / `failed` | Complete trusted final usage and terminal result digest commit in the same transaction. |
| `claimed` -> `breach` | Excess cost/usage, global spend freeze and failure record commit before the breach is raised. |
| `claimed` -> `unknown` | Ambiguous worker outcome is visible; reserve remains outstanding and the job is never requeued. |

A committed **ready** job may receive its first claim after restart, but only
after fresh trusted revalidation and before expiry. This is not consuming the
grant twice. A crash after the **worker claim** is committed, even before the
worker is invoked, leaves an ambiguous burned attempt: no automatic lease
expiry, reclaim, retry, refund or receipt-based relaunch exists.

`receipt(request_id)` exposes private inspection data, not launch credentials.
After lost responses, inspect instead of blindly resubmitting. Unknown,
cancelled and blocked reservations remain outstanding until a separately
reviewed reconciliation path can prove final usage; this slice deliberately
does not supply a reset, unfreeze or reconciliation endpoint.

The claim deadline is the earliest of request/approval expiry, price expiry,
UTC month end and claim time plus approved runtime. The real worker host must
enforce cancellation and token/call/time bounds **during** execution; a database
cannot stop a running external effect. Late completion still records actual
cost, but cannot report success. Cancellation after claim needs the future
mediated worker protocol; `cancel` only accepts ready jobs.

## Storage constraints and limits

All three distinct durable database files must be private, on the **same local
filesystem**, with reliable SQLite locks, fsync, protected backups and trusted
UTC time. Existing authorization/spend schemas remain version 1 and are reused.
An independent application/schema identifier protects the outbox. Missing
attached files are not recreated; unrelated schemas are rejected.

The coordinator uses SQLite `ATTACH`, `BEGIN IMMEDIATE`, `synchronous=FULL` for
each database and **DELETE rollback journals**. SQLite's
[attached-database atomicity](https://www.sqlite.org/lang_attach.html) relies on
these non-memory/non-WAL conditions and functioning host storage. WAL/other
journal modes, UNC paths and cross-device paths are refused, not silently
converted. Mapped network drives and storage with unreliable durability are
unsupported even if the host reports a device ID. Do not copy/move/restore one
file independently or let another service own a second ledger.

Tests exercise rollback, abrupt process termination around commit/claim,
restart, concurrency, expiry, cancellation and settlement failures. They are
not power-loss certification or proof of cloud/multi-host durability. There is
no exactly-once external-effect guarantee, target-conflict lock, ongoing
revocation feed, native/OIDC-to-grant join, App/federation proof, isolated
Agent Framework/Foundry host or Fabric stage worker. Live preflight stays
blocked until those separately reviewed components and real negative tests
are complete.
