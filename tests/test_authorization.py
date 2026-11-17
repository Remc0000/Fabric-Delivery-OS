from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import FrozenInstanceError, replace
import json
import multiprocessing
from pathlib import Path
import shutil
import sqlite3
import threading
import unittest
from uuid import uuid4

from fabric_delivery_core import (
    ApprovalBinding,
    AuthorizationDenied,
    ExecutionManifest,
    SQLiteAuthorizationStore,
    sha256_digest,
)


NOW = 1_800_000_000


def manifest() -> ExecutionManifest:
    return ExecutionManifest(
        request_id=str(uuid4()),
        installation_id="synthetic-installation",
        solution_id="synthetic-solution",
        action="deploy",
        input_digest=sha256_digest(b"synthetic specification"),
        artifact_digest=sha256_digest(b"synthetic package"),
        target_baseline_digest=sha256_digest(b"synthetic baseline"),
        environment="development",
        policy_digest=sha256_digest(b"synthetic policy"),
        execution_profile_digest=sha256_digest(b"synthetic execution profile"),
        framework_digest=sha256_digest(b"synthetic framework"),
        control_workflow_digest=sha256_digest(b"synthetic control workflow"),
        tool_snapshot_digest=sha256_digest(b"synthetic tools"),
        skill_snapshot_digest=sha256_digest(b"synthetic skills"),
        permitted_effects=("deploy_definitions",),
        created_at=NOW - 10,
        expires_at=NOW + 100,
    )


def approval(request: ExecutionManifest) -> ApprovalBinding:
    return ApprovalBinding(
        manifest_digest=request.digest,
        control_repository_id="synthetic-immutable-repository-id",
        control_workflow_digest=request.control_workflow_digest,
        run_id="synthetic-run",
        run_attempt=1,
        gate_environment="authorize-development",
        approval_evidence_digest=sha256_digest(b"synthetic verified human evidence"),
        approved_at=NOW - 1,
        expires_at=NOW + 50,
    )


def process_consume(path, request, binding, ready, start, results):
    store = SQLiteAuthorizationStore(path, clock=lambda: NOW)
    ready.put(True)
    if not start.wait(20):
        raise RuntimeError("concurrency test start timed out")
    try:
        results.put(("consumed", store.consume(request, binding).execution_id))
    except AuthorizationDenied as exc:
        results.put(("denied", exc.reason))


class ManifestTests(unittest.TestCase):
    def test_roundtrip_is_frozen_and_binds_all_fields(self):
        request = manifest()
        self.assertEqual(ExecutionManifest.from_json(request.to_json()), request)
        with self.assertRaises(FrozenInstanceError):
            request.action = "build"
        changed = replace(request, permitted_effects=("replace_data",))
        self.assertNotEqual(request.digest, changed.digest)
        reordered = json.dumps(dict(reversed(list(json.loads(request.to_json()).items()))))
        self.assertEqual(ExecutionManifest.from_json(reordered).digest, request.digest)

    def test_rejects_mutable_refs_malformed_and_ambiguous_envelopes(self):
        request = manifest()
        changes = (
            {"input_digest": "main"},
            {"framework_digest": "sha256:" + "A" * 64},
            {"request_id": "not-an-opaque-request"},
            {"permitted_effects": ["load_data"]},
            {"permitted_effects": ("load_data", "load_data")},
            {"permitted_effects": ()},
            {"created_at": True},
            {"expires_at": request.created_at},
            {"schema_version": 2},
            {"artifact_digest": None},
            {"environment": None},
        )
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(request, **change)
        serialized = request.to_json()
        for value in (
            serialized[:-1] + ',"action":"build"}',
            serialized[:-1] + ',"unknown":true}',
            serialized.replace('"schema_version":1,', ""),
            "[]",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ExecutionManifest.from_json(value)

    def test_build_can_bind_inputs_without_a_deployment_package(self):
        request = replace(
            manifest(), action="build", artifact_digest=None,
            environment=None, permitted_effects=("write_code",)
        )
        self.assertEqual(ExecutionManifest.from_json(request.to_json()), request)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.state = Path.cwd() / ".test-state" / str(uuid4())
        self.state.mkdir(parents=True)
        self.addCleanup(self.clean_state)
        self.path = self.state / "authorization.sqlite3"
        self.now = NOW
        self.store = SQLiteAuthorizationStore(self.path, clock=lambda: self.now)
        self.request = manifest()
        self.binding = approval(self.request)

    def clean_state(self):
        shutil.rmtree(self.state)
        try:
            self.state.parent.rmdir()
        except OSError:
            pass

    def assert_denied(self, reason, operation, *args):
        with self.assertRaises(AuthorizationDenied) as error:
            operation(*args)
        self.assertEqual(error.exception.reason, reason)

    def authorize(self):
        self.store.freeze(self.request)
        self.store.authorize(self.request.request_id, self.binding)

    def test_requires_pending_request_and_a_separate_approval(self):
        self.assert_denied(
            "unknown_request", self.store.consume, self.request, self.binding
        )
        self.store.freeze(self.request)
        self.assert_denied("pending", self.store.consume, self.request, self.binding)
        self.assert_denied("duplicate_request", self.store.freeze, self.request)
        self.assertIsNone(self.store.receipt(self.request.request_id))
        self.store.authorize(self.request.request_id, self.binding)
        self.assert_denied(
            "authorized", self.store.authorize, self.request.request_id, self.binding
        )
        self.assertEqual(
            self.store.consume(self.request, self.binding).manifest_digest,
            self.request.digest,
        )

    def test_consumption_and_receipt_survive_restart_and_failure(self):
        self.authorize()
        self.store = SQLiteAuthorizationStore(self.path, clock=lambda: self.now)
        receipt = self.store.consume(self.request, self.binding)
        restarted = SQLiteAuthorizationStore(self.path, clock=lambda: self.now)
        self.assertEqual(restarted.receipt(self.request.request_id), receipt)
        # A worker crash/failure cannot unconsume the grant or replace the request.
        self.assert_denied("consumed", restarted.consume, self.request, self.binding)
        self.assert_denied("consumed", restarted.revoke, self.request.request_id)
        self.assert_denied("duplicate_request", restarted.freeze, self.request)

    def test_every_changed_bound_input_permanently_invalidates(self):
        changes = (
            ("input_digest", sha256_digest(b"changed input"), "request_mismatch"),
            ("artifact_digest", sha256_digest(b"changed bytes"), "request_mismatch"),
            ("policy_digest", sha256_digest(b"changed policy"), "policy_changed"),
            ("target_baseline_digest", sha256_digest(b"drift"), "target_changed"),
            ("execution_profile_digest", sha256_digest(b"profile"), "execution_profile_changed"),
            ("framework_digest", sha256_digest(b"runtime"), "request_mismatch"),
            ("control_workflow_digest", sha256_digest(b"workflow"), "request_mismatch"),
            ("tool_snapshot_digest", sha256_digest(b"tools"), "request_mismatch"),
            ("skill_snapshot_digest", sha256_digest(b"skills"), "request_mismatch"),
            ("installation_id", "other-installation", "request_mismatch"),
            ("solution_id", "other-solution", "request_mismatch"),
            ("action", "recovery", "request_mismatch"),
            ("environment", "production", "request_mismatch"),
            ("permitted_effects", ("replace_data",), "request_mismatch"),
            ("expires_at", NOW + 1000, "request_mismatch"),
        )
        for field, value, reason in changes:
            with self.subTest(field=field):
                self.request = manifest()
                self.binding = replace(approval(self.request), run_id=str(uuid4()))
                self.authorize()
                changed = replace(self.request, **{field: value})
                self.assert_denied(reason, self.store.consume, changed, self.binding)
                self.assert_denied(
                    reason, self.store.consume, self.request, self.binding
                )
                self.assertIsNone(self.store.receipt(self.request.request_id))

    def test_rejects_wrong_gate_run_attempt_repository_and_evidence(self):
        for field, value in (
            ("control_repository_id", "other-control"),
            ("control_workflow_digest", sha256_digest(b"other workflow")),
            ("run_id", "other-run"),
            ("run_attempt", 2),
            ("gate_environment", "authorize-production"),
            ("approval_evidence_digest", sha256_digest(b"other evidence")),
            ("manifest_digest", sha256_digest(b"other request")),
            ("expires_at", NOW + 49),
        ):
            with self.subTest(field=field):
                self.request = manifest()
                self.binding = replace(approval(self.request), run_id=str(uuid4()))
                self.authorize()
                changed = replace(self.binding, **{field: value})
                self.assert_denied(
                    "approval_mismatch", self.store.consume, self.request, changed
                )
                self.assert_denied(
                    "approval_mismatch", self.store.consume, self.request, self.binding
                )

    def test_same_protected_run_cannot_authorize_a_second_request(self):
        self.authorize()
        other = manifest()
        self.store.freeze(other)
        self.assert_denied(
            "approval_replayed", self.store.authorize, other.request_id, approval(other)
        )
        self.assert_denied("pending", self.store.consume, other, approval(other))
        # A new request and independently attested run permit a fresh stage attempt.
        fresh = replace(approval(other), run_id="fresh-synthetic-run")
        self.store.authorize(other.request_id, fresh)
        self.store.consume(other, fresh)

    def test_competing_requests_cannot_share_one_protected_gate(self):
        requests = (self.request, manifest())
        for request in requests:
            self.store.freeze(request)
        start = threading.Barrier(2)

        def claim_gate(request):
            start.wait(timeout=10)
            try:
                self.store.authorize(request.request_id, approval(request))
                return "authorized"
            except AuthorizationDenied as exc:
                return exc.reason

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(claim_gate, requests))
        self.assertCountEqual(outcomes, ("authorized", "approval_replayed"))

    def test_approval_must_bind_request_and_be_current(self):
        self.store.freeze(self.request)
        for change, reason in (
            ({"manifest_digest": sha256_digest(b"wrong")}, "approval_mismatch"),
            ({"control_workflow_digest": sha256_digest(b"wrong")}, "approval_mismatch"),
            ({"approved_at": NOW + 1}, "approval_not_valid"),
            ({"approved_at": NOW - 20}, "approval_not_valid"),
            ({"expires_at": NOW}, "approval_not_valid"),
            ({"expires_at": self.request.expires_at + 1}, "approval_not_valid"),
        ):
            with self.subTest(change=change):
                self.assert_denied(
                    reason, self.store.authorize, self.request.request_id,
                    replace(self.binding, **change),
                )
        self.store.authorize(self.request.request_id, self.binding)
        self.store.consume(self.request, self.binding)

    def test_expiry_boundary_is_exclusive_and_cannot_be_rewound(self):
        self.authorize()
        self.now = self.binding.expires_at
        self.assert_denied("expired", self.store.consume, self.request, self.binding)
        self.now = NOW
        self.assert_denied("expired", self.store.consume, self.request, self.binding)

    def test_last_second_before_expiry_can_be_consumed(self):
        self.authorize()
        self.now = self.binding.expires_at - 1
        self.assertEqual(
            self.store.consume(self.request, self.binding).consumed_at, self.now
        )

    def test_revocation_is_durable_and_cannot_be_reauthorized(self):
        self.authorize()
        self.store.revoke(self.request.request_id)
        restarted = SQLiteAuthorizationStore(self.path, clock=lambda: self.now)
        self.assert_denied("revoked", restarted.consume, self.request, self.binding)
        self.assert_denied(
            "revoked", restarted.authorize, self.request.request_id, self.binding
        )
        self.assert_denied("duplicate_request", restarted.freeze, self.request)

    def test_revocation_while_pending_blocks_later_approval(self):
        self.store.freeze(self.request)
        self.store.revoke(self.request.request_id)
        self.assert_denied(
            "revoked", self.store.authorize, self.request.request_id, self.binding
        )

    def test_concurrent_processes_can_commit_only_one_claim(self):
        self.authorize()
        context = multiprocessing.get_context("spawn")
        ready, results = context.Queue(), context.Queue()
        start = context.Event()
        processes = [
            context.Process(
                target=process_consume,
                args=(self.path, self.request, self.binding, ready, start, results),
            )
            for _ in range(6)
        ]
        try:
            for process in processes:
                process.start()
            for _ in processes:
                self.assertTrue(ready.get(timeout=30))
            start.set()
            outcomes = [results.get(timeout=30) for _ in processes]
            for process in processes:
                process.join(timeout=30)
                self.assertEqual(process.exitcode, 0)
            winners = [value for state, value in outcomes if state == "consumed"]
            self.assertEqual(len(winners), 1)
            self.assertEqual(outcomes.count(("denied", "consumed")), 5)
            self.assertEqual(
                self.store.receipt(self.request.request_id).execution_id, winners[0]
            )
        finally:
            start.set()
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join()
            for queue in (ready, results):
                queue.close()
                queue.join_thread()

    def test_concurrent_revoke_and_consume_have_one_serialized_outcome(self):
        self.authorize()
        start = threading.Barrier(2)

        def act(operation, *args):
            start.wait(timeout=10)
            try:
                operation(*args)
                return "ok"
            except AuthorizationDenied as exc:
                return exc.reason

        with ThreadPoolExecutor(max_workers=2) as pool:
            claim = pool.submit(act, self.store.consume, self.request, self.binding)
            revoke = pool.submit(act, self.store.revoke, self.request.request_id)
            outcome = (claim.result(timeout=30), revoke.result(timeout=30))
        self.assertIn(outcome, (("ok", "consumed"), ("revoked", "ok")))

    def test_expiry_is_checked_after_obtaining_the_write_lock(self):
        self.authorize()
        waiting = threading.Event()
        clock_read = threading.Event()

        def clock():
            clock_read.set()
            return self.now

        self.store._clock = clock

        def claim():
            waiting.set()
            self.assert_denied(
                "expired", self.store.consume, self.request, self.binding,
            )

        with ThreadPoolExecutor(max_workers=1) as pool:
            with closing(sqlite3.connect(self.path)) as db, db:
                db.execute("BEGIN IMMEDIATE")
                result = pool.submit(claim)
                self.assertTrue(waiting.wait(timeout=10))
                self.assertFalse(clock_read.wait(timeout=0.1))
                self.now = self.binding.expires_at
            result.result(timeout=30)

    def test_corrupted_manifest_and_unsupported_database_fail_closed(self):
        self.authorize()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "UPDATE requests SET manifest=? WHERE request_id=?",
                (replace(self.request, environment="production").to_json(),
                 self.request.request_id),
            )
        self.assert_denied(
            "stored_manifest_mismatch", self.store.consume, self.request, self.binding
        )
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("PRAGMA user_version=999")
        with self.assertRaisesRegex(ValueError, "unsupported authorization database"):
            SQLiteAuthorizationStore(self.path)

    def test_invalid_times_and_in_memory_store_are_rejected(self):
        with self.assertRaises(ValueError):
            SQLiteAuthorizationStore(":memory:")
        for change in ({"created_at": NOW + 1}, {"expires_at": NOW}):
            with self.subTest(change=change):
                self.assert_denied(
                    "request_not_valid", self.store.freeze,
                    replace(self.request, **change),
                )


if __name__ == "__main__":
    unittest.main()
