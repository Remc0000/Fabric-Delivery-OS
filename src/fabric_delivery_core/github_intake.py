"""Privileged offline normalized issue intake; never authentication or execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import json

from .authorization import ExecutionManifest, _canonical, _timestamp, sha256_digest
from .preflight import _invalid_constant, _unique
from .request_registry import IssueRevision, RegistryRequest, SQLiteRequestRegistry, _positive


_MAX_CAPTURE_BYTES = 1_048_576
_DENIALS = frozenset({
    "intake_invalid_snapshot", "intake_input_too_large", "intake_invalid_json",
    "intake_unsupported_schema", "intake_invalid_registry", "intake_invalid_inputs",
    "intake_action_not_allowed", "intake_invalid_receipt",
})

__all__ = [
    "GitHubIssueSnapshot", "OfflineGitHubIntake", "GitHubIntakeReceipt",
    "GitHubIntakeDenied",
]


class GitHubIntakeDenied(Exception):
    """Closed boundary denial, containing no input values or private diagnostics."""

    def __init__(self, reason: str) -> None:
        self.reason = (
            reason if type(reason) is str and reason in _DENIALS
            else "intake_invalid_inputs"
        )
        super().__init__(self.reason)


@dataclass(frozen=True, repr=False)
class GitHubIssueSnapshot:
    """Version-1 normalized capture, not a REST response or verified identity.

    Content and User/Bot attribution are inert private data. The complete
    canonical capture, including route and timestamp, binds its revision.
    """

    repository_id: int
    repository_private: bool
    issue_number: int
    title: str
    body: str | None
    author_id: int
    author_type: str
    updated_at: int
    schema_version: int = 1

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise GitHubIntakeDenied("intake_unsupported_schema")
        try:
            for value in (self.repository_id, self.issue_number, self.author_id):
                _positive(value)
            _timestamp(self.updated_at, "updated_at")
        except ValueError:
            raise GitHubIntakeDenied("intake_invalid_snapshot") from None
        if (
            type(self.repository_private) is not bool
            or type(self.title) is not str or not self.title
            or (self.body is not None and type(self.body) is not str)
            or type(self.author_type) is not str or self.author_type not in ("User", "Bot")
        ):
            raise GitHubIntakeDenied("intake_invalid_snapshot")
        try:
            self.title.encode("utf-8")
            if self.body is not None:
                self.body.encode("utf-8")
        except UnicodeEncodeError:
            raise GitHubIntakeDenied("intake_invalid_snapshot") from None
        if len(self.to_json().encode("utf-8")) > _MAX_CAPTURE_BYTES:
            raise GitHubIntakeDenied("intake_input_too_large")

    def to_json(self) -> str:
        """Return private canonical capture JSON; never external feedback."""
        return _canonical(asdict(self))

    @classmethod
    def from_json(cls, text: str) -> GitHubIssueSnapshot:
        """Parse only the strict, bounded, flat normalized capture schema."""
        if type(text) is not str:
            raise GitHubIntakeDenied("intake_invalid_json")
        try:
            size = len(text.encode("utf-8"))
        except UnicodeEncodeError:
            raise GitHubIntakeDenied("intake_invalid_json") from None
        if size > _MAX_CAPTURE_BYTES:
            raise GitHubIntakeDenied("intake_input_too_large")
        try:
            data = json.loads(
                text, object_pairs_hook=_unique, parse_constant=_invalid_constant,
            )
        except (ValueError, RecursionError):
            raise GitHubIntakeDenied("intake_invalid_json") from None
        if type(data) is not dict or set(data) != {field.name for field in fields(cls)}:
            raise GitHubIntakeDenied("intake_invalid_json")
        return cls(**data)

    @property
    def digest(self) -> str:
        """Bind every capture field independently of the manifest input digest."""
        return sha256_digest(self.to_json().encode("utf-8"))


@dataclass(frozen=True)
class GitHubIntakeReceipt:
    """Allowlisted last-recorded local state, not authenticated feedback/readiness."""

    state: str

    def __post_init__(self) -> None:
        if type(self.state) is not str or self.state not in ("proposed", "invalidated", "revoked"):
            raise GitHubIntakeDenied("intake_invalid_receipt")

    def to_json(self) -> str:
        """Report offline state without identifiers, payloads or execution authority."""
        return _canonical({
            "state": self.state,
            "offline_only": True,
            "execution_enabled": False,
            "awaiting_human_scope": self.state == "proposed",
        })


class OfflineGitHubIntake:
    """Trusted-caller discover proposals using only an explicit existing registry."""

    def __init__(self, registry: SQLiteRequestRegistry) -> None:
        if not isinstance(registry, SQLiteRequestRegistry):
            raise GitHubIntakeDenied("intake_invalid_registry")
        self._registry = registry

    @staticmethod
    def _request(snapshot: GitHubIssueSnapshot, manifest: ExecutionManifest) -> RegistryRequest:
        if type(snapshot) is not GitHubIssueSnapshot or type(manifest) is not ExecutionManifest:
            raise GitHubIntakeDenied("intake_invalid_inputs")
        return RegistryRequest(
            manifest,
            IssueRevision(
                snapshot.repository_id, snapshot.issue_number,
                snapshot.repository_private, snapshot.digest,
            ),
        )

    def register(
        self, snapshot: GitHubIssueSnapshot, manifest: ExecutionManifest,
    ) -> GitHubIntakeReceipt:
        """Admit proposed work only; exact first human scope remains required."""
        request = self._request(snapshot, manifest)
        if manifest.action != "discover":
            raise GitHubIntakeDenied("intake_action_not_allowed")
        self._registry.register(request)
        return GitHubIntakeReceipt("proposed")

    def revalidate(
        self, snapshot: GitHubIssueSnapshot, manifest: ExecutionManifest,
    ) -> GitHubIntakeReceipt:
        """Delegate permanent drift/expiry denial; never fetch external state."""
        recorded = self._registry.revalidate(self._request(snapshot, manifest))
        return GitHubIntakeReceipt(recorded.state)
