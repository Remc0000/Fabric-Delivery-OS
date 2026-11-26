## Why

The framework needs a durable private record of which issue revision, immutable
manifest and installation policy a proposed request belongs to. Existing
authorization primitives accept externally verified grants but do not provide
this request/policy admission registry.

On 2026-11-26 the human explicitly selected: offline request/policy registry
specification, implementation and synthetic testing, with no live integrations.
That permits the bounded library below, not issue ingestion, authentication,
approval conversion, worker activation or installation setup.

## What Changes

- Add immutable versioned private-solution policy snapshots, binding an
  installation/solution, numeric repository identity, action-specific effects,
  and explicit validity interval.
- Add frozen issue revision and execution-manifest records in a dedicated local
  SQLite registry. Accepted registrations remain proposed, never authorized.
- Reject unknown policy, public/wrong repository, mismatched installation,
  disallowed action/effects, invalid lifetime and reused request/policy versions.
- Privileged policy replacement/revocation and observed request/input drift
  permanently invalidate affected proposals; reverting bytes cannot revive them.
- Persist proposed, invalidated and revoked state, with closed diagnostic codes,
  strict schema/content checks, no file recreation during ordinary operations,
  and transactionally serialized competing registrations.
- Keep every method trusted-caller-only. Caller-supplied issue metadata and policy
  values are not authenticated GitHub evidence, human approvals or live grants.

## Capabilities

### New Capabilities

- `offline-request-registry`: Local immutable policy/admission records and
  conservative revalidation for private solution requests.

### Modified Capabilities

None. Accepted baseline specifications are not yet populated. This change
implements only a bounded substep of the proposed private request boundary in
`establish-fabric-delivery-os`, preserving all its human gates.

## Impact

One standard-library Python module, public exports, synthetic unittest cases
and synchronized guides/specifications. No new runtime dependency or CLI is
needed. Existing authorization, spend, dispatch and preflight APIs are unchanged.
The registry is separate from their databases and cannot record an
ApprovalBinding, consume a grant, dispatch work or fetch external data.
