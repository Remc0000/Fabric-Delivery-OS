## Why

Move from the human-merged bounded core to a concrete Fabric delivery component,
without guessing a private solution's metadata or bypassing its stage/load gates.
Framework issue #9 records the requested software continuation; the human's
2026-11-18 instruction authorizes this reusable build, not real source access
or deployment. Issue creation and this proposal do not grant execution rights.

## What Changes

- Add strict metadata-only contracts and deterministic three-stage notebook
  compilation with exact content digests and private, non-overwriting export.
- Implement a fixed worker for explicitly selected bounded create-only
  source snapshots to new Bronze Delta tables, using the documented Spark SQL
  app-token connector and explicit Key Vault secret references.
- Keep separate definition-deployment and source/load effects, finite query/row
  bounds, schema/nullability checks, target preservation and visible partial failure.
- Verify public tests with synthetic metadata/platform doubles and official
  notebook format validation, not live source records or credentials.

## Capabilities

### New Capabilities

- `sql-bronze-ingestion`: Explicit contracts, compilation and bounded create-only
  SQL-to-Bronze worker behavior.

### Modified Capabilities

None.

## Impact

Adds a standard-library offline compiler/CLI command and fixed notebook runtime
source. Platform libraries are needed only inside an approved Fabric runtime.
Real source names, endpoints, identities, target mappings and compiled artifacts
remain private. Native SQL copy currently documents only organizational-account
authentication; no unsupported headless route is claimed. Silver/Gold semantics,
semantic models/reports, incremental/delete strategies, actual provisioning,
credentials/grants, stage deployment and live acceptance are not implemented
or authorized by this change.
