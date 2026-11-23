# Assertion observations: inspected scope and proof obligations

Historical diagnostic checkpoint: a restricted production integration now exists;
see [INVARIANT_GATE_INTEGRATION.md](INVARIANT_GATE_INTEGRATION.md). Statements
below about no runtime integration describe that earlier checkpoint.

This work adds an OFFLINE typed-AST audit and an adversarial finite-graph check.
It does not change the runtime gate, dependency matrix, candidate selection,
proviso or first-error handling. All reports explicitly set
`runtime_independence_certified=false`. A syntactically supported predicate is
not an assertion proved true and is not an independence certificate.

## What was implemented and tested

`AssertionObservationAudit.java` uses the real compiler 2.27 AST via the packaged
RMC dependencies. It recognizes the builtin assertion by its compiler label,
examines typed predicates, and lists local state-field reads and potential
same-class runtime writers. Compiler labels distinguish state fields from
parameters/locals. No expression-string evaluation or regex parsing of source
predicates is used. Plain suffixes and compiler-produced timed suffix objects
with BOTH time expressions absent are recognized; explicit timing remains outside
the supported call shape.

The initial predicate grammar deliberately covers scalar byte/short/int/boolean
constants and local state fields, comparisons/equality, boolean conjunction/
disjunction and logical negation. Calls, assignment/increment, arithmetic,
array access, nonlocal/dot reads, parameters, time/sender/self references and
unknown extensions are rejected. Well-typed source is compiled first. An
unsupported predicate can have only a partial reported read list, marked by
`read_footprint_complete=false`; that list is never a certificate.

Constructor/handler traversal records possible writes through assignments and
increments, visits conditionals/while bodies and call arguments, and fails closed
on opaque nodes/effects. Unknown method effects are shown as potential writers.
`traversal_complete` describes the diagnostic walk, not termination, absence of
time, property validity or independence. Inheritance/unsupported model constructs
make the report incomplete. Writer entries include the asserting handler itself;
an internal write before an assertion is not by itself a reason to reject an
atomic action. The relevant obligation concerns complete actions/occurrences and
the continuations that can run before a selected action.

The compiled-actor checks find six local predicate shapes in the healthy fixture
and seven in the fault fixture. All are syntactically supported, including the
intentionally false-at-runtime condition: shape support clearly is not truth.
The mixed negative fixture accepts the shapes of `x>=0` and `assertion(false)`
while rejecting increment, division, now, parameter and indexed-array predicates.
All current production barrier-gate reports remain false for these assertion
fixtures. The runtime gate was neither loosened nor replaced by this tool.

Concrete healthy footprints include:

| Assertion field | Asserting handlers | Potential same-class writers |
|---|---|---|
| Worker0.cycle | Tick | Tick |
| Worker1.cycle | Tick | Tick |
| Hub.count | Step0, Step1 | Step0, Step1 |
| Hub.done | Finish0, Finish1 | Finish0, Finish1 |

The bound assertions use fields that change at runtime. Their validity needs an
invariant/transition argument; being local and pure does not establish it. The
existing ERDG read collector does traverse ordinary call arguments, so this
inspection does not establish a general missing-assertion-read bug. In particular,
its existing global matrix still does not justify splitting different handlers
of the SAME actor.

## Counterexample: cycle condition alone is insufficient

The executable finite example models two messages of one actor: Set writes x=1,
and Check asserts x==0. Initially x=0 and both are pending. A full execution can
choose Set then Check and reach assertion failure. A hypothetical rule selecting
Check first can instead execute Check, Set and an exhaustive Idle loop, losing
that error. Its remaining cycle DOES contain a full expansion: the strong cycle
condition passes. Nevertheless the two orders have different destinations
(normal versus error), and the persistent/relational-diamond checker rejects the
choice with `diamond_failed`.

This is an adversarial counterexample to a proposed purity-only rule, not evidence
that the current unsplit-actor implementation makes that choice. The actual
runtime gate and same-actor union remain intact. It proves why merely accepting
local predicates in the time-shape scanner would be an inadequate correctness
argument for a new action certificate.

## Conditions needed before runtime support

1. Define the observed failure precisely. A source assertion can fail DURING an
   atomic handler; its failure transition/error outcome cannot be replaced by
   evaluating a state predicate only before or after the complete handler.
2. Establish typed, side-effect-free, total predicate evaluation with resolved
   storage identities. The current AST audit covers only the restricted grammar
   above. It proves neither surrounding action termination nor a range invariant.
3. Make action independence/persistence error-aware: every deferred continuation
   must preserve selected-action enabledness, relevant reads, all branch outcomes
   and reachability of assertion errors. Read/write intersections are useful
   warnings/sufficient-rule inputs, not a complete proof; queue/enabling effects
   and future messages also matter. Same-actor splitting requires its own proof.
4. Retain every selected parameter frame and nondeterministic/error outcome.
   Unknown effects or unsupported observations must fall back conservatively.
5. Apply the actual cycle proviso to the retained candidate. Mark a full barrier
   only after normal complete expansion; exceptions must stop before completion.
6. Keep the zero-time/single-bundle proof SEPARATE from property-observation
   compatibility. Recognizing an untimed assertion call can establish a syntax
   fact, not all observation obligations. External state/temporal properties need
   their own visibility argument and cannot inherit source-assertion support.

A trivially narrow future case is a side-effect-free assertion statically proved
always true (e.g. literal true): erasing that check is semantically inert and can
discharge this extra error-observation obligation, assuming the existing C1/time
conditions. This does not prove the complete reducer and has not been wired in.
The interesting counter bounds require more: verify initial values, every writer,
all assignment paths/wraps and integer arithmetic before claiming an all-reachable-
states invariant. That proof is not supplied by the present footprint report.

## Reproduce and next decision

With Java 17 and the original compiler dependency available:

```bash
bash tests/audit_assertion_observations.sh
```

Or, using an already-built executable JAR:

```bash
python3 tests/audit_assertion_observations.py --output tmp/AssertionObservationFresh
```

The wrapper rebuilds RMC, compiles the offline Java tool and runs real-source
positive/negative classification and the finite counterexample. It does not
rerun performance measurements. Reports/logs are saved in the fresh output.
Recorded Linux evidence: `results/assertion_observation_linux_20261123.json`.

Decision: retain the runtime assertion restriction. The next implementation should
prove a narrow invariant/error-compatibility fragment and test mutations that
break it, before any gate extension. Pure/local syntax or passing bounds tests
alone cannot authorize it. Runtime COND remains paused. No new macOS execution
is needed to interpret the current findings.
