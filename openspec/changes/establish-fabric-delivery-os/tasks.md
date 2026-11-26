## Progress interpretation

The separate [Teams experience checklist](../add-teams-experience-layer/tasks.md)
tracks the specification-only 2026-11-26 extension and its unapproved future
integration work. It does not mark any existing runtime/dispatcher milestone
complete or authorize setup, builds or deployment.

Reconciled on 2026-11-18 against human-merged
[framework #8](https://github.com/Remc0000/Fabric-Delivery-OS/pull/8),
the linked implementation guides, public control proof and private bootstrap
evidence. Read this checklist from the current revision, not an old merged
documentation branch.

Checked items mean only the stated bounded implementation or proof exists.
Unchecked parent milestones retain their full integration scope; completed
substeps expose partial progress. The raw checkbox percentage is an unweighted
task count, not platform readiness, execution authority or release acceptance.
Open PR work is labeled explicitly. Private identifiers/configuration and
detailed installation evidence remain in the private solution.

## 0. Authorized bounded framework core (2026-11-17)

- [x] 0.1 Record the human-authorized scope: implement only immutable-request and durable one-attempt authorization primitives; no platform or deployment authorization is inferred.
- [x] 0.2 Package a reusable offline Python core with frozen manifest/schema/digest validation and real local-file SQLite state.
- [x] 0.3 Verify binding drift, expired/revoked grants, run/attempt mismatch, durable replay denial, and competing process claims using synthetic tests.
- [x] 0.4 Document the trusted-adapter boundary, local-filesystem limits, and burned-grant behavior after a crash; do not claim approval verification or worker scheduling.
- [x] 0.5 Record human acceptance of the bounded core through the owner's merge of framework #8; no agent approval or merge was used.
- [x] 0.6 Implement the separately authorized read-only GitHub native-history observer with a tested HTTP client and explicit nonhuman installation-token provider boundary.
- [x] 0.7 Verify private registry/manifest, numeric repository/workflow/run/attempt/environment, exact ref/revision, workflow bytes, reviewer IDs, and current branch/protection policy bindings using synthetic API evidence.
- [x] 0.8 Test missing, pending, rejected, bot, wrong-ref/environment, stale, malformed, truncated, and changed evidence denials; preserve core replay/race tests.
- [x] 0.9 Document unsupported bypass verification, reviewer credential provenance, federation, rerun attribution, and execution-grant conversion; leave execution disabled.
- [x] 0.10 Record human acceptance of the dependent native verifier through framework #8; synthetic verification still does not authorize deployment.
- [x] 0.11 Implement the separately authorized PyJWT/cryptography OIDC verifier with fixed official public JWKS, exact explicitly configured subject/audience, and pinned immutable signed context.
- [x] 0.12 Test actual RSA signature verification, wrong key/algorithm/context, lifetime/skew/expiry, ambiguous signed JSON, registry/policy drift, and JWKS rotation/staleness/network denial using ephemeral in-memory signing keys.
- [x] 0.13 Keep private input assertions, native-review/grant integration, App provenance, and live installation federation visibly unsupported; verify no observation can issue an execution grant.
- [ ] 0.14 Obtain human implementation review and later live-token bootstrap proof only after the separate control test is human-merged/enabled; do not activate workers from these synthetic checks.
- [x] 0.14.1 Record human acceptance of the OIDC implementation through framework #8.
- [ ] 0.14.2 Complete the separately gated live-token/bootstrap proof; source review does not clear this activation boundary.
- [x] 0.15 Consolidate core, spend, native and OIDC source slices on the human-merged main documentation, preserving original branches without self-merging.
- [x] 0.16 Add a real credential-free offline manifest/preflight operator with bounded strict inputs, shared spend arithmetic, supported import checks and explicit live-blocked output/exit behavior.
- [x] 0.17 Verify cross-component evidence bindings cannot grant execution; test durable separate-ledger replay/breach and wrong-store identity denial, plus safe operator failures.
- [x] 0.18 Record human acceptance of the coherent integrated revision at merge commit `2816502c090ce0317b821fa987910052cde0f4fb` in framework #8; leave live native/input/OIDC joining, App provenance and dispatch disabled.
- [x] 0.19 Record the explicit agent-proposal requirement and denial scenarios: permitted proposals from existing authorized observations confer no new substantive work authority; later human gates remain intact.

### Authorized bounded local dispatch continuation (2026-11-18)

- [x] D.1 Reuse authorization/spend checks in a single attached-file SQLite grant/reservation/ready transaction, retaining permanent authorization invalidation and existing standalone APIs.
- [x] D.2 Bind the complete reviewed worker/cost/limit profile and implement one claim, pre-claim cancellation, permanent drift/expiry blocking and visible ambiguous outcomes without retry/refund.
- [x] D.3 Coordinate terminal evidence, complete trusted usage and breach freeze; surface late completion without success.
- [x] D.4 Add a disposable, input-free synthetic operator cycle with real local state and explicit live-disabled output; do not activate any worker or model.
- [x] D.5 Verify targeted/full existing suites, package/operator entry points, abrupt-process/rollback/race cases and strict OpenSpec before publishing.
- [ ] D.6 Obtain human review of this exact integrated revision and separately prove real adapter, private storage, identity and isolated-worker boundaries before activation.
- [x] D.6.1 Record human acceptance of the bounded local dispatch implementation through framework #8.
- [ ] D.6.2 Prove real adapter/private-storage/identity/isolated-worker boundaries before any live dispatch.

## 1. Human review and bounded proof

### Separately authorized bounded local spend slice (2026-11-17)

- [x] S.1 Implement immutable installation/month policy and version/validity-bound trusted price cards using integer fixed-point money, without public installation values.
- [x] S.2 Reserve maximum operation cost atomically before effects; aggregate outstanding and settled spend in one private authoritative local SQLite file.
- [x] S.3 Verify competing threads/processes, replay, invalid/stale pricing, currency/month mismatch, finite limits, durable settlement and visible excess-cost freeze.
- [x] S.4 Document no real adapter integration/model calls, no distributed or infrastructure invoice guarantee, no automatic release, and private recovery assumptions.
- [x] S.5 Record human acceptance of the bounded spend implementation through framework #8; no self-approval or merge was used.
- [ ] S.6 Separately review actual adapter enforcement, authorization/reservation/dispatch crash handling, trusted final usage and recovery before enabling any model calls.

- [x] 1.1 Record the separately authorized bounded framework/control-test scopes and human-accepted core revision; this is not approval of the complete proposed runtime.
- [x] 1.2 Implement and exercise the separately approved synthetic control smoke test, observing its protected job blocked before approval without model, source, Fabric or Azure-resource effects.
- [x] 1.3 Exercise human approval/rejection and refusal of the representative Actions-bot token; retain the [bounded public evidence](../../../README.md#what-exists-today), without claiming future App identities or production authorization are proven.

## 2. Approved bootstrap and private request boundary

- [x] 2.0 Record the human-requested reusable setup contract and current manual App enrollment steps in the README; keep installation values private and distinguish proposed scripts from shipped functionality.
  - [ ] 2.0.1 Implement and verify the separately approved parameterized setup scripts, protected credential enrollment, resumable manual checkpoints and actual installation acceptance; documentation alone does not complete onboarding.
- [ ] 2.1 Define installation schemas and role-separation validation; verify both the allowed solo profile and a disallowed conflicting assignment.
- [ ] 2.2 Implement a read-only prerequisite report; verify unsupported GitHub, model, tool, capacity, and identity capabilities block dependent setup.
  - [x] 2.2.1 Implement only offline manifest/spend-plan/import checks with explicit unknown live capabilities; this does not complete cloud/installation preflight.
  - [ ] 2.2.2 Verify actual installation configuration, CLI/tool capabilities, identities, models, GitHub protection/federation and Fabric capacity before setup activation.
- [ ] 2.3 Present an exact bootstrap plan before creating identities or rights; verify approved grants are minimal and ordinary workers cannot change them.
  - [x] 2.3.1 Record separately authorized private bootstrap plans and verify deployed credential storage preserves existing resources; this does not prove worker IAM or private retrieval.
  - [x] 2.3.2 Implement protected human-local App-key enrollment, authenticate registered App/owner permissions, and verify disabled version-bound storage; actual installation scopes and broker/runtime activation remain pending.
  - [x] 2.3.3 Implement and synthetically verify a separate private-pilot owner-local installation verifier, with source/registry-bound plan, metadata-only full-scope enumeration and mandatory token revocation; actual owner-local native proof remains pending in 2.6.1.
  - [x] 2.3.4 Refresh the pilot's referenced private bootstrap inventory and separate non-secret retrieval/provider-audit design; record bounded human resource-design/canonical-plan acceptance, fixed artifacts and local compile/regression plus offline parameter/preview-effect guards, while keeping unresolved full security validation, authenticated native preview, separate deployment/proof confirmation and actual private broker/runtime acceptance open.
- [ ] 2.4 Implement the private issue adapter and immutable request/evidence storage; verify public events contain only opaque request references.
  - [ ] 2.4.1 Enforce allowed issue repository/visibility and sanitized agent proposals without new observation/source authority; newly agent-filed requests remain proposed/awaiting approval.
  - [ ] 2.4.2 Freeze an authorized human's exact initial scope/revision/effects before discovery/design; deny labels, author identity, assignments, mutable text, validation and agent reviews as approval.
  - [ ] 2.4.3 Test proposal-without-execution, discovery-only approval without build/deploy, self-approved labels denied, changed-scope invalidation and later independent lifecycle gates before enabling ingestion.
  - [x] 2.4.4 Implement and synthetically verify only the separately authorized offline private request/policy admission registry; retain proposed state and permanent denial without claiming authenticated issue ingestion or execution joining. The human accepted this bounded implementation through [framework #16](https://github.com/Remc0000/Fabric-Delivery-OS/pull/16); see [the bounded checklist](../build-offline-request-registry/tasks.md).
  - [x] 2.4.5 Complete the separately authorized offline GitHub capture/intake adapter, synthetic isolation tests and human implementation review through [framework #17](https://github.com/Remc0000/Fabric-Delivery-OS/pull/17); this does not complete authenticated live ingestion or authorize discovery. See [the intake checklist](../build-offline-github-intake/tasks.md).
    - [x] 2.4.5.1 Implement the proposed-only normalized capture adapter and verify 27 adapter/isolation cases, all 179 regressions and the installed package; retain every live blocker.
    - [x] 2.4.5.2 Record human acceptance of the exact offline intake implementation through framework #17; no live activation is inferred.
- [ ] 2.5 Integrate version-bound requests and atomic single-use consumption with private production request storage and safe worker scheduling; local core completion alone does not complete this dispatcher integration.
  - [x] 2.5.1 Implement and test immutable binding and durable local atomic consumption in the bounded core (section 0).
  - [x] 2.5.3 Implement the bounded local atomic grant/reservation/outbox, one worker claim and conservative unknown-state protocol without claiming cloud dispatch.
  - [ ] 2.5.2 Verify authenticated adapter inputs, authoritative policy/target freshness, cloud durability, and consumption/scheduling failure handling before enabling dispatch.
  - [x] 2.5.4 Complete the separately authorized offline registry/grant/spend/outbox transaction and claim-time revalidation, synthetic race/crash proof and human review through [framework #18](https://github.com/Remc0000/Fabric-Delivery-OS/pull/18). See [the bounded coordinator checklist](../build-offline-registry-dispatch/tasks.md); this does not complete the live dispatcher.
    - [x] 2.5.4.1 Implement four-file atomic preparation/claim checks with a separate version-2 outbox; verify 37 coordinator/fault cases, all 216 regressions and the actual installed wheel without clearing live blockers.
    - [x] 2.5.4.2 Record human merge of the exact offline coordinator implementation at `f8e50fe6a24f7a6f4716040e0ec1ec931b7c1d08`; no live activation is inferred.
- [ ] 2.6 Configure approved public control federation and policy verification; verify tokens from solution repos, other refs, and wrong environments cannot launch workers.
  - [ ] 2.6.1 Authenticate actual App installation identities/effective scopes and bind private inputs, native review, OIDC, bypass policy and runtime identity in an authoritative live adapter.
    - [x] 2.6.1.1 Complete the pilot's owner-local native installation/full-selected-scope observations and confirm temporary metadata-token revocation, with safe receipts checked against the unchanged reviewed plan; live broker and authoritative authorization joining remain incomplete.

## 3. Isolated agent runtime

- [ ] 3.1 Confirm the Python/Agent Framework and Foundry integration with pinned dependencies; verify configured model authentication without human session reuse or provider fallback.
  - [x] 3.1.1 Provision the separately authorized private Azure foundation with private preservation evidence; no deployed/called model or active Agent Framework runtime is implied.
- [ ] 3.2 Implement trusted harness and separate untrusted code execution; verify generated code cannot access harness credentials, host identity endpoints, deployment identity, or shared privileged state.
- [ ] 3.3 Implement bounded role-based GitHub/Fabric tools; verify out-of-scope targets, control repository writes, and permission changes are refused outside the model.
- [ ] 3.4 Implement cancellation, finite execution bounds, and private error reporting; verify an exhausted or interrupted task never reports success.
- [ ] 3.5 Implement model-input and public-output policy enforcement; verify synthetic sensitive values are blocked in errors, query output, artifacts, and telemetry.

## 4. Skills and configuration

- [ ] 4.1 Verify supported skill formats and approved upstream sources; verify a Fabric profile loads the required expertise without installing irrelevant app tools.
  - [x] 4.1.1 Implement separately authorized supplied-data role policy/profile selection and local source/format/interface checks; actual upstream authentication, expertise and loading remain unfinished. See [the offline skill checklist](../build-offline-role-skills/tasks.md); human acceptance is recorded through [framework #19](https://github.com/Remc0000/Fabric-Delivery-OS/pull/19).
- [ ] 4.2 Implement automatic compatible skill refresh and immutable task snapshots; verify an update cannot change an approved run.
  - [x] 4.2.1 Implement pure supplied-catalog resolution, exact pins and immutable digest-bound snapshots; automatic acquisition and actual runtime snapshots remain unfinished.
- [ ] 4.3 Implement visible quarantine and last-known-good selection; verify new package feeds, sources, tools, or rights require the applicable separate approval.
  - [x] 4.3.1 Implement closed local quarantine and explicit profile/policy-bound per-reference LKG; no source/rights approval or persistent manager is inferred.
- [ ] 4.4 Implement reviewed framework/control version upgrades independently of skill refresh; verify rollback information and policy invalidation are recorded.

## 5. Fabric delivery modules

- [ ] 5.1 Implement inventory and impact contracts for new and existing solutions; verify unrelated existing items and detected drift are preserved or explicitly blocked.
- [ ] 5.2 Implement only approved ingestion and Lakehouse medallion module behavior; verify repeat-run correctness and private reconciliation evidence.
  - [x] 5.2.1 Implement and synthetically test the offline SQL-to-Bronze compiler and bounded create-only snapshot worker in [framework #10](https://github.com/Remc0000/Fabric-Delivery-OS/pull/10), still awaiting human review/merge; no live deployment/load or broader medallion completion is claimed.
  - [x] 5.2.2 Implement and verify [explicit Dev-only compiler support](../add-dev-only-sql-bronze/tasks.md), preserving version-1 bytes and independent live gates; human review/merge and private pilot acceptance remain separate.
- [ ] 5.3 Implement approved semantic-model and report modules; verify actual API, format, identity, and measure/report acceptance support.
- [ ] 5.4 Implement deterministic stage deployment with separate identities; verify exact artifact promotion and separate grants for each stage and data-changing operation.
- [ ] 5.5 Implement partial-failure evidence and separately approved recovery; verify definition rollback is not misrepresented as data restoration.

## 6. End-to-end acceptance and distribution

The separately selected [offline delivery rehearsal](../build-offline-delivery-demo/tasks.md)
exercises synthetic local consistency only. Its implementation/review does not
complete any live acceptance milestone below.

- [ ] 6.1 Execute the separately approved private reference scenario through all human checkpoints; verify the accepted test release is the one promoted to production.
- [ ] 6.2 Test rejection, concurrent development during acceptance, modified artifacts, duplicate dispatch, and recovery; verify each case stops or resumes at the correct checkpoint.
- [ ] 6.3 Produce a reusable installation guide and versioned release; verify a second isolated installation has no dependency on the author's credentials or private mappings.
  - [x] 6.3.1 Draft the generic setup/manual-checkpoint guide in [framework #11](https://github.com/Remc0000/Fabric-Delivery-OS/pull/11), still awaiting human review/merge; private pilot helpers are not a released public installer.
  - [ ] 6.3.2 Release reviewed parameterized setup tooling and verify a second isolated installation before declaring reusable installation acceptance.
- [ ] 6.4 Obtain human acceptance of evidence before declaring the first release complete; verify deferred reference ideas were not silently added to scope.
