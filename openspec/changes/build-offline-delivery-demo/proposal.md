## Why

After human merge of #19, the human explicitly selected a complete offline
rehearsal on 2026-11-26: synthetic issue, skill selection, request registration,
explicit synthetic test grant, one dispatch claim and a local test result.
This joins usable components without claiming a live delivery platform.

## What Changes

- Add an input-free `demo-delivery` operator command using fresh disposable stores.
- Demonstrate proposed-only intake, exact skill binding, refusal before a test
  grant, one registry-bound claim, terminal accounting and replay refusal.
- Demonstrate permanent pre-claim denial after either skill or issue drift.
- Supply runnable instructions and synchronize bounded human acceptance of #19.

## Capabilities

### New Capabilities

- `offline-delivery-demo`: A synthetic local consistency rehearsal, not real
  discovery, agent implementation or deployment.

### Modified Capabilities

None. Existing components and every live authorization boundary remain unchanged.

## Impact

One standard-library composition module, a CLI command, focused tests and docs.
No input paths, approvals, clients, skills, workers or callbacks are accepted.
No installation credentials, network/model/Fabric calls or cloud effects.
