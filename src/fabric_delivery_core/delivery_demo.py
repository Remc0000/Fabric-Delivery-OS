"""Input-free synthetic rehearsal; no live clients, agents or Fabric effects."""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from typing import Callable
from uuid import uuid4

from .authorization import (
    ApprovalBinding, AuthorizationDenied, ExecutionManifest,
    SQLiteAuthorizationStore, sha256_digest,
)
from .dispatch import DispatchDenied, DispatchProfile
from .github_intake import GitHubIssueSnapshot, OfflineGitHubIntake
from .preflight import OfflineCheck, OfflineReport
from .registry_dispatch import SQLiteRegistryDispatchStore
from .request_registry import (
    IssueRevision, RegistryDenied, RegistryRequest, RequestPolicy, RequestRule,
    SQLiteRequestRegistry,
)
from .skill_profiles import (
    OfflineSkillResolver, RoleSkillPolicy, RoleSkillProfile, SkillArtifact,
    SkillCatalog, SkillRef, SkillSelection, SkillSnapshot, SkillSource,
)
from .spend import PriceCard, SpendBudget, SQLiteSpendStore


@dataclass(frozen=True)
class _Scenario:
    root: Path
    now: int
    registry: SQLiteRequestRegistry
    authorization: SQLiteAuthorizationStore
    spend: SQLiteSpendStore
    queue: SQLiteRegistryDispatchStore
    capture: GitHubIssueSnapshot
    snapshot: SkillSnapshot
    request: RegistryRequest
    approval: ApprovalBinding
    profile: DispatchProfile
    budget: SpendBudget


def _require(condition: bool) -> None:
    if not condition:
        raise RuntimeError("synthetic delivery invariant failed")


def _denied(
    action: Callable[[], object],
    expected: type[AuthorizationDenied] | type[DispatchDenied] | type[RegistryDenied],
    reason: str,
) -> None:
    try:
        action()
    except expected as exc:
        if exc.reason != reason:
            raise
    else:
        raise RuntimeError("synthetic delivery denial missing")


def _scenario(root: Path, now: int) -> _Scenario:
    root.mkdir()
    period = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m")
    digest = sha256_digest(b"fixed inert delivery configuration")
    capture = GitHubIssueSnapshot(
        101, True, 7, "Synthetic delivery issue",
        "Synthetic context, not approval or executable instructions.", 202, "User", now,
    )
    ref = SkillRef("demo", "discovery-guidance")
    origin = "https://example.invalid/skills"
    skill_policy = RoleSkillPolicy(
        "demo-policy", "v1", "discover", "inert-demo-v1",
        (SkillSource("demo", origin),), (ref,), (ref,),
    )
    role = RoleSkillProfile("demo-discover", "v1", "discover", (SkillSelection(ref),))
    content = "Synthetic guidance: inspect only explicitly declared metadata.\n"
    artifact = SkillArtifact(
        ref, origin, "1" * 40, 1, content, sha256_digest(content.encode("utf-8")),
        ("inert-demo-v1",),
    )
    snapshot = OfflineSkillResolver(skill_policy).resolve(
        role, SkillCatalog((artifact,)),
    ).snapshot
    _require(SkillSnapshot.from_json(snapshot.to_json()) == snapshot)
    registry = SQLiteRequestRegistry(root / "registry.sqlite3", clock=lambda: now)
    authorization = SQLiteAuthorizationStore(root / "auth.sqlite3", clock=lambda: now)
    spend = SQLiteSpendStore(root / "spend.sqlite3", clock=lambda: now)
    budget = SpendBudget("synthetic-installation", period, "USD", "synthetic-v1", 10, 4, 1)
    card = PriceCard("synthetic-operation", "synthetic-v1", "USD", now, now + 60, 1, 1)
    spend.configure_budget(budget)
    spend.register_price(card)
    profile = DispatchProfile(
        digest, budget.digest, card.digest, card.operation, card.version,
        period, "USD", 4, 1, 20,
    )
    policy = RequestPolicy(
        budget.installation_id, "synthetic-solution", "v1", capture.repository_id,
        (RequestRule("discover", ("synthetic_local_evidence",)),), now, now + 60,
    )
    registry.register_policy(policy)
    manifest = ExecutionManifest(
        request_id=str(uuid4()), installation_id=budget.installation_id,
        solution_id=policy.solution_id, action="discover",
        input_digest=sha256_digest((capture.digest + snapshot.digest).encode("utf-8")),
        artifact_digest=None, target_baseline_digest=digest, environment=None,
        policy_digest=policy.digest, execution_profile_digest=profile.digest,
        framework_digest=digest, control_workflow_digest=digest,
        tool_snapshot_digest=digest, skill_snapshot_digest=snapshot.digest,
        permitted_effects=("synthetic_local_evidence",), created_at=now, expires_at=now + 60,
    )
    receipt = OfflineGitHubIntake(registry).register(capture, manifest)
    request = registry.inspect(manifest.request_id).request
    _require(receipt.state == "proposed" and request.manifest == manifest)
    _require(request.issue.revision_digest == capture.digest)
    authorization.freeze(manifest)
    approval = ApprovalBinding(
        manifest.digest, "synthetic-control", digest, "synthetic-run", 1,
        "synthetic-gate", digest, now, now + 60,
    )
    queue = SQLiteRegistryDispatchStore(
        root / "queue.sqlite3", registry, authorization, spend, clock=lambda: now,
    )
    return _Scenario(
        root, now, registry, authorization, spend, queue, capture, snapshot,
        request, approval, profile, budget,
    )


def _reopen(scenario: _Scenario) -> _Scenario:
    now = scenario.now
    registry = SQLiteRequestRegistry(scenario.root / "registry.sqlite3", clock=lambda: now)
    authorization = SQLiteAuthorizationStore(scenario.root / "auth.sqlite3", clock=lambda: now)
    spend = SQLiteSpendStore(scenario.root / "spend.sqlite3", clock=lambda: now)
    queue = SQLiteRegistryDispatchStore(
        scenario.root / "queue.sqlite3", registry, authorization, spend, clock=lambda: now,
    )
    return replace(
        scenario, registry=registry, authorization=authorization, spend=spend, queue=queue,
    )


def _success(scenario: _Scenario) -> None:
    request, approval, profile = scenario.request, scenario.approval, scenario.profile
    _denied(
        lambda: scenario.queue.enqueue(request, approval, profile),
        AuthorizationDenied, "pending",
    )
    _require(scenario.authorization.receipt(request.manifest.request_id) is None)
    _require(scenario.spend.monthly_state(
        scenario.budget.installation_id, scenario.budget.period,
    )["outstanding_units"] == 0)
    scenario.authorization.authorize(request.manifest.request_id, approval)
    scenario.queue.enqueue(request, approval, profile)
    scenario = _reopen(scenario)
    claim = scenario.queue.claim(request, approval, profile)
    _denied(
        lambda: scenario.queue.claim(request, approval, profile),
        DispatchDenied, "dispatch_not_ready",
    )
    result = sha256_digest(b"fixed inert local delivery test result")
    scenario.queue.finish(
        claim, succeeded=True, result_digest=result,
        actual_units=1, actual_tokens=0, actual_calls=1,
    )
    _denied(
        lambda: scenario.queue.enqueue(request, approval, profile),
        AuthorizationDenied, "consumed",
    )
    scenario = _reopen(scenario)
    receipt = scenario.queue.receipt(request.manifest.request_id)
    totals = scenario.spend.monthly_state(scenario.budget.installation_id, scenario.budget.period)
    _require(receipt["state"] == "succeeded" and receipt["result_digest"] == result)
    _require(totals["settled_units"] == 1 and totals["outstanding_units"] == 0)


def _drift(scenario: _Scenario, *, skills: bool) -> None:
    request, approval, profile = scenario.request, scenario.approval, scenario.profile
    scenario.authorization.authorize(request.manifest.request_id, approval)
    scenario.queue.enqueue(request, approval, profile)
    if skills:
        sealed = scenario.snapshot.to_json()
        original = scenario.snapshot.artifacts[0]
        content = original.content + "Synthetic compatible revision.\n"
        artifact = replace(
            original, revision="2" * 40, release_sequence=2, content=content,
            content_digest=sha256_digest(content.encode("utf-8")),
        )
        snapshot = OfflineSkillResolver(scenario.snapshot.policy).resolve(
            scenario.snapshot.profile, SkillCatalog((artifact,)),
        ).snapshot
        _require(snapshot.digest != scenario.snapshot.digest)
        _require(scenario.snapshot.to_json() == sealed)
        current = replace(
            request, manifest=replace(request.manifest, skill_snapshot_digest=snapshot.digest),
        )
    else:
        capture = replace(scenario.capture, body="Changed synthetic issue context.")
        current = replace(request, issue=IssueRevision(
            capture.repository_id, capture.issue_number, True, capture.digest,
        ))
    _denied(
        lambda: scenario.queue.claim(current, approval, profile),
        RegistryDenied, "registry_request_changed",
    )
    scenario = _reopen(scenario)
    _denied(
        lambda: scenario.queue.claim(request, approval, profile),
        DispatchDenied, "dispatch_not_ready",
    )
    _denied(
        lambda: scenario.registry.revalidate(request),
        RegistryDenied, "registry_request_changed",
    )
    receipt = scenario.queue.receipt(request.manifest.request_id)
    totals = scenario.spend.monthly_state(scenario.budget.installation_id, scenario.budget.period)
    _require(receipt["state"] == "blocked" and receipt["claim_id"] is None)
    _require(scenario.registry.inspect(request.manifest.request_id).state == "invalidated")
    _require(scenario.authorization.receipt(request.manifest.request_id) is not None)
    _require(totals["outstanding_units"] == 5 and totals["settled_units"] == 0)


def delivery_demo() -> OfflineReport:
    """Rehearse synthetic intake-to-result and durable drift, never live delivery.

    No installation state, caller-supplied grant, model route or worker is used.
    Only fresh temporary test files can receive the explicit synthetic approvals.
    """
    now = time.time_ns() // 1_000_000_000
    with TemporaryDirectory(prefix="fabric-delivery-demo-") as directory:
        root = Path(directory)
        _success(_scenario(root / "success", now))
        _drift(_scenario(root / "skills", now), skills=True)
        _drift(_scenario(root / "issue", now), skills=False)
    return OfflineReport((
        OfflineCheck("synthetic_intake_and_skills", "ready", "proposed_request_and_snapshot_bound"),
        OfflineCheck("synthetic_approval_gate", "ready", "pending_request_cannot_dispatch"),
        OfflineCheck("synthetic_dispatch_cycle", "ready", "registry_bound_claim_and_result_verified"),
        OfflineCheck("synthetic_replay", "ready", "grant_and_claim_replay_denied"),
        OfflineCheck("synthetic_skill_drift", "ready", "changed_snapshot_permanently_blocked"),
        OfflineCheck("synthetic_issue_drift", "ready", "changed_capture_permanently_blocked"),
    ))
