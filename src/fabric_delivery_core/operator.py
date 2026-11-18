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
    """Return 0 for local validity/self-test, 2 for failures, 3 for blocked preflight."""
    parser = _Parser(
        prog="fabric-delivery",
        description="Offline checks and inert self-test only. No live authority or workers.",
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
    try:
        arguments = parser.parse_args(argv)
        if arguments.command == "validate-manifest":
            report = validate_manifest(arguments.manifest)
            code = 0 if report.offline_checks_passed else 2
        elif arguments.command == "preflight":
            report = preflight(arguments.manifest, arguments.spend_plan)
            code = 3 if report.offline_checks_passed else 2
        else:
            from .self_test import dispatch_self_test

            report = dispatch_self_test()
            code = 0 if report.offline_checks_passed else 2
    except _InputError:
        report = OfflineReport((OfflineCheck("arguments", "incompatible", "invalid_arguments"),))
        code = 2
    except Exception:
        report = OfflineReport((OfflineCheck("operator", "unknown", "offline_check_failed"),))
        code = 2
    sys.stdout.write(report.to_json() + "\n")
    return code
