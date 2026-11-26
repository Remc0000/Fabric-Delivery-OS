## Why

The human explicitly requested a real Dev Fabric pilot, confirmed that its
workspace/Lakehouse do not exist, and authorized creating only those resources.
After read-only verification, the human selected an existing active trial and
its region, and approved a valid underscore-based Lakehouse name.

## What Changes

- Record bounded owner-local bootstrap, separate from agent deployment approvals.
- Create one new explicitly named Dev workspace on the selected existing capacity.
- Create one schema-enabled Lakehouse and verify persisted metadata.
- Keep private IDs, capacity/account mappings and receipts outside public Git.
- Retain source, runtime, notebook deployment/load and later-stage approvals.

## Capabilities

### New Capabilities

- `fabric-dev-bootstrap`: A separately authorized installation proof, not an
  automatic installer, hosted agent runtime or production delivery.

### Modified Capabilities

None. The existing compiler and execution/identity gates remain unchanged.

## Impact

Specification and bounded evidence only. The owner-local command uses existing
approved CLI authentication for bootstrap, not a worker's deployment grant.
No capacity activation/purchase, role/identity changes, notebook job or source read.
