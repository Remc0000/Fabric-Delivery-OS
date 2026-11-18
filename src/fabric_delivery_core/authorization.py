"""Trusted-caller primitives for immutable, one-attempt authorization.

The caller must authenticate native human approval and current installation policy.
Possession of these Python objects is not evidence of either.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Callable, Iterator
from uuid import UUID, uuid4


_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")


def sha256_digest(content: bytes) -> str:
    """Hash actual input bytes using the library's explicit digest format."""
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _text(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be a nonempty, trimmed string")


def _digest(value: object, name: str) -> None:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase sha256 digest")


def _timestamp(value: object, name: str) -> None:
    if type(value) is not int or not 0 <= value <= 2**63 - 1:
        raise ValueError(f"{name} must be a nonnegative signed-64-bit Unix second")


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class ExecutionManifest:
    """A version-1 frozen request; all revisions are content digests, not refs.

    Digests may identify compound private snapshots (for example the execution
    profile includes model deployment, region, bounds, and tool permissions).
    Effects are explicit policy-defined tokens with no implicit permissions.
    """

    request_id: str
    installation_id: str
    solution_id: str
    action: str
    input_digest: str
    artifact_digest: str | None
    target_baseline_digest: str
    environment: str | None
    policy_digest: str
    execution_profile_digest: str
    framework_digest: str
    control_workflow_digest: str
    tool_snapshot_digest: str
    skill_snapshot_digest: str
    permitted_effects: tuple[str, ...]
    created_at: int
    expires_at: int
    schema_version: int = 1

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("unsupported manifest schema_version")
        if not isinstance(self.request_id, str):
            raise ValueError("request_id must be a canonical UUID4")
        try:
            identifier = UUID(self.request_id)
        except ValueError as exc:
            raise ValueError("request_id must be a canonical UUID4") from exc
        if identifier.version != 4 or str(identifier) != self.request_id:
            raise ValueError("request_id must be a canonical UUID4")
        for name in ("installation_id", "solution_id", "action"):
            _text(getattr(self, name), name)
        if self.environment is not None:
            _text(self.environment, "environment")
        for field in fields(self):
            if field.name.endswith("_digest"):
                value = getattr(self, field.name)
                if field.name == "artifact_digest" and value is None:
                    continue
                _digest(value, field.name)
        if self.action == "deploy" and (
            self.environment is None or self.artifact_digest is None
        ):
            raise ValueError("deploy requires an environment and artifact digest")
        if not isinstance(self.permitted_effects, tuple) or not self.permitted_effects:
            raise ValueError("permitted_effects must be a nonempty tuple")
        for effect in self.permitted_effects:
            _text(effect, "permitted effect")
        if len(set(self.permitted_effects)) != len(self.permitted_effects):
            raise ValueError("permitted effects must be unique")
        _timestamp(self.created_at, "created_at")
        _timestamp(self.expires_at, "expires_at")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be later than created_at")

    def to_json(self) -> str:
        """Return the versioned canonical serialization used for binding."""
        return _canonical(asdict(self))

    @classmethod
    def from_json(cls, value: str) -> ExecutionManifest:
        """Read a strict manifest, rejecting duplicate, unknown, or missing keys."""
        def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
            result: dict[str, object] = {}
            for key, item in pairs:
                if key in result:
                    raise ValueError("duplicate manifest key")
                result[key] = item
            return result

        data = json.loads(value, object_pairs_hook=unique_object)
        if not isinstance(data, dict) or set(data) != {f.name for f in fields(cls)}:
            raise ValueError("manifest keys must match schema version 1")
        if not isinstance(data["permitted_effects"], list):
            raise ValueError("permitted_effects must be a JSON array")
        data["permitted_effects"] = tuple(data["permitted_effects"])
        return cls(**data)

    @property
    def digest(self) -> str:
        """Return the SHA-256 binding of the complete canonical manifest."""
        return sha256_digest(self.to_json().encode("utf-8"))


@dataclass(frozen=True)
class ApprovalBinding:
    """Evidence references supplied ONLY by an authenticated trusted adapter.

    The adapter verifies the human, role, gate settings, federation identity,
    immutable repository ID, workflow revision, run/attempt, and environment.
    This value does not verify a token, signature, approval, or reviewer itself.
    """

    manifest_digest: str
    control_repository_id: str
    control_workflow_digest: str
    run_id: str
    run_attempt: int
    gate_environment: str
    approval_evidence_digest: str
    approved_at: int
    expires_at: int

    def __post_init__(self) -> None:
        for name in (
            "manifest_digest", "control_workflow_digest", "approval_evidence_digest"
        ):
            _digest(getattr(self, name), name)
        for name in ("control_repository_id", "run_id", "gate_environment"):
            _text(getattr(self, name), name)
        if type(self.run_attempt) is not int or self.run_attempt < 1:
            raise ValueError("run_attempt must be a positive integer")
        _timestamp(self.approved_at, "approved_at")
        _timestamp(self.expires_at, "expires_at")
        if self.expires_at <= self.approved_at:
            raise ValueError("approval expiry must follow approved_at")

    def to_json(self) -> str:
        return _canonical(asdict(self))


@dataclass(frozen=True)
class ExecutionReceipt:
    """Persisted claim identity, not a credential and not proof a worker started."""

    request_id: str
    manifest_digest: str
    execution_id: str
    consumed_at: int


class AuthorizationDenied(Exception):
    """A closed denial code; messages never embed private request values."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class SQLiteAuthorizationStore:
    """Durable local-file request/grant store for a trusted service.

    Separate connections and BEGIN IMMEDIATE serialize competing processes.
    Use a private, persistent local filesystem with working SQLite locks/fsync,
    access controls, and protected backups. Not a multi-host/cloud state store.
    Every method is privileged; do not expose this object or its file to agents.
    """

    def __init__(
        self, path: str | Path, *, clock: Callable[[], int] | None = None
    ) -> None:
        if str(path) == ":memory:" or not str(path):
            raise ValueError("a durable filesystem path is required")
        self.path = Path(path).resolve()
        if not self.path.parent.is_dir():
            raise ValueError("database parent directory must already exist")
        self._clock = clock or (lambda: time.time_ns() // 1_000_000_000)
        with self._transaction() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("unsupported authorization database version")
            application = db.execute("PRAGMA application_id").fetchone()[0]
            tables = {
                row[0] for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%'"
                )
            }
            if application != 0 or tables != (set() if version == 0 else {"requests"}):
                raise ValueError("unsupported authorization database")
            if version == 1 and {
                row[1] for row in db.execute("PRAGMA table_info(requests)")
            } != {
                "request_id", "manifest", "digest", "state", "approval",
                "approval_key", "execution_id", "consumed_at", "denial_reason",
            }:
                raise ValueError("unsupported authorization database")
            if version == 0:
                db.execute(
                    """CREATE TABLE requests (
                        request_id TEXT PRIMARY KEY,
                        manifest TEXT NOT NULL,
                        digest TEXT NOT NULL,
                        state TEXT NOT NULL CHECK (
                            state IN ('pending','authorized','consumed','revoked','invalidated')
                        ),
                        approval TEXT,
                        approval_key TEXT UNIQUE,
                        execution_id TEXT UNIQUE,
                        consumed_at INTEGER,
                        denial_reason TEXT
                    )"""
                )
                db.execute("PRAGMA user_version = 1")

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA synchronous = FULL")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _now(self) -> int:
        now = self._clock()
        _timestamp(now, "clock result")
        return now

    @staticmethod
    def _request(db: sqlite3.Connection, request_id: str) -> sqlite3.Row:
        row = db.execute(
            "SELECT * FROM requests WHERE request_id = ?", (request_id,)
        ).fetchone()
        if row is None:
            raise AuthorizationDenied("unknown_request")
        if sha256_digest(row["manifest"].encode("utf-8")) != row["digest"]:
            raise AuthorizationDenied("stored_manifest_mismatch")
        return row

    @staticmethod
    def _require_state(row: sqlite3.Row, state: str) -> None:
        if row["state"] != state:
            raise AuthorizationDenied(row["denial_reason"] or row["state"])

    def freeze(self, manifest: ExecutionManifest) -> str:
        """Persist a new pending request; IDs can never be replaced or reused."""
        with self._transaction() as db:
            now = self._now()
            if not manifest.created_at <= now < manifest.expires_at:
                raise AuthorizationDenied("request_not_valid")
            try:
                db.execute(
                    "INSERT INTO requests(request_id,manifest,digest,state) "
                    "VALUES (?,?,?,'pending')",
                    (manifest.request_id, manifest.to_json(), manifest.digest),
                )
            except sqlite3.IntegrityError as exc:
                raise AuthorizationDenied("duplicate_request") from exc
        return manifest.digest

    def authorize(self, request_id: str, approval: ApprovalBinding) -> None:
        """Record an externally verified gate; never infer approval from a request."""
        with self._transaction() as db:
            row = self._request(db, request_id)
            self._require_state(row, "pending")
            manifest = ExecutionManifest.from_json(row["manifest"])
            now = self._now()
            if not manifest.created_at <= approval.approved_at <= now:
                raise AuthorizationDenied("approval_not_valid")
            if not now < approval.expires_at <= manifest.expires_at:
                raise AuthorizationDenied("approval_not_valid")
            if (
                approval.manifest_digest != row["digest"]
                or approval.control_workflow_digest != manifest.control_workflow_digest
            ):
                raise AuthorizationDenied("approval_mismatch")
            # One protected gate/run attempt cannot authorize a second request.
            key = _canonical(
                [
                    approval.control_repository_id, approval.run_id,
                    approval.run_attempt, approval.gate_environment,
                ]
            )
            try:
                db.execute(
                    "UPDATE requests SET state='authorized',approval=?,approval_key=? "
                    "WHERE request_id=?",
                    (approval.to_json(), key, request_id),
                )
            except sqlite3.IntegrityError as exc:
                raise AuthorizationDenied("approval_replayed") from exc

    def revoke(self, request_id: str) -> None:
        """Permanently revoke an unconsumed request; never undo consumption."""
        with self._transaction() as db:
            row = self._request(db, request_id)
            if row["state"] == "consumed":
                raise AuthorizationDenied("consumed")
            db.execute(
                "UPDATE requests SET state='revoked',denial_reason='revoked' "
                "WHERE request_id=?", (request_id,)
            )

    def consume(
        self, current_manifest: ExecutionManifest, approval: ApprovalBinding
    ) -> ExecutionReceipt:
        """Atomically burn a grant against fresh, trusted observations.

        The caller must rebuild current digests from actual bytes, policy, and
        target state, and reverify the protected control callback. Any drift
        permanently invalidates the old request. Expiry is checked after locking.
        No worker launch occurs here; a crash after commit burns the grant.
        """
        denial = None
        with self._transaction() as db:
            row = self._request(db, current_manifest.request_id)
            self._require_state(row, "authorized")
            frozen = ExecutionManifest.from_json(row["manifest"])
            now = self._now()
            if now < frozen.created_at or now < approval.approved_at:
                denial = "not_yet_valid"
            elif now >= min(frozen.expires_at, json.loads(row["approval"])["expires_at"]):
                denial = "expired"
            elif frozen.policy_digest != current_manifest.policy_digest:
                denial = "policy_changed"
            elif frozen.target_baseline_digest != current_manifest.target_baseline_digest:
                denial = "target_changed"
            elif frozen.execution_profile_digest != current_manifest.execution_profile_digest:
                denial = "execution_profile_changed"
            elif row["digest"] != current_manifest.digest:
                denial = "request_mismatch"
            elif row["approval"] != approval.to_json():
                denial = "approval_mismatch"
            if denial:
                db.execute(
                    "UPDATE requests SET state='invalidated',denial_reason=? "
                    "WHERE request_id=?", (denial, frozen.request_id)
                )
            else:
                receipt = ExecutionReceipt(
                    frozen.request_id, frozen.digest, str(uuid4()), now
                )
                db.execute(
                    "UPDATE requests SET state='consumed',execution_id=?,consumed_at=? "
                    "WHERE request_id=?",
                    (receipt.execution_id, receipt.consumed_at, receipt.request_id),
                )
        if denial:
            raise AuthorizationDenied(denial)
        return receipt

    def receipt(self, request_id: str) -> ExecutionReceipt | None:
        """Read a committed claim after restart; never reauthorize or relaunch it."""
        with self._transaction() as db:
            row = self._request(db, request_id)
            if row["state"] != "consumed":
                return None
            return ExecutionReceipt(
                request_id, row["digest"], row["execution_id"], row["consumed_at"]
            )
