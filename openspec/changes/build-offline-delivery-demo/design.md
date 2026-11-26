## Authorized boundary

The public entry point takes no inputs. It creates only fresh temporary synthetic
SQLite files, using the platform temporary location and removing its own files
after success or failure. It never opens an installation store. All local clocks
are fixed at one actual timestamp for a bounded repeatable demonstration.

The demo supplies synthetic metadata, role/source/format declarations, budget,
prices, complete discover manifests and test-only ApprovalBindings. It does not
authenticate a human, convert evidence into a live grant, download/load skills,
run an agent or perform any effect named in real solution policy.

## Three isolated scenarios

The successful scenario binds supplied capture and resolved skill snapshot,
registers a proposed discover request, freezes the manifest, and proves enqueue
denied while authorization is pending. Only then it records an explicit test
grant in its temporary authorization file. Four-file preparation consumes that
grant and reserves maximum cost. Fresh store instances claim once, reject a
second claim, record a fixed inert local result and complete trusted synthetic
usage. Grant replay is refused; terminal state and settled usage are checked.

Two additional fresh scenarios prepare otherwise valid work. One changes the
resolved skill snapshot; one changes the capture revision. Claim must reject
with the expected registry drift denial and commit blocked/invalidated state.
Reopening stores and restoring old inputs must not revive work. The consumed
grant and full reservation remain; no fake zero usage or refund is supplied.

Any absent/unexpected denial, wrong stored outcome, storage exception or
component failure prevents a successful report. The existing operator's closed
error boundary reports exit 2 without private values. Success reports exit 0 for
the rehearsal only, reusing OfflineReport with execution disabled and every
unchanged live blocker. No raw payloads, IDs, hashes, paths or errors are printed.

## Verification and next live boundary

Focused tests exercise the complete real-store flow, input refusal, component
failure, missing denial and missing terminal result, with no network. Validate
the actual installed wheel and module entry point outside the source checkout.

A separately scoped Dev SQL-to-Bronze pilot can precede full hosted agents, but
needs explicit private source metadata, target/workspace/Lakehouse baselines,
capacity/runtime/identity verification and independent deployment/load grants.
This rehearsal completes none of those requirements or Dev/Test/production gates.
