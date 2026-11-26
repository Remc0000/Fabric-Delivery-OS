## Context

The 2026-11-18 human continuation follows framework PR #8, merged by the human
at `2816502c090ce0317b821fa987910052cde0f4fb`. Framework issue #9 tracks this
module. Normative requirements live beside this design; the implementation PR
must link the issue, reviewed specification revision and evidence.

## Decisions

### 1. Compile explicit private metadata rather than discover through model output

Versioned frozen contracts carry exact source/table/column types, finite bounds,
explicit load behavior, service-principal/Key Vault references and three distinct
already selected stage Lakehouses. Unknown/duplicate fields, inline secrets,
ambiguous projections, unsafe JDBC delimiters and unsupported types/modes fail.
No actual private metadata is inferred or read by the compiler.

### 2. Use a documented app-token Spark route, not a fictional Copy connector

Current official native SQL database Copy documentation lists organizational
account authentication only. Spark's SQL connector explicitly supports app
access tokens. The bounded worker obtains the configured app secret through
NotebookUtils Key Vault retrieval, and SQL tokens via ClientSecretCredential.
This is an explicitly selected optional capability, not a private installation
identity decision. No human/default credential chain or alternative provider is
used. Real service-principal/Key Vault notebook execution still needs acceptance.

### 3. Preserve existing targets by supporting create-only snapshots first

The mode must be explicitly `create_only_snapshot`; this is not an assumed
solution refresh strategy. Precheck every target before fetching credentials,
read only projected columns up to the approved row ceiling plus one, validate
schema/types/nullability, add ingestion provenance and write Delta errorifexists.
Never truncate an over-limit result and claim a full load. Do not silently cast,
merge, delete, overwrite or evolve schema.

This is new-target Bronze support, not all of the broader medallion requirement.
There is no cross-table transaction or point-in-time consistency claim.
Partial writes stay visible; interrupted/repeated jobs do not infer rollback
or execute recovery without a new applicable authorization.
The worker emits only closed write-started/table-created events with frozen
table indices, never names or source records. Missing completion is ambiguous;
the trusted private host must capture/join events and reconcile actual effects.
These signals are not a durable evidence ledger or proof of a no-effect failure.

### 4. Freeze all stage variants once and separate definition from execution

All stages use identical reviewed worker/configuration cells, differing only in
predeclared Lakehouse dependency metadata. The release includes the exact bytes
of each stage variant and hashes. Promotion selects its reviewed variant rather
than regenerating code. The private dispatcher must bind both the release and
selected rendered artifact to the current stage grant.

Export exclusively creates a new private directory and writes release.json last
as a completeness marker. Partial export is not a usable release and never
overwrites an existing directory. Digests do not supply signatures or durable
immutability; actual bytes/storage and grants remain trusted-adapter duties.
Publish the closed manifest with an exclusive hard link, so partial manifest
writes or failed publication cannot leave a misleading completion marker.
Unsupported private filesystems fail without a fallback.

### 5. Keep activation separate from local evidence

The compiler emits allowlisted diagnostic codes with execution disabled.
Tests execute generated source against synthetic platform doubles and validate
real notebook JSON. They do not prove Spark/Fabric behavior, runtime identity,
private storage, source data quality or real costs. No tenant/rights changes,
source reads, notebook uploads, loads or scheduling occur during the build.

## Risks and open boundaries

- Exact real metadata, load semantics, capacities and analytical definitions
  still require the appropriate private discovery/design decisions.
- Real environment libraries, schema-enabled targets, identities, least-privilege
  SQL/Key Vault rights, time/cost limits and cancellation must be verified.
- The native-human/OIDC/private-input grant join and isolated workers remain
  activation prerequisites, not booleans supplied by an issue author.
- Logs can contain private Spark/SQL diagnostics and must not enter public
  Actions output or model context unclassified.

See `docs/sql-bronze-module.md` for current official platform references,
input constraints, artifact use and explicit unsupported behaviors.
