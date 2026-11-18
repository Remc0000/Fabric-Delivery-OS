from contextlib import redirect_stdout
from dataclasses import asdict, replace
from datetime import datetime, timezone
from io import StringIO
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

from fabric_delivery_core.operator import main
from fabric_delivery_core.preflight import preflight
from fabric_delivery_core.spend import PriceCard, SpendBudget
from test_authorization import NOW, manifest


class OperatorTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path.cwd() / ".test-state" / str(uuid4())
        self.directory.mkdir(parents=True)
        self.addCleanup(self.clean)
        self.manifest = manifest()
        self.manifest_path = self.directory / "private-manifest.json"
        self.manifest_path.write_text(self.manifest.to_json(), encoding="utf-8")
        self.plan_path = self.directory / "private-spend.json"
        self.plan = {
            "schema_version": 1,
            "budget": asdict(SpendBudget(
                self.manifest.installation_id,
                datetime.fromtimestamp(NOW, timezone.utc).strftime("%Y-%m"),
                "USD", "synthetic-v1", 10, 4, 1,
            )),
            "price": asdict(PriceCard(
                "synthetic-operation", "synthetic-v1", "USD", NOW - 10, NOW + 100, 1, 1
            )),
            "max_tokens": 4,
            "max_calls": 1,
        }
        self.write_plan()

    def clean(self):
        shutil.rmtree(self.directory)
        try:
            self.directory.parent.rmdir()
        except OSError:
            pass

    def write_plan(self):
        self.plan_path.write_text(json.dumps(self.plan), encoding="utf-8")

    def invoke(self, *args):
        output = StringIO()
        with patch(
            "fabric_delivery_core.preflight.time.time_ns", return_value=NOW * 1_000_000_000
        ), redirect_stdout(output):
            code = main(list(args))
        return code, json.loads(output.getvalue())

    def test_valid_manifest_is_only_local_validity_and_creates_no_database(self):
        code, result = self.invoke("validate-manifest", str(self.manifest_path))
        self.assertEqual(code, 0)
        self.assertTrue(result["offline_checks_passed"])
        self.assertIs(result["execution_enabled"], False)
        self.assertEqual(result["live_execution"], "unsupported")
        self.assertEqual(len(list(self.directory.iterdir())), 2)
        self.assertNotIn(self.manifest.installation_id, json.dumps(result))
        self.assertNotIn(self.manifest.request_id, json.dumps(result))

    def test_valid_preflight_still_exits_blocked_and_never_uses_network_or_storage(self):
        checks = ()
        with patch(
            "fabric_delivery_core.preflight._dependencies", return_value=checks
        ), patch("sqlite3.connect", side_effect=AssertionError("must not open storage")), patch(
            "urllib.request.urlopen", side_effect=AssertionError("must not use network")
        ):
            code, result = self.invoke(
                "preflight", "--manifest", str(self.manifest_path),
                "--spend-plan", str(self.plan_path),
            )
        self.assertEqual(code, 3)
        self.assertTrue(result["offline_checks_passed"])
        self.assertIs(result["execution_enabled"], False)
        self.assertIn(
            "atomic_grant_reservation_dispatch_and_recovery_unsupported", result["live_blockers"]
        )
        self.assertEqual(len(list(self.directory.iterdir())), 2)

    def test_spend_binding_currency_period_bounds_and_price_drift_are_detected(self):
        for field, key, value in (
            ("budget", "installation_id", "other-installation"),
            ("price", "currency", "EUR"),
            ("budget", "period", "2020-01"),
            ("budget", "cap_units", 4),
            ("price", "valid_until", NOW),
            ("price", "valid_from", NOW + 1),
        ):
            with self.subTest(field=field, key=key):
                old = self.plan[field][key]
                self.plan[field][key] = value
                self.write_plan()
                report = preflight(self.manifest_path, self.plan_path, now=NOW)
                self.assertFalse(report.offline_checks_passed)
                self.assertEqual(report.checks[1].status, "incompatible")
                self.plan[field][key] = old
        self.plan["max_calls"] = True
        self.write_plan()
        self.assertEqual(
            preflight(self.manifest_path, self.plan_path, now=NOW).checks[1].reason,
            "spend_plan_invalid",
        )

    def test_unknown_state_and_absent_spend_plan_never_mean_permitted(self):
        result = preflight(self.manifest_path, now=NOW)
        self.assertEqual(result.checks[1].status, "unknown")
        self.assertFalse(result.offline_checks_passed)
        self.assertIs(json.loads(result.to_json())["execution_enabled"], False)

    def test_invalid_expired_missing_and_duplicate_input_fail_without_private_echo(self):
        self.manifest_path.write_text(
            replace(self.manifest, expires_at=NOW).to_json(), encoding="utf-8"
        )
        code, report = self.invoke("validate-manifest", str(self.manifest_path))
        self.assertEqual((code, report["checks"][0]["status"]), (2, "unauthorized"))
        self.manifest_path.write_text('{"PRIVATE_FIELD":"PRIVATE_VALUE"}', encoding="utf-8")
        code, report = self.invoke("validate-manifest", str(self.manifest_path))
        self.assertEqual(code, 2)
        self.assertNotIn("PRIVATE", json.dumps(report))
        code, report = self.invoke("validate-manifest", str(self.directory / "PRIVATE_FILENAME"))
        self.assertEqual((code, report["checks"][0]["status"]), (2, "missing"))
        self.assertNotIn("PRIVATE_FILENAME", json.dumps(report))
        self.manifest_path.write_text(self.manifest.to_json(), encoding="utf-8")
        self.plan_path.write_text(
            json.dumps(self.plan)[:-1] + ',"schema_version":1}', encoding="utf-8"
        )
        self.assertEqual(
            preflight(self.manifest_path, self.plan_path, now=NOW).checks[1].reason,
            "spend_plan_invalid",
        )

    def test_oversized_input_and_unrecognized_arguments_do_not_echo_payloads(self):
        self.manifest_path.write_bytes(b"x" * 1_048_577)
        code, result = self.invoke("validate-manifest", str(self.manifest_path))
        self.assertEqual(code, 2)
        code, result = self.invoke("--token", "SYNTHETIC_PRIVATE_TOKEN_DO_NOT_ECHO")
        self.assertEqual(code, 2)
        self.assertNotIn("SYNTHETIC_PRIVATE_TOKEN", json.dumps(result))
        self.assertEqual(result["checks"][0]["reason"], "invalid_arguments")

    def test_dependency_versions_are_checked_without_accepting_prereleases_or_old_crypto(self):
        versions = {"requests": "2.34.2", "PyJWT": "2.13.0", "cryptography": "50.0.1"}
        with patch(
            "fabric_delivery_core.preflight.metadata.version", side_effect=versions.__getitem__
        ), patch("fabric_delivery_core.preflight.importlib.import_module"):
            self.assertTrue(preflight(
                self.manifest_path, self.plan_path, now=NOW
            ).offline_checks_passed)
            for package, version in (
                ("PyJWT", "2.12.0"), ("cryptography", "50.0.1rc1"), ("requests", "3.0.0"),
            ):
                with self.subTest(package=package):
                    old = versions[package]
                    versions[package] = version
                    self.assertFalse(preflight(
                        self.manifest_path, self.plan_path, now=NOW
                    ).offline_checks_passed)
                    versions[package] = old

    def test_real_module_entrypoint_is_read_only_and_returns_closed_input_failure(self):
        result = subprocess.run(
            [sys.executable, "-B", "-m", "fabric_delivery_core", "validate-manifest",
             str(self.directory / "PRIVATE_MISSING_FILE")],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, "")
        self.assertIs(json.loads(result.stdout)["execution_enabled"], False)
        self.assertNotIn("PRIVATE_MISSING_FILE", result.stdout)


if __name__ == "__main__":
    unittest.main()
