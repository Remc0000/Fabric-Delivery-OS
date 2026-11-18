# First SQL-to-Lakehouse module

Tracking: [framework issue #9](https://github.com/Remc0000/Fabric-Delivery-OS/issues/9).
The issue records intent, the
[module OpenSpec](../openspec/changes/build-sql-bronze-module/specs/sql-bronze-ingestion/spec.md)
records exact behavior, and the implementation PR records their revision,
code and evidence. Chat history is not the specification store.

## What actually works

`compile-sql-bronze` turns an explicit metadata-only contract into three
stage-bound Fabric notebook payloads and a hashed release manifest, offline.
The same fixed worker/configuration code is used for all stages; only the
predeclared Lakehouse dependency metadata differs. All three are compiled once
in the release, not regenerated during promotion.

The worker implements one explicitly selected behavior:
**bounded create-only source snapshots into new `bronze` Delta tables**.
It is not a default load strategy for any real solution. Append, merge,
incremental watermarks, deletes, existing-table modification, Silver/Gold
business rules, semantic models, reports and schedules are unsupported here.
Unknown choices are not inferred from a familiar sample schema.

```powershell
fabric-delivery compile-sql-bronze ".\examples\sql-bronze.synthetic.json" --output "D:\PrivateInstallation\synthetic-bronze-release"
```

The example is intentionally synthetic and cannot locate a real source.
For actual configuration use a protected **private** file and existing private
parent directory; never commit real contracts or generated artifacts to this
public repository. The command accepts no credentials, contacts no API, reads
no source records, creates no Fabric items and cannot run a load.

Exit 0 means only `compiled_not_deployed`, with `execution_enabled: false` and
live execution unsupported. Exit 2 reports a generic failure without input
values/paths. The output directory must not exist; existing files/directories
are never overwritten. Mapped network drives and UNC paths are unsupported.

Output contains `<stage>.notebook.ipynb`, `<stage>.create.json` for each of
`development`, `test`, `production`, and final `release.json`. The manifest
hashes the exact exported bytes and identifies deployment versus load effects.
The complete manifest is published exclusively through a local hard link after
its staging file closes; the private filesystem must support hard links.
An interrupted export may leave a partial directory **without release.json**:
it is not a complete release. No automatic cleanup/reset overwrites it.
Private directory ACLs and host storage integrity are operator prerequisites;
the module is not an immutable object store or artifact signature service.

## Exact input contract

The version-1 JSON shape is demonstrated in the synthetic example. Duplicate,
missing/unknown fields and nonfinite numbers are rejected, including nested
secret-value fields. CLI input is bounded to 1 MiB UTF-8.

- `source`: exact SQL DNS server and database from authorized discovery.
  The bounded JDBC profile requires a lowercase DNS name, port 1433, and an
  ASCII database name without connection-property delimiters.
- `identity`: explicit `service_principal_keyvault_secret`, canonical tenant
  and client UUIDs, public-cloud HTTPS Key Vault URL and secret name. These are
  **references**, never a secret value, token or user credential. No default
  credential chain, Azure CLI login, SQL authentication or human fallback exists.
- `tables`: exact source schema/table, unique lowercase target table, ordered
  explicit columns and positive finite `max_rows`. Columns specify approved
  Spark type and nullability; complex types, ambiguous case-insensitive
  projections and reserved `_fdos_` names are rejected. This bounded Delta
  profile supports simple ASCII column names, not implicit column mapping.
- `targets`: all three stage names, with distinct canonical workspace and
  Lakehouse IDs and the exact existing Lakehouse name. Shared capacities are
  allowed; capacity selection is not part of this compiler.
- `notebook_name`, mandatory `load_mode: "create_only_snapshot"`, positive
  `query_timeout_seconds` (at most one day), integer `schema_version: 1`.

The trusted deployment adapter must verify that each target exists, is
schema-enabled, has the approved capacity/identity, and still matches its
approved baseline. Supplying an ID in JSON does not verify any of those facts.

## Fixed load behavior and limits

Deployment only installs definitions. A **separate stage-bound load grant**
must authorize source reads, schema/table creation and data loading before any
job starts. The trusted dispatcher must bind the exact release, rendered
stage artifact, current source/target/policy/profile and opaque UUID4
`fdos_batch_id` job parameter. That batch ID is provenance, **not approval**.

The worker checks all selected targets for existence before fetching credentials
or reading source. It reads a Key Vault secret at execution time using the
already authorized notebook execution identity, then obtains SQL tokens with
the exact configured source-reader service principal. It never writes to SQL.
The SQL account needs only approved source SELECT access and Fabric item Read,
not the broad writer/owner roles shown by generic connector examples.

Each read explicitly supplies TLS certificate validation, exact quoted
projection, `TOP (max_rows + 1)` and finite query timeout. Over-limit reads fail
instead of silently truncating the snapshot. The persisted frame's exact
column order/types and required nonnull values are checked before its write.
Data stays inside the trusted Spark job; there is no `show`, `display`,
`collect`, model call, row logging or source-record export to the compiler.

Writes add `_fdos_batch_id`, `_fdos_ingested_at`, `_fdos_source_table`, then use
Delta **errorifexists**, never overwrite/merge/schema evolution. Rerunning
against created targets fails before new source reads; it does not duplicate
or silently replace them. The dispatcher must still prevent duplicate effects
and serialize conflicting target operations; a UUID alone is not that protection.

Snapshots are not a cross-table point-in-time consistency guarantee. Each
successful table is a separate commit. A later table failure can leave earlier
new tables present; no automatic deletion/rollback/job retry is attempted. Record
the private partial state and obtain separately approved recovery. Allowlisted
write-started/table-created events contain only the frozen table index, no
names or records. A started event without completion is ambiguous, not proof
that a write failed before commit; reconcile actual target state privately.
These progress events are not a durable evidence ledger. Capturing/joining them
to the frozen mapping and reconciling actual effects are trusted-host duties.
Spark/connector errors may contain private diagnostics: keep job logs private
and do not feed raw logs/results to an agent.

## Verified platform boundaries, not live proof

Official references consulted for this implementation:

- [Spark SQL connector](https://learn.microsoft.com/fabric/data-engineering/spark-sql-connector):
  built-in Fabric connector, explicit app access tokens, `query` and JDBC options.
- [Fabric SQL authentication](https://learn.microsoft.com/fabric/database/sql/authentication):
  Microsoft Entra only; service principals need applicable tenant/item/SQL rights.
- [Native SQL copy connector](https://learn.microsoft.com/fabric/data-factory/connector-sql-database-overview):
  currently documents organizational-account authentication only. This module
  does **not** invent native Copy activity service-principal support or silently
  switch to the Azure SQL connector.
- [Notebook definition](https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/notebook-definition):
  explicit `ipynb` and `InlineBase64`, valid v4 cells and Lakehouse dependencies.
- [Notebook credentials](https://learn.microsoft.com/fabric/data-engineering/notebookutils/notebookutils-credentials):
  Key Vault retrieval and identity-context limitations. The SQL token is acquired
  explicitly with Azure Identity; no unsupported SQL `getToken` audience is guessed.

The actual approved Fabric environment must supply PySpark, the connector,
NotebookUtils and Azure Identity, trusted execution identity, narrowly scoped
Key Vault/SQL access, runtime/cost/cancellation controls and private diagnostics.
There is no auto-install, tenant-setting change, permission grant or alternative
authentication fallback. Real authentication, notebook deployment/execution,
schema compatibility and reconciliation remain **unverified** until separately
authorized live testing; local format checks and synthetic worker doubles do
not prove them. The existing preflight therefore remains live-blocked.
