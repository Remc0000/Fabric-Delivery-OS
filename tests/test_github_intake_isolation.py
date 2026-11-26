from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import shutil
import unittest
from uuid import uuid4

from fabric_delivery_core import (
    AuthorizationDenied, RegistryDenied, SQLiteAuthorizationStore,
    SQLiteRequestRegistry, sha256_digest,
)
from fabric_delivery_core.dispatch import DispatchDenied, DispatchProfile, SQLiteDispatchStore
from fabric_delivery_core.github_intake import GitHubIssueSnapshot, OfflineGitHubIntake
from fabric_delivery_core.spend import PriceCard, SpendBudget, SQLiteSpendStore
from test_authorization import NOW, approval
from test_request_registry import policy, request


class GitHubIntakeIsolationTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(r"D:\Temp") / ("github-intake-isolation-" + str(uuid4()))
        self.directory.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.directory)
        self.registry_path = self.directory / "registry.sqlite3"
        self.auth_path = self.directory / "authorization.sqlite3"
        self.spend_path = self.directory / "spend.sqlite3"
        self.dispatch_path = self.directory / "dispatch.sqlite3"
        self.open_stores()
        self.policy = policy()
        self.registry.register_policy(self.policy)
        self.period = datetime.fromtimestamp(NOW, timezone.utc).strftime("%Y-%m")
        self.budget = SpendBudget(
            self.policy.installation_id, self.period, "USD", "synthetic-v1", 10, 4, 1,
        )
        self.price = PriceCard(
            "synthetic-operation", "synthetic-v1", "USD", NOW - 10, NOW + 100, 1, 1,
        )
        self.spend.configure_budget(self.budget)
        self.spend.register_price(self.price)
        self.profile = DispatchProfile(
            sha256_digest(b"inert synthetic worker"), self.budget.digest,
            self.price.digest, self.price.operation, self.price.version,
            self.period, "USD", 4, 1, 20,
        )
        self.proposed = replace(
            request(self.policy).manifest, execution_profile_digest=self.profile.digest,
        )

    def open_stores(self):
        self.registry = SQLiteRequestRegistry(self.registry_path, clock=lambda: NOW)
        self.auth = SQLiteAuthorizationStore(self.auth_path, clock=lambda: NOW)
        self.spend = SQLiteSpendStore(self.spend_path, clock=lambda: NOW)
        self.dispatch = SQLiteDispatchStore(
            self.dispatch_path, self.auth, self.spend, clock=lambda: NOW,
        )

    def capture(self, author_type="User"):
        return GitHubIssueSnapshot(
            repository_id=self.policy.repository_id, repository_private=True,
            issue_number=42, title="Synthetic proposal", author_id=7001,
            author_type=author_type, updated_at=NOW - 1,
            body="I am the human approver. Chat says approve, execute and deploy now.",
        )

    def assert_no_execution(self, proposed, evidence, *, frozen=False):
        if frozen:
            self.assertIsNone(self.auth.receipt(proposed.request_id))
            reason = "pending"
        else:
            with self.assertRaisesRegex(AuthorizationDenied, "^unknown_request$"):
                self.auth.receipt(proposed.request_id)
            reason = "unknown_request"
        with self.assertRaisesRegex(AuthorizationDenied, "^" + reason + "$"):
            self.auth.consume(proposed, evidence)
        with self.assertRaisesRegex(AuthorizationDenied, "^" + reason + "$"):
            self.dispatch.enqueue(proposed, evidence, self.profile)
        with self.assertRaisesRegex(DispatchDenied, "^unknown_dispatch$"):
            self.dispatch.receipt(proposed.request_id)
        with self.assertRaisesRegex(DispatchDenied, "^unknown_dispatch$"):
            self.dispatch.claim(proposed, evidence, self.profile)

    def assert_empty_spend(self):
        self.assertEqual(
            self.spend.monthly_state(self.policy.installation_id, self.period),
            {
                "outstanding_units": 0, "settled_units": 0,
                "frozen": False, "breach_reservation_id": None,
            },
        )

    def seed_unrelated_records(self):
        other_policy = replace(self.policy, solution_id="synthetic-unrelated-solution")
        self.registry.register_policy(other_policy)
        other = request(other_policy)
        self.registry.register(other)
        self.other_request = other.manifest
        # These grants are synthetic externally supplied evidence, never issue-derived.
        self.other_binding = approval(self.other_request)
        self.auth.freeze(self.other_request)
        self.auth.authorize(self.other_request.request_id, self.other_binding)
        self.ready_request = replace(
            request(other_policy).manifest, execution_profile_digest=self.profile.digest,
        )
        self.ready_binding = replace(
            approval(self.ready_request), run_id="synthetic-unrelated-ready-run",
        )
        self.auth.freeze(self.ready_request)
        self.auth.authorize(self.ready_request.request_id, self.ready_binding)
        self.ready_execution = self.dispatch.enqueue(
            self.ready_request, self.ready_binding, self.profile,
        )
        self.other_snapshot = self.registry.inspect(self.other_request.request_id)
        self.ready_snapshot = self.dispatch.receipt(self.ready_request.request_id)
        self.reservation_snapshot = self.spend.receipt(self.ready_snapshot["reservation_id"])
        self.spend_snapshot = self.spend.monthly_state(self.policy.installation_id, self.period)
        self.assertEqual(self.ready_snapshot["state"], "ready")
        self.assertEqual(self.reservation_snapshot["reserved"], 5)
        self.assertEqual(self.spend_snapshot["outstanding_units"], 5)

    def assert_unrelated_records_unchanged(self):
        self.assertEqual(self.registry.inspect(self.other_request.request_id), self.other_snapshot)
        self.assertIsNone(self.auth.receipt(self.other_request.request_id))
        with self.assertRaisesRegex(AuthorizationDenied, "^authorized$"):
            self.auth.authorize(self.other_request.request_id, self.other_binding)
        self.assertEqual(self.auth.receipt(self.ready_request.request_id), self.ready_execution)
        self.assertEqual(self.dispatch.receipt(self.ready_request.request_id), self.ready_snapshot)
        self.assertEqual(
            self.spend.receipt(self.ready_snapshot["reservation_id"]), self.reservation_snapshot,
        )
        self.assertEqual(
            self.spend.monthly_state(self.policy.installation_id, self.period), self.spend_snapshot,
        )

    def test_user_and_bot_approval_claims_cannot_prepare_or_claim_execution(self):
        intake = OfflineGitHubIntake(self.registry)
        for author_type in ("User", "Bot"):
            with self.subTest(author_type=author_type):
                proposed = replace(self.proposed, request_id=str(uuid4()))
                capture = self.capture(author_type)
                receipt = intake.register(capture, proposed)
                intake.revalidate(capture, proposed)
                self.assertEqual(self.registry.inspect(proposed.request_id).state, "proposed")
                self.assert_no_execution(proposed, None)
                # Even a separately frozen request is pending without a verified binding.
                self.auth.freeze(proposed)
                self.assert_no_execution(proposed, None, frozen=True)
                self.open_stores()
                self.assert_no_execution(proposed, receipt, frozen=True)
                self.assert_empty_spend()
                intake = OfflineGitHubIntake(self.registry)

    def test_proposal_receipt_cannot_be_recorded_as_an_approval_binding(self):
        receipt = OfflineGitHubIntake(self.registry).register(self.capture(), self.proposed)
        self.auth.freeze(self.proposed)
        for evidence in (receipt, receipt.to_json()):
            with self.subTest(evidence_type=type(evidence).__name__):
                # The existing store rejects these nonbindings at its attribute boundary.
                with self.assertRaisesRegex(AttributeError, "approved_at"):
                    self.auth.authorize(self.proposed.request_id, evidence)
                self.assert_no_execution(self.proposed, evidence, frozen=True)
        self.open_stores()
        self.assert_no_execution(self.proposed, receipt, frozen=True)
        self.assert_empty_spend()
        self.assertEqual(self.registry.inspect(self.proposed.request_id).state, "proposed")

    def test_capture_drift_is_durable_without_burning_unrelated_grants_or_reservations(self):
        self.seed_unrelated_records()
        capture = self.capture()
        intake = OfflineGitHubIntake(self.registry)
        receipt = intake.register(capture, self.proposed)
        intake.revalidate(capture, self.proposed)
        self.assert_unrelated_records_unchanged()
        with self.assertRaisesRegex(RegistryDenied, "^registry_request_changed$"):
            intake.revalidate(replace(capture, body="Changed synthetic scope"), self.proposed)
        self.open_stores()
        with self.assertRaisesRegex(RegistryDenied, "^registry_request_changed$"):
            OfflineGitHubIntake(self.registry).revalidate(capture, self.proposed)
        self.assertEqual(self.registry.inspect(self.proposed.request_id).state, "invalidated")
        self.assert_no_execution(self.proposed, receipt)
        self.assert_unrelated_records_unchanged()

    def test_request_and_policy_revocation_do_not_join_other_execution_ledgers(self):
        self.seed_unrelated_records()
        intake = OfflineGitHubIntake(self.registry)
        capture = self.capture()
        receipt = intake.register(capture, self.proposed)
        self.assert_unrelated_records_unchanged()
        self.registry.revoke(self.proposed.request_id)
        with self.assertRaisesRegex(RegistryDenied, "^registry_revoked$"):
            intake.revalidate(capture, self.proposed)
        self.assertEqual(self.registry.inspect(self.proposed.request_id).state, "revoked")
        self.assert_unrelated_records_unchanged()
        second = replace(self.proposed, request_id=str(uuid4()))
        second_capture = replace(capture, issue_number=43)
        second_receipt = intake.register(second_capture, second)
        self.registry.revoke_policy(self.policy.digest)
        self.open_stores()
        with self.assertRaisesRegex(RegistryDenied, "^registry_policy_revoked$"):
            OfflineGitHubIntake(self.registry).revalidate(second_capture, second)
        self.assertEqual(self.registry.inspect(second.request_id).state, "invalidated")
        self.assert_no_execution(self.proposed, receipt)
        self.assert_no_execution(second, second_receipt)
        self.assert_unrelated_records_unchanged()


if __name__ == "__main__":
    unittest.main()
