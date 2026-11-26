"""Offline compiler for private, explicit SQL-to-Bronze notebook contracts."""

from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
from importlib import resources
import json
import os
from pathlib import Path
import re
from uuid import UUID

from .authorization import _canonical, _text, sha256_digest
from .preflight import _invalid_constant, _unique


_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}\Z")
_TARGET = re.compile(r"[a-z][a-z0-9_]{0,127}\Z")
_STAGES = ("development", "test", "production")
_CONTRACT_STAGES = {1: _STAGES, 2: ("development",)}


def _uuid(value: object) -> None:
    if not isinstance(value, str):
        raise ValueError("invalid_metadata_identifier")
    try:
        parsed = UUID(value)
    except ValueError:
        raise ValueError("invalid_metadata_identifier") from None
    if str(parsed) != value or parsed.int == 0:
        raise ValueError("invalid_metadata_identifier")


def _sql_name(value: object) -> None:
    _text(value, "SQL identifier")
    if len(value) > 128 or not value.isprintable():
        raise ValueError("unsupported_sql_identifier")


@dataclass(frozen=True)
class BronzeColumn:
    name: str
    spark_type: str
    nullable: bool

    def __post_init__(self) -> None:
        if (
            not isinstance(self.name, str) or _NAME.fullmatch(self.name) is None
            or self.name.lower().startswith("_fdos_")
        ):
            raise ValueError("unsupported_bronze_column")
        if self.spark_type not in {
            "boolean", "tinyint", "smallint", "int", "bigint", "float", "double",
            "string", "binary", "date", "timestamp",
        }:
            match = re.fullmatch(r"decimal\(([1-9][0-9]?),((?:0|[1-9][0-9]?))\)", str(self.spark_type))
            if match is None or not 0 <= int(match[2]) <= int(match[1]) <= 38:
                raise ValueError("unsupported_spark_type")
        if type(self.nullable) is not bool:
            raise ValueError("nullable_must_be_boolean")


@dataclass(frozen=True)
class BronzeTable:
    source_schema: str
    source_table: str
    target_table: str
    columns: tuple[BronzeColumn, ...]
    max_rows: int

    def __post_init__(self) -> None:
        _sql_name(self.source_schema)
        _sql_name(self.source_table)
        if not isinstance(self.target_table, str) or _TARGET.fullmatch(self.target_table) is None:
            raise ValueError("unsupported_target_table")
        if (
            not isinstance(self.columns, tuple) or not self.columns
            or not all(isinstance(column, BronzeColumn) for column in self.columns)
            or len({column.name.casefold() for column in self.columns}) != len(self.columns)
        ):
            raise ValueError("invalid_column_projection")
        if type(self.max_rows) is not int or not 1 <= self.max_rows <= 1_000_000_000:
            raise ValueError("invalid_source_row_limit")


@dataclass(frozen=True)
class BronzeSource:
    server: str
    database: str

    def __post_init__(self) -> None:
        if not isinstance(self.server, str) or re.fullmatch(
            r"(?=.{1,253}\Z)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
            r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+", self.server,
        ) is None:
            raise ValueError("unsupported_sql_server")
        if not isinstance(self.database, str) or re.fullmatch(
            r"[A-Za-z0-9_][A-Za-z0-9_. -]{0,127}", self.database
        ) is None or self.database != self.database.strip():
            raise ValueError("unsupported_database_name")


@dataclass(frozen=True)
class BronzeIdentity:
    tenant_id: str
    client_id: str
    vault_url: str
    secret_name: str
    authentication: str

    def __post_init__(self) -> None:
        _uuid(self.tenant_id)
        _uuid(self.client_id)
        if self.authentication != "service_principal_keyvault_secret":
            raise ValueError("unsupported_authentication")
        if not isinstance(self.vault_url, str) or re.fullmatch(
            r"https://[a-z][a-z0-9-]{1,22}[a-z0-9]\.vault\.azure\.net", self.vault_url
        ) is None:
            raise ValueError("unsupported_vault_url")
        if not isinstance(self.secret_name, str) or re.fullmatch(
            r"[A-Za-z0-9-]{1,127}", self.secret_name
        ) is None:
            raise ValueError("unsupported_secret_reference")


@dataclass(frozen=True)
class BronzeTarget:
    stage: str
    workspace_id: str
    lakehouse_id: str
    lakehouse_name: str

    def __post_init__(self) -> None:
        if self.stage not in _STAGES:
            raise ValueError("unsupported_stage")
        _uuid(self.workspace_id)
        _uuid(self.lakehouse_id)
        if (
            not isinstance(self.lakehouse_name, str)
            or _NAME.fullmatch(self.lakehouse_name) is None
        ):
            raise ValueError("unsupported_lakehouse_name")


@dataclass(frozen=True)
class SqlBronzeContract:
    source: BronzeSource
    identity: BronzeIdentity
    tables: tuple[BronzeTable, ...]
    targets: tuple[BronzeTarget, ...]
    notebook_name: str
    load_mode: str
    query_timeout_seconds: int
    schema_version: int = 1

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version not in _CONTRACT_STAGES:
            raise ValueError("unsupported_contract_version")
        if not isinstance(self.source, BronzeSource) or not isinstance(self.identity, BronzeIdentity):
            raise ValueError("invalid_source_identity")
        if (
            not isinstance(self.tables, tuple) or not self.tables
            or not all(isinstance(table, BronzeTable) for table in self.tables)
            or len({table.target_table for table in self.tables}) != len(self.tables)
            or len({(table.source_schema.casefold(), table.source_table.casefold())
                    for table in self.tables}) != len(self.tables)
        ):
            raise ValueError("ambiguous_table_mapping")
        stages = _CONTRACT_STAGES[self.schema_version]
        if (
            not isinstance(self.targets, tuple) or len(self.targets) != len(stages)
            or not all(isinstance(target, BronzeTarget) for target in self.targets)
            or {target.stage for target in self.targets} != set(stages)
            or len({target.workspace_id for target in self.targets}) != len(stages)
            or len({target.lakehouse_id for target in self.targets}) != len(stages)
        ):
            raise ValueError(
                "development_target_required" if self.schema_version == 2
                else "three_distinct_stage_targets_required"
            )
        if not isinstance(self.notebook_name, str) or re.fullmatch(
            r"[A-Za-z][A-Za-z0-9 _-]{0,127}", self.notebook_name
        ) is None:
            raise ValueError("unsupported_notebook_name")
        if self.load_mode != "create_only_snapshot":
            raise ValueError("unsupported_load_mode")
        if (
            type(self.query_timeout_seconds) is not int
            or not 1 <= self.query_timeout_seconds <= 86400
        ):
            raise ValueError("finite_query_timeout_required")

    @classmethod
    def from_json(cls, value: str) -> SqlBronzeContract:
        data = json.loads(value, object_pairs_hook=_unique, parse_constant=_invalid_constant)
        if not isinstance(data, dict) or set(data) != {
            "source", "identity", "tables", "targets", "notebook_name", "load_mode",
            "query_timeout_seconds", "schema_version",
        }:
            raise ValueError("invalid_contract_keys")
        source, identity = BronzeSource(**data["source"]), BronzeIdentity(**data["identity"])
        if not isinstance(data["tables"], list) or not isinstance(data["targets"], list):
            raise ValueError("table_and_target_arrays_required")
        tables = []
        for item in data["tables"]:
            if not isinstance(item, dict) or not isinstance(item.get("columns"), list):
                raise ValueError("invalid_table_contract")
            fields = dict(item)
            fields["columns"] = tuple(BronzeColumn(**column) for column in item["columns"])
            tables.append(BronzeTable(**fields))
        targets = tuple(BronzeTarget(**target) for target in data["targets"])
        return cls(**dict(data, source=source, identity=identity, tables=tuple(tables), targets=targets))

    @property
    def digest(self) -> str:
        return sha256_digest(_canonical(asdict(self)).encode("utf-8"))


@dataclass(frozen=True)
class BronzeArtifact:
    stage: str
    workspace_id: str
    notebook_json: str
    create_payload_json: str

    @property
    def digest(self) -> str:
        return sha256_digest(self.create_payload_json.encode("utf-8"))


def compile_sql_bronze(contract: SqlBronzeContract) -> tuple[BronzeArtifact, ...]:
    """Build all stage-bound notebook payloads offline, without credentials or effects."""
    runtime = resources.files("fabric_delivery_core").joinpath("bronze_runtime.py").read_text("utf-8")
    configuration = _canonical({
        "source": asdict(contract.source), "identity": asdict(contract.identity),
        "tables": [asdict(table) for table in contract.tables],
        "query_timeout_seconds": contract.query_timeout_seconds,
    })
    sources = (
        ("parameters", "fdos_batch_id = None", {"tags": ["parameters"]}),
        ("configuration", "import json\nCONFIG = json.loads(" + repr(configuration) + ")", {}),
        ("worker", runtime + "\nrun_bronze(spark, CONFIG, fdos_batch_id)\n", {}),
    )
    cells = [
        {"id": name, "cell_type": "code", "metadata": metadata,
         "source": source.splitlines(keepends=True), "outputs": [], "execution_count": None}
        for name, source, metadata in sources
    ]
    artifacts = []
    for stage in _CONTRACT_STAGES[contract.schema_version]:
        target = next(item for item in contract.targets if item.stage == stage)
        notebook = _canonical({
            "nbformat": 4, "nbformat_minor": 5, "cells": cells,
            "metadata": {
                "kernel_info": {"name": "synapse_pyspark"},
                "language_info": {"name": "python"},
                "dependencies": {"lakehouse": {
                    "default_lakehouse": target.lakehouse_id,
                    "default_lakehouse_name": target.lakehouse_name,
                    "default_lakehouse_workspace_id": target.workspace_id,
                }},
            },
        })
        payload = _canonical({
            "displayName": contract.notebook_name, "type": "Notebook",
            "definition": {"format": "ipynb", "parts": [{
                "path": "notebook-content.ipynb", "payloadType": "InlineBase64",
                "payload": base64.b64encode(notebook.encode("utf-8")).decode("ascii"),
            }]},
        })
        artifacts.append(BronzeArtifact(stage, target.workspace_id, notebook, payload))
    return tuple(artifacts)


def write_sql_bronze_release(contract: SqlBronzeContract, output: str | Path) -> None:
    """Write a private new release directory; final manifest marks completeness.

    Never overwrite any existing directory/file. A storage failure can leave an
    incomplete directory without release.json; it is not a usable release and
    must be privately reconciled, not silently retried over.
    """
    output = Path(output)
    if str(output).startswith(("\\\\", "//")):
        raise ValueError("ordinary_private_local_directory_required")
    artifacts = compile_sql_bronze(contract)
    output.mkdir(mode=0o700)
    entries = []
    for artifact in artifacts:
        files = (
            (artifact.stage + ".notebook.ipynb", artifact.notebook_json),
            (artifact.stage + ".create.json", artifact.create_payload_json),
        )
        entries.append({
            "stage": artifact.stage, "workspace_id": artifact.workspace_id,
            "files": [
                {"path": name, "digest": sha256_digest(value.encode("utf-8"))}
                for name, value in files
            ],
        })
        for name, value in files:
            with (output / name).open("xb") as stream:
                stream.write(value.encode("utf-8"))
    release_data = {
        "schema_version": contract.schema_version, "module": "sql_bronze_create_only",
        "contract_digest": contract.digest, "execution_enabled": False,
        "required_deployment_effects": ["deploy_definitions"],
        "required_load_effects": ["read_source", "create_schema", "create_table", "load_data"],
        "stages": entries,
    }
    if contract.schema_version == 2:
        release_data.update(release_scope="development_only", promotion_supported=False)
    release = _canonical(release_data)
    pending = output / ".release.pending.json"
    with pending.open("xb") as stream:
        stream.write(release.encode("utf-8"))
    # Publish only a closed complete manifest, atomically and without replacement.
    os.link(pending, output / "release.json")
    pending.unlink()
