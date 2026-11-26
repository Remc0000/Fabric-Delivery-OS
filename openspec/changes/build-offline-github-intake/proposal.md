## Why

The human explicitly authorized a parallel offline continuation on 2026-11-26:
implement and synthetically test a GitHub issue intake adapter, and separately
specify Teams intake contracts. This is not permission to ingest live issues,
authenticate identities, convert evidence into grants or activate any runtime.

## What Changes

- Normalize a bounded, explicitly supplied private issue capture into an immutable
  issue revision, paired with a separately supplied execution manifest.
- Admit only initial `discover` proposals through the existing private registry.
  Intake never authorizes even that discovery; an exact human scope is still needed.
- Freeze issue content, attribution, timestamp and route in a canonical digest.
  Revalidation delegates permanent drift/expiry denial to the existing registry.
- Provide an allowlisted offline receipt without solution identifiers or content.
- Keep authenticated fetching, raw webhook normalization, Teams connectivity,
  public feedback delivery and all execution joining outside this implementation.

## Capabilities

### New Capabilities

- `offline-github-intake`: Trusted-caller normalization and proposed-only local
  admission of supplied private issue snapshots.

### Modified Capabilities

None. Baseline specifications remain unpopulated; related proposal progress will
explicitly distinguish this offline substep from the unfinished live adapter.

## Impact

A standard-library module, synthetic unittest cases, exports and a usage guide.
Existing registry, authorization, spend, dispatch and preflight APIs are unchanged.
The parallel [Teams change](../specify-offline-teams-intake/proposal.md) is
specification-only and supplies no working connector; its
[design](../specify-offline-teams-intake/design.md) and
[scenarios](../specify-offline-teams-intake/specs/teams-intake-contract/spec.md)
retain separate private-audience, capability and human-governance gates.
