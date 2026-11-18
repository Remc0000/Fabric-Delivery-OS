# Local spend reservations

## Scope and trust boundary

This library is packaged alongside the immutable authorization core and optional
native/OIDC observers; co-packaging alone is not coordination or authorization.
The separate [local dispatch coordinator](durable-dispatch.md) now reuses the
same checks within an atomic attached-file grant/reservation/outbox transaction.
Explicit human authorization on 2026-11-17 permits this bounded implementation,
not model calls, cloud provisioning, or deployment. Import its API from
`fabric_delivery_core.spend`. It uses Python's standard library only.

The [offline operator](offline-operator.md) reuses the same dataclass validation
and `maximum_reservation_units(card, max_tokens, max_calls)` calculation without
opening a ledger. That helper validates finite bounds and the integer maximum,
not policy provenance, remaining monthly headroom, authorization or dispatch.

This is **single-authority local SQLite accounting**, not a hard Azure invoice
ceiling. It does not cover infrastructure, capacity, idle resources, taxes,
network charges, independent callers, or costs omitted from the configured
operation. Azure budget alerts are not hard caps. No Azure or model API is used.
The actual approved monthly ceiling and all installation configuration remain
private. Never put real configuration, database files, or receipts in this repo
or public Actions output.

Only a trusted service may configure budgets, register price cards, reserve, or
settle. These Python objects do not authenticate policy, prices, human approval,
or provider usage. The caller must separately verify authorization using the
core and an approved adapter. Agents must have neither these APIs nor database
access. No real adapter integration is implemented or authorized here.

## Exact money, policy, and price contract

All monetary fields are **integers in 10^-9 of the stated currency**, not floats
or ordinary currency units. For example, an adapter converting a trusted decimal
price must use exact Decimal arithmetic and round an upper-bound rate UP to this
unit before registration. No conversion or exchange-rate fallback is provided.
Booleans, floats, negative amounts, and integers outside signed 64-bit bounds
are rejected. Python integer arithmetic prevents intermediate/aggregate overflow.
Currency codes must be explicit uppercase three-letter strings; their actual
meaning and supported price sources are trusted configuration responsibilities.

`SpendBudget(installation_id, period, currency, version, cap_units, max_tokens,
max_calls)` is an immutable UTC calendar-month policy. All bounds and the cap
are mandatory positive integers. Reconfiguring even the same installation/month
is denied; there is deliberately no in-place cap increase, reset, or unfreeze.

`PriceCard(operation, version, currency, valid_from, valid_until, token_units,
call_units)` contains trusted **all-in conservative maximum** per-token and
per-call rates. The validity interval is `[valid_from, valid_until)` in Unix
seconds. For asymmetric model rates use the worst applicable rate across *all*
input, cached, reasoning, and output tokens, and include every other possible
charge in the bounds. Unbounded/unknown pricing must block integration. All-zero
cards are unsupported. A zero component is allowed for operations billed only by
the other component. Version reuse, including identical re-registration, is
denied. Updates require a new version and trusted adapter selection; this small
library has no price revocation feed.

Budgets and cards are stored canonically with content digests. Reservations bind
both exact digests, the currency, period, operation/version, execution digest,
and finite maximum total tokens/calls. Hash checks detect accidental drift, not
a trusted administrator rewriting the file. Monthly policy limits the largest
reservation; it cannot be bypassed by specifying an arbitrary reserve amount.

## Lifecycle

1. Use `SQLiteSpendStore(path)` with a **separate**, access-controlled, persistent
   private local file, not the authorization database. Register the trusted
   `SpendBudget` and `PriceCard` once via `configure_budget` and `register_price`.
2. Before *any* authorized external work, call `reserve` with explicit
   `reservation_id`, `installation_id`, UTC `period`, `currency`,
   `execution_digest`, `operation`, `price_version`, `max_tokens`, and `max_calls`.
   The trusted adapter must bind an immutable, uniquely authorized **operation
   attempt** (including its parent manifest/execution, operation, and sequence)
   in `execution_digest`. It must not mint another digest to replay an attempt.
   The digest is unique across this database, not just within a month.
3. The store uses `BEGIN IMMEDIATE` and checks current month, policy, currency,
   card validity, execution limits, replay, and installation freeze. It computes
   `max_tokens * token_units + max_calls * call_units`. Outstanding reservations
   plus final settled amounts plus this maximum must not exceed the monthly cap.
   Competing connections serialize this check and insertion.
4. A successful response contains the reservation and exclusive `deadline`,
   the earlier of card expiry and UTC month end. The adapter must independently
   enforce aggregate token/call limits and stop work before that deadline,
   revalidate authorization, and prevent duplicate dispatch. The standalone spend API does
   not schedule work, enforce provider limits, or atomically consume an
   authorization grant with reservation/dispatch. Its receipt is NOT reusable
   execution authority. The separate local coordinator supplies one atomic
   outbox/claim protocol, not provider enforcement or a live worker.
5. After final, trusted, complete usage is known, call `settle` with the original
   ID/installation/period/currency/execution digest and integer `actual_units`,
   `actual_tokens`, `actual_calls`. An exact duplicate settlement is denied, not
   applied again. Read `receipt` after an ambiguous response; never retry the
   external operation. `monthly_state` exposes outstanding and final amounts.
   Actual cost can be lower than the conservative token/call calculation.
   The store cannot detect dishonest/incomplete reporting; the adapter must
   authenticate complete final amounts, not derive an actual bill from maximum
   rates. Settlement can arrive after the
   original month/card expiry; it is attributed to the reserved month, never
   silently shifted to another month.
6. Final cost above the reservation **or usage above either reserved bound**
   durably records `breach` with reported amounts/usage and freezes new
   reservations installation-wide, including later months. Only AFTER commit
   does `settle` raise `SpendDenied("settlement_breach")`. Existing outstanding
   work can still settle so further charges are visible. Low reported cost
   accompanying excess usage is also recorded and freezes; the
   recorded cost is what was reported, not a claim that the bill is known.
   Operators must reconcile privately. The external bill cannot be rolled back.

No automatic timeout, cancellation refund, partial settlement, retry release,
or expiry release exists: unknown outcomes remain reserved indefinitely.
Zero final usage is accepted only as a trusted assertion that no charge/effect
remains possible; a timeout alone is not that evidence. Crashes can strand a
reservation or burn an authorization; recovery needs private reconciliation and
fresh authorization, not relaunch from a receipt. A new month never releases old
outstanding reservations. The adapter must prevent work crossing its deadline;
otherwise correct cross-month billing is **not** guaranteed.

## Failures and supported persistence

`SpendDenied.reason` is a closed code without private values. Unknown/stale
pricing, absent policy, currency/period mismatch, exhausted budgets, excessive
requested limits, replay, binding mismatch, corrupt bindings,
and frozen installations fail closed. Schema/input errors raise `ValueError`.
SQLite/IO/clock errors propagate: callers must block execution, not substitute a
memory store, reset the database, or return success. Don't publish exceptions
that might include paths or private configuration. A failed reservation returns
no execution authority; inspection after failure is not a relaunch mechanism.

Use one authoritative file on a trusted local filesystem with working SQLite
locks/fsync (`synchronous=FULL`), protected ACLs/backups and reliable UTC time.
Tests exercise concurrent threads and local spawned processes against that same
file. They do **not** establish support for network shares, multi-host state,
distributed databases, failover replicas, ephemeral storage, or cloud billing
atomicity. Never create multiple authority files for the same installation.
Restoring/deleting/rolling back the file can restore spent headroom: offline
reconcile all outstanding and external costs before enabling any reservations.
No clock rollback protection, tamper-proof ledger, accounting correction API, or
administrative unfreeze is included. This is intentionally a small guard, not a
general ledger. Production integration and recovery are separate reviewed work.
