"""Offline four-file coordination; no human verification or worker activation."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
import sqlite3
import stat
import time
from typing import Callable, Iterator

from .authorization import (
    ApprovalBinding, AuthorizationDenied, ExecutionReceipt, SQLiteAuthorizationStore,
    _SCHEMA as _AUTH_SCHEMA,
)
from .dispatch import (
    DispatchClaim, DispatchDenied, DispatchProfile, SQLiteDispatchStore,
    _APPLICATION_ID as _DISPATCH_ID, _dispatch_schema, _validate_schema,
)
from .request_registry import (
    RegistryDenied, RegistryRequest, SQLiteRequestRegistry,
    _APPLICATION_ID as _REGISTRY_ID, _SCHEMA as _REGISTRY_SCHEMA,
)
from .spend import (
    SQLiteSpendStore, _APPLICATION_ID as _SPEND_ID, _SCHEMA as _SPEND_SCHEMA,
)


class SQLiteRegistryDispatchStore(SQLiteDispatchStore):
    """Privileged offline coordinator over existing registry, grant and cost files.

    Version 2 is deliberately not a legacy dispatch outbox. Host ACLs, ownership,
    reliable local storage and historical rollback/rewrite detection are external
    prerequisites. Digests bind supplied snapshots, not authenticated contents.
    """

    def __init__(
        self, path: str | Path, registry: SQLiteRequestRegistry,
        authorization: SQLiteAuthorizationStore, spend: SQLiteSpendStore, *,
        clock: Callable[[], int] | None = None,
    ) -> None:
        if (
            not isinstance(registry, SQLiteRequestRegistry)
            or not isinstance(authorization, SQLiteAuthorizationStore)
            or not isinstance(spend, SQLiteSpendStore)
            or not isinstance(path, (str, Path)) or not str(path)
            or str(path) == ":memory:" or str(path).startswith(("\\\\", "//"))
            or (clock is not None and not callable(clock))
        ):
            raise DispatchDenied("dispatch_invalid_inputs")
        self.registry = registry
        self.authorization = authorization
        self.spend = spend
        self._clock = clock or (lambda: time.time_ns() // 1_000_000_000)
        try:
            self.path = Path(path).resolve()
            self._paths = (
                self.path, authorization.path, spend.path, registry.path,
            )
            if any(
                not isinstance(item, Path) or str(item).startswith(("\\\\", "//"))
                or str(item) == ":memory:" for item in self._paths
            ):
                raise DispatchDenied("dispatch_files_unsupported")
            if not self.path.parent.is_dir():
                raise DispatchDenied("dispatch_file_unavailable")
            registry._check_identity()
            attached = tuple(self._file_identity(item) for item in self._paths[1:])
            if len(set(self._paths)) != 4 or len(set(attached)) != 3:
                raise DispatchDenied("dispatch_files_aliased")
            if len({self.path.parent.stat().st_dev, *(item[0] for item in attached)}) != 1:
                raise DispatchDenied("dispatch_filesystem_mismatch")
            if not self.path.exists():
                try:
                    self.path.touch(exist_ok=False)
                except FileExistsError:
                    pass
            self._identities = (self._file_identity(self.path), *attached)
            if len(set(self._identities)) != 4:
                raise DispatchDenied("dispatch_files_aliased")
            if len({item[0] for item in self._identities}) != 1:
                raise DispatchDenied("dispatch_filesystem_mismatch")
        except (OSError, ValueError):
            raise DispatchDenied("dispatch_file_unavailable") from None
        with self._transaction(initialize=True):
            pass

    @staticmethod
    def _file_identity(path: Path) -> tuple[int, int]:
        try:
            record = path.stat()
        except OSError:
            raise DispatchDenied("dispatch_file_unavailable") from None
        if not stat.S_ISREG(record.st_mode):
            raise DispatchDenied("dispatch_files_unsupported")
        return record.st_dev, record.st_ino

    def _check_identities(self) -> None:
        self.registry._check_identity()
        if tuple(self._file_identity(path) for path in self._paths) != self._identities:
            raise DispatchDenied("dispatch_file_replaced")

    @staticmethod
    def _journals(db: sqlite3.Connection) -> None:
        for schema in ("main", "authorization", "spend", "registry"):
            if db.execute(f"PRAGMA {schema}.journal_mode").fetchone()[0] != "delete":
                raise DispatchDenied("unsupported_journal_mode")

    @contextmanager
    def _transaction(self, *, initialize: bool = False) -> Iterator[sqlite3.Connection]:
        self._check_identities()
        try:
            db = sqlite3.connect(
                self.path.as_uri() + "?mode=rw", timeout=30,
                isolation_level=None, uri=True,
            )
        except sqlite3.Error:
            raise DispatchDenied("dispatch_storage_unavailable") from None
        db.row_factory = sqlite3.Row
        try:
            for schema, path in zip(
                ("authorization", "spend", "registry"), self._paths[1:],
            ):
                self._check_identities()
                db.execute(f"ATTACH DATABASE ? AS {schema}", (path.as_uri() + "?mode=rw",))
            self._journals(db)
            db.execute("PRAGMA foreign_keys = ON")
            for schema in ("main", "authorization", "spend", "registry"):
                db.execute(f"PRAGMA {schema}.synchronous = FULL")
            db.execute("BEGIN IMMEDIATE")
            self._check_identities()
            self._journals(db)
            for schema, application, expected in (
                ("authorization", 0, _AUTH_SCHEMA),
                ("spend", _SPEND_ID, _SPEND_SCHEMA),
                ("registry", _REGISTRY_ID, _REGISTRY_SCHEMA),
            ):
                _validate_schema(db, schema, application, 1, expected)
            application = db.execute("PRAGMA main.application_id").fetchone()[0]
            version = db.execute("PRAGMA main.user_version").fetchone()[0]
            objects = db.execute(
                "SELECT name FROM main.sqlite_master WHERE sql IS NOT NULL"
            ).fetchall()
            if initialize and application == version == 0 and not objects:
                db.execute(_dispatch_schema(registry_bound=True)["dispatches"])
                db.execute(f"PRAGMA main.application_id = {_DISPATCH_ID}")
                db.execute("PRAGMA main.user_version = 2")
            _validate_schema(
                db, "main", _DISPATCH_ID, 2, _dispatch_schema(registry_bound=True),
            )
            yield db
            self._check_identities()
            db.commit()
        except sqlite3.Error:
            db.rollback()
            raise DispatchDenied("dispatch_storage_unavailable") from None
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _inputs(
        current: RegistryRequest, approval: ApprovalBinding, profile: DispatchProfile,
    ) -> None:
        if (
            type(current) is not RegistryRequest or type(approval) is not ApprovalBinding
            or type(profile) is not DispatchProfile
        ):
            raise DispatchDenied("dispatch_invalid_inputs")
        try:
            if (
                RegistryRequest.from_json(current.to_json()) != current
                or ApprovalBinding(**asdict(approval)) != approval
                or DispatchProfile(**asdict(profile)) != profile
            ):
                raise DispatchDenied("dispatch_invalid_inputs")
        except (ValueError, TypeError, RecursionError):
            raise DispatchDenied("dispatch_invalid_inputs") from None

    def enqueue(
        self, current: RegistryRequest, approval: ApprovalBinding, profile: DispatchProfile,
    ) -> ExecutionReceipt:
        """Revalidate first, then atomically consume, reserve and prepare inert work."""
        self._inputs(current, approval, profile)
        with self._transaction() as db:
            now = self._now()
            registered = self.registry._revalidate_in_transaction(db, current, now=now)
            if not isinstance(registered, str):
                result = self._enqueue_in_transaction(
                    db, current.manifest, approval, profile, registry_digest=current.digest,
                    now=now,
                )
        if isinstance(registered, str):
            raise RegistryDenied(registered)
        if isinstance(result, str):
            raise AuthorizationDenied(result)
        return result

    def claim(
        self, current: RegistryRequest, approval: ApprovalBinding, profile: DispatchProfile,
    ) -> DispatchClaim:
        """Revalidate under the common lock; never revive claimed or blocked work."""
        self._inputs(current, approval, profile)
        with self._transaction() as db:
            row = self._job(db, current.manifest.request_id)
            if row["state"] != "ready":
                raise DispatchDenied("dispatch_not_ready")
            now = self._now()
            registered = self.registry._revalidate_in_transaction(db, current, now=now)
            if isinstance(registered, str):
                db.execute(
                    "UPDATE dispatches SET state='blocked',reason=? WHERE request_id=?",
                    (registered, current.manifest.request_id),
                )
            else:
                result = self._claim_in_transaction(
                    db, current.manifest, approval, profile, registry_digest=current.digest,
                    now=now,
                )
        if isinstance(registered, str):
            raise RegistryDenied(registered)
        if isinstance(result, str):
            raise DispatchDenied(result)
        return result
