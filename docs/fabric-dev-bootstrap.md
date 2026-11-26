# Bounded Dev Fabric bootstrap proof

On 2026-11-26 the human separately authorized owner-local inspection and creation
of one new Dev workspace and one schema-enabled Lakehouse. The existing active
trial and its region were explicitly selected; an invalid hyphenated Lakehouse
name was corrected with human approval before any write.
See [the scope and checklist](../openspec/changes/bootstrap-fabric-dev-pilot/tasks.md).

## What was actually verified

The workspace was created with explicit assignment to the selected existing
capacity. Direct readback confirmed its name, capacity ID and completed assignment.
The Lakehouse was created through the type-specific API with
`creationPayload.enableSchemas: true`; direct readback confirmed its name and
default `dbo` schema.

The SQL analytics endpoint was still `InProgress` at the immediate readback.
This is not evidence that a SQL query, notebook job or source load is ready or
has succeeded. No notebook, Spark session, Bronze table, source records, role/
identity grant, schedule, paid capacity start or new trial was requested.

Actual item IDs, capacity/account mapping and receipt remain private installation
evidence. The author's resources are not shared defaults or a service for adopters.
The command used the separately permitted owner-local CLI profile for bootstrap,
not an agent identity or execution of a native deployment approval.

## Reusable setup boundary

Another installation must independently authorize its exact target names,
existing capacity/region and administrative identity. Verify absence and
permissions before creation; never substitute a trial, start a paid capacity or
change unrelated resources from a successful readiness check.

Lakehouse names must start with a letter and contain only letters, digits and
underscores, up to 123 characters. Workspaces have a different naming rule:
do not silently change a Lakehouse name to match a workspace.
Schema support must be explicitly enabled in the REST creation payload.
See the [official Lakehouse creation guidance](https://learn.microsoft.com/fabric/data-engineering/create-lakehouse)
and [schema-enabled REST guidance](https://learn.microsoft.com/fabric/data-engineering/lakehouse-schemas#create-a-lakehouse-with-schemas-using-the-rest-api).

Track accepted operations, poll the same operation with a deadline, and retain
partial created resources if a later step fails. Do not retry POST blindly or
automatically delete/reassign resources. Tokens must never enter public Git or
model prompts; keep full responses/private mappings off public Git and unapproved
model/tool routes. The actual setup command is
not published as a released, supported installer.

## SQL-to-Bronze is the next separate pilot

The existing [compiler/worker contract](sql-bronze-module.md) still needs exact
private SQL metadata: approved server/database, source schemas/tables, ordered
columns/types/nullability, new target tables and finite row/time limits. Identity,
Key Vault references and effective source/target permissions must be verified;
do not provide secret values or source records to an agent.

That compiler currently requires distinct real Dev/Test/production mappings.
This Dev-only bootstrap does not authorize creating later environments or using
invented IDs. Supply separately approved actual mappings, or separately review
a genuine Dev-only compiler contract before compiling the live pilot release.

Obtain independent exact notebook deployment and source-read/data-load decisions.
Resource creation alone proves neither SQL authentication nor fixed-worker
behavior, hosted agents, execution-grant joining or delivery acceptance.
