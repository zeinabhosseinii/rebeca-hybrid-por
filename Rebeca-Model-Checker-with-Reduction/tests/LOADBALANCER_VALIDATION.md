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

The earlier source-level hypothesis was that causal filtering might explain
these pairs. The actual generated C++ audit disproves that explanation here:
BOTH generated matrices contain them. All real cross-instance action pairs
agree. Do not remove these pairs just to match counts.

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


## Confirmed diagnosis from the uploaded generated C++

All four supplied generated C++ variants were rebuilt with g++ C++11/O2 on the
validation host. These local runs reproduced the supplied counts exactly:

| Run | States | Transitions | Outcome |
| --- | ---: | ---: | --- |
| Original baseline | 101 | 202 | satisfied |
| Static priorities | 22 | 26 | satisfied |
| ARIA AST | 38 | 52 | satisfied |
| Original imported JSON | 64 | 128 | satisfied |
| JSON with only nonexistent matrix slots cleared | 38 | 52 | satisfied |
| Original JSON with PO disabled, sender normalization retained | 64 | 128 | satisfied |

The original JSON trace has 106 candidates, 85 dependency blocks, 64 full
expansions and ZERO singleton trials. Of the 85 blocks, 84 name a nonexistent
message 2 on a relay; the other names a real hub action. Remaining candidates
have multiple alternatives. Thus 101 -> 64 is sender normalization, not an
ample-set reduction. The control build disabling PO confirms the same 64/128.

AST has 63 candidates, 25 dependency blocks, 28 singleton trials (26 accepted,
2 rejected by the closed-successor proviso), and 12 full expansions. Correcting
only invalid-ID cells in the supplied JSON C++ produces the exact same decision
trace, including state IDs and proviso rejections, as AST, and the same 38/52.
No real dependency or proviso condition was relaxed in this experiment.

The importer fix now initializes nonexistent slots to false, then marks every
pair of real model actions dependent before applying validated JSON rows.
Real model actions omitted from JSON retain conservative dependencies. COND,
same-instance dependency, source-hash validation and deadlock stopping remain.
The actual Java importer was compiled with JDK17/Gson and regression-tested for
holes versus omitted real actions, symmetric updates, COND preservation, and
no mutation on rejected source hashes. Full Java model generation on the clean
host remains blocked by the absent original compiler artifact; the C++ replay
and standalone importer tests are distinct validation steps.

The 22-state static run uses a different priority selection policy, rather than
the conservative global-action safety scan plus BFS proviso. Smaller count and
satisfied reachability alone do not prove that policy equivalent for arbitrary
properties. No change to priorities or dynamic guard evaluation was made.

The subsequent 38-versus-22 schedule-policy investigation is documented in
[LOADBALANCER_SCHEDULING.md](LOADBALANCER_SCHEDULING.md), with an executable
controlled replay script. No production scheduling policy is changed by it.

The later conservative alternative-equivalence rule and its validation are in
[QUEUE_ALTERNATIVES.md](QUEUE_ALTERNATIVES.md). Its generated-C++ replay retains
38 states in AST/JSON and reduces their transition counters from 52 to 46.
The historical tables above describe the solver before this change.
