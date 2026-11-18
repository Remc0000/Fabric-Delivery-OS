from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sqlite3
import unittest
from uuid import uuid4

from fabric_delivery_core import AuthorizationDenied, SQLiteAuthorizationStore, sha256_digest
from fabric_delivery_core.spend import PriceCard, SpendBudget, SpendDenied, SQLiteSpendStore
from test_authorization import NOW, approval, manifest


class CoreSpendIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path.cwd() / ".test-state" / str(uuid4())
        self.directory.mkdir(parents=True)
        self.addCleanup(self.clean)
        self.auth_path = self.directory / "authorization.sqlite3"
        self.spend_path = self.directory / "spend.sqlite3"
        self.auth = SQLiteAuthorizationStore(self.auth_path, clock=lambda: NOW)
        self.spend = SQLiteSpendStore(self.spend_path, clock=lambda: NOW)
        self.manifest = manifest()
        self.period = datetime.fromtimestamp(NOW, timezone.utc).strftime("%Y-%m")
        self.spend.configure_budget(SpendBudget(
            self.manifest.installation_id, self.period, "USD", "synthetic-v1", 10, 4, 1
        ))
        self.spend.register_price(PriceCard(
            "synthetic-operation", "synthetic-v1", "USD", NOW - 10, NOW + 100, 1, 1
        ))

    def clean(self):
        shutil.rmtree(self.directory)
        try:
            self.directory.parent.rmdir()
        except OSError:
            pass

    def claim_and_reserve(self):
        self.auth.freeze(self.manifest)
        # Synthetic externally attested binding, never obtained from a live reviewer.
        binding = approval(self.manifest)
        self.auth.authorize(self.manifest.request_id, binding)
        claim = self.auth.consume(self.manifest, binding)
        attempt = sha256_digest(
            f"{claim.manifest_digest}:{claim.execution_id}:synthetic-operation:1".encode()
        )
        request = dict(
            reservation_id=str(uuid4()), installation_id=self.manifest.installation_id,
            period=self.period, currency="USD", execution_digest=attempt,
            operation="synthetic-operation", price_version="synthetic-v1",
            max_tokens=4, max_calls=1,
        )
        self.spend.reserve(**request)
        return binding, claim, request

    def test_separate_authorities_preserve_replay_denials_after_restart(self):
        binding, claim, request = self.claim_and_reserve()
        self.auth = SQLiteAuthorizationStore(self.auth_path, clock=lambda: NOW)
        self.spend = SQLiteSpendStore(self.spend_path, clock=lambda: NOW)
        self.assertEqual(self.auth.receipt(self.manifest.request_id), claim)
        with self.assertRaisesRegex(AuthorizationDenied, "^consumed$"):
            self.auth.consume(self.manifest, binding)
        with self.assertRaisesRegex(SpendDenied, "^reservation_replay$"):
            self.spend.reserve(**request)
        self.assertEqual(self.spend.receipt(request["reservation_id"])["state"], "reserved")

    def test_breach_freezes_costs_without_refunding_or_reauthorizing_a_claim(self):
        binding, claim, request = self.claim_and_reserve()
        with self.assertRaisesRegex(SpendDenied, "^settlement_breach$"):
            self.spend.settle(
                reservation_id=request["reservation_id"],
                installation_id=self.manifest.installation_id,
                period=self.period, currency="USD",
                execution_digest=request["execution_digest"],
                actual_units=12, actual_tokens=4, actual_calls=1,
            )
        self.assertTrue(self.spend.monthly_state(
            self.manifest.installation_id, self.period
        )["frozen"])
        self.assertEqual(self.auth.receipt(self.manifest.request_id), claim)
        with self.assertRaisesRegex(AuthorizationDenied, "^consumed$"):
            self.auth.consume(self.manifest, binding)

    def test_ledger_paths_cannot_be_substituted_or_initialized_inside_an_unrelated_file(self):
        with self.assertRaisesRegex(ValueError, "unsupported authorization database"):
            SQLiteAuthorizationStore(self.spend_path)
        with self.assertRaisesRegex(ValueError, "unsupported spend database"):
            SQLiteSpendStore(self.auth_path)
        unrelated = self.directory / "unrelated.sqlite3"
        with closing(sqlite3.connect(unrelated)) as db, db:
            db.execute("CREATE TABLE unrelated (value TEXT)")
        with self.assertRaisesRegex(ValueError, "unsupported authorization database"):
            SQLiteAuthorizationStore(unrelated)
        self.assertEqual(self.spend.monthly_state(
            self.manifest.installation_id, self.period
        )["outstanding_units"], 0)


if __name__ == "__main__":
    unittest.main()
