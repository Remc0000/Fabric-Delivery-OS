"""Trusted-caller offline proposal registry; no authentication, grants or dispatch."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
import json
from pathlib import Path
import sqlite3
import time
from typing import Callable, Iterator

from .authorization import (
    ExecutionManifest, _canonical, _digest, _text, _timestamp, sha256_digest,
)
from .preflight import _invalid_constant, _unique


_APPLICATION_ID = 0x46445247
_SCHEMA = {
    "policies": """CREATE TABLE policies (
        digest TEXT PRIMARY KEY, payload TEXT NOT NULL,
        installation TEXT NOT NULL, solution TEXT NOT NULL, version TEXT NOT NULL,
        UNIQUE(installation, solution, version)
    )""",
    "current_policies": """CREATE TABLE current_policies (
        installation TEXT NOT NULL, solution TEXT NOT NULL,
        digest TEXT NOT NULL REFERENCES policies(digest),
        PRIMARY KEY(installation, solution)
    )""",
    "registry_requests": """CREATE TABLE registry_requests (
        request_id TEXT PRIMARY KEY, payload TEXT NOT NULL, digest TEXT NOT NULL,
        policy_digest TEXT NOT NULL REFERENCES policies(digest),
        state TEXT NOT NULL CHECK(state IN ('proposed','invalidated','revoked')),
        reason TEXT
    )""",
}
_INVALIDATIONS = {
    "registry_policy_changed", "registry_policy_revoked", "registry_request_changed",
    "registry_route_changed", "registry_expired", "registry_not_yet_valid",
}


def _positive(value: object) -> None:
    if type(value) is not int or not 1 <= value <= 2**63 - 1:
        raise ValueError("a positive signed-64-bit numeric identity is required")


def _effects(value: object) -> None:
    if not isinstance(value, tuple) or not value:
        raise ValueError("an explicit nonempty effect tuple is required")
    for effect in value:
        _text(effect, "effect")
    if len(set(value)) != len(value):
        raise ValueError("effects must be unique")


def _object(value: object, expected: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("registry keys do not match the schema")
    return value


def _decode(value: str, record_type: type) -> dict:
    if not isinstance(value, str):
        raise ValueError("registry JSON must be text")
    return _object(
        json.loads(value, object_pairs_hook=_unique, parse_constant=_invalid_constant),
        {item.name for item in fields(record_type)},
    )


@dataclass(frozen=True)
class RequestRule:
    """Admission allowlist for one action, not permission to perform its effects."""

    action: str
    permitted_effects: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.action, "action")
        _effects(self.permitted_effects)


@dataclass(frozen=True)
class RequestPolicy:
    """Private versioned admission configuration supplied by a trusted operator."""

    installation_id: str
    solution_id: str
    version: str
    repository_id: int
    rules: tuple[RequestRule, ...]
    valid_from: int
    valid_until: int
    schema_version: int = 1

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("unsupported request-policy version")
        for name in ("installation_id", "solution_id", "version"):
            _text(getattr(self, name), name)
        _positive(self.repository_id)
        if (
            not isinstance(self.rules, tuple) or not self.rules
            or not all(isinstance(rule, RequestRule) for rule in self.rules)
            or len({rule.action for rule in self.rules}) != len(self.rules)
        ):
            raise ValueError("unique explicit action rules are required")
        _timestamp(self.valid_from, "valid_from")
        _timestamp(self.valid_until, "valid_until")
        if self.valid_until <= self.valid_from:
            raise ValueError("policy validity must be nonempty")

    def to_json(self) -> str:
        return _canonical(asdict(self))

    @classmethod
    def from_json(cls, value: str) -> RequestPolicy:
        data = _decode(value, cls)
        if not isinstance(data["rules"], list):
            raise ValueError("rules must be a JSON array")
        rules = []
        for value in data["rules"]:
            rule = _object(value, {"action", "permitted_effects"})
            if not isinstance(rule["permitted_effects"], list):
                raise ValueError("effects must be a JSON array")
            rules.append(RequestRule(rule["action"], tuple(rule["permitted_effects"])))
        return cls(**dict(data, rules=tuple(rules)))

    @property
    def digest(self) -> str:
        return sha256_digest(self.to_json().encode("utf-8"))


@dataclass(frozen=True)
class IssueRevision:
    """Trusted private issue snapshot reference; this does not fetch or authenticate it."""

    repository_id: int
    issue_number: int
    repository_private: bool
    revision_digest: str

    def __post_init__(self) -> None:
        _positive(self.repository_id)
        _positive(self.issue_number)
        if type(self.repository_private) is not bool:
            raise ValueError("repository visibility must be explicit")
        _digest(self.revision_digest, "issue revision")


@dataclass(frozen=True)
class RegistryRequest:
    """Frozen issue snapshot and complete existing execution manifest."""

    manifest: ExecutionManifest
    issue: IssueRevision

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, ExecutionManifest) or not isinstance(self.issue, IssueRevision):
            raise ValueError("a typed manifest and issue revision are required")

    def to_json(self) -> str:
        return _canonical(asdict(self))

    @classmethod
    def from_json(cls, value: str) -> RegistryRequest:
        data = _decode(value, cls)
        issue = _object(data["issue"], {item.name for item in fields(IssueRevision)})
        return cls(
            ExecutionManifest.from_json(_canonical(data["manifest"])),
            IssueRevision(**issue),
        )

    @property
    def digest(self) -> str:
        return sha256_digest(self.to_json().encode("utf-8"))


@dataclass(frozen=True)
class RegistrySnapshot:
    """Private last-recorded state, never fresh readiness or execution authority."""

    request: RegistryRequest
    state: str
    reason: str | None


class RegistryDenied(Exception):
    """Closed denial code; no private payload, identifiers or storage paths."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class SQLiteRequestRegistry:
    """Dedicated single-host proposal storage for a privileged trusted service.

    Protect the API, policy inputs and file from agents. Host locking, ACLs,
    backups and actual metadata/policy provenance remain external requirements.
    """

    def __init__(
        self, path: str | Path, *, clock: Callable[[], int] | None = None,
    ) -> None:
        if not str(path) or str(path) == ":memory:":
            raise ValueError("a durable local filesystem path is required")
        self.path = Path(path).resolve()
        if str(self.path).startswith(("\\\\", "//")) or not self.path.parent.is_dir():
            raise ValueError("an existing ordinary local parent is required")
        self._clock = clock or (lambda: time.time_ns() // 1_000_000_000)
        self._identity: tuple[int, int] | None = None
        with self._transaction(initialize=True):
            pass
        self._identity = self._file_identity()

    def _file_identity(self) -> tuple[int, int]:
        try:
            record = self.path.stat()
        except OSError:
            raise RegistryDenied("registry_file_unavailable") from None
        return record.st_dev, record.st_ino

    def _check_identity(self) -> None:
        if self._identity is not None and self._file_identity() != self._identity:
            raise RegistryDenied("registry_file_replaced")

    @contextmanager
    def _transaction(self, *, initialize: bool = False) -> Iterator[sqlite3.Connection]:
        self._check_identity()
        try:
            db = sqlite3.connect(
                self.path.as_uri() + ("?mode=rwc" if initialize else "?mode=rw"),
                timeout=30, isolation_level=None, uri=True,
            )
        except sqlite3.Error:
            raise RegistryDenied("registry_storage_unavailable") from None
        db.row_factory = sqlite3.Row
        try:
            if db.execute("PRAGMA journal_mode").fetchone()[0] != "delete":
                raise RegistryDenied("registry_journal_unsupported")
            db.execute("PRAGMA foreign_keys = ON")
            db.execute("PRAGMA synchronous = FULL")
            db.execute("BEGIN IMMEDIATE")
            self._check_identity()
            application = db.execute("PRAGMA application_id").fetchone()[0]
            version = db.execute("PRAGMA user_version").fetchone()[0]
            schema = {
                row["name"]: row["sql"] for row in db.execute(
                    "SELECT name,sql FROM sqlite_master WHERE sql IS NOT NULL"
                )
            }
            if initialize and application == version == 0 and not schema:
                for statement in _SCHEMA.values():
                    db.execute(statement)
                db.execute(f"PRAGMA application_id = {_APPLICATION_ID}")
                db.execute("PRAGMA user_version = 1")
            elif application != _APPLICATION_ID or version != 1 or schema != _SCHEMA:
                raise RegistryDenied("registry_schema_unsupported")
            yield db
            db.commit()
        except sqlite3.Error:
            db.rollback()
            raise RegistryDenied("registry_storage_unavailable") from None
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _now(self) -> int:
        value = self._clock()
        _timestamp(value, "clock result")
        return value

    @staticmethod
    def _policy(db: sqlite3.Connection, digest: str) -> RequestPolicy:
        row = db.execute("SELECT * FROM policies WHERE digest=?", (digest,)).fetchone()
        if row is None:
            raise RegistryDenied("registry_policy_unavailable")
        try:
            policy = RequestPolicy.from_json(row["payload"])
        except (ValueError, TypeError, RecursionError):
            raise RegistryDenied("registry_policy_corrupt") from None
        if (
            policy.to_json() != row["payload"] or policy.digest != row["digest"]
            or (policy.installation_id, policy.solution_id, policy.version)
            != (row["installation"], row["solution"], row["version"])
        ):
            raise RegistryDenied("registry_policy_corrupt")
        return policy

    @classmethod
    def _current(
        cls, db: sqlite3.Connection, installation: str, solution: str,
    ) -> RequestPolicy:
        row = db.execute(
            "SELECT digest FROM current_policies WHERE installation=? AND solution=?",
            (installation, solution),
        ).fetchone()
        if row is None:
            raise RegistryDenied("registry_policy_unavailable")
        policy = cls._policy(db, row["digest"])
        if (policy.installation_id, policy.solution_id) != (installation, solution):
            raise RegistryDenied("registry_policy_corrupt")
        return policy

    @staticmethod
    def _request(db: sqlite3.Connection, request_id: str) -> RegistrySnapshot:
        row = db.execute(
            "SELECT * FROM registry_requests WHERE request_id=?", (request_id,),
        ).fetchone()
        if row is None:
            raise RegistryDenied("registry_request_unknown")
        try:
            request = RegistryRequest.from_json(row["payload"])
        except (ValueError, TypeError, RecursionError):
            raise RegistryDenied("registry_request_corrupt") from None
        if (
            request.to_json() != row["payload"] or request.digest != row["digest"]
            or request.manifest.request_id != row["request_id"]
            or request.manifest.policy_digest != row["policy_digest"]
            or row["state"] not in ("proposed", "invalidated", "revoked")
            or (row["state"] == "proposed" and row["reason"] is not None)
            or (row["state"] == "invalidated" and row["reason"] not in _INVALIDATIONS)
            or (row["state"] == "revoked" and row["reason"] != "registry_revoked")
        ):
            raise RegistryDenied("registry_request_corrupt")
        return RegistrySnapshot(request, row["state"], row["reason"])

    @staticmethod
    def _require_proposed(snapshot: RegistrySnapshot) -> None:
        if snapshot.state != "proposed":
            if snapshot.reason is None:
                raise RegistryDenied("registry_request_corrupt")
            raise RegistryDenied(snapshot.reason)

    @staticmethod
    def _admission(request: RegistryRequest, policy: RequestPolicy, now: int) -> str | None:
        manifest, issue = request.manifest, request.issue
        if not issue.repository_private or issue.repository_id != policy.repository_id:
            return "registry_route_changed"
        if (
            (manifest.installation_id, manifest.solution_id)
            != (policy.installation_id, policy.solution_id)
            or manifest.policy_digest != policy.digest
        ):
            return "registry_policy_changed"
        if now < max(manifest.created_at, policy.valid_from):
            return "registry_not_yet_valid"
        if now >= min(manifest.expires_at, policy.valid_until):
            return "registry_expired"
        if manifest.expires_at > policy.valid_until:
            return "registry_request_outlives_policy"
        rule = next((rule for rule in policy.rules if rule.action == manifest.action), None)
        if rule is None:
            return "registry_action_not_allowed"
        if not set(manifest.permitted_effects).issubset(rule.permitted_effects):
            return "registry_effects_not_allowed"
        return None

    def register_policy(self, policy: RequestPolicy) -> str:
        """Register a new immutable current version and invalidate older proposals."""
        if not isinstance(policy, RequestPolicy):
            raise ValueError("a typed request policy is required")
        with self._transaction() as db:
            if not policy.valid_from <= self._now() < policy.valid_until:
                raise RegistryDenied("registry_policy_not_current")
            try:
                db.execute(
                    "INSERT INTO policies VALUES (?,?,?,?,?)",
                    (policy.digest, policy.to_json(), policy.installation_id,
                     policy.solution_id, policy.version),
                )
            except sqlite3.IntegrityError:
                raise RegistryDenied("registry_policy_version_reused") from None
            db.execute(
                "UPDATE registry_requests SET state='invalidated',reason='registry_policy_changed' "
                "WHERE state='proposed' AND policy_digest IN "
                "(SELECT digest FROM policies WHERE installation=? AND solution=?)",
                (policy.installation_id, policy.solution_id),
            )
            db.execute(
                "INSERT INTO current_policies VALUES (?,?,?) "
                "ON CONFLICT(installation,solution) DO UPDATE SET digest=excluded.digest",
                (policy.installation_id, policy.solution_id, policy.digest),
            )
        return policy.digest

    def revoke_policy(self, policy_digest: str) -> None:
        """Revoke only the current version, retaining all immutable history."""
        _digest(policy_digest, "policy digest")
        with self._transaction() as db:
            policy = self._policy(db, policy_digest)
            if self._current(db, policy.installation_id, policy.solution_id).digest != policy_digest:
                raise RegistryDenied("registry_policy_not_current")
            db.execute("DELETE FROM current_policies WHERE digest=?", (policy_digest,))
            db.execute(
                "UPDATE registry_requests SET state='invalidated',reason='registry_policy_revoked' "
                "WHERE state='proposed' AND policy_digest=?", (policy_digest,),
            )

    def register(self, request: RegistryRequest) -> str:
        """Admit one proposed immutable request, without approval or source access."""
        if not isinstance(request, RegistryRequest):
            raise ValueError("a typed registry request is required")
        manifest = request.manifest
        with self._transaction() as db:
            policy = self._current(db, manifest.installation_id, manifest.solution_id)
            denial = self._admission(request, policy, self._now())
            if denial:
                raise RegistryDenied(denial)
            try:
                db.execute(
                    "INSERT INTO registry_requests VALUES (?,?,?,?,'proposed',NULL)",
                    (manifest.request_id, request.to_json(), request.digest, policy.digest),
                )
            except sqlite3.IntegrityError:
                raise RegistryDenied("registry_request_reused") from None
        return request.digest

    def revalidate(self, current: RegistryRequest) -> RegistrySnapshot:
        """Check fresh trusted observations, committing drift/expiry before denial."""
        if not isinstance(current, RegistryRequest):
            raise ValueError("a typed registry request is required")
        with self._transaction() as db:
            result = self._revalidate_in_transaction(db, current)
        if isinstance(result, str):
            raise RegistryDenied(result)
        return result

    def _revalidate_in_transaction(
        self, db: sqlite3.Connection, current: RegistryRequest, *, now: int | None = None,
    ) -> RegistrySnapshot | str:
        """Return durable denial to the owner; operational failures still raise."""
        snapshot = self._request(db, current.manifest.request_id)
        if snapshot.state != "proposed":
            if snapshot.reason is None:
                raise RegistryDenied("registry_request_corrupt")
            return snapshot.reason
        frozen = snapshot.request
        policy = self._current(db, frozen.manifest.installation_id, frozen.manifest.solution_id)
        now = self._now() if now is None else now
        _timestamp(now, "clock result")
        denial = self._admission(frozen, policy, now)
        if denial is None and frozen.digest != current.digest:
            denial = (
                "registry_route_changed"
                if frozen.issue.repository_id != current.issue.repository_id
                or frozen.issue.repository_private != current.issue.repository_private
                else "registry_request_changed"
            )
        if denial:
            db.execute(
                "UPDATE registry_requests SET state='invalidated',reason=? WHERE request_id=?",
                (denial, current.manifest.request_id),
            )
            return denial
        return snapshot

    def revoke(self, request_id: str) -> None:
        """Permanently revoke a proposed request; no grant cancellation is performed."""
        with self._transaction() as db:
            snapshot = self._request(db, request_id)
            self._require_proposed(snapshot)
            db.execute(
                "UPDATE registry_requests SET state='revoked',reason='registry_revoked' "
                "WHERE request_id=?", (request_id,),
            )

    def inspect(self, request_id: str) -> RegistrySnapshot:
        """Read private last-recorded state, not a current authorization result."""
        with self._transaction() as db:
            snapshot = self._request(db, request_id)
            self._policy(db, snapshot.request.manifest.policy_digest)
            return snapshot
