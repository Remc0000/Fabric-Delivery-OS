"""Inert synthetic dispatch exercise in fresh, disposable local storage only."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from uuid import uuid4

from .authorization import (
    ApprovalBinding, AuthorizationDenied, ExecutionManifest,
    SQLiteAuthorizationStore, sha256_digest,
)
from .dispatch import DispatchDenied, DispatchProfile, SQLiteDispatchStore
from .preflight import OfflineCheck, OfflineReport
from .spend import PriceCard, SpendBudget, SQLiteSpendStore


def dispatch_self_test() -> OfflineReport:
    """Run a local atomic cycle and replay denial, never a real human/worker proof.

    No input paths, credentials, clients, worker callbacks or model routes are
    accepted. Synthetic approval is written only to newly created temporary
    stores and cannot authorize an installation.
    """
    now = time.time_ns() // 1_000_000_000
    period = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m")
    digest = sha256_digest(b"inert synthetic dispatch fixture")
    with TemporaryDirectory(prefix="fabric-delivery-self-test-") as directory:
        root = Path(directory)
        auth = SQLiteAuthorizationStore(root / "auth.sqlite3", clock=lambda: now)
        spend = SQLiteSpendStore(root / "spend.sqlite3", clock=lambda: now)
        queue = SQLiteDispatchStore(root / "queue.sqlite3", auth, spend, clock=lambda: now)
        budget = SpendBudget("synthetic-installation", period, "USD", "synthetic-v1", 10, 4, 1)
        card = PriceCard("synthetic-operation", "synthetic-v1", "USD", now, now + 60, 1, 1)
        spend.configure_budget(budget)
        spend.register_price(card)
        profile = DispatchProfile(
            digest, budget.digest, card.digest, card.operation, card.version,
            period, "USD", 4, 1, 20,
        )
        manifest = ExecutionManifest(
            request_id=str(uuid4()), installation_id=budget.installation_id,
            solution_id="synthetic-solution", action="synthetic_self_test",
            input_digest=digest, artifact_digest=None, target_baseline_digest=digest,
            environment=None, policy_digest=digest, execution_profile_digest=profile.digest,
            framework_digest=digest, control_workflow_digest=digest,
            tool_snapshot_digest=digest, skill_snapshot_digest=digest,
            permitted_effects=("synthetic_local_evidence",), created_at=now, expires_at=now + 60,
        )
        binding = ApprovalBinding(
            manifest.digest, "synthetic-repository", digest, "synthetic-run", 1,
            "synthetic-gate", digest, now, now + 60,
        )
        auth.freeze(manifest)
        auth.authorize(manifest.request_id, binding)
        queue.enqueue(manifest, binding, profile)
        # Reopen the real stores: the exercise is not an in-memory simulation.
        queue = SQLiteDispatchStore(root / "queue.sqlite3", auth, spend, clock=lambda: now)
        claim = queue.claim(manifest, binding, profile)
        try:
            queue.claim(manifest, binding, profile)
        except DispatchDenied as exc:
            if exc.reason != "dispatch_not_ready":
                raise
        else:
            raise RuntimeError("synthetic duplicate claim accepted")
        result = sha256_digest(b"fixed inert local result")
        queue.finish(
            claim, succeeded=True, result_digest=result,
            actual_units=1, actual_tokens=0, actual_calls=1,
        )
        try:
            queue.enqueue(manifest, binding, profile)
        except AuthorizationDenied as exc:
            if exc.reason != "consumed":
                raise
        else:
            raise RuntimeError("synthetic grant replay accepted")
        if (
            queue.receipt(manifest.request_id)["state"] != "succeeded"
            or spend.monthly_state(budget.installation_id, period)["settled_units"] != 1
        ):
            raise RuntimeError("synthetic terminal state mismatch")
    return OfflineReport((
        OfflineCheck("synthetic_dispatch_cycle", "ready", "local_atomic_cycle_verified"),
        OfflineCheck("synthetic_replay", "ready", "grant_and_claim_replay_denied"),
    ))
