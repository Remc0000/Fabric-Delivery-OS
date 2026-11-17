"""Trusted-caller, single-authority local SQLite cost reservations; no dispatch."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Callable, Iterator

from .authorization import _canonical, _digest, _text, _timestamp, sha256_digest


_MAX = 2**63 - 1
_APPLICATION_ID = 0x46445347


def _integer(value: object, name: str, minimum: int = 0) -> None:
    if type(value) is not int or not minimum <= value <= _MAX:
        raise ValueError(f"{name} must be a bounded integer")


def _currency(value: object) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[A-Z]{3}", value) is None:
        raise ValueError("currency must be an explicit uppercase three-letter code")


def _period(value: object) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", value) is None:
        raise ValueError("period must be YYYY-MM")
    if value.startswith("0000"):
        raise ValueError("period year must be positive")


def _binding(value: object) -> str:
    return sha256_digest(_canonical(asdict(value)).encode("utf-8"))


@dataclass(frozen=True)
class SpendBudget:
    """Immutable private monthly policy; money is integer 10^-9 currency units."""

    installation_id: str
    period: str
    currency: str
    version: str
    cap_units: int
    max_tokens: int
    max_calls: int

    def __post_init__(self) -> None:
        _text(self.installation_id, "installation_id")
        _text(self.version, "version")
        _period(self.period)
        _currency(self.currency)
        _integer(self.cap_units, "cap_units", 1)
        _integer(self.max_tokens, "max_tokens", 1)
        _integer(self.max_calls, "max_calls", 1)


@dataclass(frozen=True)
class PriceCard:
    """Trusted all-in upper-bound rates for one operation, not a live quote."""

    operation: str
    version: str
    currency: str
    valid_from: int
    valid_until: int
    token_units: int
    call_units: int

    def __post_init__(self) -> None:
        _text(self.operation, "operation")
        _text(self.version, "version")
        _currency(self.currency)
        _timestamp(self.valid_from, "valid_from")
        _timestamp(self.valid_until, "valid_until")
        if self.valid_until <= self.valid_from:
            raise ValueError("price validity must be nonempty")
        _integer(self.token_units, "token_units")
        _integer(self.call_units, "call_units")
        if self.token_units == self.call_units == 0:
            raise ValueError("zero-cost cards are not supported")


class SpendDenied(Exception):
    """Closed denial code without private values; storage errors propagate."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class SQLiteSpendStore:
    """Privileged API backed by a dedicated private local SQLite file.

    No authentication, authorization, price discovery, model calls, refunds,
    automatic expiry/release, or distributed/cloud accounting is supplied.
    """

    def __init__(
        self, path: str | Path, *, clock: Callable[[], int] | None = None
    ) -> None:
        if not str(path) or str(path) == ":memory:":
            raise ValueError("a durable filesystem path is required")
        self.path = Path(path).resolve()
        if not self.path.parent.is_dir():
            raise ValueError("database parent directory must already exist")
        self._clock = clock or (lambda: time.time_ns() // 1_000_000_000)
        with self._transaction() as db:
            app = db.execute("PRAGMA application_id").fetchone()[0]
            version = db.execute("PRAGMA user_version").fetchone()[0]
            tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if app == 0 and version == 0 and not tables:
                for statement in (
                    """CREATE TABLE budgets (
                        installation TEXT NOT NULL, period TEXT NOT NULL,
                        config TEXT NOT NULL, digest TEXT NOT NULL,
                        PRIMARY KEY (installation, period))""",
                    """CREATE TABLE prices (
                        operation TEXT NOT NULL, version TEXT NOT NULL,
                        card TEXT NOT NULL, digest TEXT NOT NULL,
                        PRIMARY KEY (operation, version))""",
                    """CREATE TABLE freezes (
                        installation TEXT PRIMARY KEY, reservation TEXT NOT NULL)""",
                    """CREATE TABLE reservations (
                        id TEXT PRIMARY KEY, installation TEXT NOT NULL,
                        period TEXT NOT NULL, currency TEXT NOT NULL,
                        execution_digest TEXT NOT NULL UNIQUE,
                        budget_digest TEXT NOT NULL, price_digest TEXT NOT NULL,
                        operation TEXT NOT NULL, price_version TEXT NOT NULL,
                        max_tokens INTEGER NOT NULL, max_calls INTEGER NOT NULL,
                        reserved INTEGER NOT NULL, deadline INTEGER NOT NULL,
                        created_at INTEGER NOT NULL, state TEXT NOT NULL
                            CHECK (state IN ('reserved','settled','breach')),
                        actual INTEGER, actual_tokens INTEGER, actual_calls INTEGER,
                        settled_at INTEGER)""",
                    "CREATE INDEX monthly_spend ON reservations (installation, period)",
                ):
                    db.execute(statement)
                db.execute(f"PRAGMA application_id = {_APPLICATION_ID}")
                db.execute("PRAGMA user_version = 1")
            elif app != _APPLICATION_ID or version != 1:
                raise ValueError("unsupported spend database")

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        # Kept separate from authorization storage: distinct schema and file.
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

    def configure_budget(self, budget: SpendBudget) -> None:
        """Insert once; even identical policy re-registration is denied."""
        with self._transaction() as db:
            if db.execute(
                "SELECT 1 FROM budgets WHERE installation=? AND period=?",
                (budget.installation_id, budget.period),
            ).fetchone():
                raise SpendDenied("budget_already_configured")
            db.execute(
                "INSERT INTO budgets VALUES (?,?,?,?)",
                (budget.installation_id, budget.period, _canonical(asdict(budget)), _binding(budget)),
            )

    def register_price(self, card: PriceCard) -> None:
        """Register trusted immutable rates; version reuse is always denied."""
        with self._transaction() as db:
            if db.execute(
                "SELECT 1 FROM prices WHERE operation=? AND version=?",
                (card.operation, card.version),
            ).fetchone():
                raise SpendDenied("price_version_reused")
            db.execute(
                "INSERT INTO prices VALUES (?,?,?,?)",
                (card.operation, card.version, _canonical(asdict(card)), _binding(card)),
            )

    @staticmethod
    def _totals(db: sqlite3.Connection, installation: str, period: str) -> tuple[int, int]:
        rows = db.execute(
            "SELECT state,reserved,actual FROM reservations WHERE installation=? AND period=?",
            (installation, period),
        ).fetchall()
        # Python integers avoid SQLite SUM overflow after externally incurred excess.
        return (
            sum(row["reserved"] for row in rows if row["state"] == "reserved"),
            sum(row["actual"] for row in rows if row["state"] != "reserved"),
        )

    def reserve(
        self, *, reservation_id: str, installation_id: str, period: str,
        currency: str, execution_digest: str, operation: str, price_version: str,
        max_tokens: int, max_calls: int,
    ) -> dict[str, object]:
        """Atomically reserve the computed maximum before any external effect.

        A receipt is inspection data, not a reusable worker-launch credential.
        All retries of an ID or execution digest are denied, even after settlement.
        """
        for value, name in (
            (reservation_id, "reservation_id"), (installation_id, "installation_id"),
            (operation, "operation"), (price_version, "price_version"),
        ):
            _text(value, name)
        _period(period)
        _currency(currency)
        _digest(execution_digest, "execution_digest")
        _integer(max_tokens, "max_tokens")
        _integer(max_calls, "max_calls", 1)
        with self._transaction() as db:
            now = self._clock()
            _timestamp(now, "clock result")
            current = datetime.fromtimestamp(now, timezone.utc)
            if period != current.strftime("%Y-%m"):
                raise SpendDenied("period_mismatch")
            if db.execute("SELECT 1 FROM freezes WHERE installation=?", (installation_id,)).fetchone():
                raise SpendDenied("installation_frozen")
            if db.execute(
                "SELECT 1 FROM reservations WHERE id=? OR execution_digest=?",
                (reservation_id, execution_digest),
            ).fetchone():
                raise SpendDenied("reservation_replay")
            record = db.execute(
                "SELECT * FROM budgets WHERE installation=? AND period=?", (installation_id, period)
            ).fetchone()
            if record is None:
                raise SpendDenied("missing_budget")
            budget = SpendBudget(**json.loads(record["config"]))
            if _binding(budget) != record["digest"]:
                raise SpendDenied("budget_corrupt")
            if budget.currency != currency:
                raise SpendDenied("currency_mismatch")
            if max_tokens > budget.max_tokens or max_calls > budget.max_calls:
                raise SpendDenied("execution_limit")
            price = db.execute(
                "SELECT * FROM prices WHERE operation=? AND version=?", (operation, price_version)
            ).fetchone()
            if price is None:
                raise SpendDenied("unknown_price")
            card = PriceCard(**json.loads(price["card"]))
            if _binding(card) != price["digest"]:
                raise SpendDenied("price_corrupt")
            if card.currency != currency:
                raise SpendDenied("currency_mismatch")
            if not card.valid_from <= now < card.valid_until:
                raise SpendDenied("stale_price")
            amount = max_tokens * card.token_units + max_calls * card.call_units
            if not 0 < amount <= _MAX:
                raise SpendDenied("unsupported_reservation")
            outstanding, settled = self._totals(db, installation_id, period)
            if outstanding + settled + amount > budget.cap_units:
                raise SpendDenied("budget_exhausted")
            next_month = (
                datetime(current.year + 1, 1, 1, tzinfo=timezone.utc)
                if current.month == 12 else
                datetime(current.year, current.month + 1, 1, tzinfo=timezone.utc)
            )
            deadline = min(int(next_month.timestamp()), card.valid_until)
            db.execute(
                """INSERT INTO reservations (
                    id,installation,period,currency,execution_digest,budget_digest,
                    price_digest,operation,price_version,max_tokens,max_calls,
                    reserved,deadline,created_at,state)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'reserved')""",
                (reservation_id, installation_id, period, currency, execution_digest,
                 record["digest"], price["digest"], operation, price_version,
                 max_tokens, max_calls, amount, deadline, now),
            )
            return dict(db.execute("SELECT * FROM reservations WHERE id=?", (reservation_id,)).fetchone())

    def settle(
        self, *, reservation_id: str, installation_id: str, period: str,
        currency: str, execution_digest: str, actual_units: int,
        actual_tokens: int, actual_calls: int,
    ) -> None:
        """Record trusted final usage exactly once, including excess and freeze.

        Reporting must include all costs and be final. Unknown/partial usage must
        remain outstanding; never use zero to release an uncertain reservation.
        A breach is committed BEFORE raising settlement_breach.
        """
        _integer(actual_units, "actual_units")
        _integer(actual_tokens, "actual_tokens")
        _integer(actual_calls, "actual_calls")
        _digest(execution_digest, "execution_digest")
        _period(period)
        _currency(currency)
        with self._transaction() as db:
            row = db.execute("SELECT * FROM reservations WHERE id=?", (reservation_id,)).fetchone()
            if row is None:
                raise SpendDenied("unknown_reservation")
            if (row["installation"], row["period"], row["currency"], row["execution_digest"]) != (
                installation_id, period, currency, execution_digest
            ):
                raise SpendDenied("settlement_mismatch")
            if row["state"] != "reserved":
                raise SpendDenied("settlement_replay")
            record = db.execute(
                "SELECT * FROM prices WHERE operation=? AND version=?",
                (row["operation"], row["price_version"]),
            ).fetchone()
            if record is None:
                raise SpendDenied("unknown_price")
            card = PriceCard(**json.loads(record["card"]))
            if _binding(card) != row["price_digest"] or record["digest"] != row["price_digest"]:
                raise SpendDenied("price_corrupt")
            breach = (
                actual_units > row["reserved"] or actual_tokens > row["max_tokens"]
                or actual_calls > row["max_calls"]
            )
            now = self._clock()
            _timestamp(now, "clock result")
            db.execute(
                """UPDATE reservations SET state=?,actual=?,actual_tokens=?,
                    actual_calls=?,settled_at=? WHERE id=?""",
                ("breach" if breach else "settled", actual_units, actual_tokens,
                 actual_calls, now, reservation_id),
            )
            if breach:
                db.execute(
                    "INSERT OR IGNORE INTO freezes VALUES (?,?)",
                    (installation_id, reservation_id),
                )
        if breach:
            raise SpendDenied("settlement_breach")

    def receipt(self, reservation_id: str) -> dict[str, object] | None:
        """Inspect durable state; never authorizes another execution."""
        with self._transaction() as db:
            row = db.execute("SELECT * FROM reservations WHERE id=?", (reservation_id,)).fetchone()
            return None if row is None else dict(row)

    def monthly_state(self, installation_id: str, period: str) -> dict[str, object]:
        """Inspect outstanding, settled (including excess), and global freeze."""
        _text(installation_id, "installation_id")
        _period(period)
        with self._transaction() as db:
            if not db.execute(
                "SELECT 1 FROM budgets WHERE installation=? AND period=?", (installation_id, period)
            ).fetchone():
                raise SpendDenied("missing_budget")
            outstanding, settled = self._totals(db, installation_id, period)
            frozen = db.execute(
                "SELECT reservation FROM freezes WHERE installation=?", (installation_id,)
            ).fetchone()
            return {
                "outstanding_units": outstanding, "settled_units": settled,
                "frozen": frozen is not None,
                "breach_reservation_id": None if frozen is None else frozen["reservation"],
            }
