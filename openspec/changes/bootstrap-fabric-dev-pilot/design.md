## Exact human scope and private bindings

The selected trial is already active. Its actual ID, account association, region,
target names and created item IDs are private installation evidence, not public
configuration. The human explicitly approved the region before creation.
The existing owner-local CLI profile was separately authorized; tokens must never
be printed, written into source or supplied to model/agent tools.

This is bootstrap using the owner's administrative context, not execution of a
native deployment approval or a reusable agent credential. No execution grant,
worker identity, GitHub human evidence conversion or bypass claim is created.

## Preconditions and effects

Recheck the exact selected capacity's SKU/active state and region, and verify
absence of the requested workspace. Fail on ambiguity or unexpected existing
state instead of modifying, adopting, deleting or overwriting resources.

Create one workspace with explicit capacity assignment. Verify the returned
workspace ID/name, capacity and completed assignment before Lakehouse creation.
Create one Lakehouse through the documented type-specific API with
`creationPayload.enableSchemas: true`; verify its metadata and default schema.
The SQL analytics endpoint and default schema are platform-provisioned side
effects, not permission to read records or create Bronze tables.

Every Fabric API call carries the skill attribution header. Capture any accepted
operation ID before polling; use bounded same-operation polling, no POST retries.
If a later step fails, preserve and privately report earlier created resources.
Do not automatically delete a workspace, reassign capacity or retry creation.

## Deliberately incomplete

No paid capacity start/purchase, trial extension, global settings, role grants,
App/workspace identity creation, source access, Spark session, notebook or data
load is authorized. Metadata verification establishes installation resources
only, not actual SQL authentication, schema compatibility or worker behavior.

The SQL-to-Bronze pilot still needs an exact private source contract, finite
table/column/row scope, runtime and narrowly scoped identities. Its compiler
currently binds all three stage mappings; do not invent Test/production IDs or
create those environments from this Dev-only approval. Exact release and
independent notebook deployment/load decisions remain prerequisites.
