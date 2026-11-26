from contextlib import closing, contextmanager
from dataclasses import replace
from datetime import datetime, timezone
import multiprocessing
import os
from pathlib import Path
from queue import Queue
import shutil
import sqlite3
import threading
import unittest
from unittest.mock import patch
from uuid import uuid4

from fabric_delivery_core import (
    AuthorizationDenied, RegistryDenied, SQLiteAuthorizationStore,
    SQLiteRequestRegistry, sha256_digest,
)
from fabric_delivery_core.dispatch import DispatchClaim, DispatchDenied, DispatchProfile
from fabric_delivery_core.registry_dispatch import SQLiteRegistryDispatchStore
from fabric_delivery_core.spend import PriceCard, SpendBudget, SpendDenied, SQLiteSpendStore
from test_authorization import NOW, approval
from test_request_registry import policy, request


DENIALS = (RegistryDenied, AuthorizationDenied, SpendDenied, DispatchDenied)
TIMEOUT = 30
CRASH_EXIT = 73


def open_coordinator(directory, *, clock=lambda: NOW):
    directory = Path(directory)
    registry = SQLiteRequestRegistry(directory / "registry.sqlite3", clock=clock)
    authorization = SQLiteAuthorizationStore(directory / "auth.sqlite3", clock=clock)
    spend = SQLiteSpendStore(directory / "spend.sqlite3", clock=clock)
    return SQLiteRegistryDispatchStore(
        directory / "queue.sqlite3", registry, authorization, spend, clock=clock,
    )


def competing_operation(directory, current, binding, profile, operation, ready, start, results):
    store = open_coordinator(directory)
    ready.put(True)
    if not start.wait(TIMEOUT):
        raise RuntimeError("synthetic race start timed out")
    try:
        value = getattr(store, operation)(current, binding, profile)
        results.put(("success", value))
    except DENIALS as error:
        results.put(("denied", error.reason))


def crash_operation(directory, current, binding, profile, stage):
    store = open_coordinator(directory)
    if stage == "reserved":
        reserve = store.spend._reserve_in_transaction

        def reserve_then_exit(*args, **kwargs):
            reserve(*args, **kwargs)
            os._exit(CRASH_EXIT)

        store.spend._reserve_in_transaction = reserve_then_exit
    store.enqueue(current, binding, profile)
    if stage == "claimed":
        store.claim(current, binding, profile)
    os._exit(CRASH_EXIT)


class RegistryDispatchFaultTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path.cwd() / ".test-state" / str(uuid4())
        self.directory.mkdir(parents=True)
        self.addCleanup(self.clean_directory)
        self.now = NOW
        self.store = open_coordinator(self.directory, clock=lambda: self.now)
        self.registry = SQLiteRequestRegistry(
            self.directory / "registry.sqlite3", clock=lambda: self.now,
        )
        self.auth = self.store.authorization
        self.spend = self.store.spend
        self.configuration = policy()
        self.current = request(self.configuration)
        self.period = datetime.fromtimestamp(NOW, timezone.utc).strftime("%Y-%m")
        budget = SpendBudget(
            self.current.manifest.installation_id, self.period, "USD", "synthetic-v1",
            10, 4, 1,
        )
        price = PriceCard(
            "synthetic-operation", "synthetic-v1", "USD", NOW - 10, NOW + 100, 1, 1,
        )
        self.spend.configure_budget(budget)
        self.spend.register_price(price)
        self.profile = DispatchProfile(
            sha256_digest(b"fixed inert synthetic profile"), budget.digest, price.digest,
            price.operation, price.version, self.period, "USD", 4, 1, 20,
        )
        self.current = replace(
            self.current,
            manifest=replace(
                self.current.manifest, execution_profile_digest=self.profile.digest,
                policy_digest=self.configuration.digest,
            ),
        )
        self.binding = approval(self.current.manifest)
        self.registry.register_policy(self.configuration)
        self.registry.register(self.current)
        self.auth.freeze(self.current.manifest)
        self.auth.authorize(self.current.manifest.request_id, self.binding)

    def clean_directory(self):
        shutil.rmtree(self.directory)
        try:
            self.directory.parent.rmdir()
        except OSError:
            pass

    @property
    def request_id(self):
        return self.current.manifest.request_id

    def enqueue(self):
        return self.store.enqueue(self.current, self.binding, self.profile)

    def claim(self):
        return self.store.claim(self.current, self.binding, self.profile)

    def count(self, path, table):
        with closing(sqlite3.connect(path)) as db:
            return db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def assert_no_preparation(self):
        self.assertIsNone(self.auth.receipt(self.request_id))
        with closing(sqlite3.connect(self.auth.path)) as db:
            self.assertEqual(
                db.execute(
                    "SELECT state,execution_id,consumed_at FROM requests WHERE request_id=?",
                    (self.request_id,),
                ).fetchone(),
                ("authorized", None, None),
            )
        self.assertEqual(self.count(self.spend.path, "reservations"), 0)
        self.assertEqual(self.count(self.store.path, "dispatches"), 0)
        self.assert_spend(0)

    def assert_spend(self, outstanding):
        state = self.spend.monthly_state(self.current.manifest.installation_id, self.period)
        self.assertEqual(state["outstanding_units"], outstanding)
        self.assertEqual(state["settled_units"], 0)
        self.assertFalse(state["frozen"])

    def assert_prepared(self, state):
        row = self.store.receipt(self.request_id)
        receipt = self.auth.receipt(self.request_id)
        self.assertIsNotNone(receipt)
        self.assertEqual(row["execution_id"], receipt.execution_id)
        self.assertEqual(row["registry_digest"], self.current.digest)
        self.assertEqual(row["state"], state)
        self.assertEqual(self.count(self.store.path, "dispatches"), 1)
        self.assertEqual(self.count(self.spend.path, "reservations"), 1)
        reservation = self.spend.receipt(row["reservation_id"])
        self.assertEqual(reservation["state"], "reserved")
        self.assertEqual(reservation["execution_digest"], row["execution_digest"])
        self.assertEqual(reservation["reserved"], 5)
        self.assert_spend(5)
        return row

    def stop_processes(self, processes):
        for process in processes:
            if process.pid is None:
                continue
            if process.is_alive():
                process.terminate()
            process.join(5)
            if process.is_alive():
                process.kill()
                process.join(5)
            self.assertFalse(process.is_alive(), "synthetic subprocess survived cleanup")
            process.close()

    def compete(self, operation):
        context = multiprocessing.get_context("spawn")
        ready, results, start = context.Queue(), context.Queue(), context.Event()
        processes = [
            context.Process(
                target=competing_operation,
                args=(self.directory, self.current, self.binding, self.profile, operation,
                      ready, start, results),
            )
            for _ in range(3)
        ]
        try:
            for process in processes:
                process.start()
            for _ in processes:
                self.assertTrue(ready.get(timeout=TIMEOUT))
            start.set()
            outcomes = [results.get(timeout=TIMEOUT) for _ in processes]
            for process in processes:
                process.join(TIMEOUT)
                self.assertEqual(process.exitcode, 0)
            self.assertEqual(sorted(kind for kind, _ in outcomes), ["denied", "denied", "success"])
            return next(value for kind, value in outcomes if kind == "success")
        finally:
            start.set()
            self.stop_processes(processes)
            for queue in (ready, results):
                queue.close()
                queue.join_thread()

    def crash(self, stage):
        process = multiprocessing.get_context("spawn").Process(
            target=crash_operation,
            args=(self.directory, self.current, self.binding, self.profile, stage),
        )
        try:
            process.start()
            process.join(TIMEOUT)
            self.assertEqual(process.exitcode, CRASH_EXIT, "fixture did not reach the crash point")
        finally:
            self.stop_processes([process])
        self.store = open_coordinator(self.directory, clock=lambda: self.now)

    def test_spawned_competing_enqueues_commit_one_four_file_attempt(self):
        winner = self.compete("enqueue")
        row = self.assert_prepared("ready")
        self.assertEqual(row["execution_id"], winner.execution_id)
        self.assertEqual(self.registry.inspect(self.request_id).state, "proposed")
        with closing(sqlite3.connect(self.auth.path)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM requests WHERE state='consumed'").fetchone()[0], 1)

    def test_spawned_competing_claims_have_one_durable_winner(self):
        self.enqueue()
        winner = self.compete("claim")
        row = self.assert_prepared("claimed")
        self.assertEqual(row["claim_id"], winner.claim_id)
        self.assertEqual(self.registry.inspect(self.request_id).state, "proposed")
        with self.assertRaises(DispatchDenied):
            self.claim()
        self.store.mark_unknown(winner)
        self.assert_prepared("unknown")

    def test_abrupt_exit_after_real_reserve_rolls_back_all_four_files(self):
        self.crash("reserved")
        self.assertEqual(self.registry.inspect(self.request_id).state, "proposed")
        self.assert_no_preparation()
        self.enqueue()
        self.assert_prepared("ready")

    def test_abrupt_exit_after_enqueue_commit_preserves_burned_ready_attempt(self):
        self.crash("ready")
        before = self.assert_prepared("ready")
        with self.assertRaises(DENIALS):
            self.enqueue()
        self.assertEqual(self.assert_prepared("ready"), before)
        self.assertEqual(self.registry.inspect(self.request_id).state, "proposed")
        self.claim()
        self.assert_prepared("claimed")

    def test_abrupt_exit_after_claim_commit_never_reclaims_or_refunds(self):
        self.crash("claimed")
        before = self.assert_prepared("claimed")
        with self.assertRaises(DispatchDenied):
            self.claim()
        with self.assertRaises(DENIALS):
            self.enqueue()
        self.assertEqual(self.assert_prepared("claimed"), before)
        claim = DispatchClaim(
            self.request_id, before["execution_id"], before["claim_id"],
            before["manifest_digest"], before["profile_digest"], before["deadline"],
        )
        self.store.mark_unknown(claim)
        self.assert_prepared("unknown")
        self.store = open_coordinator(self.directory, clock=lambda: self.now)
        with self.assertRaises(DispatchDenied):
            self.claim()
        self.assert_prepared("unknown")

    @contextmanager
    def observe_begin(self):
        entered = threading.Event()
        original = sqlite3.connect
        owner = threading.get_ident()

        def connect(*args, **kwargs):
            db = original(*args, **kwargs)
            if threading.get_ident() != owner:
                def trace(statement):
                    if statement.strip().upper() == "BEGIN IMMEDIATE":
                        entered.set()
                db.set_trace_callback(trace)
            return db

        # Observe real SQL entry; the connection, locking and transaction remain real.
        with patch.object(sqlite3, "connect", connect):
            yield entered

    def start_thread(self, operation):
        result = Queue()

        def run():
            try:
                result.put(("success", operation()))
            except BaseException as error:
                result.put(("error", error))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread, result

    def join_thread(self, thread):
        thread.join(TIMEOUT + 5)
        self.assertFalse(thread.is_alive(), "synthetic transaction did not release its lock")

    def test_expiry_while_waiting_on_registry_lock_commits_permanent_invalidation(self):
        with closing(sqlite3.connect(self.registry.path, isolation_level=None)) as lock:
            lock.execute("BEGIN IMMEDIATE")
            with self.observe_begin() as entered:
                thread, result = self.start_thread(self.enqueue)
                try:
                    self.assertTrue(entered.wait(TIMEOUT))
                    self.assertTrue(result.empty(), "enqueue bypassed the held registry lock")
                    self.now = self.current.manifest.expires_at
                finally:
                    lock.rollback()
                    self.join_thread(thread)
        kind, error = result.get(timeout=TIMEOUT)
        self.assertEqual(kind, "error")
        self.assertIsInstance(error, RegistryDenied)
        self.assertEqual(error.reason, "registry_expired")
        snapshot = self.registry.inspect(self.request_id)
        self.assertEqual((snapshot.state, snapshot.reason), ("invalidated", "registry_expired"))
        self.assert_no_preparation()
        self.now = NOW
        with self.assertRaises(RegistryDenied):
            self.enqueue()
        self.assert_no_preparation()

    def assert_policy_change_wins_waiting_claim(self, mutation, reason):
        self.enqueue()
        written, release, committed = threading.Event(), threading.Event(), threading.Event()
        original = self.registry._transaction

        @contextmanager
        def held_transaction(**kwargs):
            with original(**kwargs) as db:
                yield db
                written.set()
                if not release.wait(TIMEOUT):
                    raise RuntimeError("synthetic policy commit release timed out")
            committed.set()

        with patch.object(self.registry, "_transaction", held_transaction):
            policy_thread, policy_result = self.start_thread(mutation)
            claim_thread = None
            try:
                self.assertTrue(written.wait(TIMEOUT))
                with self.observe_begin() as entered:
                    claim_thread, claim_result = self.start_thread(self.claim)
                    try:
                        self.assertTrue(entered.wait(TIMEOUT))
                        self.assertTrue(claim_result.empty(), "claim bypassed uncommitted policy writes")
                    finally:
                        release.set()
                        self.join_thread(policy_thread)
                        self.join_thread(claim_thread)
            finally:
                release.set()
                self.join_thread(policy_thread)
                if claim_thread is not None:
                    self.join_thread(claim_thread)
        policy_kind, policy_value = policy_result.get(timeout=TIMEOUT)
        self.assertEqual(policy_kind, "success", repr(policy_value))
        self.assertTrue(committed.is_set())
        kind, error = claim_result.get(timeout=TIMEOUT)
        self.assertEqual(kind, "error")
        self.assertIsInstance(error, DENIALS)
        snapshot = self.registry.inspect(self.request_id)
        self.assertEqual((snapshot.state, snapshot.reason), ("invalidated", reason))
        self.assert_prepared("blocked")
        self.store = open_coordinator(self.directory, clock=lambda: self.now)
        with self.assertRaises(DENIALS):
            self.claim()
        self.assert_prepared("blocked")

    def test_policy_replacement_serializes_before_waiting_old_policy_claim(self):
        self.assert_policy_change_wins_waiting_claim(
            lambda: self.registry.register_policy(replace(self.configuration, version="synthetic-v2")),
            "registry_policy_changed",
        )

    def test_policy_revocation_serializes_before_waiting_old_policy_claim(self):
        self.assert_policy_change_wins_waiting_claim(
            lambda: self.registry.revoke_policy(self.configuration.digest),
            "registry_policy_revoked",
        )


if __name__ == "__main__":
    unittest.main()
