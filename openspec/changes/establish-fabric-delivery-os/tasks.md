## 0. Authorized bounded framework core (2026-11-17)

- [x] 0.1 Record the human-authorized scope: implement only immutable-request and durable one-attempt authorization primitives; no platform or deployment authorization is inferred.
- [x] 0.2 Package a reusable offline Python core with frozen manifest/schema/digest validation and real local-file SQLite state.
- [x] 0.3 Verify binding drift, expired/revoked grants, run/attempt mismatch, durable replay denial, and competing process claims using synthetic tests.
- [x] 0.4 Document the trusted-adapter boundary, local-filesystem limits, and burned-grant behavior after a crash; do not claim approval verification or worker scheduling.
- [ ] 0.5 Obtain human implementation review; do not self-approve or merge the core.
- [x] 0.6 Implement the separately authorized read-only GitHub native-history observer with a tested HTTP client and explicit nonhuman installation-token provider boundary.
- [x] 0.7 Verify private registry/manifest, numeric repository/workflow/run/attempt/environment, exact ref/revision, workflow bytes, reviewer IDs, and current branch/protection policy bindings using synthetic API evidence.
- [x] 0.8 Test missing, pending, rejected, bot, wrong-ref/environment, stale, malformed, truncated, and changed evidence denials; preserve core replay/race tests.
- [x] 0.9 Document unsupported bypass verification, reviewer credential provenance, federation, rerun attribution, and execution-grant conversion; leave execution disabled.
- [ ] 0.10 Obtain human review of the dependent verifier; no approval/merge/deployment authority follows from successful tests.
- [x] 0.11 Implement the separately authorized PyJWT/cryptography OIDC verifier with fixed official public JWKS, exact explicitly configured subject/audience, and pinned immutable signed context.
- [x] 0.12 Test actual RSA signature verification, wrong key/algorithm/context, lifetime/skew/expiry, ambiguous signed JSON, registry/policy drift, and JWKS rotation/staleness/network denial using ephemeral in-memory signing keys.
- [x] 0.13 Keep private input assertions, native-review/grant integration, App provenance, and live installation federation visibly unsupported; verify no observation can issue an execution grant.
- [ ] 0.14 Obtain human implementation review and later live-token bootstrap proof only after the separate control test is human-merged/enabled; do not activate workers from these synthetic checks.

## 1. Human review and bounded proof

- [ ] 1.1 Obtain explicit human approval of the applicable framework and control-test revisions; verify the approval identifies scope and revision rather than merely a completed checklist.
- [ ] 1.2 Implement only the separately approved synthetic control smoke test; verify its job remains blocked before approval and has no model, source, Fabric, or Azure-resource side effects.
- [ ] 1.3 Exercise human approval, rejection, and an unauthorized agent actor; verify the human gate cannot be satisfied by the agent.

## 2. Approved bootstrap and private request boundary

- [ ] 2.1 Define installation schemas and role-separation validation; verify both the allowed solo profile and a disallowed conflicting assignment.
- [ ] 2.2 Implement a read-only prerequisite report; verify unsupported GitHub, model, tool, capacity, and identity capabilities block dependent setup.
- [ ] 2.3 Present an exact bootstrap plan before creating identities or rights; verify approved grants are minimal and ordinary workers cannot change them.
- [ ] 2.4 Implement the private issue adapter and immutable request/evidence storage; verify public events contain only opaque request references.
- [ ] 2.5 Integrate version-bound requests and atomic single-use consumption with private production request storage and safe worker scheduling; local core completion alone does not complete this dispatcher integration.
  - [x] 2.5.1 Implement and test immutable binding and durable local atomic consumption in the bounded core (section 0).
  - [ ] 2.5.2 Verify authenticated adapter inputs, authoritative policy/target freshness, cloud durability, and consumption/scheduling failure handling before enabling dispatch.
- [ ] 2.6 Configure approved public control federation and policy verification; verify tokens from solution repos, other refs, and wrong environments cannot launch workers.

## 3. Isolated agent runtime

- [ ] 3.1 Confirm the Python/Agent Framework and Foundry integration with pinned dependencies; verify configured model authentication without human session reuse or provider fallback.
- [ ] 3.2 Implement trusted harness and separate untrusted code execution; verify generated code cannot access harness credentials, host identity endpoints, deployment identity, or shared privileged state.
- [ ] 3.3 Implement bounded role-based GitHub/Fabric tools; verify out-of-scope targets, control repository writes, and permission changes are refused outside the model.
- [ ] 3.4 Implement cancellation, finite execution bounds, and private error reporting; verify an exhausted or interrupted task never reports success.
- [ ] 3.5 Implement model-input and public-output policy enforcement; verify synthetic sensitive values are blocked in errors, query output, artifacts, and telemetry.

## 4. Skills and configuration

- [ ] 4.1 Verify supported skill formats and approved upstream sources; verify a Fabric profile loads the required expertise without installing irrelevant app tools.
- [ ] 4.2 Implement automatic compatible skill refresh and immutable task snapshots; verify an update cannot change an approved run.
- [ ] 4.3 Implement visible quarantine and last-known-good selection; verify new package feeds, sources, tools, or rights require the applicable separate approval.
- [ ] 4.4 Implement reviewed framework/control version upgrades independently of skill refresh; verify rollback information and policy invalidation are recorded.

## 5. Fabric delivery modules

- [ ] 5.1 Implement inventory and impact contracts for new and existing solutions; verify unrelated existing items and detected drift are preserved or explicitly blocked.
- [ ] 5.2 Implement only approved ingestion and Lakehouse medallion module behavior; verify repeat-run correctness and private reconciliation evidence.
- [ ] 5.3 Implement approved semantic-model and report modules; verify actual API, format, identity, and measure/report acceptance support.
- [ ] 5.4 Implement deterministic stage deployment with separate identities; verify exact artifact promotion and separate grants for each stage and data-changing operation.
- [ ] 5.5 Implement partial-failure evidence and separately approved recovery; verify definition rollback is not misrepresented as data restoration.

## 6. End-to-end acceptance and distribution

- [ ] 6.1 Execute the separately approved private reference scenario through all human checkpoints; verify the accepted test release is the one promoted to production.
- [ ] 6.2 Test rejection, concurrent development during acceptance, modified artifacts, duplicate dispatch, and recovery; verify each case stops or resumes at the correct checkpoint.
- [ ] 6.3 Produce a reusable installation guide and versioned release; verify a second isolated installation has no dependency on the author's credentials or private mappings.
- [ ] 6.4 Obtain human acceptance of evidence before declaring the first release complete; verify deferred reference ideas were not silently added to scope.
