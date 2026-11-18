import base64
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from io import BytesIO
import unittest
from unittest.mock import Mock, patch

try:
    import requests
except ModuleNotFoundError as error:
    if error.name == "requests":
        raise unittest.SkipTest("native verifier tests require the github extra") from None
    raise

from fabric_delivery_core import AuthorizationDenied, sha256_digest
from fabric_delivery_core.github_approval import (
    GitHubInstallationToken,
    GitHubNativeApprovalVerifier,
    GitHubReadClient,
    NativeApprovalPolicy,
    RegisteredControlRun,
)
from test_authorization import NOW, manifest as core_manifest


WORKFLOW = b"name: synthetic-only\non: workflow_dispatch\njobs: {}\n"


def date(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fixture():
    manifest = replace(
        core_manifest(), control_workflow_digest=sha256_digest(WORKFLOW)
    )
    policy = NativeApprovalPolicy(
        installation_id=manifest.installation_id,
        solution_id=manifest.solution_id,
        action=manifest.action,
        target_environment=manifest.environment,
        policy_digest=manifest.policy_digest,
        repository_owner="synthetic-owner",
        repository_name="synthetic-control",
        repository_id=1001,
        workflow_id=1003,
        workflow_path=".github/workflows/synthetic.yml",
        workflow_commit="a" * 40,
        workflow_digest=manifest.control_workflow_digest,
        trusted_ref="refs/heads/main",
        environment_id=1004,
        gate_environment="authorize-development",
        environment_updated_at=NOW - 300,
        required_reviewers_rule_id=41,
        deployment_branch_policy_id=43,
        human_reviewer_ids=(1010,),
        prevent_self_review=False,
        max_run_age_seconds=300,
        evidence_ttl_seconds=30,
    )
    registration = RegisteredControlRun(
        manifest.request_id, manifest.digest, policy.digest,
        policy.repository_id, 1002, 1, NOW - 9,
    )
    user = {"type": "User", "id": 1010, "login": "synthetic-human"}
    repo = {
        "id": policy.repository_id,
        "full_name": "synthetic-owner/synthetic-control",
        "private": False, "visibility": "public", "fork": False,
        "archived": False, "disabled": False,
    }
    route = "/repos/synthetic-owner/synthetic-control"
    run_path = route + "/actions/runs/1002"
    env_path = route + "/environments/authorize-development"
    responses = {
        "/installation/repositories": {"total_count": 1, "repositories": [repo]},
        route: repo,
        route + "/actions/workflows/1003": {
            "id": 1003, "path": policy.workflow_path, "state": "active",
        },
        route + "/git/ref/heads/main": {
            "ref": policy.trusted_ref,
            "object": {"type": "commit", "sha": policy.workflow_commit},
        },
        env_path: {
            "id": 1004, "name": policy.gate_environment,
            "updated_at": date(policy.environment_updated_at),
            "deployment_branch_policy": {
                "protected_branches": False, "custom_branch_policies": True,
            },
            "protection_rules": [
                {
                    "id": 41, "type": "required_reviewers",
                    "prevent_self_review": False,
                    "reviewers": [{"type": "User", "reviewer": user}],
                },
                {"id": 42, "type": "branch_policy"},
            ],
        },
        env_path + "/deployment-branch-policies": {
            "total_count": 1,
            "branch_policies": [{"id": 43, "name": "main", "type": "branch"}],
        },
        run_path: {
            "id": 1002, "run_attempt": 1, "repository": repo, "head_repository": repo,
            "workflow_id": 1003, "path": policy.workflow_path,
            "head_branch": "main", "head_sha": policy.workflow_commit,
            "event": "workflow_dispatch", "referenced_workflows": [],
            "status": "in_progress", "conclusion": None,
            "created_at": date(NOW - 8), "actor": user, "triggering_actor": user,
        },
        run_path + "/approvals": [
            {
                "state": "approved", "user": user, "comment": "synthetic comment",
                "environments": [{"id": 1004, "name": policy.gate_environment}],
            }
        ],
        run_path + "/pending_deployments": [],
        route + "/contents/" + policy.workflow_path: {
            "type": "file", "path": policy.workflow_path, "encoding": "base64",
            "content": base64.b64encode(WORKFLOW).decode("ascii"),
        },
    }
    return manifest, policy, registration, {
        path: deepcopy(response) for path, response in responses.items()
    }


class FixtureAPI:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []
        self.on_get = lambda path, count: None

    def get(self, path, *, params=None):
        self.calls.append((path, params))
        count = sum(request == path for request, _ in self.calls)
        self.on_get(path, count)
        return deepcopy(self.responses[path])


class NativeVerifierTests(unittest.TestCase):
    def setUp(self):
        self.manifest, self.policy, self.registration, responses = fixture()
        self.api = FixtureAPI(responses)
        self.now = NOW
        self.verifier = GitHubNativeApprovalVerifier(self.api, clock=lambda: self.now)
        self.route = "/repos/synthetic-owner/synthetic-control"
        self.run = self.route + "/actions/runs/1002"
        self.environment = self.route + "/environments/authorize-development"

    def verify(self):
        return self.verifier.verify(self.manifest, self.registration, self.policy)

    def assert_denied(self, reason):
        with self.assertRaises(AuthorizationDenied) as error:
            self.verify()
        self.assertEqual(error.exception.reason, reason)

    def test_native_history_is_bound_to_registry_but_never_becomes_a_grant(self):
        evidence = self.verify()
        self.assertEqual(evidence.manifest_digest, self.manifest.digest)
        self.assertEqual(evidence.registration_digest, self.registration.digest)
        self.assertEqual(evidence.policy_snapshot_digest, self.policy.digest)
        self.assertEqual((evidence.reviewer_id, evidence.run_id), (1010, 1002))
        self.assertEqual(evidence.expires_at, NOW + 30)
        self.assertEqual(
            evidence.execution_blockers,
            (
                "administrative_bypass_unverified", "federation_unverified",
                "reviewer_credential_provenance_unverified",
            ),
        )
        with self.assertRaisesRegex(
            AuthorizationDenied, "execution_authorization_unsupported"
        ):
            evidence.to_approval_binding()
        content_calls = [
            params for path, params in self.api.calls if "/contents/" in path
        ]
        self.assertEqual(content_calls, [{"ref": "a" * 40}])

    def test_missing_pending_rejected_and_ambiguous_history_are_denied(self):
        for value, reason in (
            ([], "review_missing"),
            ([dict(self.api.responses[self.run + "/approvals"][0], state="pending")],
             "review_pending"),
            ([dict(self.api.responses[self.run + "/approvals"][0], state="rejected")],
             "review_rejected"),
            (self.api.responses[self.run + "/approvals"] * 2, "ambiguous_review_history"),
        ):
            with self.subTest(reason=reason):
                original = self.api.responses[self.run + "/approvals"]
                self.api.responses[self.run + "/approvals"] = value
                self.assert_denied(reason)
                self.api.responses[self.run + "/approvals"] = original

    def test_empty_pending_deployments_is_not_proof_of_approval(self):
        self.api.responses[self.run + "/approvals"] = []
        self.assert_denied("review_missing")

    def test_pending_gate_denies_even_with_approved_history(self):
        self.api.responses[self.run + "/pending_deployments"] = [
            {"environment": {"id": 1004}, "current_user_can_approve": True}
        ]
        self.assert_denied("review_pending")

    def test_bots_apps_unenrolled_users_and_login_impersonation_are_denied(self):
        review = self.api.responses[self.run + "/approvals"][0]
        for user in (
            {"id": 1010, "type": "Bot", "login": "synthetic-human"},
            {"id": 1010, "type": "User", "login": "synthetic-agent[bot]"},
            {"id": 7777, "type": "User", "login": "synthetic-human"},
            {"id": 1010, "type": "App", "login": "synthetic-app"},
        ):
            with self.subTest(user=user):
                review["user"] = user
                self.assert_denied("reviewer_not_authorized_human")

    def test_wrong_or_recreated_environment_cannot_reuse_same_name(self):
        review = self.api.responses[self.run + "/approvals"][0]
        for environment in (
            {"id": 1004, "name": "authorize-production"},
            {"id": 9999, "name": self.policy.gate_environment},
        ):
            with self.subTest(environment=environment):
                review["environments"] = [environment]
                self.assert_denied("review_environment_mismatch")
        self.api.responses[self.environment]["id"] = 9999
        self.assert_denied("environment_policy_changed")

    def test_run_identity_ref_revision_event_workflow_and_fork_are_bound(self):
        original = deepcopy(self.api.responses[self.run])
        for change, reason in (
            ({"id": 9999}, "run_attempt_mismatch"),
            ({"run_attempt": 2}, "run_attempt_mismatch"),
            ({"head_branch": "other"}, "run_binding_mismatch"),
            ({"head_sha": "b" * 40}, "run_binding_mismatch"),
            ({"event": "pull_request_target"}, "run_binding_mismatch"),
            ({"path": ".github/workflows/other.yml"}, "run_binding_mismatch"),
            ({"workflow_id": 9999}, "run_binding_mismatch"),
            ({"head_repository": {"id": 9999}}, "run_binding_mismatch"),
            ({"repository": {"id": 9999}}, "run_binding_mismatch"),
            ({"referenced_workflows": [{"path": "mutable-reuse@main"}]},
             "run_binding_mismatch"),
        ):
            with self.subTest(change=change):
                self.api.responses[self.run] = dict(original, **change)
                self.assert_denied(reason)

    def test_failed_cancelled_queued_or_waiting_runs_never_satisfy_gate(self):
        for status, conclusion in (
            ("completed", "failure"), ("completed", "cancelled"),
            ("completed", "skipped"), ("waiting", None), ("pending", None),
            ("queued", None),
        ):
            with self.subTest(status=status, conclusion=conclusion):
                self.api.responses[self.run].update(status=status, conclusion=conclusion)
                self.assert_denied("run_not_approved")
        self.api.responses[self.run].update(status="completed", conclusion="success")
        self.verify()

    def test_registration_and_policy_changes_are_denied_before_api_access(self):
        original = self.registration
        for change, reason in (
            ({"manifest_digest": sha256_digest(b"other")}, "request_binding_mismatch"),
            ({"request_id": "unregistered-opaque-request"}, "request_binding_mismatch"),
            ({"repository_id": 9999}, "request_binding_mismatch"),
            ({"policy_snapshot_digest": sha256_digest(b"other")}, "policy_changed"),
            ({"run_attempt": 2}, "unsupported_run_attempt"),
        ):
            with self.subTest(change=change):
                self.registration = replace(original, **change)
                self.assert_denied(reason)
                self.assertEqual(self.api.calls, [])
        self.registration = original
        self.policy = replace(self.policy, evidence_ttl_seconds=60)
        self.assert_denied("policy_changed")

    def test_changed_parent_policy_or_manifest_needs_a_new_registration(self):
        self.manifest = replace(self.manifest, policy_digest=sha256_digest(b"new"))
        self.assert_denied("request_binding_mismatch")
        self.registration = replace(
            self.registration, manifest_digest=self.manifest.digest
        )
        self.assert_denied("policy_changed")

    def test_policy_identity_and_protection_drift_are_denied(self):
        original = deepcopy(self.api.responses[self.environment])
        for change in (
            {"id": 9999},
            {"name": "different-gate"},
            {"updated_at": date(NOW)},
            {"deployment_branch_policy": {
                "protected_branches": 0, "custom_branch_policies": 1,
            }},
            {"protection_rules": []},
        ):
            with self.subTest(change=change):
                self.api.responses[self.environment] = dict(original, **change)
                self.assert_denied("environment_policy_changed")
        self.api.responses[self.environment] = original
        original["protection_rules"][0]["prevent_self_review"] = True
        self.assert_denied("environment_policy_changed")

    def test_team_reviewer_policy_is_visibly_unsupported(self):
        reviewer = self.api.responses[self.environment]["protection_rules"][0]["reviewers"][0]
        reviewer["type"] = "Team"
        self.assert_denied("unsupported_reviewer_policy")

    def test_removed_reviewers_and_wildcard_or_extra_branches_are_denied(self):
        rule = self.api.responses[self.environment]["protection_rules"][0]
        reviewers = rule["reviewers"]
        rule["reviewers"] = []
        self.assert_denied("environment_policy_changed")
        rule["reviewers"] = reviewers
        path = self.environment + "/deployment-branch-policies"
        self.api.responses[path]["branch_policies"][0]["name"] = "*"
        self.assert_denied("environment_policy_changed")
        self.api.responses[path]["branch_policies"][0]["name"] = "main"
        self.api.responses[path]["branch_policies"].append(
            {"id": 44, "name": "other", "type": "branch"}
        )
        self.api.responses[path]["total_count"] = 2
        self.assert_denied("environment_policy_changed")

    def test_public_mutable_repository_name_alone_is_never_sufficient(self):
        self.api.responses[self.route]["id"] = 9999
        self.assert_denied("control_repository_mismatch")

    def test_control_visibility_workflow_state_and_current_ref_are_verified(self):
        self.api.responses[self.route]["private"] = True
        self.assert_denied("control_repository_mismatch")
        self.api.responses[self.route]["private"] = False
        self.api.responses[self.route + "/actions/workflows/1003"]["state"] = "disabled_manually"
        self.assert_denied("workflow_mismatch")
        self.api.responses[self.route + "/actions/workflows/1003"]["state"] = "active"
        self.api.responses[self.route + "/git/ref/heads/main"]["object"]["sha"] = "b" * 40
        self.assert_denied("trusted_ref_changed")

    def test_actual_workflow_bytes_are_checked_not_just_path_or_revision_label(self):
        path = self.route + "/contents/" + self.policy.workflow_path
        self.api.responses[path]["content"] = base64.b64encode(b"changed").decode()
        self.assert_denied("workflow_content_mismatch")
        self.api.responses[path]["content"] = "invalid base64!!!"
        self.assert_denied("workflow_content_unavailable")

    def test_installation_access_is_verified_and_truncation_is_never_ignored(self):
        path = "/installation/repositories"
        self.api.responses[path] = {"total_count": 0, "repositories": []}
        self.assert_denied("installation_repository_mismatch")
        self.api.responses[path] = {"total_count": 101, "repositories": []}
        self.assert_denied("github_evidence_incomplete")

    def test_self_review_policy_is_explicit_and_a_distinct_human_can_approve(self):
        self.policy = replace(self.policy, prevent_self_review=True)
        self.registration = replace(
            self.registration, policy_snapshot_digest=self.policy.digest
        )
        self.api.responses[self.environment]["protection_rules"][0]["prevent_self_review"] = True
        self.assert_denied("self_review_denied")
        self.api.responses[self.run]["actor"] = {"id": 2020}
        self.api.responses[self.run]["triggering_actor"] = {"id": 2020}
        self.verify()

    def test_run_predating_request_registration_cannot_be_relabelled(self):
        self.api.responses[self.run]["created_at"] = date(self.manifest.created_at - 1)
        self.assert_denied("stale_github_evidence")

    def test_stale_evidence_and_expired_requests_are_denied(self):
        self.policy = replace(self.policy, max_run_age_seconds=8)
        self.registration = replace(
            self.registration, policy_snapshot_digest=self.policy.digest
        )
        self.assert_denied("stale_github_evidence")
        self.now = self.manifest.expires_at
        self.assert_denied("request_not_valid")

    def test_policy_change_or_rerun_during_observation_is_denied(self):
        def mutate(path, count):
            if path == self.environment and count == 2:
                self.api.responses[path]["updated_at"] = date(NOW)

        self.api.on_get = mutate
        self.assert_denied("environment_policy_changed")
        self.setUp()

        def rerun(path, count):
            if path == self.run and count == 2:
                self.api.responses[path]["run_attempt"] = 2

        self.api.on_get = rerun
        self.assert_denied("run_attempt_mismatch")

    def test_changed_history_or_time_during_fetch_never_yields_fresh_evidence(self):
        def mutate(path, count):
            if path == self.run + "/approvals" and count == 2:
                self.api.responses[path][0]["comment"] = "changed"

        self.api.on_get = mutate
        self.assert_denied("github_evidence_changed")
        self.setUp()

        def advance_clock(path, count):
            if path == self.run + "/pending_deployments" and count == 2:
                self.now = NOW + 30

        self.api.on_get = advance_clock
        self.assert_denied("stale_github_evidence")

    def test_malformed_api_fields_are_closed_denials_not_python_type_errors(self):
        for path, key, value in (
            (self.route, "full_name", None),
            (self.run, "run_attempt", True),
            (self.run, "created_at", "not-a-timestamp"),
            (self.environment, "protection_rules", None),
            (self.environment, "deployment_branch_policy", None),
        ):
            with self.subTest(path=path, key=key):
                original = self.api.responses[path][key]
                self.api.responses[path][key] = value
                self.assert_denied("malformed_github_evidence")
                self.api.responses[path][key] = original
        self.api.responses[self.run + "/approvals"][0]["state"] = []
        self.assert_denied("malformed_github_evidence")

    def test_registry_profile_rejects_mutable_refs_and_ambiguous_human_ids(self):
        for change in (
            {"workflow_commit": "main"},
            {"trusted_ref": "refs/heads/release/*"},
            {"workflow_path": "../untrusted.yml"},
            {"repository_name": ".."},
            {"human_reviewer_ids": (1010, 1010)},
            {"human_reviewer_ids": (True,)},
            {"human_reviewer_ids": ()},
            {"max_run_age_seconds": 0},
            {"prevent_self_review": None},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(self.policy, **change)


class ReadClientTests(unittest.TestCase):
    def make_client(self, body=b"{}", *, status=200, headers=None, provider=None):
        response = requests.Response()
        response.status_code = status
        response.headers.update(headers or {})
        response.raw = BytesIO(body)
        session = Mock()
        session.get.return_value = response
        with patch(
            "fabric_delivery_core.github_approval.requests.Session", return_value=session
        ):
            client = GitHubReadClient(
                provider or (
                    lambda: GitHubInstallationToken("ghs_SYNTHETIC_NOT_A_SECRET", NOW + 10)
                ),
                clock=lambda: NOW,
            )
        self.addCleanup(client.close)
        return client, session

    def test_get_uses_explicit_app_token_tls_timeouts_and_no_ambient_auth(self):
        client, session = self.make_client(b'{"value":1}')
        self.assertEqual(client.get("/installation/repositories"), {"value": 1})
        self.assertFalse(session.trust_env)
        session.get.assert_called_once()
        args, kwargs = session.get.call_args
        self.assertEqual(args, ("https://api.github.com/installation/repositories",))
        self.assertIs(kwargs["allow_redirects"], False)
        self.assertIs(kwargs["verify"], True)
        self.assertEqual(kwargs["timeout"], (5, 20))
        self.assertEqual(
            kwargs["headers"]["Authorization"], "Bearer ghs_SYNTHETIC_NOT_A_SECRET"
        )
        self.assertNotIn("SYNTHETIC_NOT_A_SECRET", repr(
            GitHubInstallationToken("ghs_SYNTHETIC_NOT_A_SECRET", NOW + 10)
        ))

    def test_personal_tokens_and_expired_tokens_are_not_accepted(self):
        for value in ("ghp_SYNTHETIC", "github_pat_SYNTHETIC", "gho_SYNTHETIC"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                GitHubInstallationToken(value, NOW + 10)
        client, session = self.make_client(
            provider=lambda: GitHubInstallationToken("ghs_SYNTHETIC", NOW)
        )
        with self.assertRaisesRegex(AuthorizationDenied, "github_auth_unavailable"):
            client.get("/installation/repositories")
        session.get.assert_not_called()

    def test_stateless_installation_tokens_are_forwarded_unchanged(self):
        value = (
            "ghs_12345_eyJhbGciOiJSUzI1NiJ9."
            "eyJzeW50aGV0aWMiOnRydWV9.synthetic_signature-_"
        )
        client, session = self.make_client(
            b'{"total_count":0,"repositories":[]}',
            provider=lambda: GitHubInstallationToken(value, NOW + 10),
        )
        self.assertEqual(
            client.get("/installation/repositories"),
            {"total_count": 0, "repositories": []},
        )
        session.get.assert_called_once()
        self.assertEqual(
            session.get.call_args.kwargs["headers"]["Authorization"],
            "Bearer " + value,
        )
        self.assertNotIn(value, repr(GitHubInstallationToken(value, NOW + 10)))

    def test_malformed_installation_token_input_is_rejected_before_http(self):
        for value in (
            "ghs_", "ghs_valid\n", "ghs_valid\r\nX-Injected: value",
            "ghs_contains space", "ghs_nonascii_\u00e9", "ghu_SYNTHETIC",
        ):
            with self.subTest(value=value):
                client, session = self.make_client(
                    provider=lambda value=value: GitHubInstallationToken(value, NOW + 10)
                )
                with self.assertRaisesRegex(
                    AuthorizationDenied, "^github_auth_unavailable$"
                ):
                    client.get("/installation/repositories")
                session.get.assert_not_called()

    def test_api_errors_redirects_and_transport_details_never_leak(self):
        for status in (301, 302, 401, 403, 404, 429, 500):
            with self.subTest(status=status):
                client, _ = self.make_client(b"PRIVATE_RESPONSE", status=status)
                with self.assertRaisesRegex(AuthorizationDenied, "^github_api_unavailable$"):
                    client.get("/installation/repositories")
        client, session = self.make_client()
        session.get.side_effect = requests.ConnectionError("PRIVATE_CREDENTIAL_DETAIL")
        with self.assertRaisesRegex(AuthorizationDenied, "^github_api_unavailable$"):
            client.get("/installation/repositories")

    def test_incomplete_oversized_or_ambiguous_json_is_not_accepted(self):
        for body, headers, reason in (
            (b"{}", {"Link": '<https://untrusted.invalid/>; rel="next"'},
             "github_evidence_incomplete"),
            (b"{}", {"Link": '<https://untrusted.invalid/>; rel=next'},
             "github_evidence_incomplete"),
            (b"x" * 1_048_577, {}, "github_evidence_too_large"),
            (b'{"state":"rejected","state":"approved"}', {}, "github_api_unavailable"),
            (b'{"value":NaN}', {}, "github_api_unavailable"),
            (b"not-json-private-response", {}, "github_api_unavailable"),
        ):
            with self.subTest(reason=reason):
                client, session = self.make_client(body, headers=headers)
                with self.assertRaisesRegex(AuthorizationDenied, f"^{reason}$"):
                    client.get("/installation/repositories")
                session.get.assert_called_once()

    def test_untrusted_origins_and_relative_traversal_are_rejected_without_http(self):
        client, session = self.make_client()
        for path in (
            "https://untrusted.invalid/", "//untrusted.invalid/",
            "/repos/a/../installation/token", "/user",
            "/repos/a/%2e%2e/installation/token",
            "/installation/repositoriesAnything",
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                client.get(path)
        session.get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
