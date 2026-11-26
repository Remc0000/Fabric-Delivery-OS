## Why

A separately authorized Dev pilot has a real development target but no approved
Test or production mappings. The existing version-1 compiler rightly refuses
incomplete three-stage contracts. Inventing later target IDs or provisioning
unapproved stages is not an acceptable workaround.

## What Changes

- Add an explicitly selected version-2 development-only contract using the
  existing metadata shape and exactly one development target.
- Compile only the development notebook/payload and publish a version-2
  completion manifest that marks development-only scope and no promotion support.
- Preserve version-1 validation, contract digests, notebook bytes and manifest
  bytes. Its three distinct stage targets remain mandatory.
- Keep identity, finite row/query bounds, fixed create-only worker behavior,
  private output and separate deployment/load authority unchanged.

The human explicitly authorized this software build, related specifications
and synthetic testing. Source metadata discovery and pilot choices are private;
they are not notebook deployment, source-record or load approval.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `sql-bronze-ingestion`: explicit development-only release support without
  weakening the existing three-stage contract.

## Impact

The offline compiler, focused tests, synthetic examples and module guide change.
No runtime host, approval adapter, identity, permission, source read, notebook
deployment, Fabric job, capacity change or new environment is supplied.
