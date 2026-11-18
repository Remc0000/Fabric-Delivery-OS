## Purpose

Provide a bounded reusable local operation-cost guard without claiming to cap
cloud invoices or implementing model/provider dispatch.

## ADDED Requirements

### Requirement: Trusted immutable pricing and finite policy
The local guard SHALL require explicit installation/month cap, currency, policy
version, finite token/call maxima, and trusted operation price version/validity.
Money SHALL use integer fixed-point units without float rounding. Missing,
unknown, stale, future, incompatible, or all-zero prices SHALL NOT authorize
execution. Configuration/version reuse SHALL be denied.

#### Scenario: An operation has unknown or expired pricing
- **WHEN** a caller requests a reservation without a currently valid registered price
- **THEN** the guard denies it without granting work or changing providers

### Requirement: Atomic monthly reservations
Before authorized work, the guard SHALL atomically reserve its computed maximum
cost only if all outstanding reservations plus final settlements plus that
maximum fit the installation's UTC monthly cap. Reservations SHALL bind the
policy/card digests, operation attempt, currency, month, and finite usage bounds.
Wrong current month or currency SHALL be denied.

#### Scenario: Competing local connections reach the boundary
- **WHEN** simultaneous reservations share one authoritative supported local SQLite file
- **THEN** only reservations whose aggregate fits the cap commit
- **AND** other reservations fail visibly without a success-shaped fallback

### Requirement: Single-use durable final settlement and breach visibility
Reservation IDs and operation-attempt digests SHALL NOT be reused. Final
settlement SHALL require exact original binding and SHALL reject replay. It
SHALL accept trusted final cost below conservative rates without treating those
maximum rates as minimum charges. It SHALL retain actual reported excess, mark a visible
breach, and freeze new reservations installation-wide before reporting failure
when actual cost or usage exceeds the reservation. Existing work SHALL remain
settleable during freeze. No automatic release or unfreeze SHALL be provided.

#### Scenario: Actual cost exceeds the reserved maximum
- **WHEN** final provider cost exceeds the reservation
- **THEN** the excess and breach survive restart and new reservations are denied
- **AND** no external invoice rollback or hidden adjustment is claimed

#### Scenario: Settlement has the wrong currency or month
- **WHEN** final reporting does not match the reservation's original binding
- **THEN** settlement is denied and the outstanding reservation remains

### Requirement: Explicit integration and billing boundaries
The guard SHALL be limited to a trusted single-authority local SQLite profile.
It SHALL NOT call models/cloud APIs, authenticate approval or usage, automatically
dispatch work, or claim a hard infrastructure/cloud billing ceiling. Azure budget
alerts SHALL NOT be represented as hard caps. Integration SHALL independently
enforce bounds, prevent duplicate work, stop before card expiry/UTC month end,
and reconcile authorization/reservation/dispatch failures before enabling work.
Real installation values and evidence SHALL remain private.

#### Scenario: A worker crashes or final usage is unknown
- **WHEN** a reservation is outstanding after interruption or expiry
- **THEN** it stays reserved until trusted complete final settlement
- **AND** its receipt does not authorize replay or prove that work started
