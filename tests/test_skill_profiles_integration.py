from contextlib import closing
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sqlite3
import unittest
from uuid import uuid4

from fabric_delivery_core.authorization import SQLiteAuthorizationStore, sha256_digest
from fabric_delivery_core.dispatch import DispatchDenied, DispatchProfile
from fabric_delivery_core.registry_dispatch import SQLiteRegistryDispatchStore
from fabric_delivery_core.request_registry import RegistryDenied, SQLiteRequestRegistry
from fabric_delivery_core.skill_profiles import (
    OfflineSkillResolver,
    RoleSkillPolicy,
    RoleSkillProfile,
    SkillArtifact,
    SkillCatalog,
    SkillDenied,
    SkillRef,
    SkillSelection,
    SkillSnapshot,
    SkillSource,
)
from fabric_delivery_core.spend import PriceCard, SpendBudget, SQLiteSpendStore
from test_authorization import NOW, approval
from test_request_registry import policy, request


class SkillProfilesIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path.cwd() / ".test-state" / str(uuid4())
        self.directory.mkdir(parents=True)
        self.addCleanup(self.clean)
        self.registry = SQLiteRequestRegistry(
            self.directory / "registry.sqlite3", clock=lambda: NOW,
        )
        self.auth = SQLiteAuthorizationStore(
            self.directory / "auth.sqlite3", clock=lambda: NOW,
        )
        self.spend = SQLiteSpendStore(
            self.directory / "spend.sqlite3", clock=lambda: NOW,
        )
        self.request_policy = policy()
        self.registry.register_policy(self.request_policy)
        self.period = datetime.fromtimestamp(NOW, timezone.utc).strftime("%Y-%m")
        self.budget = SpendBudget(
            self.request_policy.installation_id, self.period, "USD", "synthetic-v1",
            10, 4, 1,
        )
        self.price = PriceCard(
            "synthetic-operation", "synthetic-v1", "USD", NOW - 10, NOW + 100, 1, 1,
        )
        self.spend.configure_budget(self.budget)
        self.spend.register_price(self.price)
        self.dispatch_profile = DispatchProfile(
            sha256_digest(b"fixed synthetic worker"), self.budget.digest,
            self.price.digest, self.price.operation, self.price.version,
            self.period, "USD", 4, 1, 20,
        )
        self.queue_path = self.directory / "queue.sqlite3"
        self.store = self.open_dispatch()

        # Origins, immutable OIDs and interface labels are synthetic declarations only.
        self.primary_source = SkillSource("synthetic-primary", "https://primary.invalid")
        self.secondary_source = SkillSource("synthetic-secondary", "https://secondary.invalid")
        self.primary = SkillRef(self.primary_source.source_id, "synthetic-core")
        self.secondary = SkillRef(self.secondary_source.source_id, "synthetic-review")
        self.extra = SkillRef(self.primary_source.source_id, "synthetic-extra")
        self.skill_policy = RoleSkillPolicy(
            "synthetic-role-policy", "v1", "synthetic-role", "synthetic-interface",
            (self.primary_source, self.secondary_source),
            (self.primary, self.secondary, self.extra), (self.primary,),
        )
        self.skill_profile = RoleSkillProfile(
            "synthetic-role-profile", "v1", "synthetic-role",
            (SkillSelection(self.primary), SkillSelection(self.secondary)),
        )
        self.primary_artifact = self.artifact(
            self.primary, self.primary_source, "a" * 40,
            "# Synthetic guidance\napprove/grant/install are inert words.\n",
        )
        self.secondary_artifact = self.artifact(
            self.secondary, self.secondary_source, "b" * 40, "# Synthetic review\n",
        )
        self.extra_artifact = self.artifact(
            self.extra, self.primary_source, "c" * 40, "# Synthetic extra\n",
        )
        self.catalog = SkillCatalog((
            self.primary_artifact, self.secondary_artifact, self.extra_artifact,
        ))
        self.resolver = OfflineSkillResolver(self.skill_policy)
        self.initial = self.resolver.resolve(self.skill_profile, self.catalog).snapshot
        self.current, self.binding = self.register_snapshot(self.initial, authorized=True)
        self.pending, _ = self.register_snapshot(self.initial, authorized=False)

    def clean(self):
        shutil.rmtree(self.directory)
        try:
            self.directory.parent.rmdir()
        except OSError:
            pass

    @staticmethod
    def artifact(ref, source, revision, content, sequence=1):
        return SkillArtifact(
            ref, source.origin, revision, sequence, content,
            sha256_digest(content.encode("utf-8")), ("synthetic-interface",),
        )

    def open_dispatch(self):
        return SQLiteRegistryDispatchStore(
            self.queue_path, self.registry, self.auth, self.spend, clock=lambda: NOW,
        )

    def register_snapshot(self, snapshot, *, authorized):
        proposed = request(self.request_policy)
        current = replace(proposed, manifest=replace(
            proposed.manifest, skill_snapshot_digest=snapshot.digest,
            execution_profile_digest=self.dispatch_profile.digest,
        ))
        self.registry.register(current)
        self.auth.freeze(current.manifest)
        binding = None
        if authorized:
            # Externally supplied synthetic approval fixture, NEVER resolver-derived authority.
            binding = replace(approval(current.manifest), run_id=str(uuid4()))
            self.auth.authorize(current.manifest.request_id, binding)
        return current, binding

    def ledger_state(self):
        """Compare complete persisted data, including grants, reservations and outbox rows."""
        result = []
        for path in (self.registry.path, self.auth.path, self.spend.path, self.queue_path):
            with closing(sqlite3.connect(path)) as db:
                result.append(tuple(db.iterdump()))
        return tuple(result)

    def assert_no_execution(self, current, state="authorized"):
        request_id = current.manifest.request_id
        self.assertIsNone(self.auth.receipt(request_id))
        with closing(sqlite3.connect(self.auth.path)) as db:
            self.assertEqual(db.execute(
                "SELECT state FROM requests WHERE request_id=?", (request_id,),
            ).fetchone()[0], state)
        monthly = self.spend.monthly_state(self.request_policy.installation_id, self.period)
        self.assertEqual(monthly["outstanding_units"], 0)
        self.assertEqual(monthly["settled_units"], 0)
        with self.assertRaisesRegex(DispatchDenied, "^unknown_dispatch$"):
            self.store.receipt(request_id)

    def assert_durable_drift_denial(self, current, binding, snapshot):
        self.assertNotEqual(snapshot.digest, current.manifest.skill_snapshot_digest)
        changed = replace(current, manifest=replace(
            current.manifest, skill_snapshot_digest=snapshot.digest,
        ))
        # RoleSkillPolicy is not RequestPolicy: the latter's binding must stay intact.
        self.assertEqual(changed.manifest.policy_digest, self.request_policy.digest)
        before = self.ledger_state()[1:]
        with self.assertRaisesRegex(RegistryDenied, "^registry_request_changed$"):
            self.store.enqueue(changed, binding, self.dispatch_profile)
        self.registry = SQLiteRequestRegistry(self.registry.path, clock=lambda: NOW)
        self.auth = SQLiteAuthorizationStore(self.auth.path, clock=lambda: NOW)
        self.spend = SQLiteSpendStore(self.spend.path, clock=lambda: NOW)
        self.store = self.open_dispatch()
        denied = self.registry.inspect(current.manifest.request_id)
        self.assertEqual(denied.state, "invalidated")
        self.assertEqual(denied.reason, "registry_request_changed")
        self.assertEqual(denied.request, current)
        with self.assertRaisesRegex(RegistryDenied, "^registry_request_changed$"):
            self.store.enqueue(current, binding, self.dispatch_profile)
        self.assertEqual(self.ledger_state()[1:], before)
        self.assert_no_execution(current)

    def test_allowed_edits_content_and_load_order_permanently_deny_approved_run(self):
        newer = self.artifact(
            self.primary, self.primary_source, "d" * 40, "# New synthetic content\n", 2,
        )
        edited_content = "# Manually edited synthetic guidance\n"
        edited = replace(
            self.primary_artifact, content=edited_content,
            content_digest=sha256_digest(edited_content.encode("utf-8")),
        )
        variants = (
            ("allowed addition", replace(self.skill_profile, selections=(
                *self.skill_profile.selections, SkillSelection(self.extra),
            )), self.catalog),
            ("load order", replace(
                self.skill_profile, selections=tuple(reversed(self.skill_profile.selections)),
            ), self.catalog),
            ("new content and catalog", self.skill_profile, SkillCatalog((
                *self.catalog.artifacts, newer,
            ))),
            ("edited bytes at same declared OID", self.skill_profile, SkillCatalog((
                edited, self.secondary_artifact, self.extra_artifact,
            ))),
        )
        for name, profile, catalog in variants:
            with self.subTest(change=name):
                current, binding = self.register_snapshot(self.initial, authorized=True)
                result = self.resolver.resolve(profile, catalog)
                self.assertFalse(result.used_last_known_good)
                self.assert_durable_drift_denial(current, binding, result.snapshot)

    def test_sealed_snapshot_bytes_survive_future_resolutions_and_policy_changes(self):
        sealed = self.initial.to_json().encode("utf-8")
        restored = SkillSnapshot.from_json(sealed.decode("utf-8"))
        before = self.ledger_state()
        reordered = replace(
            self.skill_profile, selections=tuple(reversed(self.skill_profile.selections)),
        )
        self.resolver.resolve(reordered, self.catalog)
        newer = self.artifact(
            self.primary, self.primary_source, "d" * 64, "# Future synthetic text\r\n", 2,
        )
        self.resolver.resolve(self.skill_profile, SkillCatalog((
            *self.catalog.artifacts, newer,
        )))
        revised_policy = replace(self.skill_policy, version="v2")
        OfflineSkillResolver(revised_policy).resolve(self.skill_profile, self.catalog)
        fallback = self.resolver.resolve(
            self.skill_profile, SkillCatalog(()), last_known_good=restored,
        )
        self.assertTrue(fallback.used_last_known_good)
        self.assertEqual(fallback.snapshot.fallback_snapshot_digest, restored.digest)
        self.assertNotEqual(fallback.snapshot.digest, restored.digest)
        self.assertEqual(self.initial.to_json().encode("utf-8"), sealed)
        self.assertEqual(restored.to_json().encode("utf-8"), sealed)
        self.assertEqual(restored.digest, self.initial.digest)
        self.assertEqual(self.ledger_state(), before)

    def test_success_quarantine_fallback_and_guidance_never_change_real_ledgers(self):
        bad = replace(
            self.primary_artifact, revision="e" * 40, release_sequence=2,
            content_digest=sha256_digest(b"not the supplied content"),
        )
        scenarios = (
            ("success", self.catalog, None, False, False),
            ("quarantine", SkillCatalog((*self.catalog.artifacts, bad)), None, False, True),
            ("fallback", SkillCatalog((bad,)), self.initial, True, True),
        )
        for name, catalog, previous, used_fallback, quarantined in scenarios:
            with self.subTest(resolution=name):
                before = self.ledger_state()
                result = self.resolver.resolve(
                    self.skill_profile, catalog, last_known_good=previous,
                )
                self.assertEqual(result.used_last_known_good, used_fallback)
                self.assertEqual(bool(result.quarantined), quarantined)
                self.assertEqual(result.snapshot.artifacts[0].content, self.primary_artifact.content)
                self.assertEqual(self.ledger_state(), before)
                self.assertEqual(self.registry.inspect(self.current.manifest.request_id).state, "proposed")
                self.assert_no_execution(self.current)
                self.assert_no_execution(self.pending, "pending")
        before = self.ledger_state()
        with self.assertRaises(SkillDenied):
            self.resolver.resolve(self.skill_profile, SkillCatalog((bad,)))
        self.assertEqual(self.ledger_state(), before)

    def test_resolution_and_snapshot_are_not_approval_bindings_for_dispatch(self):
        result = self.resolver.resolve(self.skill_profile, self.catalog)
        drifted = replace(self.current, manifest=replace(
            self.current.manifest, skill_snapshot_digest=sha256_digest(b"changed skills"),
        ))
        before = self.ledger_state()
        for operation in (self.store.enqueue, self.store.claim):
            for current in (self.current, self.pending, drifted):
                for not_approval in (result, result.snapshot):
                    with self.subTest(
                        operation=operation.__name__, request_id=current.manifest.request_id,
                        value=type(not_approval).__name__,
                    ):
                        with self.assertRaisesRegex(DispatchDenied, "^dispatch_invalid_inputs$"):
                            operation(current, not_approval, self.dispatch_profile)
        self.assertEqual(self.ledger_state(), before)
        self.assert_no_execution(self.current)
        self.assert_no_execution(self.pending, "pending")

    def test_removed_source_required_change_and_pin_cannot_reuse_lkg_authority(self):
        pinned_artifact = self.artifact(
            self.primary, self.primary_source, "f" * 40, "# Pinned synthetic content\n", 2,
        )
        variants = (
            ("removed source", replace(
                self.skill_policy, approved_sources=(self.primary_source,),
                allowed_skills=(self.primary, self.extra),
            ), replace(self.skill_profile, selections=(SkillSelection(self.primary),)), self.catalog),
            ("new requirement", replace(
                self.skill_policy, required_skills=(self.primary, self.extra),
            ), replace(self.skill_profile, selections=(
                *self.skill_profile.selections, SkillSelection(self.extra),
            )), self.catalog),
            ("manual pin", self.skill_policy, replace(self.skill_profile, selections=(
                SkillSelection(self.primary, pinned_artifact.revision),
                SkillSelection(self.secondary),
            )), SkillCatalog((*self.catalog.artifacts, pinned_artifact))),
        )
        sealed = self.initial.to_json()
        for name, skill_policy, profile, catalog in variants:
            with self.subTest(change=name):
                resolver = OfflineSkillResolver(skill_policy)
                before = self.ledger_state()
                with self.assertRaises(SkillDenied):
                    resolver.resolve(profile, catalog, last_known_good=self.initial)
                self.assertEqual(self.ledger_state(), before)
                current, binding = self.register_snapshot(self.initial, authorized=True)
                result = resolver.resolve(profile, catalog)
                self.assertFalse(result.used_last_known_good)
                self.assert_durable_drift_denial(current, binding, result.snapshot)
                self.assertEqual(self.initial.to_json(), sealed)


if __name__ == "__main__":
    unittest.main()
