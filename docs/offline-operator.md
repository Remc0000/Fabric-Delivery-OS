# Offline operator and integrated package

The package combines immutable requests/single-use local claims, local spend
accounting, read-only GitHub native approval observation and official-JWKS OIDC
verification. This is a working bounded library, **not the original complete
issue-to-Fabric runtime, installer, or live authorization service**.

## Installation and commands

Use Python 3.11+ and your organization's approved package source. From a reviewed
checkout, `python -m pip install .` installs the standard-library authorization,
spend and operator code. `python -m pip install ".[github]"` adds Requests for
native API observation; `python -m pip install ".[oidc]"` also adds PyJWT/crypto.
Installations are operator actions, not actions performed by the CLI.

```powershell
fabric-delivery validate-manifest "D:\PrivateInstallation\manifest.json"
fabric-delivery preflight --manifest "D:\PrivateInstallation\manifest.json" --spend-plan "D:\PrivateInstallation\offline-spend.json"
fabric-delivery self-test-dispatch
```

`python -m fabric_delivery_core` is equivalent. Paths are placeholders: supply
ordinary local files in private storage, not real configuration committed here.
UNC paths are rejected; do not use mapped network drives. Inputs are bounded to
1 MiB UTF-8 JSON. Manifest validation and preflight use no credential flags,
environment credentials, API clients, ledger access, state writes, approvals,
reservations, workers or network calls. Installed Python packages and
filesystem/runtime integrity are trusted.

All commands emit one JSON object with generic closed check/reason codes.
No input identifiers, values, digests, paths, exceptions or raw credentials are
echoed, including invalid command arguments. Output includes
`scope: "offline_only"`, `execution_enabled: false`, `live_execution:
"unsupported"` and explicit live blockers. Keep actual input files private.

| Command/result | Exit | Meaning |
| --- | --- | --- |
| `validate-manifest`, valid and current | 0 | Local frozen schema and `[created_at, expires_at)` validity only |
| Any command, invalid/missing/unknown local input, import or self-test failure | 2 | Offline check failed; no permission follows |
| `preflight`, all requested offline checks pass | 3 | Live readiness still blocked; **never use this as a deployment gate success** |
| `self-test-dispatch`, inert local cycle passes | 0 | Synthetic temporary storage only, not a human/worker/readiness proof |

`self-test-dispatch` accepts no installation inputs. Unlike the two read-only
checks, it creates and removes fresh disposable SQLite stores and uses synthetic
approval fixtures only there. It exercises enqueue, restart, one claim, inert
completion, settlement and replay denial. See [the dispatch guide](durable-dispatch.md).
It emits the same explicit live-blocked output; no live approval or worker starts.

Help exits 0 without checking readiness. The immutable manifest schema is
described in [authorization-core.md](authorization-core.md). Validation does not
rehash underlying files or prove that supplied digests represent real inputs,
approved policy, a current target or an actual person.

Preflight checks Requests, PyJWT and cryptography importability and supported
stable version ranges, matching the `oidc` extra. Missing extras block this
full-evidence-library profile; they do not prevent base manifest validation.
These checks do not prove package origin or supply-chain integrity.

## Private offline spend-plan format

This narrow version-1 **offline input**, not a full installation schema, has
exactly these top-level keys; duplicates, unknown/missing keys and nonfinite JSON
are invalid:

- `schema_version`: integer `1`.
- `budget`: exact `SpendBudget` fields: `installation_id`, `period`, `currency`,
  `version`, `cap_units`, `max_tokens`, `max_calls`.
- `price`: exact `PriceCard` fields: `operation`, `version`, `currency`,
  `valid_from`, `valid_until`, `token_units`, `call_units`.
- `max_tokens`: nonnegative integer for this prospective operation.
- `max_calls`: positive integer for this prospective operation.

Money uses integer **10^-9 currency units**, never float currency amounts.
See [spend-guardrails.md](spend-guardrails.md) for all field constraints and
conservative all-in pricing obligations. No real price/card is supplied here.

Preflight checks the installation matches the manifest, budget/card currencies
match, the UTC month is current, card validity includes now, requested token/call
bounds fit the policy, and the same conservative maximum used by the ledger fits
the supplied cap. No plan means `unknown`, not permitted. This checks only
arithmetic/schema/binding, **not authentic pricing, operation permission, existing
reservations, settled usage, real headroom, adapter enforcement or invoice cost**.
It does not register or reserve the supplied budget/card.

## Reusable interface and scope

`fabric_delivery_core.preflight.validate_manifest(path)` and
`preflight(manifest_path, spend_plan_path=None)` return immutable `OfflineReport`
objects with typed checks and an allowlisted `to_json()`. Their clock override
is for deterministic tests, never caller-controlled live policy. Results are
diagnostic, not self-authenticating evidence. Both paths always report live
execution unsupported even when `offline_checks_passed` is true.

Cross-component tests verify durable separate-ledger replay/breach behavior,
wrong-database rejection, shared native/OIDC bindings and the fact that neither
successful observation can become an approval binding. Synthetic signing keys,
HTTP evidence and externally attested approval fixtures are not live human
approvals or installation acceptance. Sequential standalone ledger calls still
can strand state. The separate [local outbox](durable-dispatch.md) now coordinates
grant consumption, reservation and ready state atomically under its documented
single-host rollback-journal constraints; it does not supply a live adapter.

## Next trusted-adapter boundary

Before effects can be enabled, separately reviewed integration must:

1. Establish an authoritative private issue/request/policy registry and prove
   the real integration/runtime App identity and role separation. Rehash actual
   private inputs, artifacts, policy, target baseline and runtime snapshots.
2. Measure actual installation OIDC claims through a separately human-enabled
   control test. Bind exact subject/context/immutable identities; GitHub does not
   sign private workflow inputs or the private manifest digest.
3. Join fresh native-human approval and verified OIDC evidence to that registered
   request; independently verify disabled administrative bypass and human
   credential isolation. Unknown evidence remains denied; signed reruns do not
   overcome native history's missing attempt attribution.
4. Integrate and independently verify the local outbox or a separately reviewed
   production equivalent, including real storage durability, authenticated
   claims, cancellation and ambiguous effects. The local coordinator does not
   prove this live integration. Never relaunch from a receipt or release unknown cost.
5. Add isolated Microsoft Agent Framework/Foundry execution and mediated tools,
   trusted complete usage, fixed separately authorized Dev/Test/Prod workers,
   and approved Fabric ingestion/Lakehouse/semantic-model/report modules.
6. Pass separately authorized live negative tests and human end-to-end
   acceptance before activation. Cloud foundation existence, successful imports
   and synthetic tests do not satisfy these prerequisites.
