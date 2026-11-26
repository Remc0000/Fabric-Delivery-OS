from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fabric_delivery_core.operator import main
from fabric_delivery_core.preflight import LIVE_BLOCKERS


class DeliveryDemoTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(dir=Path.cwd())
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.factory = patch(
            "fabric_delivery_core.delivery_demo.TemporaryDirectory",
            side_effect=lambda **kwargs: TemporaryDirectory(dir=self.directory, **kwargs),
        )
        self.factory.start()
        self.addCleanup(self.factory.stop)

    def invoke(self, *args):
        output = StringIO()
        with redirect_stdout(output), patch(
            "socket.socket.connect", side_effect=AssertionError("network forbidden"),
        ):
            code = main(["demo-delivery", *args])
        return code, json.loads(output.getvalue())

    def test_complete_real_store_rehearsal_is_inert_and_cleans_its_files(self):
        code, report = self.invoke()
        self.assertEqual(code, 0)
        self.assertTrue(report["offline_checks_passed"])
        self.assertIs(report["execution_enabled"], False)
        self.assertEqual(report["live_execution"], "unsupported")
        self.assertEqual(report["live_blockers"], list(LIVE_BLOCKERS))
        self.assertEqual(len(report["checks"]), 6)
        self.assertTrue(all(check["status"] == "ready" for check in report["checks"]))
        self.assertNotIn("synthetic-installation", json.dumps(report))
        self.assertNotIn("Synthetic context", json.dumps(report))
        self.assertNotIn("sha256:", json.dumps(report))
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_no_private_inputs_are_accepted_or_opened(self):
        for option in ("--store", "--manifest", "--token", "--approve"):
            with self.subTest(option=option), patch("sqlite3.connect") as connect:
                code, report = self.invoke(option, "PRIVATE_INPUT")
                self.assertEqual(code, 2)
                self.assertEqual(report["checks"][0]["reason"], "invalid_arguments")
                self.assertNotIn("PRIVATE_INPUT", json.dumps(report))
                connect.assert_not_called()

    def test_component_failures_are_closed_and_never_report_partial_success(self):
        for target in (
            "OfflineSkillResolver.resolve",
            "OfflineGitHubIntake.register",
            "SQLiteAuthorizationStore.authorize",
            "SQLiteRegistryDispatchStore.claim",
            "SQLiteRegistryDispatchStore.finish",
        ):
            with self.subTest(target=target), patch(
                "fabric_delivery_core.delivery_demo." + target,
                side_effect=OSError("PRIVATE_DIAGNOSTIC"),
            ):
                code, report = self.invoke()
                self.assertEqual(code, 2)
                self.assertFalse(report["offline_checks_passed"])
                self.assertEqual(report["checks"][0]["reason"], "offline_check_failed")
                self.assertNotIn("PRIVATE_DIAGNOSTIC", json.dumps(report))
                self.assertEqual(list(self.directory.iterdir()), [])

    def test_missing_pending_denial_is_a_failed_rehearsal(self):
        with patch(
            "fabric_delivery_core.delivery_demo.SQLiteRegistryDispatchStore.enqueue",
            return_value=None,
        ):
            code, report = self.invoke()
        self.assertEqual(code, 2)
        self.assertFalse(report["offline_checks_passed"])

    def test_missing_terminal_accounting_is_not_a_successful_result(self):
        with patch(
            "fabric_delivery_core.delivery_demo.SQLiteRegistryDispatchStore.finish",
            return_value=None,
        ):
            code, report = self.invoke()
        self.assertEqual(code, 2)
        self.assertFalse(report["offline_checks_passed"])


if __name__ == "__main__":
    unittest.main()
