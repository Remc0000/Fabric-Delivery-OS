## Why

After human-merging PR #18, the human explicitly authorized an offline
role/skill layer on 2026-11-26: manually managed role selections, supplied source/
compatibility policy and immutable snapshots, with parallel implementation,
independent tests and contract review. No downloads, new rights, model calls,
hosting resources or activation are authorized.

## What Changes

- Add strict editable profile/policy/catalog records and manual immutable-revision
  pins. Only explicitly selected, allowed skills satisfy a role's required set.
- Resolve the newest eligible candidate by its supplied release sequence, checking
  origin, exact content hash, dependency/format and declared runtime interface.
- Return visible quarantine decisions; permit last-known-good material only from
  an explicit matching snapshot, visibly labeled rather than silently substituted.
- Freeze complete policy/profile, selected exact text and catalog/fallback digests
  in a snapshot usable as the existing manifest's skill snapshot digest.
- Preserve existing execution gates. Snapshot creation cannot authorize a request
  or change an already approved run; live retrieval/loading/source proof is deferred.

## Capabilities

### New Capabilities

- `offline-role-skills`: Local role-policy selection and immutable supplied-skill
  snapshots, without a skill downloader, execution host or permission broker.

### Modified Capabilities

None. Existing runtime/skill proposals retain their full live scope.

## Impact

One standard-library module, synthetic unit/integration tests, exports and guides.
No existing store/operator API changes, network calls, dependency installation,
actual upstream skill acquisition or agent hosting.
