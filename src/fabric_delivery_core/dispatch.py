"""Single-host atomic grant/reservation/outbox coordination for trusted callers.

No evidence is authenticated and no worker or external API is invoked here.
All three files and this API must remain outside agent control.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sqlite3
import time
from typing import Callable, Iterator
from uuid import uuid4

from .authorization import (
    ApprovalBinding, AuthorizationDenied, ExecutionManifest, ExecutionReceipt,
    SQLiteAuthorizationStore, _canonical, _digest, _text, _timestamp, sha256_digest,
)
from .spend import (
    SQLiteSpendStore, SpendDenied, _APPLICATION_ID as _SPEND_ID,
    _currency, _integer, _period,
)


_APPLICATION_ID = 0x46444451
_COLUMNS = {
    "request_id", "execution_id", "manifest_digest", "approval", "profile",
    "profile_digest", "reservation_id", "execution_digest", "deadline", "state",
    "claim_id", "claimed_at", "finished_at", "result_digest", "reason",
}
_DISPATCH_DDL = """CREATE TABLE dispatches (
                        request_id TEXT PRIMARY KEY, execution_id TEXT UNIQUE NOT NULL,
                        manifest_digest TEXT NOT NULL, approval TEXT NOT NULL,
                        profile TEXT NOT NULL, profile_digest TEXT NOT NULL,
                        reservation_id TEXT UNIQUE NOT NULL,
                        execution_digest TEXT UNIQUE NOT NULL, deadline INTEGER NOT NULL,
                        state TEXT NOT NULL CHECK(state IN
                            ('ready','claimed','succeeded','failed','breach',
                             'blocked','cancelled','unknown')),
                        claim_id TEXT UNIQUE, claimed_at INTEGER, finished_at INTEGER,
                        result_digest TEXT, reason TEXT{registry_column}
                    )"""


def _dispatch_schema(*, registry_bound: bool = False) -> dict[str, str]:
    return {"dispatches": _DISPATCH_DDL.format(
        registry_column=", registry_digest TEXT NOT NULL" if registry_bound else "",
    )}


def _validate_schema(
    db: sqlite3.Connection, schema: str, application: int, version: int,
    expected: dict[str, str],
) -> None:
    """Validate fixed internal schemas, including constraints and explicit indexes."""
    if (
        db.execute(f"PRAGMA {schema}.application_id").fetchone()[0] != application
        or db.execute(f"PRAGMA {schema}.user_version").fetchone()[0] != version
        or {
            row[0]: row[1] for row in db.execute(
                f"SELECT name,sql FROM {schema}.sqlite_master WHERE sql IS NOT NULL"
            )
        } != expected
    ):
        raise DispatchDenied("unsupported_dispatch_database")


@dataclass(frozen=True)
class DispatchProfile:
    """Approved execution profile including immutable worker and cost snapshots.

    ``worker_digest`` identifies a fixed reviewed worker/runtime configuration,
    not an executable path or an agent-selected shell command.
    """

    worker_digest: str
    budget_digest: str
    price_digest: str
    operation: str
    price_version: str
    period: str
    currency: str
    max_tokens: int
    max_calls: int
    max_runtime_seconds: int

    def __post_init__(self) -> None:
        for name in ("worker_digest", "budget_digest", "price_digest"):
            _digest(getattr(self, name), name)
        _text(self.operation, "operation")
        _text(self.price_version, "price_version")
        _period(self.period)
        _currency(self.currency)
        _integer(self.max_tokens, "max_tokens")
        _integer(self.max_calls, "max_calls", 1)
        _integer(self.max_runtime_seconds, "max_runtime_seconds", 1)

    def to_json(self) -> str:
        return _canonical(asdict(self))

    @property
    def digest(self) -> str:
        return sha256_digest(self.to_json().encode("utf-8"))


@dataclass(frozen=True)
class DispatchClaim:
    """Private one-attempt identity, not a credential or permission to relaunch."""

    request_id: str
    execution_id: str
    claim_id: str
    manifest_digest: str
    profile_digest: str
    deadline: int


class DispatchDenied(Exception):
    """Closed failure reason without private input or provider errors."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class SQLiteDispatchStore:
    """Atomic local outbox over the existing authorization and spend stores.

    SQLite super-journal atomicity requires durable distinct files on one local
    filesystem with reliable locks/fsync and DELETE journals. WAL, memory,
    unrelated schemas and cross-device paths are refused, not reconfigured.
    Host storage, file ACLs and exclusive trusted-service ownership are operator
    prerequisites; this is not a distributed queue or exactly-once effect API.
    """

    def __init__(
        self, path: str | Path, authorization: SQLiteAuthorizationStore,
        spend: SQLiteSpendStore, *, clock: Callable[[], int] | None = None,
    ) -> None:
        if not str(path) or str(path) == ":memory:":
            raise ValueError("a durable filesystem path is required")
        self.path = Path(path).resolve()
        self.authorization = authorization
        self.spend = spend
        self._clock = clock or (lambda: time.time_ns() // 1_000_000_000)
        paths = (self.path, authorization.path, spend.path)
        if len(set(paths)) != 3 or any(
            str(item).startswith(("\\\\", "//")) for item in paths
        ):
            raise ValueError("distinct ordinary local database paths are required")
        if not self.path.parent.is_dir() or any(not item.is_file() for item in paths[1:]):
            raise ValueError("existing local ledger files and outbox parent are required")
        if len({item.parent.stat().st_dev for item in paths}) != 1:
            raise ValueError("all databases must use the same local filesystem")
        with self._transaction(initialize=True):
            pass

    @contextmanager
    def _transaction(self, *, initialize: bool = False) -> Iterator[sqlite3.Connection]:
        target = self.path.as_uri() + ("?mode=rwc" if initialize else "?mode=rw")
        db = sqlite3.connect(target, timeout=30, isolation_level=None, uri=True)
        db.row_factory = sqlite3.Row
        try:
            for schema, path in (
                ("authorization", self.authorization.path), ("spend", self.spend.path),
            ):
                db.execute(
                    f"ATTACH DATABASE ? AS {schema}", (path.as_uri() + "?mode=rw",)
                )
            for schema in ("main", "authorization", "spend"):
                if db.execute(f"PRAGMA {schema}.journal_mode").fetchone()[0] != "delete":
                    raise DispatchDenied("unsupported_journal_mode")
                db.execute(f"PRAGMA {schema}.synchronous = FULL")
            db.execute("BEGIN IMMEDIATE")
            self._schema(db, "authorization", 0, {"requests"})
            self._schema(db, "spend", _SPEND_ID, {"budgets", "prices", "freezes", "reservations"})
            app = db.execute("PRAGMA main.application_id").fetchone()[0]
            version = db.execute("PRAGMA main.user_version").fetchone()[0]
            tables = db.execute("SELECT name FROM main.sqlite_master WHERE type='table'").fetchall()
            if initialize and app == version == 0 and not tables:
                db.execute(_dispatch_schema()["dispatches"])
                db.execute(f"PRAGMA main.application_id = {_APPLICATION_ID}")
                db.execute("PRAGMA main.user_version = 1")
            self._schema(db, "main", _APPLICATION_ID, {"dispatches"})
            if {row[1] for row in db.execute("PRAGMA main.table_info(dispatches)")} != _COLUMNS:
                raise DispatchDenied("unsupported_dispatch_database")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _schema(
        db: sqlite3.Connection, schema: str, application: int, tables: set[str],
    ) -> None:
        if (
            db.execute(f"PRAGMA {schema}.application_id").fetchone()[0] != application
            or db.execute(f"PRAGMA {schema}.user_version").fetchone()[0] != 1
            or {
                row[0] for row in db.execute(
                    f"SELECT name FROM {schema}.sqlite_master WHERE type='table'"
                )
            } != tables
        ):
            raise DispatchDenied("unsupported_dispatch_database")

    def _now(self) -> int:
        now = self._clock()
        _timestamp(now, "clock result")
        return now

    def enqueue(
        self, current_manifest: ExecutionManifest, approval: ApprovalBinding,
        profile: DispatchProfile,
    ) -> ExecutionReceipt:
        """Commit consumption, maximum reservation and ready record together.

        Fresh input/policy/target and human identity verification are external.
        Spend/config/storage failures roll back all three writes. Authorization
        drift is instead permanently committed before its denial is raised.
        """
        with self._transaction() as db:
            result = self._enqueue_in_transaction(db, current_manifest, approval, profile)
        if isinstance(result, str):
            raise AuthorizationDenied(result)
        return result

    def _enqueue_in_transaction(
        self, db: sqlite3.Connection, current_manifest: ExecutionManifest,
        approval: ApprovalBinding, profile: DispatchProfile, *,
        registry_digest: str | None = None, now: int | None = None,
    ) -> ExecutionReceipt | str:
        """Caller commits authorization denials; other failures roll back."""
        result = self.authorization._consume_in_transaction(
            db, current_manifest, approval, **({} if now is None else {"now": now}),
        )
        if isinstance(result, str):
            return result
        if profile.digest != current_manifest.execution_profile_digest:
            raise DispatchDenied("profile_mismatch")
        reservation_id = str(uuid4())
        execution_digest = sha256_digest(_canonical(asdict(result)).encode("utf-8"))
        reservation = self.spend._reserve_in_transaction(
            db, reservation_id=reservation_id,
            installation_id=current_manifest.installation_id,
            period=profile.period, currency=profile.currency,
            execution_digest=execution_digest, operation=profile.operation,
            price_version=profile.price_version, max_tokens=profile.max_tokens,
            max_calls=profile.max_calls,
            **({} if now is None else {"now": now}),
        )
        if (
            reservation["budget_digest"] != profile.budget_digest
            or reservation["price_digest"] != profile.price_digest
        ):
            raise DispatchDenied("spend_snapshot_mismatch")
        deadline = min(current_manifest.expires_at, approval.expires_at, reservation["deadline"])
        if not (self._now() if now is None else now) < deadline:
            raise DispatchDenied("dispatch_expired")
        values = (
            result.request_id, result.execution_id, result.manifest_digest,
            approval.to_json(), profile.to_json(), profile.digest,
            reservation_id, execution_digest, deadline,
        )
        extra_column = ",registry_digest" if registry_digest is not None else ""
        extra_value = ",?" if registry_digest is not None else ""
        if registry_digest is not None:
            _digest(registry_digest, "registry_digest")
            values += (registry_digest,)
        db.execute(
            "INSERT INTO dispatches "
            "(request_id,execution_id,manifest_digest,approval,profile,"
            "profile_digest,reservation_id,execution_digest,deadline" + extra_column + ",state) "
            "VALUES (?,?,?,?,?,?,?,?,?" + extra_value + ",'ready')",
            values,
        )
        return result

    @staticmethod
    def _job(db: sqlite3.Connection, request_id: str) -> sqlite3.Row:
        row = db.execute("SELECT * FROM dispatches WHERE request_id=?", (request_id,)).fetchone()
        if row is None:
            raise DispatchDenied("unknown_dispatch")
        return row

    def claim(
        self, current_manifest: ExecutionManifest, approval: ApprovalBinding,
        profile: DispatchProfile,
    ) -> DispatchClaim:
        """Claim once against fresh trusted bindings; never retry a claimed job.

        A crash after this commit is ambiguous, including before worker launch.
        Inspect/reconcile it; do not requeue, refund or launch from a receipt.
        """
        with self._transaction() as db:
            result = self._claim_in_transaction(db, current_manifest, approval, profile)
        if isinstance(result, str):
            raise DispatchDenied(result)
        return result

    def _claim_in_transaction(
        self, db: sqlite3.Connection, current_manifest: ExecutionManifest,
        approval: ApprovalBinding, profile: DispatchProfile, *,
        registry_digest: str | None = None, now: int | None = None,
    ) -> DispatchClaim | str:
        """Caller commits blocked denials before raising them."""
        row = self._job(db, current_manifest.request_id)
        if row["state"] != "ready":
            raise DispatchDenied("dispatch_not_ready")
        request = self.authorization._request(db, current_manifest.request_id)
        reservation = db.execute(
            "SELECT * FROM reservations WHERE id=?", (row["reservation_id"],)
        ).fetchone()
        now = self._now() if now is None else now
        _timestamp(now, "clock result")
        denial = None
        if (
            request["state"] != "consumed"
            or request["execution_id"] != row["execution_id"]
            or request["digest"] != row["manifest_digest"]
            or request["approval"] != row["approval"]
            or row["manifest_digest"] != current_manifest.digest
            or row["approval"] != approval.to_json()
            or row["profile"] != profile.to_json()
            or row["profile_digest"] != profile.digest
            or profile.digest != current_manifest.execution_profile_digest
            or (registry_digest is not None and row["registry_digest"] != registry_digest)
        ):
            denial = "dispatch_binding_changed"
        elif now < request["consumed_at"] or now >= row["deadline"]:
            denial = "dispatch_expired"
        elif db.execute(
            "SELECT 1 FROM freezes WHERE installation=?", (current_manifest.installation_id,)
        ).fetchone():
            denial = "installation_frozen"
        elif (
            reservation is None or reservation["state"] != "reserved"
            or reservation["execution_digest"] != row["execution_digest"]
            or reservation["installation"] != current_manifest.installation_id
            or reservation["budget_digest"] != profile.budget_digest
            or reservation["price_digest"] != profile.price_digest
            or reservation["max_tokens"] != profile.max_tokens
            or reservation["max_calls"] != profile.max_calls
            or now >= reservation["deadline"]
        ):
            denial = "reservation_not_current"
        if denial:
            db.execute(
                "UPDATE dispatches SET state='blocked',reason=? WHERE request_id=?",
                (denial, current_manifest.request_id),
            )
            return denial
        claim = DispatchClaim(
            row["request_id"], row["execution_id"], str(uuid4()),
            row["manifest_digest"], row["profile_digest"],
            min(row["deadline"], now + profile.max_runtime_seconds),
        )
        db.execute(
            """UPDATE dispatches SET state='claimed',claim_id=?,claimed_at=?,
                deadline=? WHERE request_id=?""",
            (claim.claim_id, now, claim.deadline, claim.request_id),
        )
        return claim

    def cancel(self, request_id: str) -> None:
        """Privileged pre-claim cancellation; never restore a grant or release cost."""
        with self._transaction() as db:
            row = self._job(db, request_id)
            if row["state"] != "ready":
                raise DispatchDenied("dispatch_not_ready")
            db.execute(
                "UPDATE dispatches SET state='cancelled',reason='cancelled' WHERE request_id=?",
                (request_id,),
            )

    def _claimed(self, db: sqlite3.Connection, claim: DispatchClaim) -> sqlite3.Row:
        row = self._job(db, claim.request_id)
        if row["state"] != "claimed":
            raise DispatchDenied("dispatch_not_claimed")
        if (
            row["execution_id"], row["claim_id"], row["manifest_digest"],
            row["profile_digest"], row["deadline"],
        ) != (
            claim.execution_id, claim.claim_id, claim.manifest_digest,
            claim.profile_digest, claim.deadline,
        ):
            raise DispatchDenied("claim_mismatch")
        return row

    def mark_unknown(self, claim: DispatchClaim) -> None:
        """Persist ambiguous worker outcome without settling or freeing its reserve."""
        with self._transaction() as db:
            self._claimed(db, claim)
            db.execute(
                "UPDATE dispatches SET state='unknown',reason='worker_outcome_unknown' "
                "WHERE request_id=?", (claim.request_id,),
            )

    def finish(
        self, claim: DispatchClaim, *, succeeded: bool, result_digest: str,
        actual_units: int, actual_tokens: int, actual_calls: int,
    ) -> None:
        """Atomically persist trusted final usage and terminal state, including breach.

        Never supply agent-reported or partial usage. A real adapter must enforce
        the deadline during execution; this store only refuses late success.
        """
        if type(succeeded) is not bool:
            raise ValueError("succeeded must be an explicit boolean")
        _digest(result_digest, "result_digest")
        with self._transaction() as db:
            row = self._claimed(db, claim)
            manifest = ExecutionManifest.from_json(
                self.authorization._request(db, claim.request_id)["manifest"]
            )
            profile = DispatchProfile(**json.loads(row["profile"]))
            breach = self.spend._settle_in_transaction(
                db, reservation_id=row["reservation_id"], installation_id=manifest.installation_id,
                period=profile.period, currency=profile.currency,
                execution_digest=row["execution_digest"], actual_units=actual_units,
                actual_tokens=actual_tokens, actual_calls=actual_calls,
            )
            now = self._now()
            late = now < row["claimed_at"] or now >= row["deadline"]
            state = "breach" if breach else "succeeded" if succeeded and not late else "failed"
            reason = (
                "settlement_breach" if breach else "worker_deadline_exceeded" if late else
                None if succeeded else "worker_failed"
            )
            db.execute(
                "UPDATE dispatches SET state=?,reason=?,finished_at=?,result_digest=? "
                "WHERE request_id=?",
                (state, reason, now, result_digest, claim.request_id),
            )
        if breach:
            raise SpendDenied("settlement_breach")
        if late:
            raise DispatchDenied("worker_deadline_exceeded")

    def receipt(self, request_id: str) -> dict[str, object]:
        """Private inspection only; no receipt or terminal state permits relaunch."""
        with self._transaction() as db:
            return dict(self._job(db, request_id))
