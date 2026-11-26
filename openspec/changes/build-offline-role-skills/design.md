## Typed version-1 records

- `SkillRef(source_id, skill_id)` is an explicit qualified identity.
- `SkillSelection(ref, revision=None)` selects that reference; null revision means
  newest eligible supplied candidate, not an implicit download. A pin is a full
  lowercase 40- or 64-character immutable Git-style object ID, never a branch/tag.
- `SkillSource(source_id, origin)` declares an exact HTTPS origin with no embedded
  credentials, query, fragment or whitespace. This is not authenticated provenance.
- `RoleSkillPolicy(policy_id, version, role_id, runtime_interface, approved_sources,
  allowed_skills, required_skills, schema_version=1)` holds unique typed tuples;
  required references are a subset of allowed references, whose sources are known.
- `RoleSkillProfile(profile_id, version, role_id, selections, schema_version=1)`
  holds unique explicit typed selections in intentional load order.
- `SkillArtifact(ref, origin, revision, release_sequence, content, content_digest,
  runtime_interfaces, dependency_type="skill", format_id="skill-md-v1",
  schema_version=1)` preserves exact supplied UTF-8 text. Sequence is a positive
  signed-64-bit integer; digest is the declared expected SHA-256 of its exact UTF-8
  bytes. A mismatch is a resolvable quarantine condition, not constructor success
  proof. Runtime interface/dependency/format fields are explicit declarations.
- `SkillCatalog(artifacts, schema_version=1)` rejects duplicate reference/revision
  and ambiguous reference/sequence pairs rather than guessing release order.
- `SkillQuarantine(ref, revision, reason)` holds a closed private decision, no content.
- `SkillSnapshot(profile, policy, artifacts, catalog_digest,
  fallback_snapshot_digest=None, schema_version=1, fallback_refs=())` freezes complete records and
  selected artifact bytes in profile order, verifying local eligibility and pins.
- `SkillResolution(snapshot, quarantined, used_last_known_good)` exposes the
  immutable result and visible decisions; fallback status matches snapshot binding.
- `SkillDenied` surfaces closed diagnostics, optionally private quarantine records.

All sequences/containers are immutable tuples and every basic field is strictly
validated. Profile, policy, artifact, catalog and snapshot provide canonical JSON
and strict round trips; snapshot digest is SHA-256 of the existing compact
ASCII-escaped canonical JSON bytes. Content digest instead hashes exact supplied
UTF-8 text bytes, including line endings/BOM. No normalization or script execution.
Profiles, approved sources and allowed references are nonempty; required references
may be explicitly empty and catalogs may be empty. Every selected reference must
resolve, so no partial successful snapshot drops a required or optional selection.
Pretty-printed input JSON is supported: hashes use canonical output, not raw input.

Profile/policy JSON is bounded to 64 KiB, artifact content to 1 MiB, and artifact/
catalog/snapshot canonical or raw input JSON to 16 MiB. At most 32 selections,
sources, references or catalog artifacts are accepted. Types/version/duplicates/
unknown fields/nonfinite/depth/Unicode errors fail with closed diagnostics; raw
input is bounded before parsing and constructor paths apply the same bounds.
No private content/origin/profile values appear in repr or errors. Explicit JSON
serialization is private, not a public-output sanitizer.

## Local selection

`OfflineSkillResolver(policy).resolve(profile, catalog, *,
last_known_good=None) -> SkillResolution` requires typed explicit inputs. It
checks the role, allowed selections and required set before producing a snapshot.
No default role, source, policy, skill set, tool permission or model is inferred.

Each valid typed catalog candidate is checked against source/origin policy, actual
content hash, `dependency_type == "skill"`, `format_id == "skill-md-v1"` and membership
of the policy's runtime interface in its declarations. Failed candidates are
visibly quarantined for this resolution. Other dependency types are not skills.
The format/interface labels are this offline contract, not proof of real Copilot,
Agent Framework, Foundry or Fabric compatibility. Markdown remains opaque guidance.

For each selection, match its qualified reference and optional exact revision,
then pick the greatest eligible declared release sequence. There is no SemVer
inference, remote freshness check or authenticity proof of release order.
Selecting an older eligible catalog item is accompanied by any rejected newer
candidate's quarantine status; it is not mislabeled a previously approved snapshot.
No eligible selected skill means closed denial unless explicit fallback applies.
Latest is compared only inside one qualified reference, never across sources.
Manual pins resolve to exactly that revision or fail. Ambiguity checks include
quarantined candidates; rejecting a bad tied candidate cannot hide a sequence tie.

Fallback requires a valid supplied snapshot with exactly matching complete
profile/policy digests. Recheck its artifact hashes/eligibility/pins; do not
restore a removed source, bypass changed requirements or replace a manual pin.
Use matching fallback artifacts only when no eligible current candidate exists.
New snapshot binds the current catalog and prior snapshot digest; the result
explicitly marks last-known-good use. Its caller-designated status is not human
approval, and mismatched/invalid supplied fallback fails instead of being ignored.
Fallback is evaluated per selected reference. `fallback_refs` records exactly
which ordered references came from the prior snapshot; it is a unique subset of
selections and is nonempty exactly when the fallback digest/status is present.
Snapshot deserialization verifies local content/policy/pin/order/field consistency
only. Without supplied external evidence it cannot authenticate the catalog,
fallback history, provenance or whether those opaque context digests are truthful.

## Edits, approvals and provenance

Humans can edit local profile/policy JSON and explicitly select/pin additional
allowed references. Missing required or out-of-policy additions fail closed.
Policy changes, new sources/capabilities and real access still need applicable
human governance outside this module. Policy/version labels are not an immutable
history ledger; full content digests bind changes.

Snapshot creation is pure local data processing: no filesystem discovery,
download, persistence, model/tool execution, credentials or ledger writes.
Existing approved snapshots never mutate or resolve again against a new catalog.
Changing profile/order, content, policy or selected revisions yields a new
snapshot digest; existing registry/authorization binding rejects changed run input.
This module does not create or consume an ApprovalBinding.
Role/runtime labels select guidance, not IAM, MCP, CLI, model or endpoint rights.
Policy/catalog edits do not mutate existing snapshots or automatically revoke
grants. Real source revocation/current-policy enforcement is a separate runtime
gate; changed run digests remain subject to existing durable input denial.

Current source/role metadata, immutable revision labels and interface declarations
are supplied trusted-caller assertions, not authenticated Git evidence or proof
of adequate expertise. Real role profiles still need applicable Skills for Fabric,
Azure/Foundry/GitHub/OpenSpec/testing, Rayfin for Fabric apps and attributable
Microsoft Learn guidance. Live acquisition, actual package/runtime compatibility,
skill loading, quarantine persistence, human identity and a management UI remain
separate unimplemented work.

## Parallel ownership

The implementation worker owns `skill_profiles.py` and `test_skill_profiles.py`.
The independent worker owns `test_skill_profiles_integration.py`, using existing
stores to prove changed snapshots cannot alter an approved run or grant rights.
A third reviews this contract read-only. Main owns specs/docs/exports and review
records. Worker commits and local tests are not human implementation acceptance.
