"""Credential-free offline operator commands; deliberately no live execution."""

from __future__ import annotations

import argparse
import sys

from .preflight import OfflineCheck, OfflineReport, preflight, validate_manifest


class _InputError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _InputError()


def main(argv: list[str] | None = None) -> int:
    """Return 0 for local checks/compilation, 2 for failures, 3 for blocked preflight."""
    parser = _Parser(
        prog="fabric-delivery",
        description="Offline checks, artifact compilation and inert self-test. No live authority or workers.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    validate = subcommands.add_parser("validate-manifest", help="check a private frozen manifest")
    validate.add_argument("manifest", help="ordinary local manifest JSON file")
    readiness = subcommands.add_parser("preflight", help="report offline inputs and live blockers")
    readiness.add_argument("--manifest", required=True, help="ordinary local manifest JSON file")
    readiness.add_argument("--spend-plan", help="optional private offline spend-plan JSON file")
    subcommands.add_parser(
        "self-test-dispatch", help="exercise synthetic atomic dispatch in disposable local stores"
    )
    bronze = subcommands.add_parser(
        "compile-sql-bronze", help="compile reviewed SQL metadata into a new private release directory"
    )
    bronze.add_argument("contract", help="private metadata-only contract JSON file")
    bronze.add_argument("--output", required=True, help="new directory under protected private storage")
    try:
        arguments = parser.parse_args(argv)
        if arguments.command == "validate-manifest":
            report = validate_manifest(arguments.manifest)
            code = 0 if report.offline_checks_passed else 2
        elif arguments.command == "preflight":
            report = preflight(arguments.manifest, arguments.spend_plan)
            code = 3 if report.offline_checks_passed else 2
        elif arguments.command == "self-test-dispatch":
            from .self_test import dispatch_self_test

            report = dispatch_self_test()
            code = 0 if report.offline_checks_passed else 2
        else:
            from .preflight import _read
            from .sql_bronze import SqlBronzeContract, write_sql_bronze_release

            contract = SqlBronzeContract.from_json(_read(arguments.contract))
            write_sql_bronze_release(contract, arguments.output)
            report = OfflineReport((
                OfflineCheck("sql_bronze_artifacts", "ready", "compiled_not_deployed"),
            ))
            code = 0
    except _InputError:
        report = OfflineReport((OfflineCheck("arguments", "incompatible", "invalid_arguments"),))
        code = 2
    except Exception:
        report = OfflineReport((OfflineCheck("operator", "unknown", "offline_check_failed"),))
        code = 2
    sys.stdout.write(report.to_json() + "\n")
    return code
