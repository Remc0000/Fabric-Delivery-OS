# Complete offline delivery rehearsal

`demo-delivery` joins the existing components in a **synthetic local rehearsal**.
It is usable now, but it does not run an AI agent, contact GitHub/Fabric, fetch
skills, authenticate a human, deploy a notebook or load source records.
See [the bounded design](../openspec/changes/build-offline-delivery-demo/design.md).

## Run it on D:

From the reviewed source checkout, with Python 3.11+ and no package installation:

```powershell
Set-Location D:\Fabric-Delivery-OS
$env:PYTHONPATH="$PWD\src"
$env:TEMP='D:\Temp'
$env:TMP='D:\Temp'
$env:PYTHONDONTWRITEBYTECODE='1'
python -B -m fabric_delivery_core demo-delivery
```

Use an existing D: temporary parent with ordinary local SQLite file support.
If the package is already installed, `fabric-delivery demo-delivery` is equivalent.
No store, manifest, token, approval or callback argument is accepted.

## What the six results prove

| Check | Real local behavior |
| --- | --- |
| Intake and skills | Supplied inert issue capture and resolved synthetic skill bytes bind a proposed discover request |
| Approval gate | Proposed intake and a skill snapshot cannot enqueue while authorization is pending |
| Dispatch cycle | An explicit temporary test grant is consumed with maximum reservation, one fresh-store claim and a fixed inert result/settlement |
| Replay | Second claim and consumed-grant replay are denied |
| Skill drift | A new locally eligible snapshot permanently blocks prepared work; old bytes cannot restore it |
| Issue drift | Changed capture invalidates the proposal and blocks claim; grant stays consumed and full reservation remains |

Success exits 0 and prints one allowlisted JSON report. `offline_checks_passed`
is true, but **`execution_enabled` remains false** and all existing live blockers
remain. It prints no capture content, identities, hashes, file paths or raw
diagnostics. An unexpected/missing denial, missing terminal result or component/
storage failure exits 2; there is no partial success report.

Each of the three scenarios has separate fresh temporary registry, authorization,
spend and version-2 outbox files. The command removes only its own temporary state
on success or failure. This is not installation recovery, human-gate proof,
OneLake data storage or a production durability certification.

## When can we build in Fabric?

A small separately authorized **Dev pilot** can precede the complete hosted-agent
platform. The existing [SQL-to-Bronze module](sql-bronze-module.md) already compiles
stage-bound notebooks offline; the first live test must verify its actual
Fabric/runtime/identity behavior rather than repeat local format checks.

Before that live step, record the exact private Dev workspace and schema-enabled
Lakehouse, capacity/runtime, permitted source tables/columns and finite row limits,
existing target baseline, narrowly scoped identities and private diagnostics.
Obtain explicit permission for the read-only verification and then independent
notebook deployment and create-only data-load attempts. Unknown capabilities,
missing rights or existing target tables remain blockers, not defaults.

The rehearsal does not require Foundry agents to be hosted, and hosting is not
permission to deploy. Neither this command nor a merged PR authorizes any Fabric
effect, new identity/rights, source reads, or later Test/production promotion.
