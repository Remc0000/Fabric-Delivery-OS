## Context

Version 1 freezes three distinct stage mappings and artifacts. A bounded pilot
must be able to stop at development without pretending that later targets
exist. The human authorized this software continuation, not live execution.

## Decisions

### Explicit version, no inferred missing stages

Keep the dataclass and exact JSON fields unchanged. Schema version 1 retains
its existing meaning. Schema version 2 explicitly means development-only and
requires exactly one target whose stage is `development`. It rejects empty,
Test-only, production-only, mixed, duplicate and full three-stage target sets.
Neither version silently falls back to the other.

Both versions retain the exact app/Key Vault references, bounded supported
types, positive row ceiling up to 1,000,000,000, finite query timeout and
mandatory `create_only_snapshot`. Selecting a larger pilot ceiling is not
permission to run or a cloud invoice cap.

### Versioned completion marker

The compiler traverses only the stages permitted by the validated version.
Version 2 exports `development.notebook.ipynb`, `development.create.json` and
`release.json`, using the same fixed worker/configuration cells. Its manifest
has `schema_version: 2`, `release_scope: "development_only"` and
`promotion_supported: false`, with exactly one hashed stage entry.

Version 1 retains its exact prior manifest shape and artifact bytes. A golden
synthetic fixture verifies contract, payload and complete-manifest digests.
The same development payload can have the same hash in both versions; authority
must bind the complete release, contract, stage and policy, not payload bytes
alone. Source/identity details and rendered releases remain private.

### No promotion shortcut

A development-only release supplies no Test/production artifacts or targets.
Any future trusted adapter must understand and enforce the manifest version,
reject unsupported versions, and refuse later-stage use of this release.
Three-stage delivery requires a newly reviewed version-1 contract with real
approved mappings and a freshly bound complete release; editing a manifest
or reusing a development artifact is not promotion authority.

### Keep live proof separate

Synthetic tests prove compilation and private filesystem behavior only.
Actual SQL connector type/nullability compatibility, runtime/source identities,
Key Vault access, cost/cancellation policy, notebook deployment, source-record
access and load/reconciliation remain separately verified and authorized.
Sensitive source-column decisions belong to the private solution plan, not
this public framework specification.

## Alternatives

Allowing missing stages in version 1 would silently weaken existing contracts.
Dummy IDs would misrepresent target verification. Creating later environments
would exceed the approved scope. A separately versioned Dev-only contract
avoids each of those approaches without duplicating the worker.

## Failure and Recovery

Invalid contracts fail before output creation. Export still uses exclusive file
creation and atomic final-manifest publication; failures can leave private
partial state without a completion marker. There is no overwrite, automatic
cleanup/retry, grant conversion, worker activation or schema/data mutation.
