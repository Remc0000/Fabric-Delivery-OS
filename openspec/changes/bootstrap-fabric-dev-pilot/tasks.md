## 1. Bounded owner-local Dev bootstrap

- [x] 1.1 Record human permission for scoped metadata verification and exactly two new Dev resources.
- [x] 1.2 Verify existing active trial, obtain explicit region/capacity selection and correct the invalid Lakehouse name with human approval.
- [x] 1.3 Recheck selected capacity/name absence and create only the workspace and schema-enabled Lakehouse.
- [x] 1.4 Verify persisted assignment/schema metadata and retain private item IDs/receipt.
- [x] 1.5 Publish sanitized specification/evidence in [framework #21](https://github.com/Remc0000/Fabric-Delivery-OS/pull/21) without claiming an installer or live data delivery.
- [ ] 1.6 Obtain human documentation review/merge; publication is not acceptance.

## 2. SQL-to-Bronze remains separate

- [ ] 2.1 Freeze private source/table/column/finite row scope and actual identity/runtime prerequisites.
- [ ] 2.2 Resolve real stage mappings or separately approve a Dev-only compiler contract; never invent later-stage IDs.
- [ ] 2.3 Obtain independent exact notebook deployment and source-read/data-load approval, then verify worker outcomes privately.

## Bounded evidence on 2026-11-26

- Current owner-local metadata confirmed the selected existing trial was active
  and the exact requested workspace did not exist.
- Explicit workspace creation succeeded; direct readback verified its assigned
  capacity and `capacityAssignmentProgress: Completed`.
- Explicit schema-enabled Lakehouse creation succeeded; direct readback verified
  its name and `properties.defaultSchema: dbo`.
- The automatically provisioned SQL endpoint was initially `InProgress` and
  subsequently reported provisioning `Success`. Actual SQL queries and any
  source/runtime/job behavior remain unproven.
- Actual mapping and receipt were retained privately, outside public Git.
  No capacity/rights/identity changes, source reads, notebook jobs or loads occurred.
- All 9 current OpenSpec changes passed strict validation; 41 relative links in
  changed Markdown resolved and whitespace checks passed. Public source contains
  no live item/account mapping. Human documentation review/merge remains pending.
