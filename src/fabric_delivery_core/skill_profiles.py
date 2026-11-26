"""Pure offline supplied-skill selection; no acquisition, activation or authority.

Origins, revisions, release order and compatibility labels are caller assertions,
not authenticated source history or proof of an actual runtime's compatibility.
Explicit JSON contains private records; repr and denial messages do not.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from ipaddress import IPv6Address
import json
import math
import re
from urllib.parse import urlsplit

from .authorization import _canonical, _digest, _text, sha256_digest
from .preflight import _invalid_constant, _unique
from .request_registry import _positive


__all__ = [
    "SkillRef", "SkillSelection", "SkillSource", "RoleSkillPolicy",
    "RoleSkillProfile", "SkillArtifact", "SkillCatalog", "SkillQuarantine",
    "SkillSnapshot", "SkillResolution", "SkillDenied", "OfflineSkillResolver",
]

_SMALL_JSON = 64 * 1024
_LARGE_JSON = 16 * 1024 * 1024
_CONTENT_BYTES = 1024 * 1024
_REVISION = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_QUARANTINE_REASONS = frozenset({
    "skill_source_unapproved", "skill_origin_mismatch", "skill_content_mismatch",
    "skill_dependency_not_skill", "skill_format_unsupported",
    "skill_runtime_incompatible",
})
_DENIAL_REASONS = frozenset({
    "skill_invalid_record", "skill_invalid_json", "skill_unsupported_schema",
    "skill_size_limit", "skill_role_mismatch", "skill_not_allowed",
    "skill_required_missing", "skill_unavailable", "skill_invalid_fallback",
})


class SkillDenied(Exception):
    """Closed public code with optional private, resolution-local observations."""

    def __init__(self, reason: str, quarantined: tuple[SkillQuarantine, ...] = ()) -> None:
        self.reason = (
            reason if type(reason) is str and reason in _DENIAL_REASONS
            else "skill_invalid_record"
        )
        try:
            _tuple(quarantined, SkillQuarantine, nonempty=False)
        except (SkillDenied, ValueError, TypeError, AttributeError):
            raise ValueError("skill_invalid_record") from None
        self.quarantined = quarantined
        super().__init__(self.reason)


def _string(value: object) -> None:
    if type(value) is not str:
        raise ValueError("invalid string")
    _text(value, "field")
    value.encode("utf-8")


def _hash(value: object) -> None:
    if type(value) is not str:
        raise ValueError("invalid digest")
    _digest(value, "field")


def _revision(value: object) -> None:
    if type(value) is not str or _REVISION.fullmatch(value) is None:
        raise ValueError("invalid revision")


def _origin(value: object) -> None:
    _string(value)
    if (
        not value.startswith("https://")
        or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value)
        or any(c in value for c in ('?', '#', '\\', '<', '>', '"', '{', '}', '|', '^', '`'))
        or re.search(r"%(?![0-9a-fA-F]{2})", value)
    ):
        raise ValueError("invalid origin")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https" or not parsed.netloc or not parsed.hostname
        or parsed.username is not None or parsed.password is not None
    ):
        raise ValueError("invalid origin")
    if parsed.port is not None and not 1 <= parsed.port <= 65535:
        raise ValueError("invalid origin")
    if parsed.netloc.endswith(":"):
        raise ValueError("invalid origin")
    if ":" in parsed.hostname:
        IPv6Address(parsed.hostname)
        if "%" in parsed.hostname:
            raise ValueError("invalid origin")
    else:
        hostname = parsed.hostname.encode("idna").decode("ascii")
        if len(hostname) > 253 or any(
            re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label) is None
            for label in hostname.rstrip(".").split(".")
        ):
            raise ValueError("invalid origin")


def _record(value: object, record_type: type) -> None:
    if type(value) is not record_type:
        raise ValueError("invalid record type")
    record_type.__post_init__(value)


def _tuple(value: object, item_type: type, *, nonempty: bool = True) -> None:
    if type(value) is not tuple or len(value) > 32 or (nonempty and not value):
        raise ValueError("invalid tuple")
    for item in value:
        if item_type is str:
            _string(item)
        else:
            _record(item, item_type)


def _unique_items(values: tuple) -> None:
    if len(set(values)) != len(values):
        raise ValueError("duplicate identity")


def _json_tree(value: object, depth: int = 0) -> None:
    if depth > 32:
        raise ValueError("invalid depth")
    if type(value) is str:
        value.encode("utf-8")
    elif type(value) is float and not math.isfinite(value):
        raise ValueError("nonfinite value")
    elif type(value) is dict:
        for key, item in value.items():
            _json_tree(key, depth + 1)
            _json_tree(item, depth + 1)
    elif type(value) is list:
        for item in value:
            _json_tree(item, depth + 1)


class _Record:
    __slots__ = ()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(<private>)"

    def __post_init__(self) -> None:
        if hasattr(self, "schema_version") and (
            type(self.schema_version) is not int or self.schema_version != 1
        ):
            raise SkillDenied("skill_unsupported_schema") from None
        try:
            self._validate()
            self.to_json()
        except (ValueError, TypeError, OverflowError, RecursionError, AttributeError):
            raise SkillDenied("skill_invalid_record") from None

    def to_json(self) -> str:
        """Serialize private exact records using the existing ASCII canonical form."""
        try:
            text = _canonical(asdict(self))
            size = len(text.encode("utf-8"))
        except (ValueError, TypeError, OverflowError, RecursionError, AttributeError):
            raise SkillDenied("skill_invalid_record") from None
        if size > _json_limit(type(self)):
            raise SkillDenied("skill_size_limit") from None
        return text

    @classmethod
    def from_json(cls, text: str):
        """Read exact fields, bounded before parsing; no default field inference."""
        if type(text) is not str:
            raise SkillDenied("skill_invalid_json") from None
        try:
            size = len(text.encode("utf-8"))
        except UnicodeError:
            raise SkillDenied("skill_invalid_json") from None
        if size > _json_limit(cls):
            raise SkillDenied("skill_size_limit") from None
        try:
            data = json.loads(
                text, object_pairs_hook=_unique, parse_constant=_invalid_constant,
            )
            _json_tree(data)
            return _from_data(cls, data)
        except (ValueError, TypeError, OverflowError, RecursionError, AttributeError):
            raise SkillDenied("skill_invalid_json") from None

    @property
    def digest(self) -> str:
        return sha256_digest(self.to_json().encode("utf-8"))


@dataclass(frozen=True, repr=False, slots=True)
class SkillRef(_Record):
    source_id: str
    skill_id: str

    def _validate(self) -> None:
        _string(self.source_id)
        _string(self.skill_id)


@dataclass(frozen=True, repr=False, slots=True)
class SkillSelection(_Record):
    ref: SkillRef
    revision: str | None = None

    def _validate(self) -> None:
        _record(self.ref, SkillRef)
        if self.revision is not None:
            _revision(self.revision)


@dataclass(frozen=True, repr=False, slots=True)
class SkillSource(_Record):
    source_id: str
    origin: str

    def _validate(self) -> None:
        _string(self.source_id)
        _origin(self.origin)


@dataclass(frozen=True, repr=False, slots=True)
class RoleSkillPolicy(_Record):
    policy_id: str
    version: str
    role_id: str
    runtime_interface: str
    approved_sources: tuple[SkillSource, ...]
    allowed_skills: tuple[SkillRef, ...]
    required_skills: tuple[SkillRef, ...]
    schema_version: int = 1

    def _validate(self) -> None:
        for value in (self.policy_id, self.version, self.role_id, self.runtime_interface):
            _string(value)
        _tuple(self.approved_sources, SkillSource)
        _tuple(self.allowed_skills, SkillRef)
        _tuple(self.required_skills, SkillRef, nonempty=False)
        sources = tuple(source.source_id for source in self.approved_sources)
        _unique_items(sources)
        _unique_items(self.allowed_skills)
        _unique_items(self.required_skills)
        if not set(self.required_skills) <= set(self.allowed_skills) or any(
            ref.source_id not in sources for ref in self.allowed_skills
        ):
            raise ValueError("invalid policy references")


@dataclass(frozen=True, repr=False, slots=True)
class RoleSkillProfile(_Record):
    profile_id: str
    version: str
    role_id: str
    selections: tuple[SkillSelection, ...]
    schema_version: int = 1

    def _validate(self) -> None:
        for value in (self.profile_id, self.version, self.role_id):
            _string(value)
        _tuple(self.selections, SkillSelection)
        _unique_items(tuple(selection.ref for selection in self.selections))


@dataclass(frozen=True, repr=False, slots=True)
class SkillArtifact(_Record):
    """Exact inert text and unproven immutable revision/release declarations."""

    ref: SkillRef
    origin: str
    revision: str
    release_sequence: int
    content: str
    content_digest: str
    runtime_interfaces: tuple[str, ...]
    dependency_type: str = "skill"
    format_id: str = "skill-md-v1"
    schema_version: int = 1

    def _validate(self) -> None:
        _record(self.ref, SkillRef)
        _origin(self.origin)
        _revision(self.revision)
        _positive(self.release_sequence)
        if type(self.content) is not str:
            raise ValueError("invalid content")
        if len(self.content.encode("utf-8")) > _CONTENT_BYTES:
            raise SkillDenied("skill_size_limit") from None
        _hash(self.content_digest)
        _tuple(self.runtime_interfaces, str)
        _unique_items(self.runtime_interfaces)
        _string(self.dependency_type)
        _string(self.format_id)


@dataclass(frozen=True, repr=False, slots=True)
class SkillCatalog(_Record):
    artifacts: tuple[SkillArtifact, ...]
    schema_version: int = 1

    def _validate(self) -> None:
        _tuple(self.artifacts, SkillArtifact, nonempty=False)
        _unique_items(tuple((item.ref, item.revision) for item in self.artifacts))
        _unique_items(tuple((item.ref, item.release_sequence) for item in self.artifacts))


@dataclass(frozen=True, repr=False, slots=True)
class SkillQuarantine(_Record):
    ref: SkillRef
    revision: str
    reason: str

    def _validate(self) -> None:
        _record(self.ref, SkillRef)
        _revision(self.revision)
        if type(self.reason) is not str or self.reason not in _QUARANTINE_REASONS:
            raise ValueError("invalid quarantine code")


def _profile_policy(profile: RoleSkillProfile, policy: RoleSkillPolicy) -> None:
    if profile.role_id != policy.role_id:
        raise SkillDenied("skill_role_mismatch") from None
    selected = {selection.ref for selection in profile.selections}
    if not selected <= set(policy.allowed_skills):
        raise SkillDenied("skill_not_allowed") from None
    if not set(policy.required_skills) <= selected:
        raise SkillDenied("skill_required_missing") from None


def _eligibility(artifact: SkillArtifact, policy: RoleSkillPolicy) -> str | None:
    sources = {source.source_id: source.origin for source in policy.approved_sources}
    if artifact.ref.source_id not in sources:
        return "skill_source_unapproved"
    if artifact.origin != sources[artifact.ref.source_id]:
        return "skill_origin_mismatch"
    if sha256_digest(artifact.content.encode("utf-8")) != artifact.content_digest:
        return "skill_content_mismatch"
    if artifact.dependency_type != "skill":
        return "skill_dependency_not_skill"
    if artifact.format_id != "skill-md-v1":
        return "skill_format_unsupported"
    if policy.runtime_interface not in artifact.runtime_interfaces:
        return "skill_runtime_incompatible"
    return None


@dataclass(frozen=True, repr=False, slots=True)
class SkillSnapshot(_Record):
    """Immutable local binding, not source/approval proof or permission to load."""

    profile: RoleSkillProfile
    policy: RoleSkillPolicy
    artifacts: tuple[SkillArtifact, ...]
    catalog_digest: str
    fallback_snapshot_digest: str | None = None
    schema_version: int = 1
    fallback_refs: tuple[SkillRef, ...] = ()

    def _validate(self) -> None:
        _record(self.profile, RoleSkillProfile)
        _record(self.policy, RoleSkillPolicy)
        _tuple(self.artifacts, SkillArtifact)
        _tuple(self.fallback_refs, SkillRef, nonempty=False)
        _unique_items(self.fallback_refs)
        _hash(self.catalog_digest)
        if self.fallback_snapshot_digest is not None:
            _hash(self.fallback_snapshot_digest)
        _profile_policy(self.profile, self.policy)
        if (
            bool(self.fallback_refs) != (self.fallback_snapshot_digest is not None)
            or self.fallback_refs != tuple(
                selection.ref for selection in self.profile.selections
                if selection.ref in self.fallback_refs
            )
        ):
            raise ValueError("invalid fallback references")
        if len(self.artifacts) != len(self.profile.selections):
            raise ValueError("invalid snapshot selection")
        for selection, artifact in zip(self.profile.selections, self.artifacts):
            if (
                selection.ref != artifact.ref
                or (selection.revision is not None and selection.revision != artifact.revision)
                or _eligibility(artifact, self.policy) is not None
            ):
                raise ValueError("invalid snapshot artifact")


@dataclass(frozen=True, repr=False, slots=True)
class SkillResolution(_Record):
    snapshot: SkillSnapshot
    quarantined: tuple[SkillQuarantine, ...]
    used_last_known_good: bool

    def _validate(self) -> None:
        _record(self.snapshot, SkillSnapshot)
        _tuple(self.quarantined, SkillQuarantine, nonempty=False)
        if type(self.used_last_known_good) is not bool or self.used_last_known_good != (
            bool(self.snapshot.fallback_refs)
        ):
            raise ValueError("invalid fallback binding")


def _json_limit(cls: type) -> int:
    return _SMALL_JSON if cls in (RoleSkillProfile, RoleSkillPolicy) else _LARGE_JSON


_NESTED = {
    SkillSelection: {"ref": SkillRef},
    RoleSkillPolicy: {
        "approved_sources": (SkillSource,), "allowed_skills": (SkillRef,),
        "required_skills": (SkillRef,),
    },
    RoleSkillProfile: {"selections": (SkillSelection,)},
    SkillArtifact: {"ref": SkillRef, "runtime_interfaces": (str,)},
    SkillCatalog: {"artifacts": (SkillArtifact,)},
    SkillQuarantine: {"ref": SkillRef},
    SkillSnapshot: {
        "profile": RoleSkillProfile, "policy": RoleSkillPolicy,
        "artifacts": (SkillArtifact,), "fallback_refs": (SkillRef,),
    },
    SkillResolution: {"snapshot": SkillSnapshot, "quarantined": (SkillQuarantine,)},
}


def _from_data(cls: type, data: object):
    if type(data) is not dict or set(data) != {item.name for item in fields(cls)}:
        raise ValueError("invalid JSON schema fields")
    converted = dict(data)
    for name, nested in _NESTED.get(cls, {}).items():
        value = data[name]
        if type(nested) is tuple:
            if type(value) is not list or len(value) > 32:
                raise ValueError("invalid JSON array")
            item_type = nested[0]
            converted[name] = tuple(
                item if item_type is str else _from_data(item_type, item) for item in value
            )
        else:
            converted[name] = _from_data(nested, value)
    return cls(**converted)


class OfflineSkillResolver:
    """Trusted-caller pure resolver, with no cache or approved-run connection."""

    __slots__ = ("_policy",)

    def __init__(self, policy: RoleSkillPolicy) -> None:
        try:
            _record(policy, RoleSkillPolicy)
        except (ValueError, TypeError, AttributeError):
            raise SkillDenied("skill_invalid_record") from None
        self._policy = policy

    def __repr__(self) -> str:
        return "OfflineSkillResolver(<private>)"

    def resolve(
        self, profile: RoleSkillProfile, catalog: SkillCatalog, *,
        last_known_good: SkillSnapshot | None = None,
    ) -> SkillResolution:
        try:
            _record(self._policy, RoleSkillPolicy)
            _record(profile, RoleSkillProfile)
            _record(catalog, SkillCatalog)
        except (ValueError, TypeError, AttributeError):
            raise SkillDenied("skill_invalid_record") from None
        if last_known_good is not None:
            try:
                _record(last_known_good, SkillSnapshot)
                if (
                    last_known_good.profile.digest != profile.digest
                    or last_known_good.policy.digest != self._policy.digest
                ):
                    raise ValueError("invalid fallback")
            except (SkillDenied, ValueError, TypeError, AttributeError):
                raise SkillDenied("skill_invalid_fallback") from None
        _profile_policy(profile, self._policy)
        eligible = {}
        quarantined = []
        for artifact in catalog.artifacts:
            reason = _eligibility(artifact, self._policy)
            if reason is not None:
                quarantined.append(SkillQuarantine(artifact.ref, artifact.revision, reason))
            else:
                eligible.setdefault(artifact.ref, []).append(artifact)
        selected = []
        fallback_refs = []
        for selection in profile.selections:
            candidates = [
                item for item in eligible.get(selection.ref, ())
                if selection.revision is None or item.revision == selection.revision
            ]
            if candidates:
                selected.append(max(candidates, key=lambda item: item.release_sequence))
            elif last_known_good is not None:
                selected.append(next(
                    item for item in last_known_good.artifacts if item.ref == selection.ref
                ))
                fallback_refs.append(selection.ref)
            else:
                raise SkillDenied("skill_unavailable", tuple(quarantined)) from None
        snapshot = SkillSnapshot(
            profile, self._policy, tuple(selected), catalog.digest,
            last_known_good.digest if fallback_refs else None,
            fallback_refs=tuple(fallback_refs),
        )
        return SkillResolution(snapshot, tuple(quarantined), bool(fallback_refs))
