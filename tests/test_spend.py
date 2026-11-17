from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timezone
import multiprocessing
from pathlib import Path
import shutil
import sqlite3
import unittest
from uuid import uuid4

from fabric_delivery_core import sha256_digest
from fabric_delivery_core.spend import PriceCard, SpendBudget, SpendDenied, SQLiteSpendStore


NOW = int(datetime(2026, 11, 17, tzinfo=timezone.utc).timestamp())
PERIOD = "2026-11"


def request(identifier):
    return dict(
        reservation_id=identifier, installation_id="synthetic", period=PERIOD,
        currency="USD", execution_digest=sha256_digest(identifier.encode()),
        operation="synthetic-model", price_version="v1", max_tokens=4, max_calls=1,
    )


def competing_reserve(path, identifier, ready, start, results):
    store = SQLiteSpendStore(path, clock=lambda: NOW)
    ready.put(True)
    if not start.wait(20):
        raise RuntimeError("concurrency start timeout")
    try:
        store.reserve(**request(identifier))
        results.put("reserved")
    except SpendDenied as exc:
        results.put(exc.reason)


class SpendTests(unittest.TestCase):
    def setUp(self):
        self.state = Path.cwd() / ".test-state" / str(uuid4())
        self.state.mkdir(parents=True)
        self.addCleanup(self.clean_state)
        self.path = self.state / "spend.sqlite3"
        self.now = NOW
        self.store = SQLiteSpendStore(self.path, clock=lambda: self.now)
        self.budget = SpendBudget("synthetic", PERIOD, "USD", "v1", 10, 4, 1)
        self.card = PriceCard("synthetic-model", "v1", "USD", NOW - 10, NOW + 100, 1, 1)
        self.store.configure_budget(self.budget)
        self.store.register_price(self.card)

    def clean_state(self):
        shutil.rmtree(self.state)
        try:
            self.state.parent.rmdir()
        except OSError:
            pass

    def deny(self, reason, callback, **kwargs):
        with self.assertRaises(SpendDenied) as error:
            callback(**kwargs)
        self.assertEqual(error.exception.reason, reason)

    def settle(self, identifier="one", **changes):
        args = dict(
            reservation_id=identifier, installation_id="synthetic", period=PERIOD,
            currency="USD", execution_digest=sha256_digest(identifier.encode()),
            actual_units=3, actual_tokens=2, actual_calls=1,
        )
        args.update(changes)
        self.store.settle(**args)

    def test_exact_concurrent_thread_boundary_and_outstanding_aggregation(self):
        def reserve(index):
            try:
                self.store.reserve(**request(str(index)))
                return "reserved"
            except SpendDenied as exc:
                return exc.reason

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(reserve, range(8)))
        self.assertEqual(results.count("reserved"), 2)
        self.assertEqual(results.count("budget_exhausted"), 6)
        self.assertEqual(self.store.monthly_state("synthetic", PERIOD)["outstanding_units"], 10)

    def test_local_process_connections_serialize_at_cap(self):
        context = multiprocessing.get_context("spawn")
        ready, results = context.Queue(), context.Queue()
        start = context.Event()
        processes = [
            context.Process(
                target=competing_reserve,
                args=(str(self.path), str(index), ready, start, results),
            )
            for index in range(4)
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
            self.assertEqual(outcomes.count("reserved"), 2)
            self.assertEqual(outcomes.count("budget_exhausted"), 2)
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join()
            ready.close()
            results.close()
            ready.join_thread()
            results.join_thread()

    def test_settlement_release_restart_and_global_replay_denial(self):
        receipt = self.store.reserve(**request("one"))
        self.assertEqual(receipt["reserved"], 5)
        self.assertEqual(receipt["deadline"], NOW + 100)
        self.deny("reservation_replay", self.store.reserve, **request("one"))
        duplicate = request("another-id")
        duplicate["execution_digest"] = request("one")["execution_digest"]
        self.deny("reservation_replay", self.store.reserve, **duplicate)
        self.settle()
        self.store = SQLiteSpendStore(self.path, clock=lambda: self.now)
        self.assertEqual(self.store.receipt("one")["actual"], 3)
        self.assertEqual(self.store.monthly_state("synthetic", PERIOD)["settled_units"], 3)
        self.store.reserve(**request("two"))
        self.deny("budget_exhausted", self.store.reserve, **request("three"))
        self.deny("settlement_replay", self.settle)
        self.deny("reservation_replay", self.store.reserve, **request("one"))

    def test_unknown_stale_future_and_currency_prices_fail_closed(self):
        for change, reason in (
            ({"operation": "unknown"}, "unknown_price"),
            ({"price_version": "missing"}, "unknown_price"),
            ({"currency": "EUR"}, "currency_mismatch"),
        ):
            args = request("one")
            args.update(change)
            self.deny(reason, self.store.reserve, **args)
        for now in (NOW - 11, NOW + 100):
            self.now = now
            self.deny("stale_price", self.store.reserve, **request("one"))
        self.now = NOW
        self.store.register_price(replace(self.card, version="eur", currency="EUR"))
        args = request("one")
        args["price_version"] = "eur"
        self.deny("currency_mismatch", self.store.reserve, **args)
        self.assertIsNone(self.store.receipt("one"))

    def test_month_limits_missing_policy_and_immutable_configuration(self):
        for changes, reason in (
            ({"period": "2026-10"}, "period_mismatch"),
            ({"max_tokens": 5}, "execution_limit"),
            ({"max_calls": 2}, "execution_limit"),
            ({"installation_id": "unconfigured"}, "missing_budget"),
        ):
            args = request("one")
            args.update(changes)
            self.deny(reason, self.store.reserve, **args)
        self.deny("budget_already_configured", self.store.configure_budget, budget=self.budget)
        self.deny("price_version_reused", self.store.register_price, card=self.card)
        self.store.register_price(replace(self.card, version="expensive", call_units=11))
        args = request("one")
        args["price_version"] = "expensive"
        self.deny("budget_exhausted", self.store.reserve, **args)

    def test_wrong_settlement_binding_cannot_release(self):
        self.store.reserve(**request("one"))
        for changes in (
            {"period": "2026-12"}, {"currency": "EUR"},
            {"installation_id": "other"}, {"execution_digest": sha256_digest(b"other")},
        ):
            self.deny("settlement_mismatch", self.settle, **changes)
        self.assertEqual(self.store.receipt("one")["state"], "reserved")
        self.assertEqual(self.store.monthly_state("synthetic", PERIOD)["outstanding_units"], 5)
        self.deny("unknown_reservation", self.settle, identifier="missing")

    def test_conservative_rates_are_not_a_minimum_actual_charge(self):
        self.store.reserve(**request("one"))
        self.settle(actual_units=1, actual_tokens=4)
        self.assertEqual(self.store.receipt("one")["actual"], 1)
        self.assertEqual(self.store.monthly_state("synthetic", PERIOD)["settled_units"], 1)
        self.assertFalse(self.store.monthly_state("synthetic", PERIOD)["frozen"])

    def test_aggregate_is_per_installation_not_per_operation_and_deadline_is_utc(self):
        long_card = replace(self.card, version="long", valid_until=NOW + 90 * 86400)
        self.store.register_price(long_card)
        self.store.register_price(replace(self.card, operation="another-operation"))
        first = request("one")
        first["price_version"] = "long"
        receipt = self.store.reserve(**first)
        month_end = int(datetime(2026, 12, 1, tzinfo=timezone.utc).timestamp())
        self.assertEqual(receipt["deadline"], month_end)
        second = request("two")
        second["operation"] = "another-operation"
        self.store.reserve(**second)
        self.deny("budget_exhausted", self.store.reserve, **request("three"))
        self.store.configure_budget(replace(self.budget, installation_id="isolated"))
        third = request("isolated-attempt")
        third["installation_id"] = "isolated"
        self.store.reserve(**third)
        self.assertEqual(self.store.monthly_state("isolated", PERIOD)["outstanding_units"], 5)

    def test_visible_external_excess_aggregate_does_not_overflow_sqlite_sum(self):
        self.store.reserve(**request("one"))
        self.store.reserve(**request("two"))
        maximum = 2**63 - 1
        self.deny("settlement_breach", self.settle, actual_units=maximum)
        self.deny("settlement_breach", self.settle, identifier="two", actual_units=maximum)
        state = self.store.monthly_state("synthetic", PERIOD)
        self.assertEqual(state["settled_units"], maximum * 2)
        self.assertTrue(state["frozen"])

    def test_excess_is_committed_visible_and_freezes_across_months(self):
        self.store.reserve(**request("one"))
        self.store.reserve(**request("two"))
        self.deny("settlement_breach", self.settle, actual_units=12)
        self.store = SQLiteSpendStore(self.path, clock=lambda: self.now)
        self.assertEqual(self.store.receipt("one")["state"], "breach")
        state = self.store.monthly_state("synthetic", PERIOD)
        self.assertEqual(state, dict(
            outstanding_units=5, settled_units=12, frozen=True, breach_reservation_id="one"
        ))
        self.deny("installation_frozen", self.store.reserve, **request("three"))
        self.deny("settlement_replay", self.settle)
        self.settle("two")
        self.assertTrue(self.store.monthly_state("synthetic", PERIOD)["frozen"])
        self.now = int(datetime(2026, 12, 1, tzinfo=timezone.utc).timestamp())
        self.store.configure_budget(replace(self.budget, period="2026-12"))
        args = request("next")
        args["period"] = "2026-12"
        self.deny("installation_frozen", self.store.reserve, **args)

    def test_excess_usage_with_low_reported_cost_still_freezes(self):
        self.store.reserve(**request("one"))
        self.deny("settlement_breach", self.settle, actual_tokens=5, actual_units=1)
        receipt = self.store.receipt("one")
        self.assertEqual((receipt["actual"], receipt["actual_tokens"]), (1, 5))
        self.assertTrue(self.store.monthly_state("synthetic", PERIOD)["frozen"])

    def test_old_outstanding_never_expires_or_releases_implicitly(self):
        self.store.reserve(**request("one"))
        self.now = int(datetime(2026, 12, 1, tzinfo=timezone.utc).timestamp())
        self.assertEqual(self.store.monthly_state("synthetic", PERIOD)["outstanding_units"], 5)
        self.settle()
        self.assertEqual(self.store.receipt("one")["state"], "settled")

    def test_fixed_integer_money_and_storage_errors_fail_closed(self):
        for value in (True, 1.1, -1, 2**63):
            with self.subTest(value=value), self.assertRaises(ValueError):
                replace(self.budget, cap_units=value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.settle(actual_units=value)
        with self.assertRaises(ValueError):
            replace(self.card, token_units=0, call_units=0)
        with self.assertRaises(ValueError):
            SQLiteSpendStore(":memory:")
        other = self.state / "unrelated.sqlite3"
        with closing(sqlite3.connect(other)) as db:
            db.execute("CREATE TABLE unrelated (value TEXT)")
        with self.assertRaises(ValueError):
            SQLiteSpendStore(other)
        self.path.unlink()
        self.path.mkdir()
        with self.assertRaises(sqlite3.OperationalError):
            self.store.reserve(**request("one"))


if __name__ == "__main__":
    unittest.main()
