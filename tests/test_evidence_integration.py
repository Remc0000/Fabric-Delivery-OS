from dataclasses import replace
import unittest

try:
    from test_github_oidc import OidcFixture
except unittest.SkipTest:
    raise unittest.SkipTest("combined evidence tests require the oidc extra") from None

from fabric_delivery_core import AuthorizationDenied
from fabric_delivery_core.github_approval import GitHubNativeApprovalVerifier
from test_github_approval import FixtureAPI


class EvidenceIntegrationTests(OidcFixture):
    def test_native_and_signed_evidence_share_binding_but_neither_grants_execution(self):
        api = FixtureAPI(self.native_responses)
        native = GitHubNativeApprovalVerifier(api, clock=lambda: self.now).verify(
            self.manifest, self.registration.control_run, self.native
        )
        identity = self.verify()
        self.assertEqual(native.manifest_digest, identity.manifest_digest)
        self.assertEqual(native.policy_snapshot_digest, identity.native_policy_digest)
        self.assertEqual(native.registration_digest, self.registration.control_run.digest)
        self.assertEqual(native.run_id, identity.run_id)
        self.assertTrue(native.execution_blockers)
        self.assertTrue(identity.execution_blockers)
        for observation in (native, identity):
            with self.assertRaisesRegex(
                AuthorizationDenied, "^execution_authorization_unsupported$"
            ):
                observation.to_approval_binding()

    def test_signed_rerun_does_not_override_native_history_attempt_limit(self):
        self.registration = replace(
            self.registration,
            control_run=replace(self.registration.control_run, run_attempt=2),
        )
        identity = self.verify(self.token(dict(self.claims, run_attempt="2")))
        self.assertEqual(identity.run_attempt, 2)
        with self.assertRaisesRegex(AuthorizationDenied, "^unsupported_run_attempt$"):
            GitHubNativeApprovalVerifier(
                FixtureAPI(self.native_responses), clock=lambda: self.now
            ).verify(self.manifest, self.registration.control_run, self.native)


if __name__ == "__main__":
    unittest.main()
