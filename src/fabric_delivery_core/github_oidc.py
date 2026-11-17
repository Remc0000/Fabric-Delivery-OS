"""Verify GitHub-signed workload identity, never human or execution authority."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from email.utils import parsedate_to_datetime
import json
import re
import time

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
import jwt
import requests

from .authorization import (
    ApprovalBinding,
    AuthorizationDenied,
    ExecutionManifest,
    _canonical,
    _digest,
    _text,
    sha256_digest,
)
from .github_approval import (
    NativeApprovalPolicy,
    RegisteredControlRun,
    _reject_json_constant,
    _unique_json,
)


GITHUB_ISSUER = "https://token.actions.githubusercontent.com"
GITHUB_JWKS_URL = GITHUB_ISSUER + "/.well-known/jwks"
_KID = re.compile(r"[A-Za-z0-9._-]{1,128}\Z")
_COMPACT = re.compile(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\Z")


def _now() -> int:
    return time.time_ns() // 1_000_000_000


def _bound(value: object, minimum: int, maximum: int, name: str) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer within supported bounds")


def _decimal_id(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[1-9][0-9]{0,19}", value) is not None


def _strict_segment(segment: str) -> dict:
    data = json.loads(
        jwt.utils.base64url_decode(segment).decode("utf-8"),
        object_pairs_hook=_unique_json,
        parse_constant=_reject_json_constant,
    )
    if not isinstance(data, dict):
        raise ValueError("JWT segment must be an object")
    return data


@dataclass(frozen=True)
class GitHubOidcPolicy:
    """Explicit, private reviewed OIDC settings; no default audience or subject.

    The native policy separately pins repository/workflow/ref/environment state.
    Its digest and this complete policy digest must be registered before dispatch.
    """

    issuer: str
    audience: str
    subject: str
    native_policy_digest: str
    repository_owner_id: str
    environment_node_id: str
    max_lifetime_seconds: int
    max_token_age_seconds: int
    clock_skew_seconds: int
    max_jwks_age_seconds: int

    def __post_init__(self) -> None:
        if self.issuer != GITHUB_ISSUER:
            raise ValueError("only the official GitHub.com OIDC issuer is supported")
        for name in ("audience", "subject", "environment_node_id"):
            _text(getattr(self, name), name)
        if not _decimal_id(self.repository_owner_id):
            raise ValueError("repository_owner_id must be a canonical decimal ID")
        _digest(self.native_policy_digest, "native_policy_digest")
        _bound(self.max_lifetime_seconds, 1, 600, "max_lifetime_seconds")
        _bound(
            self.max_token_age_seconds, 1, self.max_lifetime_seconds,
            "max_token_age_seconds",
        )
        _bound(self.clock_skew_seconds, 0, 30, "clock_skew_seconds")
        _bound(self.max_jwks_age_seconds, 1, 300, "max_jwks_age_seconds")

    @property
    def digest(self) -> str:
        return sha256_digest(_canonical(asdict(self)).encode("utf-8"))


@dataclass(frozen=True)
class RegisteredOidcRequest:
    """Authoritative PRIVATE registry binding, never callback-supplied state."""

    control_run: RegisteredControlRun
    oidc_policy_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.control_run, RegisteredControlRun):
            raise ValueError("a private registered control run is required")
        _digest(self.oidc_policy_digest, "oidc_policy_digest")

    @property
    def digest(self) -> str:
        return sha256_digest(_canonical(asdict(self)).encode("utf-8"))


class GitHubJwksClient:
    """Read only the fixed official public JWKS with no credentials or cache.

    Every verification fetches anew. Removed/unknown keys and all network errors
    deny; no previous response, disk key, token-provided URL, or fallback is used.
    HTTP Date/Age and elapsed fetch time must satisfy explicit freshness policy.
    """

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.trust_env = False

    def __enter__(self) -> GitHubJwksClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._session.close()

    def key(self, kid: str, policy: GitHubOidcPolicy) -> RSAPublicKey:
        """Select exactly one strong RS256 signing key from fresh official data."""
        started = time.monotonic()
        try:
            with self._session.get(
                GITHUB_JWKS_URL,
                headers={
                    "Accept": "application/json",
                    "Cache-Control": "no-cache",
                    "User-Agent": "fabric-delivery-core-oidc-verifier",
                },
                timeout=(5, 15),
                allow_redirects=False,
                verify=True,
                stream=True,
            ) as response:
                if response.status_code != 200:
                    raise AuthorizationDenied("oidc_jwks_unavailable")
                now = _now()
                try:
                    issued = parsedate_to_datetime(response.headers.get("Date", ""))
                    age = response.headers.get("Age", "0")
                    if issued.tzinfo is None or re.fullmatch(r"[0-9]{1,9}", age) is None:
                        raise ValueError()
                    apparent_age = max(now - issued.timestamp(), int(age))
                except (TypeError, ValueError, OverflowError):
                    raise AuthorizationDenied("oidc_jwks_stale") from None
                if (
                    issued.timestamp() > now + policy.clock_skew_seconds
                    or apparent_age > policy.max_jwks_age_seconds
                ):
                    raise AuthorizationDenied("oidc_jwks_stale")
                content = bytearray()
                for chunk in response.iter_content(chunk_size=16384):
                    content.extend(chunk)
                    if len(content) > 262144:
                        raise AuthorizationDenied("invalid_oidc_jwks")
                elapsed = time.monotonic() - started
                if (
                    not 0 <= elapsed <= 20
                    or apparent_age + elapsed > policy.max_jwks_age_seconds
                    or _now() - issued.timestamp() > policy.max_jwks_age_seconds
                ):
                    raise AuthorizationDenied("oidc_jwks_stale")
                data = json.loads(
                    content.decode("utf-8"),
                    object_pairs_hook=_unique_json,
                    parse_constant=_reject_json_constant,
                )
            return self._select(data, kid)
        except AuthorizationDenied:
            raise
        except (requests.RequestException, UnicodeError, ValueError, RecursionError):
            raise AuthorizationDenied("oidc_jwks_unavailable") from None

    @staticmethod
    def _select(data: object, kid: str) -> RSAPublicKey:
        if not isinstance(data, dict) or not isinstance(data.get("keys"), list):
            raise AuthorizationDenied("invalid_oidc_jwks")
        if not 1 <= len(data["keys"]) <= 32:
            raise AuthorizationDenied("invalid_oidc_jwks")
        seen = set()
        selected = None
        for entry in data["keys"]:
            if not isinstance(entry, dict):
                raise AuthorizationDenied("invalid_oidc_jwks")
            identifier = entry.get("kid")
            if (
                not isinstance(identifier, str)
                or not _KID.fullmatch(identifier)
                or identifier in seen
                or entry.get("kty") != "RSA"
                or entry.get("alg") != "RS256"
                or entry.get("use") != "sig"
                or entry.get("key_ops", ["verify"]) != ["verify"]
                or set(entry) & {"d", "p", "q", "dp", "dq", "qi", "oth"}
            ):
                raise AuthorizationDenied("invalid_oidc_jwks")
            seen.add(identifier)
            if identifier == kid:
                selected = entry
        if selected is None:
            raise AuthorizationDenied("oidc_unknown_key")
        try:
            key = jwt.PyJWK.from_dict(selected, algorithm="RS256").key
            if not isinstance(key, RSAPublicKey) or not 2048 <= key.key_size <= 8192:
                raise ValueError()
        except (jwt.PyJWTError, TypeError, ValueError):
            raise AuthorizationDenied("invalid_oidc_jwks") from None
        return key


@dataclass(frozen=True)
class GitHubOidcEvidence:
    """Private verified workload-identity observation, never an execution grant."""

    manifest_digest: str
    registration_digest: str
    native_policy_digest: str
    oidc_policy_digest: str
    token_digest: str
    token_id_digest: str
    repository_id: int
    repository_owner_id: str
    run_id: int
    run_attempt: int
    issued_at: int
    not_before: int
    expires_at: int
    observed_at: int

    @property
    def execution_blockers(self) -> tuple[str, ...]:
        return (
            "private_request_claim_unsupported",
            "native_review_grant_integration_unverified",
            "administrative_bypass_unverified",
            "reviewer_credential_provenance_unverified",
            "github_app_provenance_unverified",
            "live_installation_federation_unproven",
        )

    def to_approval_binding(self) -> ApprovalBinding:
        raise AuthorizationDenied("execution_authorization_unsupported")


class GitHubOidcVerifier:
    """Verify signed context against registered private policy using PyJWT.

    GitHub does not sign workflow_dispatch inputs or a private manifest digest.
    Registry association is explicitly not represented as a signed input claim.
    This object has no token exchange, native review, grant, or worker methods.
    """

    def __init__(self, jwks: GitHubJwksClient) -> None:
        self._jwks = jwks

    def verify(
        self,
        token: str,
        manifest: ExecutionManifest,
        registration: RegisteredOidcRequest,
        native_policy: NativeApprovalPolicy,
        policy: GitHubOidcPolicy,
    ) -> GitHubOidcEvidence:
        run = registration.control_run
        now = _now()
        if not manifest.created_at <= now < manifest.expires_at:
            raise AuthorizationDenied("request_not_valid")
        if (
            run.request_id != manifest.request_id
            or run.manifest_digest != manifest.digest
            or run.repository_id != native_policy.repository_id
            or (manifest.installation_id, manifest.solution_id, manifest.action,
                manifest.environment)
            != (native_policy.installation_id, native_policy.solution_id,
                native_policy.action, native_policy.target_environment)
        ):
            raise AuthorizationDenied("request_binding_mismatch")
        if (
            registration.oidc_policy_digest != policy.digest
            or policy.native_policy_digest != native_policy.digest
            or run.policy_snapshot_digest != native_policy.digest
            or manifest.policy_digest != native_policy.policy_digest
            or manifest.control_workflow_digest != native_policy.workflow_digest
        ):
            raise AuthorizationDenied("oidc_policy_changed")
        if not manifest.created_at <= run.dispatched_at <= now:
            raise AuthorizationDenied("stale_registration")
        try:
            if (
                not isinstance(token, str)
                or len(token) > 32768
                or _COMPACT.fullmatch(token) is None
            ):
                raise ValueError()
            header_segment, payload_segment, _ = token.split(".")
            header = _strict_segment(header_segment)
            untrusted_payload = _strict_segment(payload_segment)
        except (ValueError, UnicodeError, RecursionError):
            raise AuthorizationDenied("invalid_oidc_token") from None
        kid = header.get("kid")
        if (
            header.get("alg") != "RS256"
            or header.get("typ") != "JWT"
            or not isinstance(kid, str)
            or not _KID.fullmatch(kid)
            or set(header) - {"alg", "kid", "typ", "x5t"}
        ):
            raise AuthorizationDenied("unsupported_oidc_header")
        for name in ("iat", "nbf", "exp"):
            value = untrusted_payload.get(name)
            if type(value) is not int or not 0 <= value < 2**63:
                raise AuthorizationDenied("invalid_oidc_token")
        key = self._jwks.key(kid, policy)
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=policy.issuer,
                audience=policy.audience,
                subject=policy.subject,
                leeway=policy.clock_skew_seconds,
                options={
                    "require": ["iss", "aud", "sub", "exp", "nbf", "iat", "jti"],
                    "strict_aud": True,
                },
            )
        except (jwt.PyJWTError, TypeError, ValueError):
            raise AuthorizationDenied("invalid_oidc_token") from None
        now = _now()
        issued, not_before, expires = (claims[name] for name in ("iat", "nbf", "exp"))
        skew = policy.clock_skew_seconds
        if (
            not manifest.created_at <= now < manifest.expires_at
            or issued < run.dispatched_at - skew
            or not issued < expires
            or not not_before < expires
            or expires - min(issued, not_before) > policy.max_lifetime_seconds
            or now - issued >= policy.max_token_age_seconds
            or now >= expires
            or now + skew < max(issued, not_before)
        ):
            raise AuthorizationDenied("oidc_lifetime_denied")
        owner = native_policy.repository_owner
        repository = owner + "/" + native_policy.repository_name
        expected = {
            "repository": repository,
            "repository_id": str(native_policy.repository_id),
            "repository_owner": owner,
            "repository_owner_id": policy.repository_owner_id,
            "repository_visibility": "public",
            "ref": native_policy.trusted_ref,
            "ref_type": "branch",
            "sha": native_policy.workflow_commit,
            "workflow_ref": (
                repository + "/" + native_policy.workflow_path + "@"
                + native_policy.trusted_ref
            ),
            "workflow_sha": native_policy.workflow_commit,
            "run_id": str(run.run_id),
            "run_attempt": str(run.run_attempt),
            "environment": native_policy.gate_environment,
            "environment_node_id": policy.environment_node_id,
            "event_name": "workflow_dispatch",
            "runner_environment": "github-hosted",
        }
        if (
            any(type(claims.get(name)) is not str or claims[name] != value
                for name, value in expected.items())
            or "job_workflow_ref" in claims
            or "job_workflow_sha" in claims
        ):
            raise AuthorizationDenied("oidc_claim_mismatch")
        jti = claims.get("jti")
        if not isinstance(jti, str) or re.fullmatch(r"[A-Za-z0-9._:-]{1,256}", jti) is None:
            raise AuthorizationDenied("invalid_oidc_token")
        return GitHubOidcEvidence(
            manifest.digest, registration.digest, native_policy.digest, policy.digest,
            sha256_digest(token.encode("ascii")), sha256_digest(jti.encode("utf-8")),
            native_policy.repository_id, policy.repository_owner_id,
            run.run_id, run.run_attempt, issued, not_before,
            min(expires, issued + policy.max_token_age_seconds, manifest.expires_at), now,
        )
