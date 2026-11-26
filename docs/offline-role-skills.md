# Offline role and skill snapshots

This usable Python component resolves **explicitly supplied local data**, not
installed skills or live agents. It does not download, discover, load or execute
skills, call a model, persist state, grant rights or modify any ledger. The
[bounded contract](../openspec/changes/build-offline-role-skills/design.md)
separates this implementation from the future runtime and skill-source manager.

## Manually managed inputs

An authorized operator supplies a `RoleSkillPolicy` with exact approved HTTPS
origins, qualified allowed/required references and an offline runtime-interface
label. A `RoleSkillProfile` selects allowed references in load order, optionally
pinned to a full lowercase 40/64-character Git-style object ID. Every selected
reference must resolve; optional selections cannot silently disappear.

Profile and policy records support `to_json()` and `from_json()`. Start edits
from generated JSON: all fields, including defaults, must remain present.
Pretty printing is allowed; digests hash canonical output. These records and
skill/snapshot JSON are **private input/evidence**, not public workflow payloads.
Version labels are not an immutable history ledger; complete digests bind edits.
Changing source/capability policy still requires applicable human governance
outside this resolver.

A `SkillCatalog` contains supplied bytes, hashes, immutable revision labels,
declared release sequences and format/interface labels. Exact UTF-8 content is
hashed without newline/BOM normalization. The resolver checks local eligibility,
not upstream authenticity, true release freshness or actual SDK compatibility.
Labels are not IAM or tool rights; Markdown is opaque guidance.

For each qualified reference, latest means the largest eligible **supplied**
release sequence, not SemVer or an online update. Hash/source/origin/type/format/
interface failures appear as private closed-code quarantine records. Duplicate
reference/revision or reference/sequence pairs fail the catalog outright,
including duplicates involving quarantined candidates.

## Runnable synthetic example

Use the source checkout on D: with Python 3.11 or later; no dependency download
or cloud configuration is needed:

```powershell
Set-Location D:\Fabric-Delivery-OS
$env:PYTHONPATH="$PWD\src"
$env:PYTHONDONTWRITEBYTECODE='1'
```

Save the Python block below as `D:\Temp\role_skill_demo.py` and run
`python -B D:\Temp\role_skill_demo.py` in that shell. It only prints synthetic
boolean outcomes. `example.invalid` is an inert label: the code makes no request.
This is a synthetic role, not a shipped Skills for Fabric profile.

```python
import json
from dataclasses import replace

from fabric_delivery_core import (
    OfflineSkillResolver, RoleSkillPolicy, RoleSkillProfile, SkillArtifact,
    SkillCatalog, SkillRef, SkillSelection, SkillSnapshot, SkillSource,
    sha256_digest,
)

ref = SkillRef("demo", "fabric-design")
origin = "https://example.invalid/skills"
policy = RoleSkillPolicy(
    policy_id="demo-policy",
    version="v1",
    role_id="build",
    runtime_interface="offline-demo-v1",
    approved_sources=(SkillSource("demo", origin),),
    allowed_skills=(ref,),
    required_skills=(ref,),
)
profile = RoleSkillProfile(
    profile_id="demo-build",
    version="v1",
    role_id="build",
    selections=(SkillSelection(ref),),
)
resolver = OfflineSkillResolver(policy)


def artifact(revision, sequence, content):
    return SkillArtifact(
        ref=ref,
        origin=origin,
        revision=revision,
        release_sequence=sequence,
        content=content,
        content_digest=sha256_digest(content.encode("utf-8")),
        runtime_interfaces=("offline-demo-v1",),
    )


old = artifact("1" * 40, 1, "Synthetic guidance: inspect declared metadata.\n")
new = artifact("2" * 40, 2, "Synthetic guidance: also test declared changes.\n")
first = resolver.resolve(profile, SkillCatalog((old,)))
sealed = first.snapshot.to_json()
current = SkillCatalog((old, new))
updated = resolver.resolve(profile, current)
assert updated.snapshot.artifacts[0].revision == new.revision

edited = json.loads(profile.to_json())
edited["selections"][0]["revision"] = old.revision
pinned = RoleSkillProfile.from_json(json.dumps(edited, indent=2))
pinned_result = resolver.resolve(pinned, current)
assert pinned_result.snapshot.artifacts[0].revision == old.revision

corrupt = replace(new, revision="3" * 40, release_sequence=3, content="changed")
fallback = resolver.resolve(
    profile, SkillCatalog((corrupt,)), last_known_good=first.snapshot,
)
assert fallback.used_last_known_good
assert fallback.snapshot.fallback_refs == (ref,)
assert fallback.snapshot.fallback_snapshot_digest == first.snapshot.digest
assert fallback.quarantined[0].reason == "skill_content_mismatch"
assert first.snapshot.to_json() == sealed
assert SkillSnapshot.from_json(sealed).digest == first.snapshot.digest
assert updated.snapshot.digest != first.snapshot.digest

print(json.dumps({
    "latest_selected": True,
    "manual_pin_preserved": True,
    "corruption_quarantined": True,
    "explicit_fallback_used": True,
    "original_snapshot_unchanged": True,
}))
```

## Fallback and immutable approved runs

Last-known-good is an **explicit caller-supplied snapshot**, not inferred approval.
Its full profile/policy digests must match; hashes, eligibility and manual pins
are rechecked. Invalid supplied fallback is denied even if current candidates
would suffice. Use it per reference only when no eligible current candidate
exists; mixed snapshots record exact `fallback_refs` in profile order and bind
the prior snapshot digest. An older eligible current catalog item is not LKG.

Snapshots embed selected bytes, profile and policy. Deserialization proves local
self-consistency only, not catalog/history/authenticity claims or permissions.
Creating a newer snapshot never changes an older one. Feed `snapshot.digest` into
the existing manifest's `skill_snapshot_digest`; this does not replace the
separate `tool_snapshot_digest` or create/consume an approval.

The [registry-bound coordinator](offline-registry-dispatch.md) rejects changed
approved run inputs durably. The pure resolver does not automatically revoke
existing grants after an edit or source revocation; an authenticated live
current-policy/revocation gate remains separate.

## Limits and remaining runtime work

Profile/policy JSON is limited to 64 KiB, content to 1 MiB per artifact and raw/
canonical artifact/catalog/snapshot JSON to 16 MiB, with at most 32 references,
sources, selections or catalog artifacts. Malformed types, duplicates, unknown
fields, unsupported schema versions, nonfinite values, depth and Unicode errors
produce closed denials; do not put private values into logs to diagnose them.

Actual Skills for Fabric expertise, Azure/Foundry/GitHub/OpenSpec/testing skills,
Rayfin for Fabric apps and Microsoft Learn grounding are still requirements,
not resources acquired or verified by this example. Live approved-source
updates, revision authentication, runtime loaders, persistent quarantine,
management UI and hosted identities/model/tool execution remain unimplemented.
