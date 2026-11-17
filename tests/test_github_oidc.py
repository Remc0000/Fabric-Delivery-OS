from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from email.utils import format_datetime
from io import BytesIO
import json
import unittest
from unittest.mock import Mock, patch

try:
    import jwt
    import requests
    from cryptography.hazmat.primitives.asymmetric import rsa
except ModuleNotFoundError as error:
    if error.name in ("jwt", "requests", "cryptography"):
        raise unittest.SkipTest("OIDC tests require the oidc extra") from None
    raise

from fabric_delivery_core import AuthorizationDenied, sha256_digest
from fabric_delivery_core.github_oidc import (
    GITHUB_ISSUER,
    GITHUB_JWKS_URL,
    GitHubJwksClient,
    GitHubOidcPolicy,
    GitHubOidcVerifier,
    RegisteredOidcRequest,
)
from test_github_approval import NOW, fixture


class DuplicatePayload(json.JSONEncoder):
    def encode(self, value):
        result = super().encode(value)
        if isinstance(value, dict) and "repository_id" in value:
            return result[:-1] + ',"repository_id":"1001"}'
        return result


class DuplicateHeader(json.JSONEncoder):
    def encode(self, value):
        result = super().encode(value)
        if isinstance(value, dict) and "kid" in value:
            return result[:-1] + ',"kid":"synthetic-key-1"}'
        return result


def public_jwk(key, kid):
    value = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    return dict(value, kid=kid, use="sig", alg="RS256")


class OidcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key1 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.key2 = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        self.manifest, self.native, control_run, _ = fixture()
        self.policy = GitHubOidcPolicy(
            issuer=GITHUB_ISSUER,
            audience="urn:synthetic:dispatcher",
            subject="bootstrap-selected-synthetic-immutable-subject",
            native_policy_digest=self.native.digest,
            repository_owner_id="2001",
            environment_node_id="SYNTHETIC_ENVIRONMENT_NODE_1004",
            max_lifetime_seconds=600,
            max_token_age_seconds=300,
            clock_skew_seconds=10,
            max_jwks_age_seconds=60,
        )
        self.registration = RegisteredOidcRequest(control_run, self.policy.digest)
        self.now = NOW
        now = patch(
            "fabric_delivery_core.github_oidc._now", side_effect=lambda: self.now
        )
        now.start()
        self.addCleanup(now.stop)
        test = self

        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime.fromtimestamp(test.now, tz)

        jwt_clock = patch("jwt.api_jwt.datetime", FixedDatetime)
        jwt_clock.start()
        self.addCleanup(jwt_clock.stop)
        self.keys = [public_jwk(self.key1, "synthetic-key-1")]
        self.status = 200
        self.headers = {}
        self.raw_body = None
        self.session = Mock()
        self.session.get.side_effect = self.response
        with patch(
            "fabric_delivery_core.github_oidc.requests.Session", return_value=self.session
        ):
            self.jwks = GitHubJwksClient()
        self.addCleanup(self.jwks.close)
        self.verifier = GitHubOidcVerifier(self.jwks)
        repo = self.native.repository_owner + "/" + self.native.repository_name
        self.claims = {
            "iss": self.policy.issuer,
            "aud": self.policy.audience,
            "sub": self.policy.subject,
            "jti": "synthetic-token-identity",
            "iat": NOW - 5, "nbf": NOW - 5, "exp": NOW + 295,
            "repository": repo,
            "repository_id": str(self.native.repository_id),
            "repository_owner": self.native.repository_owner,
            "repository_owner_id": self.policy.repository_owner_id,
            "repository_visibility": "public",
            "ref": self.native.trusted_ref,
            "ref_type": "branch",
            "sha": self.native.workflow_commit,
            "workflow_ref": (
                repo + "/" + self.native.workflow_path + "@" + self.native.trusted_ref
            ),
            "workflow_sha": self.native.workflow_commit,
            "run_id": str(control_run.run_id),
            "run_attempt": "1",
            "environment": self.native.gate_environment,
            "environment_node_id": self.policy.environment_node_id,
            "event_name": "workflow_dispatch",
            "runner_environment": "github-hosted",
        }

    def response(self, *_args, **_kwargs):
        response = requests.Response()
        response.status_code = self.status
        response.headers["Date"] = format_datetime(
            datetime.fromtimestamp(self.now, timezone.utc), usegmt=True
        )
        response.headers.update(self.headers)
        response.raw = BytesIO(
            self.raw_body if self.raw_body is not None
            else json.dumps({"keys": self.keys}).encode("utf-8")
        )
        return response

    def token(self, claims=None, *, key=None, headers=None, encoder=None):
        return jwt.encode(
            self.claims if claims is None else claims,
            self.key1 if key is None else key,
            algorithm="RS256",
            headers=headers or {"kid": "synthetic-key-1", "typ": "JWT"},
            json_encoder=encoder,
        )

    def verify(self, token=None):
        return self.verifier.verify(
            self.token() if token is None else token,
            self.manifest, self.registration, self.native, self.policy,
        )

    def assert_denied(self, reason, token=None):
        with self.assertRaises(AuthorizationDenied) as error:
            self.verify(token)
        self.assertEqual(error.exception.reason, reason)

    def test_real_rsa_signature_and_exact_signed_context_are_verified(self):
        token = self.token()
        evidence = self.verify(token)
        self.assertEqual(evidence.manifest_digest, self.manifest.digest)
        self.assertEqual(evidence.registration_digest, self.registration.digest)
        self.assertEqual(evidence.oidc_policy_digest, self.policy.digest)
        self.assertEqual(evidence.token_digest, sha256_digest(token.encode("ascii")))
        self.assertEqual((evidence.run_id, evidence.run_attempt), (1002, 1))
        self.assertEqual(evidence.repository_owner_id, "2001")
        self.assertLessEqual(evidence.expires_at, self.manifest.expires_at)
        self.assertNotIn(token, repr(evidence))
        self.assertIn("private_request_claim_unsupported", evidence.execution_blockers)
        with self.assertRaisesRegex(
            AuthorizationDenied, "^execution_authorization_unsupported$"
        ):
            evidence.to_approval_binding()

    def test_fixed_official_jwks_origin_no_credentials_redirects_or_ambient_auth(self):
        self.verify()
        args, kwargs = self.session.get.call_args
        self.assertEqual(args, (GITHUB_JWKS_URL,))
        self.assertIs(kwargs["allow_redirects"], False)
        self.assertIs(kwargs["verify"], True)
        self.assertEqual(kwargs["timeout"], (5, 15))
        self.assertFalse(self.session.trust_env)
        self.assertNotIn("Authorization", kwargs["headers"])

    def test_bad_signature_and_same_kid_wrong_key_are_denied(self):
        self.assert_denied("invalid_oidc_token", self.token(key=self.key2))
        self.keys = [public_jwk(self.key2, "synthetic-key-1")]
        self.assert_denied("invalid_oidc_token")

    def test_hmac_none_unexpected_headers_and_untrusted_key_urls_are_denied(self):
        hmac = jwt.encode(
            self.claims, b"synthetic-only-test-key-not-a-runtime-secret" * 2,
            algorithm="HS256", headers={"kid": "synthetic-key-1"},
        )
        self.assert_denied("unsupported_oidc_header", hmac)
        self.assert_denied(
            "invalid_oidc_token", jwt.encode(self.claims, "", algorithm="none")
        )
        for headers in (
            {"kid": "synthetic-key-1", "jku": "https://untrusted.invalid/jwks"},
            {"kid": "synthetic-key-1", "x5u": "https://untrusted.invalid/cert"},
            {"kid": "synthetic-key-1", "jwk": self.keys[0]},
            {"kid": "synthetic-key-1", "crit": ["unrecognized"]},
            {"kid": "../keys"},
            {"typ": "JWT"},
            {"kid": "synthetic-key-1", "typ": "not-JWT"},
        ):
            with self.subTest(headers=headers):
                self.assert_denied(
                    "unsupported_oidc_header", self.token(headers=headers)
                )
        self.session.get.assert_not_called()

    def test_issuer_audience_subject_and_multiple_audiences_are_not_approximated(self):
        for change in (
            {"iss": "https://untrusted.invalid"},
            {"iss": GITHUB_ISSUER + "/"},
            {"aud": "urn:other:dispatcher"},
            {"aud": [self.policy.audience, "urn:other"]},
            {"sub": "repo:synthetic-owner/synthetic-control:environment:authorize-development"},
        ):
            with self.subTest(change=change):
                self.assert_denied("invalid_oidc_token", self.token(dict(self.claims, **change)))

    def test_every_required_signed_context_mismatch_is_denied(self):
        changes = {
            "repository": "synthetic-owner/other-control",
            "repository_id": "9999",
            "repository_owner": "other-owner",
            "repository_owner_id": "9999",
            "repository_visibility": "private",
            "ref": "refs/heads/other",
            "ref_type": "tag",
            "sha": "b" * 40,
            "workflow_ref": "synthetic-owner/synthetic-control/.github/workflows/other.yml@main",
            "workflow_sha": "b" * 40,
            "run_id": "9999",
            "run_attempt": "2",
            "environment": "authorize-production",
            "environment_node_id": "OTHER_SYNTHETIC_NODE",
            "event_name": "pull_request_target",
            "runner_environment": "self-hosted",
        }
        for claim, value in changes.items():
            with self.subTest(claim=claim):
                self.assert_denied(
                    "oidc_claim_mismatch", self.token(dict(self.claims, **{claim: value}))
                )

    def test_missing_context_or_integer_identity_never_falls_back_to_subject(self):
        for claim in (
            "repository_id", "repository_owner_id", "workflow_ref", "workflow_sha",
            "environment", "environment_node_id", "run_id", "run_attempt",
        ):
            with self.subTest(claim=claim):
                claims = dict(self.claims)
                del claims[claim]
                self.assert_denied("oidc_claim_mismatch", self.token(claims))
        self.assert_denied(
            "oidc_claim_mismatch", self.token(dict(self.claims, repository_id=1001))
        )
        self.assert_denied(
            "oidc_claim_mismatch", self.token(dict(self.claims, run_attempt="01"))
        )

    def test_reusable_workflow_claims_require_a_separate_supported_profile(self):
        for change in (
            {"job_workflow_ref": self.claims["workflow_ref"]},
            {"job_workflow_sha": self.native.workflow_commit},
        ):
            with self.subTest(change=change):
                self.assert_denied(
                    "oidc_claim_mismatch", self.token(dict(self.claims, **change))
                )

    def test_expired_future_and_missing_or_wrong_type_numeric_dates_are_denied(self):
        for change in (
            {"exp": NOW - 20}, {"nbf": NOW + 11}, {"iat": NOW + 11},
            {"iat": "1800000000"}, {"nbf": True}, {"exp": float(NOW + 100)},
        ):
            with self.subTest(change=change):
                self.assert_denied(
                    "invalid_oidc_token", self.token(dict(self.claims, **change))
                )
        for claim in ("iat", "nbf", "exp", "jti", "iss", "aud", "sub"):
            claims = dict(self.claims)
            del claims[claim]
            with self.subTest(missing=claim):
                self.assert_denied("invalid_oidc_token", self.token(claims))

    def test_skew_is_bounded_but_expiry_and_age_have_no_grace(self):
        self.verify(self.token(dict(self.claims, iat=NOW + 10, nbf=NOW + 10)))
        self.assert_denied(
            "invalid_oidc_token", self.token(dict(self.claims, iat=NOW + 11))
        )
        self.assert_denied(
            "oidc_lifetime_denied", self.token(dict(self.claims, exp=NOW))
        )
        self.policy = replace(self.policy, max_token_age_seconds=5)
        self.registration = replace(
            self.registration, oidc_policy_digest=self.policy.digest
        )
        self.assert_denied("oidc_lifetime_denied")

    def test_excessive_validity_window_and_token_predating_dispatch_are_denied(self):
        self.assert_denied(
            "oidc_lifetime_denied",
            self.token(dict(self.claims, exp=NOW + 596)),
        )
        self.assert_denied(
            "oidc_lifetime_denied", self.token(dict(self.claims, nbf=NOW - 400))
        )
        self.assert_denied(
            "oidc_lifetime_denied",
            self.token(dict(self.claims, iat=NOW - 30, nbf=NOW - 30)),
        )

    def test_private_registry_or_policy_drift_denies_before_key_lookup(self):
        original = self.registration
        for registration, reason in (
            (replace(original, oidc_policy_digest=sha256_digest(b"changed")),
             "oidc_policy_changed"),
            (replace(original, control_run=replace(
                original.control_run, manifest_digest=sha256_digest(b"other")
            )), "request_binding_mismatch"),
        ):
            with self.subTest(reason=reason):
                self.registration = registration
                self.assert_denied(reason)
        self.session.get.assert_not_called()

    def test_expired_request_and_delay_while_fetching_keys_are_rechecked(self):
        token = self.token()
        self.now = self.manifest.expires_at
        self.assert_denied("request_not_valid", token)
        self.now = NOW
        get_response = self.response

        def delayed(*args, **kwargs):
            self.now = NOW + 400
            return get_response(*args, **kwargs)

        self.session.get.side_effect = delayed
        self.assert_denied("invalid_oidc_token", token)

    def test_duplicate_signed_json_is_rejected_even_with_a_valid_signature(self):
        for encoder in (DuplicatePayload, DuplicateHeader):
            with self.subTest(encoder=encoder.__name__):
                self.assert_denied("invalid_oidc_token", self.token(encoder=encoder))
        self.session.get.assert_not_called()

    def test_rotation_fetches_fresh_keys_and_removed_keys_never_use_a_fallback(self):
        self.verify()
        self.keys = [public_jwk(self.key2, "synthetic-key-2")]
        self.verify(self.token(key=self.key2, headers={"kid": "synthetic-key-2"}))
        self.assert_denied("oidc_unknown_key")
        self.assertEqual(self.session.get.call_count, 3)

    def test_unknown_key_network_failure_and_redirect_do_not_reuse_prior_keys(self):
        self.verify()
        self.assert_denied(
            "oidc_unknown_key", self.token(headers={"kid": "unregistered-key"})
        )
        self.status = 302
        self.headers["Location"] = "https://untrusted.invalid/jwks"
        self.assert_denied("oidc_jwks_unavailable")
        self.session.get.side_effect = requests.ConnectionError("PRIVATE_CONTEXT_DETAIL")
        self.assert_denied("oidc_jwks_unavailable")

    def test_stale_or_future_http_date_and_age_are_fail_closed(self):
        for headers in (
            {"Date": format_datetime(datetime.fromtimestamp(NOW - 61, timezone.utc))},
            {"Date": format_datetime(datetime.fromtimestamp(NOW + 11, timezone.utc))},
            {"Age": "61"}, {"Age": "not-a-number"}, {"Date": "not-a-date"},
        ):
            with self.subTest(headers=headers):
                self.headers = headers
                self.assert_denied("oidc_jwks_stale")

    def test_ambiguous_malformed_or_wrong_algorithm_jwks_are_denied(self):
        original = deepcopy(self.keys[0])
        for keys in (
            [original, original],
            [dict(original, alg="HS256")],
            [dict(original, kty="oct")],
            [dict(original, use="enc")],
            [dict(original, key_ops=["sign"])],
            [dict(original, d="PRIVATE_KEY_MUST_NOT_BE_ACCEPTED")],
            [dict(original, n="not-valid-base64url!")],
            [],
        ):
            with self.subTest(keys=keys):
                self.keys = keys
                self.assert_denied("invalid_oidc_jwks")
        weak = rsa.generate_private_key(public_exponent=65537, key_size=1024)
        self.keys = [public_jwk(weak, "synthetic-key-1")]
        self.assert_denied("invalid_oidc_jwks")

    def test_jwks_body_bounds_duplicate_keys_and_slow_fetch_fail_closed(self):
        for body, reason in (
            (b'{"keys":[],"keys":[]}', "oidc_jwks_unavailable"),
            (b"x" * 262145, "invalid_oidc_jwks"),
            (b'{"keys":null}', "invalid_oidc_jwks"),
        ):
            with self.subTest(reason=reason):
                self.raw_body = body
                self.assert_denied(reason)
        self.raw_body = None
        with patch(
            "fabric_delivery_core.github_oidc.time.monotonic", side_effect=[100, 121]
        ):
            self.assert_denied("oidc_jwks_stale")

    def test_signed_private_input_extensions_never_become_execution_authority(self):
        token = self.token(dict(
            self.claims, request_id="other-private-request",
            manifest_digest=sha256_digest(b"other private inputs"),
        ))
        evidence = self.verify(token)
        self.assertIn("private_request_claim_unsupported", evidence.execution_blockers)
        with self.assertRaises(AuthorizationDenied):
            evidence.to_approval_binding()

    def test_signed_attempt_two_is_verifiable_but_not_native_review_or_grant_proof(self):
        self.registration = replace(
            self.registration, control_run=replace(
                self.registration.control_run, run_attempt=2
            )
        )
        evidence = self.verify(self.token(dict(self.claims, run_attempt="2")))
        self.assertEqual(evidence.run_attempt, 2)
        self.assertIn(
            "native_review_grant_integration_unverified", evidence.execution_blockers
        )

    def test_explicit_subject_and_bounded_trust_policy_are_mandatory(self):
        for change in (
            {"issuer": "https://untrusted.invalid"},
            {"issuer": GITHUB_ISSUER + "/"},
            {"audience": ""}, {"subject": ""},
            {"repository_owner_id": "02001"},
            {"max_lifetime_seconds": 601},
            {"max_token_age_seconds": 601},
            {"clock_skew_seconds": 31},
            {"max_jwks_age_seconds": 301},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(self.policy, **change)


if __name__ == "__main__":
    unittest.main()
