# Fabric Delivery OS

Specification-first, human-governed delivery for Microsoft Fabric.

## Status

The first bounded implementation is `fabric-delivery-core`, a Python 3.11+
library for immutable request binding and durable, atomic, single-use grant
consumption. This core build was explicitly authorized on 2026-11-17.
It is **not a working agent platform or a deployed authorization service**.
The broader OpenSpec design remains proposed; builds and each deployment still
require their applicable human authorization.

## Authorization core

- Validated frozen manifests bind SHA-256 input/artifact, policy, baseline,
  runtime, workflow, tool, skill, environment, action, and explicit effects.
- A private local SQLite file persists pending, authorized, consumed, revoked,
  and invalidated requests across processes and restarts.
- Consumption permanently denies expiry, revocation, replay, changed approved
  inputs, or mismatched protected-run evidence. One concurrent claimant wins.
- Approval bindings are supplied by a **trusted adapter after external native
  human-gate and identity verification**. Constructing a Python object is not
  human approval. The library grants no credentials and launches no workers.

See [API usage, lifecycle, and trust boundaries](docs/authorization-core.md).
There are no runtime dependencies. From the repository root in PowerShell:

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
```

Tests use only synthetic data and project-local SQLite files, then clean them up.
For packaging with already available build tools:

```powershell
python -m pip wheel --no-build-isolation --no-deps --wheel-dir .build\dist .
```

Build tooling requires setuptools 68+ (and wheel for older setuptools); package
installation is separate from tests. No cloud access, model calls, source
queries, approval adapter, or model-agent loop is included. Microsoft Agent
Framework and Foundry remain the intended future model runtime.

## Three-repository architecture

| Repository | Visibility | Responsibility |
| --- | --- | --- |
| Framework | Public | Reusable runtime contracts, modules, skills integration, and specifications |
| Installation control | Public | Trusted native GitHub approval gates for one installation |
| Solution | Private | Issues, solution specifications, implementation, and private delivery evidence |

GitHub Free supports native required-reviewer gates in the public control
repository. Private solution workflows do not inherit that protection merely by
calling a public reusable workflow.

Agents cannot approve work, administer approval rules, or obtain credentials
that bypass the trusted control plane. Every build requires an approved build
request. Every deployment to development, test, or production requires its own
explicit human approval.

Public control runs expose their existence and timing. They must not contain
solution code, source metadata, prompts, records, or private logs.

## Specification workflow

Draft proposals live under `openspec/changes`. They remain unapproved until a
human explicitly reviews the applicable revision. OpenSpec validation checks
document structure; it does not prove security or authorize implementation.

Skills update automatically from approved sources, with a reproducible snapshot
for each run. Framework and control-plane upgrades are separate reviewed changes.
