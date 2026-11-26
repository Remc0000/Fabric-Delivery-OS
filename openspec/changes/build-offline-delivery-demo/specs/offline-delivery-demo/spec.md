## ADDED Requirements

### Requirement: Input-free disposable rehearsal

The operator SHALL compose existing intake, skills, registry, authorization,
spend and version-2 dispatch using only fresh disposable synthetic state.
It SHALL NOT accept installation paths, approvals, clients or worker callbacks.

#### Scenario: Attempt to use existing private state

- **WHEN** a caller passes a store, manifest, token or other extra argument
- **THEN** the command rejects it without opening that state or echoing input

### Requirement: Explicit grant and one local claim

Proposed intake and skill resolution SHALL NOT authorize dispatch. The demo
SHALL verify refusal before its explicit synthetic grant, one claim, terminal
result/accounting and replay refusal using real store APIs.

#### Scenario: A required check fails

- **WHEN** a component fails, an expected denial is missing or terminal state is wrong
- **THEN** the demo returns no successful report and the operator exits 2 with closed output

### Requirement: Durable drift refusal

Separate skill/capture drift scenarios SHALL verify permanent pre-claim blocking,
including reopening and restoring old inputs, consumed grant and held reservation.

#### Scenario: A prepared skill snapshot changes

- **WHEN** the supplied current snapshot differs before claim
- **THEN** ready work is blocked and old input cannot restore the job

#### Scenario: A prepared issue capture changes

- **WHEN** the supplied current issue revision differs before claim
- **THEN** the proposal is invalidated and no local claim or refund is produced

### Requirement: Offline result is not Fabric delivery

Reports SHALL reuse execution-disabled offline markers and unchanged live blockers,
omit private values and never claim model work, authenticated human gates or Fabric effects.

#### Scenario: All synthetic checks pass

- **WHEN** the operator exits 0
- **THEN** only local rehearsal consistency is established; live execution remains unsupported
