"""Read-only native approval observations, not federation or execution authority."""

from __future__ import annotations

import base64
import binascii
from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
import re
import time
from typing import Callable
from urllib.parse import quote, unquote

import requests

from .authorization import (
    ApprovalBinding,
    AuthorizationDenied,
    ExecutionManifest,
    _canonical,
    _digest,
    _text,
    _timestamp,
    sha256_digest,
)


_SLUG = re.compile(r"[A-Za-z0-9_.-]+\Z")
_SHA = re.compile(r"[0-9a-f]{40}\Z")
_WORKFLOW = re.compile(r"\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml\Z")


def _positive(value: object, name: str) -> None:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")


def _object(value: object) -> dict:
    if not isinstance(value, dict):
        raise AuthorizationDenied("malformed_github_evidence")
    return value


def _array(value: object) -> list:
    if not isinstance(value, list):
        raise AuthorizationDenied("malformed_github_evidence")
    return value


def _identifier(value: object) -> int:
    if type(value) is not int or value < 1:
        raise AuthorizationDenied("malformed_github_evidence")
    return value


def _string(value: object) -> str:
    if not isinstance(value, str):
        raise AuthorizationDenied("malformed_github_evidence")
    return value


def _date(value: object) -> int:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", value
    ):
        raise AuthorizationDenied("malformed_github_evidence")
    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
    except (ValueError, OverflowError):
        raise AuthorizationDenied("malformed_github_evidence") from None


def _unique_json(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _reject_json_constant(_: str) -> None:
    raise ValueError("nonfinite JSON value")


@dataclass(frozen=True)
class GitHubInstallationToken:
    """Short-lived installation credential from a trusted external App provider.

    Never supply a personal/user token. Token minting and App-key storage are
    deliberately outside this module; the credential is excluded from repr.
    """

    value: str = field(repr=False)
    expires_at: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or re.fullmatch(
            r"ghs_[A-Za-z0-9_]+", self.value
        ) is None:
            raise ValueError("a GitHub App installation-token format is required")
        _timestamp(self.expires_at, "expires_at")


class GitHubReadClient:
    """GET-only GitHub.com REST client with TLS, no redirects or ambient auth.

    Install the ``github`` extra. No shell/gh CLI, netrc, human credential lookup,
    arbitrary API origin, response logging, or write method is provided.
    Collections exceeding one 100-item page are explicitly unsupported.
    """

    def __init__(
        self,
        token_provider: Callable[[], GitHubInstallationToken],
        *,
        clock: Callable[[], int] | None = None,
    ) -> None:
        self._token_provider = token_provider
        self._clock = clock or (lambda: time.time_ns() // 1_000_000_000)
        self._session = requests.Session()
        self._session.trust_env = False

    def __enter__(self) -> GitHubReadClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._session.close()

    def get(self, path: str, *, params: dict | None = None) -> object:
        """Read a bounded JSON response, failing closed without private errors."""
        if (
            not isinstance(path, str)
            or not (path.startswith("/repos/") or path == "/installation/repositories")
            or re.fullmatch(r"/[A-Za-z0-9_.%/-]+", path) is None
            or "//" in unquote(path)
            or any(part in (".", "..") for part in unquote(path).split("/"))
            or "\\" in unquote(path)
        ):
            raise ValueError("only fixed-origin GitHub read paths are supported")
        try:
            token = self._token_provider()
            now = self._clock()
            _timestamp(now, "clock result")
        except Exception:
            raise AuthorizationDenied("github_auth_unavailable") from None
        if not isinstance(token, GitHubInstallationToken) or now >= token.expires_at:
            raise AuthorizationDenied("github_auth_unavailable")
        try:
            with self._session.get(
                "https://api.github.com" + path,
                params=params,
                headers={
                    "Authorization": "Bearer " + token.value,
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "fabric-delivery-core-native-evidence",
                    "Cache-Control": "no-cache",
                },
                timeout=(5, 20),
                allow_redirects=False,
                stream=True,
                verify=True,
            ) as response:
                if response.status_code != 200:
                    raise AuthorizationDenied("github_api_unavailable")
                if "next" in response.links:
                    raise AuthorizationDenied("github_evidence_incomplete")
                content = bytearray()
                for chunk in response.iter_content(chunk_size=65536):
                    content.extend(chunk)
                    if len(content) > 1_048_576:
                        raise AuthorizationDenied("github_evidence_too_large")
                return json.loads(
                    content.decode("utf-8"),
                    object_pairs_hook=_unique_json,
                    parse_constant=_reject_json_constant,
                )
        except AuthorizationDenied:
            raise
        except (requests.RequestException, UnicodeError, ValueError, RecursionError):
            raise AuthorizationDenied("github_api_unavailable") from None


@dataclass(frozen=True)
class NativeApprovalPolicy:
    """Reviewed PRIVATE registry policy, never values accepted from a callback.

    This bounded profile supports workflow_dispatch, exact branch restrictions,
    individually enrolled human user IDs, and a single native gate.
    """

    installation_id: str
    solution_id: str
    action: str
    target_environment: str | None
    policy_digest: str
    repository_owner: str
    repository_name: str
    repository_id: int
    workflow_id: int
    workflow_path: str
    workflow_commit: str
    workflow_digest: str
    trusted_ref: str
    environment_id: int
    gate_environment: str
    environment_updated_at: int
    required_reviewers_rule_id: int
    deployment_branch_policy_id: int
    human_reviewer_ids: tuple[int, ...]
    prevent_self_review: bool
    max_run_age_seconds: int
    evidence_ttl_seconds: int

    def __post_init__(self) -> None:
        for name in ("installation_id", "solution_id", "action", "gate_environment"):
            _text(getattr(self, name), name)
        if self.target_environment is not None:
            _text(self.target_environment, "target_environment")
        for name in ("repository_owner", "repository_name"):
            if not isinstance(getattr(self, name), str) or _SLUG.fullmatch(
                getattr(self, name)
            ) is None or getattr(self, name) in (".", ".."):
                raise ValueError(f"{name} must be a repository routing segment")
        for name in (
            "repository_id", "workflow_id", "environment_id",
            "required_reviewers_rule_id", "deployment_branch_policy_id",
            "max_run_age_seconds", "evidence_ttl_seconds",
        ):
            _positive(getattr(self, name), name)
        for name in ("policy_digest", "workflow_digest"):
            _digest(getattr(self, name), name)
        if not isinstance(self.workflow_path, str) or not _WORKFLOW.fullmatch(
            self.workflow_path
        ):
            raise ValueError("an exact local workflow YAML path is required")
        if not isinstance(self.workflow_commit, str) or not _SHA.fullmatch(
            self.workflow_commit
        ):
            raise ValueError("workflow_commit must be a full lowercase Git SHA")
        _text(self.trusted_ref, "trusted_ref")
        if (
            not self.trusted_ref.startswith("refs/heads/")
            or re.fullmatch(r"refs/heads/[A-Za-z0-9._/-]+", self.trusted_ref) is None
            or not self.trusted_ref.removeprefix("refs/heads/")
            or any(char in self.trusted_ref for char in "*?[\\~^:@ ")
            or ".." in self.trusted_ref
            or "//" in self.trusted_ref
        ):
            raise ValueError("an exact branch ref is required; patterns are unsupported")
        _timestamp(self.environment_updated_at, "environment_updated_at")
        if (
            not isinstance(self.human_reviewer_ids, tuple)
            or not self.human_reviewer_ids
            or len(set(self.human_reviewer_ids)) != len(self.human_reviewer_ids)
        ):
            raise ValueError("human_reviewer_ids must be a nonempty unique tuple")
        for identifier in self.human_reviewer_ids:
            _positive(identifier, "human reviewer ID")
        if type(self.prevent_self_review) is not bool:
            raise ValueError("prevent_self_review must be explicit")

    @property
    def digest(self) -> str:
        """Bind every private verification setting independently of parent policy."""
        return sha256_digest(_canonical(asdict(self)).encode("utf-8"))


@dataclass(frozen=True)
class RegisteredControlRun:
    """Private, durable adapter registration of an actually dispatched request."""

    request_id: str
    manifest_digest: str
    policy_snapshot_digest: str
    repository_id: int
    run_id: int
    run_attempt: int
    dispatched_at: int

    def __post_init__(self) -> None:
        _text(self.request_id, "request_id")
        for name in ("manifest_digest", "policy_snapshot_digest"):
            _digest(getattr(self, name), name)
        for name in ("repository_id", "run_id", "run_attempt"):
            _positive(getattr(self, name), name)
        _timestamp(self.dispatched_at, "dispatched_at")

    @property
    def digest(self) -> str:
        return sha256_digest(_canonical(asdict(self)).encode("utf-8"))


@dataclass(frozen=True)
class NativeApprovalEvidence:
    """Fresh, bound API observation; NEVER a grant or callback authentication.

    REST has no per-review approval time/attempt or administrative-bypass field.
    A request can be bound only to first-attempt history; use a new run for retry.
    """

    request_id: str
    manifest_digest: str
    registration_digest: str
    policy_snapshot_digest: str
    repository_id: int
    run_id: int
    run_attempt: int
    environment_id: int
    reviewer_id: int
    evidence_digest: str
    observed_at: int
    expires_at: int

    @property
    def execution_blockers(self) -> tuple[str, ...]:
        return (
            "administrative_bypass_unverified",
            "federation_unverified",
            "reviewer_credential_provenance_unverified",
        )

    def to_approval_binding(self) -> ApprovalBinding:
        """Refuse to silently promote a REST observation into execution authority."""
        raise AuthorizationDenied("execution_authorization_unsupported")


class GitHubNativeApprovalVerifier:
    """Observe authenticated GitHub evidence against a trusted private registry.

    No caller-supplied approved boolean, webhook JSON, run title, reviewer login,
    or public request label is accepted as authorization.
    """

    def __init__(
        self, client: GitHubReadClient, *, clock: Callable[[], int] | None = None
    ) -> None:
        self._client = client
        self._clock = clock or (lambda: time.time_ns() // 1_000_000_000)

    def _now(self) -> int:
        now = self._clock()
        _timestamp(now, "clock result")
        return now

    def verify(
        self,
        manifest: ExecutionManifest,
        registration: RegisteredControlRun,
        policy: NativeApprovalPolicy,
    ) -> NativeApprovalEvidence:
        """Fetch current evidence, deny drift/ambiguity, and return a bounded observation."""
        started = self._now()
        if not manifest.created_at <= started < manifest.expires_at:
            raise AuthorizationDenied("request_not_valid")
        if (
            registration.request_id != manifest.request_id
            or registration.manifest_digest != manifest.digest
            or registration.repository_id != policy.repository_id
            or (manifest.installation_id, manifest.solution_id, manifest.action,
                manifest.environment)
            != (policy.installation_id, policy.solution_id, policy.action,
                policy.target_environment)
        ):
            raise AuthorizationDenied("request_binding_mismatch")
        if (
            registration.policy_snapshot_digest != policy.digest
            or manifest.policy_digest != policy.policy_digest
            or manifest.control_workflow_digest != policy.workflow_digest
        ):
            raise AuthorizationDenied("policy_changed")
        if registration.run_attempt != 1:
            raise AuthorizationDenied("unsupported_run_attempt")
        if not (
            policy.environment_updated_at <= registration.dispatched_at
            and manifest.created_at <= registration.dispatched_at <= started
        ):
            raise AuthorizationDenied("stale_registration")
        route = f"/repos/{policy.repository_owner}/{policy.repository_name}"
        run_path = f"{route}/actions/runs/{registration.run_id}"
        environment = quote(policy.gate_environment, safe="")
        paths = {
            "repository": route,
            "workflow": f"{route}/actions/workflows/{policy.workflow_id}",
            "ref": f"{route}/git/ref/{quote(policy.trusted_ref[5:], safe='/')}",
            "environment": f"{route}/environments/{environment}",
            "branches": f"{route}/environments/{environment}/deployment-branch-policies",
            "run": run_path,
            "history": f"{run_path}/approvals",
            "pending": f"{run_path}/pending_deployments",
        }
        installation = _object(
            self._client.get("/installation/repositories", params={"per_page": 100})
        )
        repositories = self._collection(installation, "repositories")
        if policy.repository_id not in {
            _identifier(_object(repo).get("id")) for repo in repositories
        }:
            raise AuthorizationDenied("installation_repository_mismatch")

        before = {
            name: self._client.get(
                path, params={"per_page": 100} if name == "branches" else None
            )
            for name, path in paths.items()
        }
        run_created, reviewer_id = self._check(
            before, registration, policy, started
        )
        content = _object(
            self._client.get(
                f"{route}/contents/{policy.workflow_path}",
                params={"ref": policy.workflow_commit},
            )
        )
        try:
            if (
                content.get("type") != "file"
                or content.get("path") != policy.workflow_path
                or content.get("encoding") != "base64"
                or not isinstance(content.get("content"), str)
            ):
                raise ValueError()
            workflow_bytes = base64.b64decode(
                "".join(content["content"].splitlines()), validate=True
            )
        except (ValueError, binascii.Error):
            raise AuthorizationDenied("workflow_content_unavailable") from None
        if sha256_digest(workflow_bytes) != policy.workflow_digest:
            raise AuthorizationDenied("workflow_content_mismatch")

        after = {
            name: self._client.get(
                path, params={"per_page": 100} if name == "branches" else None
            )
            for name, path in paths.items()
        }
        finished = self._now()
        self._check(after, registration, policy, finished)
        if _canonical(before) != _canonical(after):
            raise AuthorizationDenied("github_evidence_changed")
        expires = min(
            manifest.expires_at,
            run_created + policy.max_run_age_seconds,
            started + policy.evidence_ttl_seconds,
        )
        if not started <= finished < expires:
            raise AuthorizationDenied("stale_github_evidence")
        evidence_digest = sha256_digest(
            _canonical(
                {
                    "manifest_digest": manifest.digest,
                    "registration_digest": registration.digest,
                    "policy_snapshot_digest": policy.digest,
                    "observations": after,
                    "workflow_digest": sha256_digest(workflow_bytes),
                    "observed_at": finished,
                    "expires_at": expires,
                }
            ).encode("utf-8")
        )
        return NativeApprovalEvidence(
            manifest.request_id, manifest.digest, registration.digest, policy.digest,
            policy.repository_id, registration.run_id, 1, policy.environment_id,
            reviewer_id, evidence_digest, finished, expires,
        )

    @staticmethod
    def _collection(response: dict, key: str) -> list:
        values = _array(response.get(key))
        total = response.get("total_count")
        if type(total) is not int or total != len(values) or total > 100:
            raise AuthorizationDenied("github_evidence_incomplete")
        return values

    def _check(
        self,
        evidence: dict,
        registration: RegisteredControlRun,
        policy: NativeApprovalPolicy,
        now: int,
    ) -> tuple[int, int]:
        repo = _object(evidence["repository"])
        if (
            _identifier(repo.get("id")) != policy.repository_id
            or _string(repo.get("full_name")).casefold()
            != f"{policy.repository_owner}/{policy.repository_name}".casefold()
            or repo.get("private") is not False
            or repo.get("visibility") != "public"
            or repo.get("fork") is not False
            or repo.get("archived") is not False
            or repo.get("disabled") is not False
        ):
            raise AuthorizationDenied("control_repository_mismatch")
        workflow = _object(evidence["workflow"])
        if (
            _identifier(workflow.get("id")) != policy.workflow_id
            or workflow.get("path") != policy.workflow_path
            or workflow.get("state") != "active"
        ):
            raise AuthorizationDenied("workflow_mismatch")
        ref = _object(evidence["ref"])
        ref_object = _object(ref.get("object"))
        if (
            ref.get("ref") != policy.trusted_ref
            or ref_object.get("type") != "commit"
            or ref_object.get("sha") != policy.workflow_commit
        ):
            raise AuthorizationDenied("trusted_ref_changed")
        self._check_environment(evidence, policy)
        run = _object(evidence["run"])
        if (
            _identifier(run.get("id")) != registration.run_id
            or _identifier(run.get("run_attempt")) != 1
        ):
            raise AuthorizationDenied("run_attempt_mismatch")
        if (
            _identifier(_object(run.get("repository")).get("id")) != policy.repository_id
            or _identifier(_object(run.get("head_repository")).get("id"))
            != policy.repository_id
            or _identifier(run.get("workflow_id")) != policy.workflow_id
            or run.get("path") != policy.workflow_path
            or run.get("head_branch") != policy.trusted_ref.removeprefix("refs/heads/")
            or run.get("head_sha") != policy.workflow_commit
            or run.get("event") != "workflow_dispatch"
            or run.get("referenced_workflows") not in (None, [])
        ):
            raise AuthorizationDenied("run_binding_mismatch")
        if (run.get("status"), run.get("conclusion")) not in (
            ("in_progress", None), ("completed", "success")
        ):
            raise AuthorizationDenied("run_not_approved")
        run_created = _date(run.get("created_at"))
        if not (
            registration.dispatched_at <= run_created <= now
            and now < run_created + policy.max_run_age_seconds
        ):
            raise AuthorizationDenied("stale_github_evidence")
        if _array(evidence["pending"]):
            raise AuthorizationDenied("review_pending")
        history = _array(evidence["history"])
        if not history:
            raise AuthorizationDenied("review_missing")
        if len(history) != 1:
            raise AuthorizationDenied("ambiguous_review_history")
        review = _object(history[0])
        environments = _array(review.get("environments"))
        if (
            len(environments) != 1
            or _identifier(_object(environments[0]).get("id")) != policy.environment_id
            or environments[0].get("name") != policy.gate_environment
        ):
            raise AuthorizationDenied("review_environment_mismatch")
        state = _string(review.get("state"))
        if state != "approved":
            raise AuthorizationDenied(
                {"pending": "review_pending", "rejected": "review_rejected"}.get(
                    state, "review_state_unsupported"
                )
            )
        reviewer_id = self._human(_object(review.get("user")), policy)
        if policy.prevent_self_review and reviewer_id in {
            _identifier(_object(run.get(actor)).get("id"))
            for actor in ("actor", "triggering_actor")
        }:
            raise AuthorizationDenied("self_review_denied")
        return run_created, reviewer_id

    @staticmethod
    def _human(user: dict, policy: NativeApprovalPolicy) -> int:
        identifier = _identifier(user.get("id"))
        login = user.get("login")
        if (
            user.get("type") != "User"
            or not isinstance(login, str)
            or not login
            or login.casefold().endswith("[bot]")
            or identifier not in policy.human_reviewer_ids
        ):
            raise AuthorizationDenied("reviewer_not_authorized_human")
        return identifier

    def _check_environment(self, evidence: dict, policy: NativeApprovalPolicy) -> None:
        environment = _object(evidence["environment"])
        branch_mode = _object(environment.get("deployment_branch_policy"))
        if (
            _identifier(environment.get("id")) != policy.environment_id
            or environment.get("name") != policy.gate_environment
            or _date(environment.get("updated_at")) != policy.environment_updated_at
            or branch_mode.get("protected_branches") is not False
            or branch_mode.get("custom_branch_policies") is not True
        ):
            raise AuthorizationDenied("environment_policy_changed")
        rules = _array(environment.get("protection_rules"))
        reviewers = [
            _object(rule) for rule in rules
            if _object(rule).get("type") == "required_reviewers"
        ]
        if (
            len(reviewers) != 1
            or any(rule.get("type") not in ("required_reviewers", "branch_policy")
                   for rule in rules)
        ):
            raise AuthorizationDenied("environment_policy_changed")
        rule = reviewers[0]
        if (
            _identifier(rule.get("id")) != policy.required_reviewers_rule_id
            or rule.get("prevent_self_review") is not policy.prevent_self_review
        ):
            raise AuthorizationDenied("environment_policy_changed")
        actual = []
        for item in _array(rule.get("reviewers")):
            item = _object(item)
            if item.get("type") != "User":
                raise AuthorizationDenied("unsupported_reviewer_policy")
            actual.append(self._human(_object(item.get("reviewer")), policy))
        if sorted(actual) != sorted(policy.human_reviewer_ids):
            raise AuthorizationDenied("environment_policy_changed")
        branches = self._collection(_object(evidence["branches"]), "branch_policies")
        if len(branches) != 1:
            raise AuthorizationDenied("environment_policy_changed")
        branch = _object(branches[0])
        if (
            _identifier(branch.get("id")) != policy.deployment_branch_policy_id
            or branch.get("type") != "branch"
            or branch.get("name") != policy.trusted_ref.removeprefix("refs/heads/")
        ):
            raise AuthorizationDenied("environment_policy_changed")
