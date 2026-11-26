## 1. Explicit offline continuation

- [x] 1.1 Record human authorization for parallel offline registry/authorization/spend/outbox coordination and synthetic grants/tests only.
- [x] 1.2 Freeze atomic denial, version-2 legacy isolation, claim freshness and conservative accounting contracts with disjoint ownership.
- [x] 1.3 Implement the coordinator and minimal reusable transaction helpers without changing standalone public behavior.
- [x] 1.4 Verify focused admission/claim/terminal/schema/denial cases with real synthetic stores.
- [x] 1.5 Independently verify competing processes, lock-time expiry, rollback and abrupt-process recovery.
- [x] 1.6 Resolve contract review, integrate docs/exports and validate affected/full tests, strict OpenSpec and the installed wheel.
- [ ] 1.7 Obtain human review/merge of the exact offline implementation.

## 2. Not authorized by this slice

- [ ] 2.1 Separately prove current live input/policy provenance, authenticated human scope, native/OIDC/private-input grants and bypass prevention.
- [ ] 2.2 Separately authorize and prove isolated workers, per-effect cancellation, real storage recovery and any model/source/API calls.
- [ ] 2.3 Obtain distinct deployment/functional acceptance decisions; local atomicity never authorizes cloud activation.

## Bounded evidence on 2026-11-26

- 29 focused coordinator cases plus 8 independently authored process/lock/crash
  cases passed together. Coverage includes mutual version-1/version-2 refusal,
  complete proposal binding, durable pre-claim denial, no-grant/receipt misuse,
  shared lock-time clock, schema/file/journal guards and retained reservations.
- All 216 unittest cases passed after integration; existing standalone APIs and
  the inert dispatch operator retained behavior. The operator still reports
  `execution_enabled: false` and its unchanged live blockers.
- The actual wheel was built with an existing D: build environment without
  dependency downloads and installed into an ignored D: test target. All 37
  coordinator/fault cases and the public export passed from outside the checkout,
  with network calls forbidden before import and in spawned validation processes.
- All 7 OpenSpec changes passed strict noninteractive validation; 44 local links
  across the changed Markdown files resolved and whitespace checks passed.
- The independent contract review resolved consistent lock-time observations,
  returned terminal denials, proposal versus human-approval binding and executable
  schema/legacy isolation before integration. No global privileged bypass or
  authentic live input/human/skill-content proof is inferred.
- Synthetic process failures establish local SQLite recovery evidence, not
  power-loss certification, distributed durability or a real worker lifecycle.
  Human implementation review/merge and every live gate remain separate.
