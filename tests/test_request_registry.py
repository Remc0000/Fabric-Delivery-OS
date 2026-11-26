from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from dataclasses import FrozenInstanceError, replace
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import sqlite3
import threading
import unittest
from unittest.mock import patch
from uuid import uuid4

from fabric_delivery_core import (
    AuthorizationDenied, IssueRevision, RegistryDenied, RegistryRequest,
    RequestPolicy, RequestRule, SQLiteAuthorizationStore, SQLiteRequestRegistry,
    sha256_digest,
)
from fabric_delivery_core.spend import SQLiteSpendStore
from test_authorization import NOW, manifest


def policy():
    return RequestPolicy(
        "synthetic-installation", "synthetic-solution", "synthetic-v1", 1001,
        (
            RequestRule("discover", ("inspect_metadata",)),
            RequestRule("build", ("write_code",)),
            RequestRule("deploy", ("deploy_definitions",)),
        ),
        NOW - 20, NOW + 1000,
    )


def request(configuration):
    value = replace(
        manifest(), action="discover", artifact_digest=None, environment=None,
        policy_digest=configuration.digest, permitted_effects=("inspect_metadata",),
        installation_id=configuration.installation_id, solution_id=configuration.solution_id,
    )
    return RegistryRequest(
        value, IssueRevision(configuration.repository_id, 42, True, sha256_digest(b"synthetic issue")),
    )


def process_register(path, proposed, ready, start, results):
    registry = SQLiteRequestRegistry(path, clock=lambda: NOW)
    ready.put(True)
    if not start.wait(20):
        raise RuntimeError("concurrency test start timed out")
    try:
        results.put(("registered", registry.register(proposed)))
    except RegistryDenied as error:
        results.put(("denied", error.reason))


class RegistryRecordTests(unittest.TestCase):
    def test_strict_roundtrip_binds_issue_policy_and_manifest(self):
        configuration = policy()
        proposed = request(configuration)
        self.assertEqual(RequestPolicy.from_json(configuration.to_json()), configuration)
        self.assertEqual(RegistryRequest.from_json(proposed.to_json()), proposed)
        self.assertNotEqual(
            replace(proposed, issue=replace(proposed.issue, revision_digest=sha256_digest(b"changed"))).digest,
            proposed.digest,
        )
        with self.assertRaises(FrozenInstanceError):
            configuration.version = "changed"
        for record, reader in (
            (configuration.to_json(), RequestPolicy.from_json),
            (proposed.to_json(), RegistryRequest.from_json),
        ):
            for value in (
                record[:-1] + ',"unexpected":true}',
                record[:-1] + record[1:],
                "[]", '{"manifest":null}',
            ):
                with self.subTest(value=value[:30]), self.assertRaises((ValueError, TypeError)):
                    reader(value)

    def test_invalid_types_ambiguous_rules_and_nested_fields_are_denied(self):
        configuration = policy()
        for change in (
            {"repository_id": True}, {"repository_id": 2**63},
            {"schema_version": True}, {"rules": []},
            {"rules": (configuration.rules[0], configuration.rules[0])},
            {"valid_until": configuration.valid_from},
            {"valid_from": True}, {"version": " "},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(configuration, **change)
        for effects in ((), ["read"], ("read", "read"), ("",)):
            with self.subTest(effects=effects), self.assertRaises(ValueError):
                RequestRule("discover", effects)
        for change in (
            {"repository_private": 1}, {"issue_number": True},
            {"issue_number": 0}, {"revision_digest": "main"},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(request(configuration).issue, **change)
        data = json.loads(configuration.to_json())
        data["rules"][0]["unknown"] = "not allowed"
        with self.assertRaises(ValueError):
            RequestPolicy.from_json(json.dumps(data))
        data = json.loads(request(configuration).to_json())
        data["issue"]["token"] = "SYNTHETIC_NEVER_STORE_CREDENTIALS"
        with self.assertRaises(ValueError):
            RegistryRequest.from_json(json.dumps(data))


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path.cwd() / ".test-state" / str(uuid4())
        self.directory.mkdir(parents=True)
        self.addCleanup(self.clean)
        self.path = self.directory / "registry.sqlite3"
        self.now = NOW
        self.registry = SQLiteRequestRegistry(self.path, clock=lambda: self.now)
        self.policy = policy()
        self.proposed = request(self.policy)

    def clean(self):
        shutil.rmtree(self.directory)
        try:
            self.directory.parent.rmdir()
        except OSError:
            pass

    def assert_denied(self, reason, operation, *args):
        with self.assertRaises(RegistryDenied) as error:
            operation(*args)
        self.assertEqual(error.exception.reason, reason)
        self.assertEqual(str(error.exception), reason)

    def register(self):
        self.registry.register_policy(self.policy)
        self.registry.register(self.proposed)

    def test_admission_survives_reopen_but_does_not_create_authorization(self):
        self.register()
        reopened = SQLiteRequestRegistry(self.path, clock=lambda: NOW)
        snapshot = reopened.revalidate(self.proposed)
        self.assertEqual(snapshot.request, self.proposed)
        self.assertEqual(snapshot.state, "proposed")
        self.assertIsNone(snapshot.reason)
        authorization = SQLiteAuthorizationStore(self.directory / "auth.sqlite3", clock=lambda: NOW)
        with self.assertRaisesRegex(AuthorizationDenied, "^unknown_request$"):
            authorization.receipt(self.proposed.manifest.request_id)

    def test_unknown_policy_wrong_route_action_effects_and_lifetime_are_denied(self):
        self.assert_denied("registry_policy_unavailable", self.registry.register, self.proposed)
        self.registry.register_policy(self.policy)
        changes = (
            ("registry_route_changed", replace(self.proposed, issue=replace(self.proposed.issue, repository_private=False))),
            ("registry_route_changed", replace(self.proposed, issue=replace(self.proposed.issue, repository_id=2001))),
            ("registry_policy_changed", replace(self.proposed, manifest=replace(self.proposed.manifest, policy_digest=sha256_digest(b"other")))),
            ("registry_action_not_allowed", replace(self.proposed, manifest=replace(self.proposed.manifest, action="unknown"))),
            ("registry_effects_not_allowed", replace(self.proposed, manifest=replace(self.proposed.manifest, action="build"))),
            ("registry_not_yet_valid", replace(self.proposed, manifest=replace(self.proposed.manifest, created_at=NOW + 1))),
            ("registry_expired", replace(self.proposed, manifest=replace(self.proposed.manifest, expires_at=NOW))),
            ("registry_request_outlives_policy", replace(self.proposed, manifest=replace(self.proposed.manifest, expires_at=NOW + 1001))),
            ("registry_policy_unavailable", replace(self.proposed, manifest=replace(self.proposed.manifest, solution_id="another-solution"))),
        )
        for reason, proposed in changes:
            with self.subTest(reason=reason):
                self.assert_denied(reason, self.registry.register, proposed)
                self.assert_denied("registry_request_unknown", self.registry.inspect, proposed.manifest.request_id)

    def test_request_and_policy_version_reuse_never_replace_existing_records(self):
        self.register()
        self.assert_denied("registry_request_reused", self.registry.register, self.proposed)
        self.assert_denied("registry_policy_version_reused", self.registry.register_policy, self.policy)
        self.assert_denied(
            "registry_policy_version_reused", self.registry.register_policy,
            replace(self.policy, repository_id=2001),
        )
        self.assertEqual(self.registry.revalidate(self.proposed).request, self.proposed)

    def test_policy_replacement_is_atomic_and_isolated_to_its_solution(self):
        self.register()
        other_policy = replace(self.policy, solution_id="synthetic-other")
        other_request = request(other_policy)
        self.registry.register_policy(other_policy)
        self.registry.register(other_request)
        newer = replace(self.policy, version="synthetic-v2")
        self.registry.register_policy(newer)
        self.assert_denied("registry_policy_changed", self.registry.revalidate, self.proposed)
        self.assertEqual(self.registry.inspect(self.proposed.manifest.request_id).state, "invalidated")
        self.assertEqual(self.registry.revalidate(other_request).state, "proposed")
        self.assert_denied("registry_policy_version_reused", self.registry.register_policy, self.policy)
        replacement = request(newer)
        self.registry.register(replacement)
        self.assertEqual(self.registry.revalidate(replacement).state, "proposed")

    def test_policy_and_request_revocation_are_permanent(self):
        self.register()
        self.registry.revoke(self.proposed.manifest.request_id)
        self.assert_denied("registry_revoked", self.registry.revalidate, self.proposed)
        self.assert_denied("registry_request_reused", self.registry.register, self.proposed)
        second = request(self.policy)
        self.registry.register(second)
        self.registry.revoke_policy(self.policy.digest)
        self.assert_denied("registry_policy_revoked", self.registry.revalidate, second)
        self.assert_denied("registry_policy_unavailable", self.registry.register, request(self.policy))
        self.assert_denied("registry_policy_version_reused", self.registry.register_policy, self.policy)

    def test_failed_policy_update_rolls_back_version_pointer_and_invalidations(self):
        self.register()
        newer = replace(self.policy, version="synthetic-v2")
        original = self.registry._transaction

        @contextmanager
        def interrupted(**kwargs):
            with original(**kwargs) as db:
                yield db
                raise sqlite3.OperationalError("SYNTHETIC_INTERRUPTED_COMMIT")

        with patch.object(self.registry, "_transaction", interrupted):
            self.assert_denied(
                "registry_storage_unavailable", self.registry.register_policy, newer,
            )
        self.assertEqual(self.registry.revalidate(self.proposed).state, "proposed")
        self.assert_denied("registry_policy_changed", self.registry.register, request(newer))
        self.registry.register_policy(newer)
        self.assert_denied("registry_policy_changed", self.registry.revalidate, self.proposed)

    def test_every_observed_issue_or_manifest_change_cannot_be_reverted(self):
        self.registry.register_policy(self.policy)
        changes = (
            ("registry_route_changed", {"issue": replace(self.proposed.issue, repository_private=False)}),
            ("registry_route_changed", {"issue": replace(self.proposed.issue, repository_id=2001)}),
            ("registry_request_changed", {"issue": replace(self.proposed.issue, issue_number=43)}),
            ("registry_request_changed", {"issue": replace(self.proposed.issue, revision_digest=sha256_digest(b"changed"))}),
        )
        changes += tuple(
            ("registry_request_changed", {"manifest": replace(self.proposed.manifest, **{field: sha256_digest(field.encode())})})
            for field in (
                "input_digest", "target_baseline_digest", "execution_profile_digest",
                "policy_digest", "framework_digest", "control_workflow_digest",
                "tool_snapshot_digest", "skill_snapshot_digest",
            )
        )
        changes += (
            ("registry_request_changed", {"manifest": replace(self.proposed.manifest, permitted_effects=("write_code",))}),
            ("registry_request_changed", {"manifest": replace(self.proposed.manifest, action="build")}),
        )
        for reason, change in changes:
            with self.subTest(change=tuple(change)):
                proposed = replace(self.proposed, manifest=replace(self.proposed.manifest, request_id=str(uuid4())))
                self.registry.register(proposed)
                if "manifest" in change:
                    change = {"manifest": replace(change["manifest"], request_id=proposed.manifest.request_id)}
                current = replace(proposed, **change)
                self.assert_denied(reason, self.registry.revalidate, current)
                reopened = SQLiteRequestRegistry(self.path, clock=lambda: NOW)
                self.assert_denied(reason, reopened.revalidate, proposed)

    def test_expiry_and_clock_rewind_are_durable_denials_not_live_readiness(self):
        self.register()
        self.now = self.proposed.manifest.expires_at
        self.assertEqual(self.registry.inspect(self.proposed.manifest.request_id).state, "proposed")
        self.assert_denied("registry_expired", self.registry.revalidate, self.proposed)
        self.now = NOW
        self.assert_denied("registry_expired", self.registry.revalidate, self.proposed)
        another = request(self.policy)
        self.registry.register(another)
        self.now = another.manifest.created_at - 1
        self.assert_denied("registry_not_yet_valid", self.registry.revalidate, another)

    def test_expiry_is_checked_after_lock_acquisition(self):
        self.register()
        entered = threading.Event()
        original = self.registry._transaction

        @contextmanager
        def transaction(**kwargs):
            entered.set()
            with original(**kwargs) as db:
                yield db

        with closing(sqlite3.connect(self.path, isolation_level=None)) as lock:
            lock.execute("BEGIN IMMEDIATE")
            with patch.object(self.registry, "_transaction", transaction), ThreadPoolExecutor(1) as executor:
                future = executor.submit(self.registry.revalidate, self.proposed)
                self.assertTrue(entered.wait(10))
                self.now = self.proposed.manifest.expires_at
                lock.commit()
                self.assert_denied("registry_expired", future.result, 10)
        self.assertEqual(self.registry.inspect(self.proposed.manifest.request_id).state, "invalidated")

    def test_competing_processes_commit_one_registration(self):
        self.registry.register_policy(self.policy)
        context = multiprocessing.get_context("spawn")
        ready, results, start = context.Queue(), context.Queue(), context.Event()
        processes = [
            context.Process(target=process_register, args=(self.path, self.proposed, ready, start, results))
            for _ in range(2)
        ]
        try:
            for process in processes:
                process.start()
            for _ in processes:
                self.assertTrue(ready.get(timeout=20))
            start.set()
            outcomes = [results.get(timeout=20) for _ in processes]
            for process in processes:
                process.join(20)
                self.assertEqual(process.exitcode, 0)
            self.assertEqual(sorted(kind for kind, _ in outcomes), ["denied", "registered"])
            self.assertIn(("denied", "registry_request_reused"), outcomes)
            self.assertEqual(self.registry.inspect(self.proposed.manifest.request_id).request, self.proposed)
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                process.join(20)
            ready.close()
            results.close()

    def test_corrupt_payload_lookup_digest_and_reason_are_closed_denials(self):
        for table, column, value, reason in (
            ("policies", "payload", '{"private":"SYNTHETIC"}', "registry_policy_corrupt"),
            ("policies", "version", "SYNTHETIC_CHANGED", "registry_policy_corrupt"),
            ("registry_requests", "payload", '{"private":"SYNTHETIC"}', "registry_request_corrupt"),
            ("registry_requests", "digest", sha256_digest(b"changed"), "registry_request_corrupt"),
            ("registry_requests", "reason", "SYNTHETIC_PRIVATE", "registry_request_corrupt"),
        ):
            with self.subTest(table=table, column=column):
                path = self.directory / str(uuid4())
                registry = SQLiteRequestRegistry(path, clock=lambda: NOW)
                registry.register_policy(self.policy)
                registry.register(self.proposed)
                with closing(sqlite3.connect(path)) as db:
                    db.execute(f"UPDATE {table} SET {column}=?", (value,))
                    db.commit()
                self.assert_denied(reason, registry.inspect, self.proposed.manifest.request_id)

    def test_unrelated_schemas_and_schema_changes_are_not_converted(self):
        for store_type in (SQLiteAuthorizationStore, SQLiteSpendStore):
            with self.subTest(store=store_type.__name__):
                path = self.directory / str(uuid4())
                store_type(path, clock=lambda: NOW)
                with closing(sqlite3.connect(path)) as db:
                    before = db.execute("SELECT sql FROM sqlite_master").fetchall()
                self.assert_denied("registry_schema_unsupported", SQLiteRequestRegistry, path)
                with closing(sqlite3.connect(path)) as db:
                    self.assertEqual(db.execute("SELECT sql FROM sqlite_master").fetchall(), before)
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("ALTER TABLE registry_requests ADD COLUMN unsafe TEXT")
            db.commit()
        self.assert_denied("registry_schema_unsupported", self.registry.inspect, str(uuid4()))

    def test_missing_and_replaced_files_are_not_reinitialized(self):
        self.register()
        self.path.unlink()
        self.assert_denied("registry_file_unavailable", self.registry.inspect, self.proposed.manifest.request_id)
        self.assertFalse(self.path.exists())
        replacement = self.directory / "replacement.sqlite3"
        SQLiteRequestRegistry(replacement, clock=lambda: NOW)
        os.replace(replacement, self.path)
        self.assert_denied("registry_file_replaced", self.registry.inspect, self.proposed.manifest.request_id)

    def test_unsupported_journal_and_storage_failure_remain_explicit(self):
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("PRAGMA journal_mode=WAL").fetchone()[0], "wal")
        self.assert_denied("registry_journal_unsupported", self.registry.register_policy, self.policy)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        with patch(
            "fabric_delivery_core.request_registry.sqlite3.connect",
            side_effect=sqlite3.OperationalError("SYNTHETIC_PRIVATE_PATH"),
        ):
            self.assert_denied("registry_storage_unavailable", self.registry.inspect, str(uuid4()))


if __name__ == "__main__":
    unittest.main()
