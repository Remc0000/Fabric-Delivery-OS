import ast
import base64
from contextlib import redirect_stdout
from dataclasses import asdict, replace
from io import StringIO
import json
from pathlib import Path
import shutil
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fabric_delivery_core import sha256_digest
from fabric_delivery_core.bronze_runtime import run_bronze
from fabric_delivery_core.operator import main
from fabric_delivery_core.sql_bronze import (
    BronzeColumn, BronzeIdentity, BronzeSource, BronzeTable, BronzeTarget,
    SqlBronzeContract, compile_sql_bronze, write_sql_bronze_release,
)


def contract():
    return SqlBronzeContract(
        BronzeSource("synthetic.example.invalid", "synthetic_database"),
        BronzeIdentity(
            "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222",
            "https://synthetic-vault.vault.azure.net", "synthetic-reader",
            "service_principal_keyvault_secret",
        ),
        (BronzeTable("Synthetic", "Things", "things", (
            BronzeColumn("ThingID", "int", False), BronzeColumn("Amount", "decimal(18,2)", True),
        ), 100),),
        tuple(
            BronzeTarget(stage, str(uuid4()), str(uuid4()), "synthetic_lakehouse")
            for stage in ("development", "test", "production")
        ),
        "Synthetic Bronze", "create_only_snapshot", 60,
    )


class CompilerTests(unittest.TestCase):
    def setUp(self):
        self.contract = contract()
        self.directory = Path.cwd() / ".test-state" / str(uuid4())
        self.directory.mkdir(parents=True)
        self.addCleanup(self.clean)

    def clean(self):
        shutil.rmtree(self.directory)
        try:
            self.directory.parent.rmdir()
        except OSError:
            pass

    def test_strict_contract_roundtrip_and_deterministic_bound_notebooks(self):
        rebuilt = SqlBronzeContract.from_json(json.dumps(asdict(self.contract)))
        self.assertEqual(rebuilt, self.contract)
        first = compile_sql_bronze(rebuilt)
        self.assertEqual(first, compile_sql_bronze(rebuilt))
        code = []
        for artifact, target in zip(first, self.contract.targets):
            notebook = json.loads(artifact.notebook_json)
            payload = json.loads(artifact.create_payload_json)
            self.assertEqual(payload["definition"]["format"], "ipynb")
            part = payload["definition"]["parts"][0]
            self.assertEqual(base64.b64decode(part["payload"]).decode(), artifact.notebook_json)
            self.assertEqual(
                notebook["metadata"]["dependencies"]["lakehouse"]["default_lakehouse"],
                target.lakehouse_id,
            )
            for cell in notebook["cells"]:
                self.assertIsNone(cell["execution_count"])
                self.assertEqual(cell["outputs"], [])
                ast.parse("".join(cell["source"]))
            code.append(notebook["cells"])
        self.assertEqual(code[0], code[1])
        self.assertEqual(code[1], code[2])
        changed = replace(self.contract, query_timeout_seconds=61)
        self.assertNotEqual(compile_sql_bronze(changed)[0].digest, first[0].digest)

    def test_legacy_example_contract_artifacts_and_release_remain_byte_compatible(self):
        legacy = replace(
            self.contract, notebook_name="Synthetic SQL Bronze",
            targets=tuple(
                BronzeTarget(
                    stage, digit * 8 + "-" + digit * 4 + "-4" + digit * 3
                    + "-8" + digit * 3 + "-" + digit * 12,
                    lakehouse * 8 + "-" + lakehouse * 4 + "-4" + lakehouse * 3
                    + "-8" + lakehouse * 3 + "-" + lakehouse * 12,
                    "synthetic_lakehouse",
                )
                for stage, digit, lakehouse in (
                    ("development", "3", "4"), ("test", "5", "6"), ("production", "7", "8")
                )
            ),
        )
        self.assertEqual(
            legacy.digest, "sha256:057a52c8929a38f4e9b504a9b390f0ec2c2aad3073dfcbd26449a633580864ee"
        )
        self.assertEqual(
            tuple(artifact.digest for artifact in compile_sql_bronze(legacy)),
            (
                "sha256:cf6fbf6c6d607f2b93ebb7ca2c18d4acce41892143d6e690a9af0d514a9dcf3b",
                "sha256:68843171d9b985ce915c93f2f5feead4b37c665a38bcde997c4cf6f37c2a2713",
                "sha256:03e1358374abf974c5fa0f314614618572bb7523005349e3e93a530d482f05cf",
            ),
        )
        destination = self.directory / "legacy"
        write_sql_bronze_release(legacy, destination)
        self.assertEqual(
            sha256_digest((destination / "release.json").read_bytes()),
            "sha256:2265a0e9b8e2906be76d22d27381209b1c478014c07aad30beb68531c613a2c7",
        )

    def test_explicit_dev_only_roundtrips_and_uses_identical_development_worker_bytes(self):
        development = replace(
            self.contract, schema_version=2, targets=self.contract.targets[:1]
        )
        rebuilt = SqlBronzeContract.from_json(json.dumps(asdict(development)))
        self.assertEqual(rebuilt, development)
        artifacts = compile_sql_bronze(rebuilt)
        self.assertEqual(len(artifacts), 1)
        self.assertEqual(artifacts, compile_sql_bronze(rebuilt))
        self.assertEqual(artifacts[0], compile_sql_bronze(self.contract)[0])
        self.assertNotEqual(rebuilt.digest, self.contract.digest)

    def test_contract_versions_do_not_infer_or_expand_development_scope(self):
        for targets in (
            (), self.contract.targets[1:2], self.contract.targets[2:],
            self.contract.targets[:2], self.contract.targets,
            self.contract.targets[:1] * 2,
        ):
            with self.subTest(targets=targets), self.assertRaisesRegex(
                ValueError, "^development_target_required$"
            ):
                replace(self.contract, schema_version=2, targets=targets)
        with self.assertRaisesRegex(ValueError, "^three_distinct_stage_targets_required$"):
            replace(self.contract, targets=self.contract.targets[:1])
        for version in (0, 3, True, 2.0, "2", None):
            value = asdict(self.contract)
            value.update(schema_version=version, targets=value["targets"][:1])
            with self.subTest(version=version), self.assertRaisesRegex(
                ValueError, "^unsupported_contract_version$"
            ):
                SqlBronzeContract.from_json(json.dumps(value))

    def test_dev_only_keeps_identity_row_and_query_bounds_fail_closed(self):
        development = replace(self.contract, schema_version=2, targets=self.contract.targets[:1])
        invalid = []
        for ceiling in (0, -1, 1_000_000_001, 1_000_000_000_000_000_000, True):
            value = asdict(development)
            value["tables"][0]["max_rows"] = ceiling
            invalid.append(value)
        for timeout in (0, 86401, True):
            value = asdict(development)
            value["query_timeout_seconds"] = timeout
            invalid.append(value)
        for key, value in (
            ("authentication", "azure_cli"),
            ("client_secret", "NEVER_ACCEPT_SECRET_VALUES"),
        ):
            data = asdict(development)
            data["identity"][key] = value
            invalid.append(data)
        for value in invalid:
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                SqlBronzeContract.from_json(json.dumps(value))

    def test_unknown_duplicate_missing_secret_and_unsupported_configuration_denied(self):
        value = json.dumps(asdict(self.contract))
        invalid = (
            value[:-1] + ',"schema_version":1}',
            value[:-1] + ',"secret":"NEVER_ACCEPT_SECRET_VALUES"}',
            value.replace('"create_only_snapshot"', '"overwrite"'),
            value.replace('"service_principal_keyvault_secret"', '"azure_cli"'),
            value.replace('"max_rows": 100', '"max_rows": true'),
            value.replace('"nullable": false', '"nullable": 0'),
        )
        for item in invalid:
            with self.subTest(item=item[-50:]), self.assertRaises((ValueError, TypeError)):
                SqlBronzeContract.from_json(item)
        nested = asdict(self.contract)
        nested["identity"]["client_secret"] = "NEVER_ACCEPT_SECRET_VALUES"
        with self.assertRaises(TypeError):
            SqlBronzeContract.from_json(json.dumps(nested))

    def test_identifier_jdbc_path_and_projection_ambiguity_rejected(self):
        for field, value in (
            ("server", "server.invalid;trustServerCertificate=true"),
            ("database", "database;user=human"),
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                replace(self.contract.source, **{field: value})
        table = self.contract.tables[0]
        for change in (
            {"target_table": "../outside"},
            {"source_table": "contains\ncontrol"},
            {"columns": (BronzeColumn("id", "int", True), BronzeColumn("ID", "int", True))},
            {"columns": (BronzeColumn("id", "int", True),) * 2},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(table, **change)
        for name, datatype in (("_FDOS_BATCH_ID", "string"), ("unsafe.column", "int"), ("id", "array<int>")):
            with self.subTest(name=name), self.assertRaises(ValueError):
                BronzeColumn(name, datatype, True)
        with self.assertRaises(ValueError):
            replace(self.contract, targets=(self.contract.targets[0],) * 3)

    def test_release_hashes_exact_bytes_and_never_overwrites_or_contacts_network(self):
        destination = self.directory / "release"
        with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")):
            write_sql_bronze_release(self.contract, destination)
        record = json.loads((destination / "release.json").read_text())
        self.assertIs(record["execution_enabled"], False)
        for stage in record["stages"]:
            for item in stage["files"]:
                self.assertEqual(sha256_digest((destination / item["path"]).read_bytes()), item["digest"])
        before = (destination / "release.json").read_bytes()
        with self.assertRaises(FileExistsError):
            write_sql_bronze_release(self.contract, destination)
        self.assertEqual((destination / "release.json").read_bytes(), before)

    def test_export_failure_leaves_no_completion_manifest(self):
        original = Path.open
        destination = self.directory / "interrupted"

        def fail_second(path, *args, **kwargs):
            if path.name == "test.notebook.ipynb":
                raise OSError("synthetic persistence failure")
            return original(path, *args, **kwargs)

        with patch.object(Path, "open", fail_second), self.assertRaises(OSError):
            write_sql_bronze_release(self.contract, destination)
        self.assertTrue(destination.is_dir())
        self.assertFalse((destination / "release.json").exists())

    def test_cli_writes_only_private_artifacts_and_emits_no_contract_values(self):
        source = self.directory / "private-contract.json"
        source.write_text(json.dumps(asdict(self.contract)), encoding="utf-8")
        destination = self.directory / "output"
        output = StringIO()
        with redirect_stdout(output):
            code = main(["compile-sql-bronze", str(source), "--output", str(destination)])
        self.assertEqual(code, 0)
        result = json.loads(output.getvalue())
        self.assertIs(result["execution_enabled"], False)
        self.assertEqual(result["checks"][0]["reason"], "compiled_not_deployed")
        self.assertNotIn("synthetic", output.getvalue().lower())
        self.assertNotIn(str(destination), output.getvalue())
        output = StringIO()
        with redirect_stdout(output):
            code = main(["compile-sql-bronze", str(source), "--output", str(destination)])
        self.assertEqual(code, 2)
        self.assertNotIn(str(destination), output.getvalue())

    def test_dev_only_cli_exports_one_scoped_hashed_release_without_activation(self):
        development = replace(self.contract, schema_version=2, targets=self.contract.targets[:1])
        source = self.directory / "private-dev-contract.json"
        source.write_text(json.dumps(asdict(development)), encoding="utf-8")
        destination = self.directory / "development"
        output = StringIO()
        with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")):
            with redirect_stdout(output):
                code = main(["compile-sql-bronze", str(source), "--output", str(destination)])
        self.assertEqual(code, 0)
        self.assertNotIn("synthetic", output.getvalue().lower())
        self.assertNotIn(str(destination), output.getvalue())
        record = json.loads((destination / "release.json").read_text())
        self.assertEqual(record["schema_version"], 2)
        self.assertEqual(record["release_scope"], "development_only")
        self.assertIs(record["promotion_supported"], False)
        self.assertIs(record["execution_enabled"], False)
        self.assertEqual(record["contract_digest"], development.digest)
        self.assertEqual(
            set(path.name for path in destination.iterdir()),
            {"development.notebook.ipynb", "development.create.json", "release.json"},
        )
        self.assertEqual([stage["stage"] for stage in record["stages"]], ["development"])
        for item in record["stages"][0]["files"]:
            self.assertEqual(sha256_digest((destination / item["path"]).read_bytes()), item["digest"])
        before = (destination / "release.json").read_bytes()
        with self.assertRaises(FileExistsError):
            write_sql_bronze_release(development, destination)
        self.assertEqual(before, (destination / "release.json").read_bytes())

    def test_partial_manifest_or_failed_publication_never_marks_release_complete(self):
        original = Path.open

        def partial_manifest(path, *args, **kwargs):
            if path.name == ".release.pending.json":
                with original(path, *args, **kwargs) as stream:
                    stream.write(b'{"incomplete":')
                raise OSError("synthetic interrupted manifest")
            return original(path, *args, **kwargs)

        development = replace(self.contract, schema_version=2, targets=self.contract.targets[:1])
        for selected in (self.contract, development):
            for failure in ("manifest", "publication"):
                destination = self.directory / (str(selected.schema_version) + failure)
                context = (
                    patch.object(Path, "open", partial_manifest) if failure == "manifest"
                    else patch("fabric_delivery_core.sql_bronze.os.link", side_effect=OSError("publication failed"))
                )
                with self.subTest(version=selected.schema_version, failure=failure):
                    with context, self.assertRaises(OSError):
                        write_sql_bronze_release(selected, destination)
                    self.assertTrue((destination / ".release.pending.json").exists())
                    self.assertFalse((destination / "release.json").exists())


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.contract = contract()
        artifact = compile_sql_bronze(self.contract)[0]
        self.notebook = json.loads(artifact.notebook_json)
        configuration = {}
        exec("".join(self.notebook["cells"][1]["source"]), configuration)
        self.configuration = configuration["CONFIG"]
        self.spark = MagicMock()
        self.spark.catalog.tableExists.return_value = False
        self.frame = MagicMock()
        self.frame.schema.fields = [
            SimpleNamespace(name=column.name, dataType=SimpleNamespace(
                simpleString=lambda kind=column.spark_type: kind
            ))
            for column in self.contract.tables[0].columns
        ]
        self.frame.count.return_value = 2
        self.frame.filter.return_value.limit.return_value.count.return_value = 0
        self.frame.persist.return_value = self.frame
        self.frame.withColumn.return_value = self.frame
        self.frame.write.format.return_value.mode.return_value = self.frame.write
        self.reader = self.spark.read
        self.reader.option.return_value = self.reader
        self.reader.mssql.return_value = self.frame
        self.modules = {name: ModuleType(name) for name in (
            "com", "com.microsoft", "com.microsoft.sqlserver",
            "com.microsoft.sqlserver.jdbc", "com.microsoft.sqlserver.jdbc.spark",
            "azure", "azure.identity", "notebookutils", "pyspark", "pyspark.sql",
            "pyspark.sql.functions",
        )}
        self.modules["azure"].identity = self.modules["azure.identity"]
        self.credential = MagicMock()
        self.credential.get_token.return_value.token = "SYNTHETIC_SECRET_DO_NOT_LOG"
        self.credential_factory = MagicMock()
        self.credential_factory.return_value.__enter__.return_value = self.credential
        self.modules["azure.identity"].ClientSecretCredential = self.credential_factory
        self.modules["notebookutils"].credentials = MagicMock()
        self.modules["pyspark"].StorageLevel = SimpleNamespace(DISK_ONLY="synthetic-storage")
        self.modules["pyspark.sql"].functions = MagicMock()
        self.batch = str(uuid4())
        self.emit = MagicMock()

    def run_worker(self):
        with patch.dict("sys.modules", self.modules), patch("builtins.print", self.emit):
            run_bronze(self.spark, self.configuration, self.batch)

    def test_generated_worker_uses_explicit_projection_tls_app_token_and_no_overwrite(self):
        with patch.dict("sys.modules", self.modules), patch("builtins.print", self.emit):
            exec(
                "".join(self.notebook["cells"][2]["source"]),
                {"spark": self.spark, "CONFIG": self.configuration, "fdos_batch_id": self.batch},
            )
        options = dict(call.args for call in self.reader.option.call_args_list)
        self.assertEqual(
            options["query"], "SELECT TOP (101) [ThingID], [Amount] FROM [Synthetic].[Things]"
        )
        self.assertIn("encrypt=true;trustServerCertificate=false", options["url"])
        self.assertEqual(options["accesstoken"], "SYNTHETIC_SECRET_DO_NOT_LOG")
        self.credential.get_token.assert_called_once_with("https://database.windows.net/.default")
        self.frame.write.format.assert_called_once_with("delta")
        self.frame.write.format.return_value.mode.assert_called_once_with("errorifexists")
        self.frame.write.saveAsTable.assert_called_once_with("bronze.things")
        self.frame.unpersist.assert_called_once()

    def test_existing_targets_block_before_any_credential_or_source_read(self):
        self.spark.catalog.tableExists.return_value = True
        with self.assertRaisesRegex(RuntimeError, "^target_already_exists$"):
            self.run_worker()
        self.credential_factory.assert_not_called()
        self.reader.option.assert_not_called()
        self.spark.sql.assert_not_called()

    def test_existing_later_target_blocks_all_tables_before_credentials(self):
        self.configuration["tables"].append(dict(
            self.configuration["tables"][0], source_table="MoreThings", target_table="more_things"
        ))
        self.spark.catalog.tableExists.side_effect = [False, True]
        with self.assertRaisesRegex(RuntimeError, "^target_already_exists$"):
            self.run_worker()
        self.credential_factory.assert_not_called()
        self.reader.option.assert_not_called()

    def test_row_schema_and_null_failures_never_write_and_always_unpersist(self):
        for reason in ("source_row_limit_exceeded", "source_schema_mismatch", "source_nullability_failed"):
            with self.subTest(reason=reason):
                self.frame.reset_mock()
                self.frame.count.return_value = 2
                self.frame.schema.fields[0].name = "ThingID"
                self.frame.filter.return_value.limit.return_value.count.return_value = 0
                if reason == "source_row_limit_exceeded":
                    self.frame.count.return_value = 101
                elif reason == "source_schema_mismatch":
                    self.frame.schema.fields[0].name = "wrong"
                else:
                    self.frame.filter.return_value.limit.return_value.count.return_value = 1
                with self.assertRaisesRegex(RuntimeError, "^" + reason + "$"):
                    self.run_worker()
                self.frame.write.saveAsTable.assert_not_called()
                self.frame.unpersist.assert_called_once()

    def test_identifier_quotes_are_data_and_batch_is_not_an_authorization_or_retry_flag(self):
        self.configuration["tables"][0]["source_table"] = "odd]; DROP TABLE other;--"
        self.run_worker()
        query = dict(call.args for call in self.reader.option.call_args_list)["query"]
        self.assertIn("[odd]]; DROP TABLE other;--]", query)
        self.batch = "not-a-grant"
        with self.assertRaisesRegex(ValueError, "^invalid_batch_id$"):
            self.run_worker()

    def test_write_failures_propagate_without_retry_and_release_cached_source(self):
        self.frame.write.saveAsTable.side_effect = OSError("synthetic storage error")
        with self.assertRaisesRegex(OSError, "synthetic storage error"):
            self.run_worker()
        self.frame.write.saveAsTable.assert_called_once()
        self.frame.unpersist.assert_called_once()

    def test_later_failure_records_partial_progress_without_rollback_or_retry(self):
        self.configuration["tables"].append(dict(
            self.configuration["tables"][0], source_table="MoreThings", target_table="more_things"
        ))
        self.frame.write.saveAsTable.side_effect = [None, OSError("second table failed")]
        with self.assertRaisesRegex(OSError, "second table failed"):
            self.run_worker()
        self.assertEqual(self.frame.write.saveAsTable.call_count, 2)
        self.assertEqual(self.frame.unpersist.call_count, 2)
        self.assertEqual(
            [json.loads(call.args[0]) for call in self.emit.call_args_list],
            [
                {"event": "bronze_write_started", "table_index": 0},
                {"event": "bronze_table_created", "table_index": 0},
                {"event": "bronze_write_started", "table_index": 1},
            ],
        )
        self.assertTrue(all(
            call.args[0] == "CREATE SCHEMA IF NOT EXISTS bronze"
            for call in self.spark.sql.call_args_list
        ))


if __name__ == "__main__":
    unittest.main()
