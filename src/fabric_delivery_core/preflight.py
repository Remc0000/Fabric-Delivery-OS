"""Offline local input checks; no authentication, state writes, network or dispatch."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import importlib
from importlib import metadata
import json
from pathlib import Path
import re
import time

from .authorization import ExecutionManifest, _canonical, _timestamp
from .spend import PriceCard, SpendBudget, SpendDenied, maximum_reservation_units


LIVE_BLOCKERS = (
    "trusted_private_registry_and_input_revalidation_required",
    "native_review_and_oidc_grant_join_unsupported",
    "administrative_bypass_and_human_credential_provenance_unverified",
    "runtime_app_provenance_and_identity_separation_unverified",
    "live_installation_federation_unproven",
    "spend_headroom_pricing_provenance_and_adapter_limits_unverified",
    "live_dispatch_and_recovery_unverified",
    "isolated_agent_and_stage_deployment_workers_unimplemented",
    "fabric_delivery_modules_and_acceptance_unimplemented",
)


@dataclass(frozen=True)
class OfflineCheck:
    name: str
    status: str
    reason: str


@dataclass(frozen=True)
class OfflineReport:
    """Allowlisted results with no input values, identifiers, paths or credentials."""

    checks: tuple[OfflineCheck, ...]

    @property
    def offline_checks_passed(self) -> bool:
        return all(check.status in ("ready", "not_applicable") for check in self.checks)

    def to_json(self) -> str:
        return _canonical({
            "schema_version": 1,
            "scope": "offline_only",
            "offline_checks_passed": self.offline_checks_passed,
            "execution_enabled": False,
            "live_execution": "unsupported",
            "live_blockers": LIVE_BLOCKERS,
            "checks": [asdict(check) for check in self.checks],
        })


def _unique(pairs: list[tuple[str, object]]) -> dict:
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError("duplicate input key")
        data[key] = value
    return data


def _invalid_constant(_: str) -> None:
    raise ValueError("nonfinite JSON value")


def _read(path: str | Path) -> str:
    path = Path(path)
    if str(path).startswith(("\\\\", "//")) or not path.is_file():
        raise OSError("ordinary local file required")
    with path.open("rb") as stream:
        value = stream.read(1_048_577)
    if len(value) > 1_048_576:
        raise ValueError("offline input too large")
    return value.decode("utf-8")


def _load_manifest(
    path: str | Path, now: int
) -> tuple[ExecutionManifest | None, OfflineCheck]:
    try:
        manifest = ExecutionManifest.from_json(_read(path))
    except OSError:
        return None, OfflineCheck("manifest", "missing", "manifest_unreadable")
    except (ValueError, TypeError, RecursionError):
        return None, OfflineCheck("manifest", "incompatible", "manifest_invalid")
    if not manifest.created_at <= now < manifest.expires_at:
        return None, OfflineCheck("manifest", "unauthorized", "manifest_not_current")
    return manifest, OfflineCheck("manifest", "ready", "schema_and_validity_only")


def validate_manifest(path: str | Path, *, now: int | None = None) -> OfflineReport:
    """Validate a local frozen envelope without freezing or authorizing a request."""
    now = time.time_ns() // 1_000_000_000 if now is None else now
    _timestamp(now, "clock result")
    _, check = _load_manifest(path, now)
    return OfflineReport((check,))


def _dependencies() -> tuple[OfflineCheck, ...]:
    requirements = (
        ("native_api_library", "requests", "requests", (2, 32, 5), (3, 0, 0)),
        ("jwt_library", "PyJWT", "jwt", (2, 13, 0), (3, 0, 0)),
        (
            "crypto_library", "cryptography",
            "cryptography.hazmat.primitives.asymmetric.rsa", (46, 0, 0), (51, 0, 0),
        ),
    )
    checks = []
    for name, distribution, module, minimum, upper in requirements:
        try:
            version = metadata.version(distribution)
            if re.fullmatch(r"[0-9]+\.[0-9]+(?:\.[0-9]+)?", version) is None:
                raise ValueError()
            parts = tuple(int(part) for part in version.split("."))
            parts += (0,) * (3 - len(parts))
            if not minimum <= parts < upper:
                raise ValueError()
            importlib.import_module(module)
        except (metadata.PackageNotFoundError, ImportError):
            checks.append(OfflineCheck(name, "missing", "optional_dependency_missing"))
        except Exception:
            checks.append(OfflineCheck(name, "incompatible", "optional_dependency_unusable"))
        else:
            checks.append(OfflineCheck(name, "ready", "supported_import_only"))
    return tuple(checks)


def _spend_check(
    path: str | Path | None, manifest: ExecutionManifest | None, now: int
) -> OfflineCheck:
    if path is None:
        return OfflineCheck("spend_plan", "unknown", "spend_plan_not_supplied")
    if manifest is None:
        return OfflineCheck("spend_plan", "unknown", "manifest_context_unavailable")
    try:
        data = json.loads(
            _read(path), object_pairs_hook=_unique, parse_constant=_invalid_constant
        )
        if not isinstance(data, dict) or set(data) != {
            "schema_version", "budget", "price", "max_tokens", "max_calls",
        }:
            raise ValueError()
        if type(data["schema_version"]) is not int or data["schema_version"] != 1:
            raise ValueError()
        if not isinstance(data["budget"], dict) or not isinstance(data["price"], dict):
            raise ValueError()
        budget = SpendBudget(**data["budget"])
        card = PriceCard(**data["price"])
        maximum = maximum_reservation_units(card, data["max_tokens"], data["max_calls"])
        if (
            budget.installation_id != manifest.installation_id
            or budget.currency != card.currency
            or budget.period != datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m")
            or not card.valid_from <= now < card.valid_until
            or data["max_tokens"] > budget.max_tokens
            or data["max_calls"] > budget.max_calls
            or maximum > budget.cap_units
        ):
            return OfflineCheck("spend_plan", "incompatible", "spend_binding_or_bounds_invalid")
    except OSError:
        return OfflineCheck("spend_plan", "missing", "spend_plan_unreadable")
    except (ValueError, TypeError, RecursionError, SpendDenied, OverflowError):
        return OfflineCheck("spend_plan", "incompatible", "spend_plan_invalid")
    return OfflineCheck("spend_plan", "ready", "local_bounds_only_not_ledger_headroom")


def preflight(
    manifest_path: str | Path,
    spend_plan_path: str | Path | None = None,
    *,
    now: int | None = None,
) -> OfflineReport:
    """Assess supplied local inputs and imports; live deployment stays unsupported."""
    now = time.time_ns() // 1_000_000_000 if now is None else now
    _timestamp(now, "clock result")
    manifest, check = _load_manifest(manifest_path, now)
    return OfflineReport((
        check, _spend_check(spend_plan_path, manifest, now), *_dependencies(),
    ))
