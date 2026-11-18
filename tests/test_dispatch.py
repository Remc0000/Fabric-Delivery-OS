from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timezone
import multiprocessing
import os
from pathlib import Path
import shutil
import sqlite3
import unittest
from unittest.mock import patch
from uuid import uuid4

from fabric_delivery_core import AuthorizationDenied, SQLiteAuthorizationStore, sha256_digest
from fabric_delivery_core.dispatch import DispatchDenied, DispatchProfile, SQLiteDispatchStore
from fabric_delivery_core.spend import (
    PriceCard, SpendBudget, SpendDenied, SQLiteSpendStore,
)
from test_authorization import NOW, approval, manifest


def open_dispatch(directory, *, clock=lambda: NOW):
    directory = Path(directory)
    auth = SQLiteAuthorizationStore(directory / "auth.sqlite3", clock=clock)
    spend = SQLiteSpendStore(directory / "spend.sqlite3", clock=clock)
    return SQLiteDispatchStore(directory / "queue.sqlite3", auth, spend, clock=clock)


def process_enqueue(directory, request, binding, profile, ready, start, results):
    store = open_dispatch(directory)
    ready.put(True)
    if not start.wait(20):
        raise RuntimeError("concurrency test start timed out")
    try:
        results.put(("enqueued", store.enqueue(request, binding, profile).execution_id))
    except AuthorizationDenied as exc:
        results.put(("denied", exc.reason))


def crash_during_enqueue(directory, request, binding, profile, after_commit):
    store = open_dispatch(directory)
    if after_commit:
        store.enqueue(request, binding, profile)
        if after_commit == "claimed":
            store.claim(request, binding, profile)
    else:
        original = store.spend._reserve_in_transaction

        def reserve_and_crash(*args, **kwargs):
            original(*args, **kwargs)
            os._exit(73)

        store.spend._reserve_in_transaction = reserve_and_crash
        store.enqueue(request, binding, profile)
    os._exit(73)


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path.cwd() / ".test-state" / str(uuid4())
        self.directory.mkdir(parents=True)
        self.addCleanup(self.clean)
        self.now = NOW
        self.store = open_dispatch(self.directory, clock=lambda: self.now)
        self.auth = self.store.authorization
        self.spend = self.store.spend
        self.request = manifest()
        self.period = datetime.fromtimestamp(NOW, timezone.utc).strftime("%Y-%m")
        self.budget = SpendBudget(
            self.request.installation_id, self.period, "USD", "synthetic-v1", 10, 4, 1
        )
        self.price = PriceCard(
            "synthetic-operation", "synthetic-v1", "USD", NOW - 10, NOW + 100, 1, 1
        )
        self.spend.configure_budget(self.budget)
        self.spend.register_price(self.price)
        self.profile = DispatchProfile(
            sha256_digest(b"fixed synthetic worker"), self.budget.digest,
            self.price.digest, self.price.operation, self.price.version, self.period,
            "USD", 4, 1, 20,
        )
        self.request = replace(self.request, execution_profile_digest=self.profile.digest)
        self.binding = approval(self.request)
        self.auth.freeze(self.request)
        self.auth.authorize(self.request.request_id, self.binding)

    def clean(self):
        shutil.rmtree(self.directory)
        try:
            self.directory.parent.rmdir()
        except OSError:
            pass

    def enqueue(self):
        return self.store.enqueue(self.request, self.binding, self.profile)

    def claim(self):
        return self.store.claim(self.request, self.binding, self.profile)

    def finish(self, claim, **overrides):
        arguments = dict(
            succeeded=True, result_digest=sha256_digest(b"synthetic result"),
            actual_units=3, actual_tokens=2, actual_calls=1,
        )
        arguments.update(overrides)
        return self.store.finish(claim, **arguments)

    def test_atomic_cycle_survives_restart_and_settles_without_replay(self):
        receipt = self.enqueue()
        self.store = open_dispatch(self.directory)
        row = self.store.receipt(self.request.request_id)
        self.assertEqual(row["execution_id"], receipt.execution_id)
        self.assertEqual(self.auth.receipt(self.request.request_id), receipt)
        self.assertEqual(self.spend.receipt(row["reservation_id"])["reserved"], 5)
        claim = self.claim()
        self.assertEqual(claim.deadline, NOW + 20)
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_not_ready$"):
            self.claim()
        self.finish(claim)
        self.assertEqual(self.store.receipt(self.request.request_id)["state"], "succeeded")
        self.assertEqual(
            self.spend.monthly_state(self.request.installation_id, self.period)["settled_units"], 3
        )
        with self.assertRaisesRegex(AuthorizationDenied, "^consumed$"):
            self.enqueue()
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_not_claimed$"):
            self.finish(claim)

    def test_spend_denial_rolls_back_consumption_and_outbox_then_can_prepare_once(self):
        with patch.object(
            self.spend, "_reserve_in_transaction", side_effect=SpendDenied("budget_exhausted")
        ), self.assertRaisesRegex(SpendDenied, "^budget_exhausted$"):
            self.enqueue()
        self.assertIsNone(self.auth.receipt(self.request.request_id))
        with self.assertRaisesRegex(DispatchDenied, "^unknown_dispatch$"):
            self.store.receipt(self.request.request_id)
        self.enqueue()
        self.assertEqual(self.spend.monthly_state(
            self.request.installation_id, self.period
        )["outstanding_units"], 5)

    def test_failure_after_both_writes_rolls_back_both_ledgers(self):
        with patch.object(
            self.store, "_now", side_effect=OSError("synthetic disk failure")
        ), self.assertRaisesRegex(OSError, "synthetic disk failure"):
            self.enqueue()
        self.assertIsNone(self.auth.receipt(self.request.request_id))
        self.assertEqual(self.spend.monthly_state(
            self.request.installation_id, self.period
        )["outstanding_units"], 0)
        self.enqueue()

    def test_authorization_drift_is_committed_not_rolled_back_by_denial(self):
        drifted = replace(self.request, input_digest=sha256_digest(b"changed input"))
        with self.assertRaisesRegex(AuthorizationDenied, "^request_mismatch$"):
            self.store.enqueue(drifted, self.binding, self.profile)
        with self.assertRaisesRegex(AuthorizationDenied, "^request_mismatch$"):
            self.enqueue()
        self.assertEqual(self.spend.monthly_state(
            self.request.installation_id, self.period
        )["outstanding_units"], 0)

    def test_unapproved_profile_and_wrong_cost_snapshots_never_consume(self):
        with self.assertRaisesRegex(DispatchDenied, "^profile_mismatch$"):
            self.store.enqueue(self.request, self.binding, replace(self.profile, max_tokens=3))
        changed = replace(self.profile, price_digest=sha256_digest(b"different prices"))
        request = replace(
            self.request, request_id=str(uuid4()), execution_profile_digest=changed.digest
        )
        binding = replace(approval(request), run_id="different-synthetic-run")
        self.auth.freeze(request)
        self.auth.authorize(request.request_id, binding)
        with self.assertRaisesRegex(DispatchDenied, "^spend_snapshot_mismatch$"):
            self.store.enqueue(request, binding, changed)
        self.assertIsNone(self.auth.receipt(request.request_id))
        self.assertEqual(self.spend.monthly_state(
            self.request.installation_id, self.period
        )["outstanding_units"], 0)

    def test_cancelled_and_expired_jobs_never_relaunch_or_refund(self):
        self.enqueue()
        self.store.cancel(self.request.request_id)
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_not_ready$"):
            self.claim()
        self.assertEqual(self.store.receipt(self.request.request_id)["state"], "cancelled")
        self.assertEqual(self.spend.monthly_state(
            self.request.installation_id, self.period
        )["outstanding_units"], 5)

    def test_claim_rechecks_expiry_inside_lock_and_keeps_permanent_block(self):
        self.enqueue()
        self.now = self.binding.expires_at
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_expired$"):
            self.claim()
        self.now = NOW
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_not_ready$"):
            self.claim()
        self.assertEqual(self.store.receipt(self.request.request_id)["state"], "blocked")

    def test_fresh_binding_drift_blocks_claim_even_if_original_is_restored(self):
        self.enqueue()
        changed = replace(self.request, target_baseline_digest=sha256_digest(b"drift"))
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_binding_changed$"):
            self.store.claim(changed, self.binding, self.profile)
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_not_ready$"):
            self.claim()

    def test_independently_settled_reservation_cannot_launch(self):
        self.enqueue()
        row = self.store.receipt(self.request.request_id)
        self.spend.settle(
            reservation_id=row["reservation_id"], installation_id=self.request.installation_id,
            period=self.period, currency="USD", execution_digest=row["execution_digest"],
            actual_units=0, actual_tokens=0, actual_calls=0,
        )
        with self.assertRaisesRegex(DispatchDenied, "^reservation_not_current$"):
            self.claim()

    def test_breach_elsewhere_blocks_a_previously_ready_job(self):
        self.enqueue()
        execution = sha256_digest(b"another approved synthetic operation")
        self.spend.reserve(
            reservation_id="other-synthetic-reservation",
            installation_id=self.request.installation_id, period=self.period, currency="USD",
            execution_digest=execution, operation=self.price.operation,
            price_version=self.price.version, max_tokens=4, max_calls=1,
        )
        with self.assertRaises(SpendDenied):
            self.spend.settle(
                reservation_id="other-synthetic-reservation",
                installation_id=self.request.installation_id, period=self.period, currency="USD",
                execution_digest=execution, actual_units=6, actual_tokens=4, actual_calls=1,
            )
        with self.assertRaisesRegex(DispatchDenied, "^installation_frozen$"):
            self.claim()
        self.assertEqual(self.store.receipt(self.request.request_id)["state"], "blocked")

    def test_unknown_outcome_is_visible_without_reclaim_or_refund(self):
        self.enqueue()
        claim = self.claim()
        self.store.mark_unknown(claim)
        self.assertEqual(self.store.receipt(self.request.request_id)["state"], "unknown")
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_not_ready$"):
            self.claim()
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_not_claimed$"):
            self.finish(claim)
        self.assertEqual(self.spend.monthly_state(
            self.request.installation_id, self.period
        )["outstanding_units"], 5)

    def test_finish_rolls_back_settlement_if_terminal_record_cannot_commit(self):
        self.enqueue()
        claim = self.claim()
        with patch.object(
            self.store, "_now", side_effect=OSError("synthetic terminal failure")
        ), self.assertRaises(OSError):
            self.finish(claim)
        row = self.store.receipt(self.request.request_id)
        self.assertEqual(row["state"], "claimed")
        self.assertEqual(self.spend.receipt(row["reservation_id"])["state"], "reserved")
        self.finish(claim)

    def test_breach_and_terminal_failure_are_committed_together_before_raising(self):
        self.enqueue()
        claim = self.claim()
        with self.assertRaisesRegex(SpendDenied, "^settlement_breach$"):
            self.finish(claim, actual_units=12)
        self.assertEqual(self.store.receipt(self.request.request_id)["state"], "breach")
        state = self.spend.monthly_state(self.request.installation_id, self.period)
        self.assertTrue(state["frozen"])
        self.assertEqual(state["settled_units"], 12)

    def test_failure_and_late_success_record_cost_without_reporting_success(self):
        self.enqueue()
        claim = self.claim()
        self.now = claim.deadline
        with self.assertRaisesRegex(DispatchDenied, "^worker_deadline_exceeded$"):
            self.finish(claim)
        row = self.store.receipt(self.request.request_id)
        self.assertEqual((row["state"], row["reason"]), ("failed", "worker_deadline_exceeded"))
        self.assertEqual(self.spend.receipt(row["reservation_id"])["state"], "settled")

    def test_wrong_claim_cannot_settle_and_ordinary_worker_failure_is_visible(self):
        self.enqueue()
        claim = self.claim()
        with self.assertRaisesRegex(DispatchDenied, "^claim_mismatch$"):
            self.finish(replace(claim, claim_id=str(uuid4())))
        self.finish(claim, succeeded=False)
        row = self.store.receipt(self.request.request_id)
        self.assertEqual((row["state"], row["reason"]), ("failed", "worker_failed"))

    def test_threads_claim_at_most_once(self):
        self.enqueue()

        def claim():
            try:
                return ("claimed", self.claim().claim_id)
            except DispatchDenied as exc:
                return ("denied", exc.reason)

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: claim(), range(8)))
        self.assertEqual(sum(kind == "claimed" for kind, _ in results), 1)
        self.assertEqual(sum(kind == "denied" for kind, _ in results), 7)

    def test_processes_enqueue_one_atomic_attempt(self):
        context = multiprocessing.get_context("spawn")
        ready, results, start = context.Queue(), context.Queue(), context.Event()
        processes = [
            context.Process(
                target=process_enqueue,
                args=(str(self.directory), self.request, self.binding, self.profile,
                      ready, start, results),
            )
            for _ in range(3)
        ]
        try:
            for process in processes:
                process.start()
            for _ in processes:
                self.assertTrue(ready.get(timeout=30))
            start.set()
            outcomes = [results.get(timeout=30) for _ in processes]
            for process in processes:
                process.join(30)
                self.assertEqual(process.exitcode, 0)
            self.assertEqual(sum(kind == "enqueued" for kind, _ in outcomes), 1)
            self.assertEqual(sum(kind == "denied" for kind, _ in outcomes), 2)
            self.assertEqual(self.spend.monthly_state(
                self.request.installation_id, self.period
            )["outstanding_units"], 5)
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                process.join(5)
            for queue in (ready, results):
                queue.close()
                queue.join_thread()

    def test_process_crash_before_commit_leaves_no_consumption_or_reservation(self):
        self.crash(False)
        self.assertIsNone(self.auth.receipt(self.request.request_id))
        self.assertEqual(self.spend.monthly_state(
            self.request.installation_id, self.period
        )["outstanding_units"], 0)
        self.enqueue()

    def test_process_crash_after_commit_preserves_one_ready_attempt(self):
        self.crash(True)
        self.assertIsNotNone(self.auth.receipt(self.request.request_id))
        with self.assertRaisesRegex(AuthorizationDenied, "^consumed$"):
            self.enqueue()
        self.assertEqual(self.store.receipt(self.request.request_id)["state"], "ready")
        self.claim()

    def test_process_crash_after_claim_never_restores_a_launchable_job(self):
        self.crash("claimed")
        restarted = open_dispatch(self.directory)
        self.assertEqual(restarted.receipt(self.request.request_id)["state"], "claimed")
        with self.assertRaisesRegex(DispatchDenied, "^dispatch_not_ready$"):
            restarted.claim(self.request, self.binding, self.profile)
        self.assertEqual(self.spend.monthly_state(
            self.request.installation_id, self.period
        )["outstanding_units"], 5)

    def crash(self, after_commit):
        process = multiprocessing.get_context("spawn").Process(
            target=crash_during_enqueue,
            args=(str(self.directory), self.request, self.binding, self.profile, after_commit),
        )
        process.start()
        process.join(30)
        if process.is_alive():
            process.terminate()
            process.join(5)
            self.fail("crash fixture did not finish")
        self.assertEqual(process.exitcode, 73)

    def test_unsupported_journals_unrelated_schemas_and_replaced_files_are_refused(self):
        with closing(sqlite3.connect(self.spend.path)) as db:
            self.assertEqual(db.execute("PRAGMA journal_mode=WAL").fetchone()[0], "wal")
        with self.assertRaisesRegex(DispatchDenied, "^unsupported_journal_mode$"):
            self.enqueue()
        with closing(sqlite3.connect(self.spend.path)) as db:
            db.execute("PRAGMA journal_mode=DELETE")
            db.execute("CREATE TABLE unrelated (value TEXT)")
            db.commit()
        with self.assertRaisesRegex(DispatchDenied, "^unsupported_dispatch_database$"):
            self.enqueue()
        with self.assertRaises(ValueError):
            SQLiteDispatchStore(self.auth.path, self.auth, self.spend)

    def test_missing_ledger_is_not_silently_recreated(self):
        self.spend.path.unlink()
        with self.assertRaises(sqlite3.OperationalError):
            self.enqueue()
        self.assertFalse(self.spend.path.exists())


if __name__ == "__main__":
    unittest.main()
