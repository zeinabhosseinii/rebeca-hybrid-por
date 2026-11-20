# LoadBalancerSmall validation

The input preserves the user-provided model: source/relay counters wrap after 2,
hub load counters wrap after 3. The original larger LoadBalancer is retained.

The standalone ARIA run with JDK 17 completed successfully:

- 7 actions; 28 unordered action pairs including diagonal.
- 18 INDEPENDENT, 10 ALWAYS, 0 COND.
- Priority-annotated model and source-hashed JSON generated successfully.

These are static-analysis results, not measured state-space sizes. This model
cannot exercise runtime conditional-dependency pruning because no pair is COND.
The balance sentence in the source is a comment, not a checked assertion/LTL
property. The default dynamic check covers deadlock/deadline reachability.

RMC generation could not be run on the clean validation host: the dependency
`org.rebecalang:compiler:LATEST` is not in its Maven cache or bundled repository.
Use the same compiler artifact as the user's successful desktop build to avoid
silently changing compiler semantics. The user reports 101 baseline states;
that number is not yet reproduced on this host.

Run `bash tests/compare_loadbalancer.sh` on the desktop with that dependency.
It prints baseline, static priorities, ARIA AST, ARIA JSON results separately.
It runs no terminal-skipping mode: every deadlock still throws and stops.
Equal property outcomes are a regression check, not proof of POR correctness.
Transition totals may include attempted transitions during POR fallback.

## Investigation of the desktop results 38 / 64 / 22

The user supplied completed results: baseline 101/202, static 22/26,
ARIA AST 38/52, ARIA JSON 64/128 (states/transitions); all satisfied.

Two cross-instance dependencies in the exported JSON are:

- Hub.ReceiveSecondary <-> Bootstrapper.Initialize: ALWAYS
- Hub.ReceivePrimary <-> Bootstrapper.Initialize: ALWAYS

The internal AST SDI predicate excludes causally related actions; the exporter
retains these two shared-destination conflicts. Thus the two relations do not
have identical definitions. Do not remove these pairs just to match counts.

The importer also initializes unused per-class message-ID slots as dependent.
The current global-ID safety scan considers such slots. With max ID 2 and five
instances having only one message server, this should reject every singleton
candidate, contradicting the observed partial reduction. Inspect actual generated
C++, not only current Java/templates: the generator may have emitted a different
predicate/matrix. No stale-artifact cause has been established yet.

The static run enforces actor priorities PrimarySrc=1, SecondarySrc=2,
PrimaryRelay=3, SecondaryRelay=4, Hub=5, Bootstrapper=6 and hub method priorities
ReceiveSecondary=1, ReceivePrimary=2. It chooses among highest-priority enabled
actors/messages, whereas the unannotated dynamic runs choose a singleton only
when safety/alternatives/proviso allow it. This is a different selection policy;
22 states does not by itself show the dynamic policy is incorrect.

`python3 tests/audit_loadbalancer.py` reads existing generated C++ to export both
matrices and their differences, unused-ID blockers, candidate order, actual
safety functions and static initialization. No Java compiler is needed.
`bash tests/diagnose_loadbalancer.sh` preserves a before audit, regenerates with
POR_DIAGNOSTICS, and packages matrices/C++/reports/traces in a ZIP. Diagnostic
traces identify candidate alternatives, the first dependency blocker, closed
successors rejecting the proviso, accepted singleton trials, and full fallback.
The added logging does not change dependency decisions or deadlock behavior.
