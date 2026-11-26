## 1. Scope and specification

- [x] 1.1 Record explicit human authorization for Dev-only software, specs and synthetic tests.
- [x] 1.2 Specify versioned scope, preserved version-1 bytes and independent live gates.

## 2. Implementation

- [x] 2.1 Validate explicit version-2 development-only targets without relaxing version 1.
- [x] 2.2 Compile one Dev artifact and publish a scoped version-2 completion manifest.
- [x] 2.3 Add a synthetic Dev-only example and update the public module guide.

## 3. Verification and publication

- [x] 3.1 Verify denial, CLI, export failure and exact version-1 compatibility cases.
- [x] 3.2 Run regressions, installed-wheel checks and strict OpenSpec/document checks.
- [ ] 3.3 Publish the sanitized implementation PR for independent human review.
- [ ] 3.4 Obtain human implementation review and merge.

## 4. Deferred private pilot gates

- [ ] 4.1 Review sensitive column selection and exact private source/target mappings.
- [ ] 4.2 Verify approved runtime/source identities, rights and connector compatibility.
- [ ] 4.3 Obtain separate notebook-deployment and bounded source/load authorization.
- [ ] 4.4 Execute and reconcile the approved private Dev pilot, without model row access.

Verification: 247 regressions passed, including 19 compiler/worker cases.
The actual installed wheel passed those 19 cases and its module entrypoint
outside the checkout with sockets forbidden. Ten strict OpenSpec changes,
42 relative document links and whitespace checks passed. Version-1 synthetic
contract/payload/complete-manifest golden digests are unchanged. These are
offline checks, not Fabric deployment or connector/source-record proof.
