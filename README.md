# Fabric Delivery OS

Specification-first, human-governed delivery for Microsoft Fabric.

## Status

This repository currently contains design proposals, not a working agent platform.
Creating repositories or completing OpenSpec documents does not approve any
implementation, build, infrastructure change, or deployment.

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
