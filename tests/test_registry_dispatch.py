from contextlib import closing
from dataclasses import replace
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import sqlite3
import unittest
from unittest.mock import patch
from uuid import uuid4

from fabric_delivery_core.authorization import (
    AuthorizationDenied, SQLiteAuthorizationStore, sha256_digest,
)
from fabric_delivery_core.dispatch import DispatchDenied, DispatchProfile, SQLiteDispatchStore
from fabric_delivery_core.github_intake import GitHubIntakeReceipt
from fabric_delivery_core.registry_dispatch import SQLiteRegistryDispatchStore
from fabric_delivery_core.request_registry import RegistryDenied, SQLiteRequestRegistry
from fabric_delivery_core.spend import PriceCard, SpendBudget, SpendDenied, SQLiteSpendStore
from test_authorization import NOW, approval
from test_request_registry import policy, request


class RegistryDispatchTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path.cwd() / ".test-state" / str(uuid4())
        self.directory.mkdir(parents=True)
        self.addCleanup(self.clean)
        self.now = NOW
        self.registry = SQLiteRequestRegistry(
            self.directory / "registry.sqlite3", clock=lambda: self.now,
        )
        self.auth = SQLiteAuthorizationStore(
            self.directory / "auth.sqlite3", clock=lambda: self.now,
        )
        self.spend = SQLiteSpendStore(
            self.directory / "spend.sqlite3", clock=lambda: self.now,
        )
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
            sha256_digest(b"fixed synthetic worker"), self.budget.digest,
            self.price.digest, self.price.operation, self.price.version,
            self.period, "USD", 4, 1, 20,
        )
        proposed = request(self.policy)
        self.current = replace(
            proposed, manifest=replace(
                proposed.manifest, execution_profile_digest=self.profile.digest,
            ),
        )
        # Approval is an external synthetic fixture, never derived from issue attribution.
        self.binding = approval(self.current.manifest)
        self.registry.register(self.current)
        self.auth.freeze(self.current.manifest)
        self.auth.authorize(self.current.manifest.request_id, self.binding)
        self.path = self.directory / "queue.sqlite3"
        self.store = self.open()

    def clean(self):
        shutil.rmtree(self.directory)
        try:
            self.directory.parent.rmdir()
        except OSError:
            pass

    def open(self, path=None):
        return SQLiteRegistryDispatchStore(
            self.path if path is None else path, self.registry, self.auth, self.spend,
            clock=lambda: self.now,
        )

    def enqueue(self):
        return self.store.enqueue(self.current, self.binding, self.profile)

    def claim(self):
        return self.store.claim(self.current, self.binding, self.profile)

    def finish(self, claim):
        self.store.finish(
            claim, succeeded=True, result_digest=sha256_digest(b"synthetic result"),
            actual_units=3, actual_tokens=2, actual_calls=1,
        )

    def auth_state(self):
        with closing(sqlite3.connect(self.auth.path)) as db:
            return db.execute(
                "SELECT state FROM requests WHERE request_id=?",
                (self.current.manifest.request_id,),
            ).fetchone()[0]

    def no_effects(self, state="authorized"):
        self.assertEqual(self.auth_state(), state)
        self.assertEqual(self.spend.monthly_state(
            self.policy.installation_id, self.period,
        )["outstanding_units"], 0)
        with self.assertRaisesRegex(DispatchDenied, "^unknown_dispatch$"):
            self.store.receipt(self.current.manifest.request_id)

    def held(self):
        self.assertEqual(self.auth_state(), "consumed")
        self.assertEqual(self.spend.monthly_state(
            self.policy.installation_id, self.period,
        )["outstanding_units"], 5)

    def drift(self, **change):
        return replace(self.current, manifest=replace(self.current.manifest, **change))

    def test_atomic_lifecycle_reopens_settles_and_never_replays(self):
        receipt = self.enqueue()
        self.store = self.open()
        row = self.store.receipt(self.current.manifest.request_id)
        self.assertEqual(row["registry_digest"], self.current.digest)
        self.assertEqual(row["execution_id"], receipt.execution_id)
        self.assertEqual(self.auth.receipt(receipt.request_id), receipt)
        self.held()
        claim = self.claim()
        self.store = self.open()
        self.assertEqual(claim.deadline, NOW + 20)
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_not_ready$"):
            self.claim()
        self.finish(claim)
        self.store = self.open()
        self.assertEqual(self.store.receipt(receipt.request_id)["state"], "succeeded")
        self.assertEqual(self.spend.monthly_state(
            self.policy.installation_id, self.period,
        )["settled_units"], 3)
        with self.assertRaisesRegex(AuthorizationDenied, "^consumed$"):
            self.enqueue()
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_not_claimed$"):
            self.finish(claim)

    def test_proposed_pending_and_missing_grant_do_not_prepare(self):
        with closing(sqlite3.connect(self.auth.path)) as db:
            db.execute("UPDATE requests SET state='pending',approval=NULL,approval_key=NULL")
            db.commit()
        with self.assertRaisesRegex(AuthorizationDenied, "^pending$"):
            self.enqueue()
        self.no_effects("pending")
        with closing(sqlite3.connect(self.auth.path)) as db:
            db.execute("DELETE FROM requests")
            db.commit()
        with self.assertRaisesRegex(AuthorizationDenied, "^unknown_request$"):
            self.enqueue()
        self.assertEqual(self.registry.inspect(self.current.manifest.request_id).state, "proposed")
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM dispatches").fetchone()[0], 0)
        with closing(sqlite3.connect(self.spend.path)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM reservations").fetchone()[0], 0)

    def test_receipt_and_untyped_inputs_fail_before_observed_drift(self):
        drifted = self.drift(input_digest=sha256_digest(b"changed"))
        inputs = (
            (drifted, GitHubIntakeReceipt("proposed"), self.profile),
            (self.current, None, self.profile),
            (self.current.to_json(), self.binding, self.profile),
            (self.current.manifest, self.binding, self.profile),
            (self.current, self.binding, self.profile.to_json()),
        )
        for method in (self.store.enqueue, self.store.claim):
            for values in inputs:
                with self.subTest(method=method.__name__, value=type(values[1]).__name__):
                    with self.assertRaisesRegex(DispatchDenied, "^dispatch_invalid_inputs$"):
                        method(*values)
        self.assertEqual(self.registry.inspect(self.current.manifest.request_id).state, "proposed")
        self.no_effects()

    def test_invalid_typed_nested_inputs_fail_closed_without_effects(self):
        invalid = self.drift(input_digest=sha256_digest(b"valid at creation"))
        object.__setattr__(invalid.manifest, "input_digest", "SYNTHETIC_PRIVATE_INVALID")
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_invalid_inputs$"):
            self.store.enqueue(invalid, self.binding, self.profile)
        self.no_effects()
        self.assertEqual(self.registry.inspect(self.current.manifest.request_id).state, "proposed")

    def test_manifest_snapshot_action_and_route_drift_are_permanent(self):
        changes = (
            ("input_digest", sha256_digest(b"new input")),
            ("skill_snapshot_digest", sha256_digest(b"new skills")),
            ("tool_snapshot_digest", sha256_digest(b"new tools")),
            ("framework_digest", sha256_digest(b"new framework")),
            ("execution_profile_digest", sha256_digest(b"new profile")),
            ("action", "build"),
        )
        for name, value in changes:
            proposed = request(self.policy)
            current = replace(proposed, manifest=replace(
                proposed.manifest, execution_profile_digest=self.profile.digest,
            ))
            binding = replace(approval(current.manifest), run_id=str(uuid4()))
            self.registry.register(current)
            self.auth.freeze(current.manifest)
            self.auth.authorize(current.manifest.request_id, binding)
            changed = replace(current, manifest=replace(current.manifest, **{name: value}))
            with self.subTest(name=name):
                for observed in (changed, current):
                    with self.assertRaisesRegex(RegistryDenied, "^registry_request_changed$"):
                        self.store.enqueue(observed, binding, self.profile)
                self.assertIsNone(self.auth.receipt(current.manifest.request_id))
                self.assertEqual(self.registry.inspect(current.manifest.request_id).state, "invalidated")
        route = replace(self.current, issue=replace(self.current.issue, repository_id=2002))
        with self.assertRaisesRegex(RegistryDenied, "^registry_route_changed$"):
            self.store.enqueue(route, self.binding, self.profile)
        with self.assertRaisesRegex(RegistryDenied, "^registry_route_changed$"):
            self.enqueue()
        self.no_effects()

    def test_issue_revision_and_number_are_bound_even_with_identical_manifest(self):
        changed = replace(self.current, issue=replace(
            self.current.issue, issue_number=43, revision_digest=sha256_digest(b"new issue"),
        ))
        with self.assertRaisesRegex(RegistryDenied, "^registry_request_changed$"):
            self.store.enqueue(changed, self.binding, self.profile)
        with self.assertRaisesRegex(RegistryDenied, "^registry_request_changed$"):
            self.enqueue()
        self.no_effects()

    def test_registry_check_precedes_authorization_and_expiry_is_durable(self):
        self.now = self.current.manifest.expires_at
        with patch.object(self.auth, "_consume_in_transaction", side_effect=AssertionError):
            with self.assertRaisesRegex(RegistryDenied, "^registry_expired$"):
                self.enqueue()
        self.now = NOW
        with self.assertRaisesRegex(RegistryDenied, "^registry_expired$"):
            self.enqueue()
        self.no_effects()

    def test_authorization_drift_commits_without_spending(self):
        changed = replace(self.binding, approval_evidence_digest=sha256_digest(b"changed binding"))
        with self.assertRaisesRegex(AuthorizationDenied, "^approval_mismatch$"):
            self.store.enqueue(self.current, changed, self.profile)
        with self.assertRaisesRegex(AuthorizationDenied, "^approval_mismatch$"):
            self.enqueue()
        self.no_effects("invalidated")
        self.assertEqual(self.registry.inspect(self.current.manifest.request_id).state, "proposed")

    def test_profile_and_spend_failure_roll_back_tentative_consumption(self):
        with self.assertRaisesRegex(DispatchDenied, "^profile_mismatch$"):
            self.store.enqueue(
                self.current, self.binding, replace(self.profile, max_tokens=3),
            )
        self.no_effects()
        with closing(sqlite3.connect(self.spend.path)) as db:
            db.execute("DELETE FROM budgets")
            db.commit()
        with self.assertRaisesRegex(SpendDenied, "^missing_budget$"):
            self.enqueue()
        self.spend.configure_budget(self.budget)
        self.no_effects()
        self.enqueue()
        self.held()

    def test_snapshot_mismatch_rolls_back_reservation_and_consumption(self):
        changed_profile = replace(self.profile, price_digest=sha256_digest(b"wrong price"))
        proposed = request(self.policy)
        current = replace(proposed, manifest=replace(
            proposed.manifest, execution_profile_digest=changed_profile.digest,
        ))
        binding = replace(approval(current.manifest), run_id=str(uuid4()))
        self.registry.register(current)
        self.auth.freeze(current.manifest)
        self.auth.authorize(current.manifest.request_id, binding)
        with self.assertRaisesRegex(DispatchDenied, "^spend_snapshot_mismatch$"):
            self.store.enqueue(current, binding, changed_profile)
        self.assertIsNone(self.auth.receipt(current.manifest.request_id))
        self.no_effects()

    def test_operational_and_trusted_clock_failures_roll_back_not_success(self):
        with patch.object(self.spend, "_reserve_in_transaction", side_effect=sqlite3.OperationalError(
            "SYNTHETIC_PRIVATE_STORAGE_MESSAGE",
        )):
            with self.assertRaisesRegex(DispatchDenied, "^dispatch_storage_unavailable$"):
                self.enqueue()
        self.no_effects()
        with patch.object(self.store, "_clock", side_effect=OSError("synthetic trusted clock")):
            with self.assertRaisesRegex(OSError, "^synthetic trusted clock$"):
                self.enqueue()
        self.no_effects()

    def test_one_lock_time_clock_snapshot_ignores_attached_store_clocks(self):
        with patch.object(self.store, "_clock", side_effect=[NOW, NOW + 1]) as clock:
            with patch.object(self.registry, "_clock", side_effect=AssertionError), patch.object(
                self.auth, "_clock", side_effect=AssertionError,
            ), patch.object(self.spend, "_clock", side_effect=AssertionError):
                self.enqueue()
                self.claim()
            self.assertEqual(clock.call_count, 2)

    def test_revocation_before_claim_blocks_without_refund(self):
        self.enqueue()
        self.registry.revoke(self.current.manifest.request_id)
        with self.assertRaisesRegex(RegistryDenied, "^registry_revoked$"):
            self.claim()
        self.assertEqual(self.store.receipt(self.current.manifest.request_id)["state"], "blocked")
        self.held()
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_not_ready$"):
            self.claim()

    def test_policy_replacement_before_claim_blocks_without_refund(self):
        self.enqueue()
        self.registry.register_policy(replace(self.policy, version="synthetic-v2"))
        with self.assertRaisesRegex(RegistryDenied, "^registry_policy_changed$"):
            self.claim()
        self.held()
        self.assertEqual(
            self.store.receipt(self.current.manifest.request_id)["reason"], "registry_policy_changed",
        )
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_not_ready$"):
            self.claim()

    def test_claim_drift_blocks_permanently_even_after_restoring_old_request(self):
        self.enqueue()
        changed = self.drift(tool_snapshot_digest=sha256_digest(b"changed after enqueue"))
        with self.assertRaisesRegex(RegistryDenied, "^registry_request_changed$"):
            self.store.claim(changed, self.binding, self.profile)
        self.held()
        self.assertEqual(self.registry.inspect(self.current.manifest.request_id).state, "invalidated")
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_not_ready$"):
            self.claim()

    def test_policy_revocation_before_enqueue_never_consumes_or_reserves(self):
        self.registry.revoke_policy(self.policy.digest)
        with self.assertRaisesRegex(RegistryDenied, "^registry_policy_revoked$"):
            self.enqueue()
        self.no_effects()

    def test_claim_registry_expiry_commits_invalidation_and_block_together(self):
        self.enqueue()
        self.now = self.current.manifest.expires_at
        with self.assertRaisesRegex(RegistryDenied, "^registry_expired$"):
            self.claim()
        self.now = NOW
        self.held()
        self.assertEqual(self.registry.inspect(self.current.manifest.request_id).reason, "registry_expired")
        self.assertEqual(self.store.receipt(self.current.manifest.request_id)["reason"], "registry_expired")
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_not_ready$"):
            self.claim()

    def test_registry_corruption_is_operational_not_durable_block(self):
        self.enqueue()
        with closing(sqlite3.connect(self.registry.path)) as db:
            db.execute(
                "UPDATE registry_requests SET payload=?", ('{"invalid":"synthetic"}',),
            )
            db.commit()
        with self.assertRaisesRegex(RegistryDenied, "^registry_request_corrupt$"):
            self.claim()
        self.held()
        self.assertEqual(self.store.receipt(self.current.manifest.request_id)["state"], "ready")
        with closing(sqlite3.connect(self.registry.path)) as db:
            db.execute("UPDATE registry_requests SET payload=?", (self.current.to_json(),))
            db.commit()
        self.claim()

    def test_claim_registry_digest_mismatch_blocks_even_when_manifest_matches(self):
        self.enqueue()
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("UPDATE dispatches SET registry_digest=?", (sha256_digest(b"wrong issue"),))
            db.commit()
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_binding_changed$"):
            self.claim()
        self.held()
        self.assertEqual(self.store.receipt(self.current.manifest.request_id)["state"], "blocked")

    def test_post_claim_revocation_allows_truthful_terminal_accounting(self):
        self.enqueue()
        claim = self.claim()
        self.registry.revoke_policy(self.policy.digest)
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_not_ready$"):
            self.claim()
        self.finish(claim)
        self.assertEqual(self.store.receipt(self.current.manifest.request_id)["state"], "succeeded")
        self.assertEqual(self.auth_state(), "consumed")

    def test_cancel_and_unknown_preserve_reserve_and_deny_reclaim(self):
        self.enqueue()
        self.store.cancel(self.current.manifest.request_id)
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_not_ready$"):
            self.claim()
        self.held()
        proposed = request(self.policy)
        current = replace(proposed, manifest=replace(
            proposed.manifest, execution_profile_digest=self.profile.digest,
        ))
        binding = replace(approval(current.manifest), run_id=str(uuid4()))
        self.registry.register(current)
        self.auth.freeze(current.manifest)
        self.auth.authorize(current.manifest.request_id, binding)
        self.store.enqueue(current, binding, self.profile)
        claim = self.store.claim(current, binding, self.profile)
        self.store.mark_unknown(claim)
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_not_ready$"):
            self.store.claim(current, binding, self.profile)
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_not_claimed$"):
            self.finish(claim)
        self.assertEqual(self.store.receipt(current.manifest.request_id)["state"], "unknown")
        self.assertEqual(self.spend.monthly_state(
            self.policy.installation_id, self.period,
        )["outstanding_units"], 10)

    def test_legacy_v1_v2_are_mutually_refused_without_changes(self):
        before = self.path.read_bytes()
        with self.assertRaisesRegex(DispatchDenied, "^unsupported_dispatch_database$"):
            SQLiteDispatchStore(self.path, self.auth, self.spend, clock=lambda: NOW)
        self.assertEqual(before, self.path.read_bytes())
        legacy_path = self.directory / "legacy.sqlite3"
        SQLiteDispatchStore(legacy_path, self.auth, self.spend, clock=lambda: NOW)
        before = legacy_path.read_bytes()
        with self.assertRaisesRegex(DispatchDenied, "^unsupported_dispatch_database$"):
            self.open(legacy_path)
        self.assertEqual(before, legacy_path.read_bytes())
        self.no_effects()

    def test_missing_files_are_not_recreated(self):
        for path in (self.path, self.auth.path, self.spend.path, self.registry.path):
            with self.subTest(path=path.name):
                held = path.with_suffix(".held")
                path.rename(held)
                try:
                    with self.assertRaises((DispatchDenied, RegistryDenied)):
                        self.enqueue()
                    self.assertFalse(path.exists())
                finally:
                    held.rename(path)
        self.no_effects()

    def test_instance_detects_replaced_files_and_old_registry_instance(self):
        for path in (self.path, self.auth.path, self.spend.path, self.registry.path):
            with self.subTest(path=path.name):
                replacement = path.with_suffix(".replacement")
                shutil.copyfile(path, replacement)
                original = path.with_suffix(".original")
                path.rename(original)
                replacement.rename(path)
                try:
                    with self.assertRaises((DispatchDenied, RegistryDenied)):
                        self.enqueue()
                    if path == self.registry.path:
                        with self.assertRaisesRegex(RegistryDenied, "^registry_file_replaced$"):
                            self.open()
                finally:
                    path.unlink()
                    original.rename(path)
        self.no_effects()

    def test_hard_link_alias_paths_are_refused(self):
        alias = self.directory / "alias.sqlite3"
        os.link(self.auth.path, alias)
        before = self.auth.path.read_bytes()
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_files_aliased$"):
            self.open(alias)
        self.assertEqual(before, self.auth.path.read_bytes())
        self.no_effects()

    def test_foreign_executable_schema_objects_in_any_file_are_refused(self):
        for path, table in (
            (self.path, "dispatches"), (self.auth.path, "requests"),
            (self.spend.path, "reservations"), (self.registry.path, "registry_requests"),
        ):
            for statement, drop in (
                ("CREATE VIEW unexpected AS SELECT 1", "DROP VIEW unexpected"),
                (f"CREATE TRIGGER unexpected AFTER INSERT ON {table} BEGIN SELECT 1; END",
                 "DROP TRIGGER unexpected"),
                ("CREATE TABLE unexpected (value TEXT)", "DROP TABLE unexpected"),
            ):
                with self.subTest(path=path.name, statement=statement):
                    with closing(sqlite3.connect(path)) as db:
                        db.execute(statement)
                        db.commit()
                    before = path.read_bytes()
                    try:
                        with self.assertRaisesRegex(DispatchDenied, "^unsupported_dispatch_database$"):
                            self.open()
                        self.assertEqual(before, path.read_bytes())
                    finally:
                        with closing(sqlite3.connect(path)) as db:
                            db.execute(drop)
                            db.commit()
        self.no_effects()

    def test_same_column_shape_without_required_constraints_is_refused(self):
        with closing(sqlite3.connect(self.path)) as db:
            ddl = db.execute(
                "SELECT sql FROM sqlite_master WHERE name='dispatches'",
            ).fetchone()[0]
            db.execute("DROP TABLE dispatches")
            db.execute(ddl.replace("registry_digest TEXT NOT NULL", "registry_digest TEXT"))
            db.commit()
        before = self.path.read_bytes()
        with self.assertRaisesRegex(DispatchDenied, "^unsupported_dispatch_database$"):
            self.open()
        self.assertEqual(before, self.path.read_bytes())

    def test_wal_files_are_refused_without_changing_journal_mode(self):
        for path in (self.path, self.auth.path, self.spend.path, self.registry.path):
            with self.subTest(path=path.name):
                with closing(sqlite3.connect(path)) as db:
                    self.assertEqual(db.execute("PRAGMA journal_mode=WAL").fetchone()[0], "wal")
                try:
                    with self.assertRaisesRegex(DispatchDenied, "^unsupported_journal_mode$"):
                        self.open()
                    with closing(sqlite3.connect(path)) as db:
                        self.assertEqual(db.execute("PRAGMA journal_mode").fetchone()[0], "wal")
                finally:
                    with closing(sqlite3.connect(path)) as db:
                        db.execute("PRAGMA journal_mode=DELETE")
        self.no_effects()

    def test_memory_unc_and_invalid_store_inputs_are_closed(self):
        for path in (":memory:", "", None, "\\\\synthetic-host\\private\\queue.sqlite3"):
            with self.subTest(path=path):
                with self.assertRaisesRegex(DispatchDenied, "^dispatch_invalid_inputs$"):
                    self.open(path if path is not None else 123)
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_invalid_inputs$"):
            SQLiteRegistryDispatchStore(self.path, GitHubIntakeReceipt("proposed"), self.auth, self.spend)
        self.no_effects()


if __name__ == "__main__":
    unittest.main()
