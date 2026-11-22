# Online full-expansion barriers for the BFS cycle proviso

This is an executable proviso refinement, not a state-count target and not a
lookup in a saved graph. C1/dependency certificates, parameter alternatives,
nondeterministic execution and error exceptions are unchanged. Runtime COND
pruning remains disabled.

## Rule

A candidate is exhaustive only when its alternatives are exactly the entire
eligible queue-alternative group of its actor and no other actor is currently
eligible under the existing FTTS time/priority rules. Every outcome is executed.
Such a candidate is a full expansion, so accepting it does not prune any enabled
behavior and requires no cycle restriction. It is recorded as `full_candidate`,
not a genuine reduced expansion.

Otherwise **every** generated successor must be new/open, or an explicitly
completed full-expansion barrier. One closed partial successor rejects the whole
candidate, including when another nondeterministic successor is a valid barrier.

`TimedBFSState.porFullExpanded` starts false. It becomes true only after normal
completion of an exhaustive trial or full fallback. `usedReducedSet=false` is
never interpreted as a barrier: that default also describes an unprocessed state.
A thrown deadlock, deadline, assertion or other error exits before the marker is
set. The current partially expanded state cannot certify itself.

## Scope and sufficient argument

A node-wide barrier is enabled only for ARIA, no symmetry/property model or
property definitions, and a fail-closed static zero-time certificate. Both
constructors and handlers are inspected. Explicit after/deadline expressions,
time primitives, unknown syntax/calls, inheritance, synchronous methods,
AST extensions, annotations, global/environment/feature declarations, records
and interfaces disable this certificate. This deliberately conservative scope
ensures one zero-time bundle per stored state; no marker from one time bundle is
used to justify another. Outside it, closed successors retain the previous
rule. Exhaustive candidates remain safe because they retain all enabled steps.

Assuming the existing C1 and observation conditions, consider the graph of the
actually selected candidates plus full fallback edges. Every edge from a partial
expansion either points to a state processed later (new/open at trial time) or
to a previously completed full vertex. Remove full vertices. Remaining edges
strictly increase processing order, so they cannot form a cycle. Therefore every
cycle crosses a full expansion. This is the same strong sufficient cycle
condition checked by the independent graph audit, enforced with online metadata.
No full graph or model-specific actor name is consulted by the C++ rule.

The argument requires the zero-time/one-bundle invariant; it is not claimed for
timed state merging, symmetry, arbitrary LTL/visibility assumptions or opaque
code. Failed-trial edges may remain as in the old solver; they are checked as
legal full-graph edges, and the selected preserving core is audited separately.

`POR_LEGACY_PROVISO` restores the old all-successors-new/open predicate for
controlled comparison. It does not change dependency decisions or deadlock stops.

## Prototype, negative cases and native measurements

`cycle_barrier_reference.py` first exercises the rule over finite semantic graphs.
Tests cover a certified edge to an already fully expanded vertex, a partial loop
that must not starve an error, a nondeterministic bad successor alongside a valid
barrier, and an exhaustive self-loop that is already the full behavior.
The actual C++ helper/trial snippets are compiled at O0/O2, with legacy controls.
The real compiler AST tests reject timing in constructors as well as handlers.

Fresh Java generation, C++11/O2 execution and same-source legacy controls yielded:

| Model | Baseline (no reduction) | Legacy ARIA | New ARIA AST = JSON |
|---|---:|---:|---:|
| LoadBalancerSmall | 101 / 202 | 27 / 32 | 27 / 31 |
| QuiescenceResend | 1041 / 4062 | 338 / 720 | 201 / 328 |

Cells are reached states / report transition counters; all four positive paths
are satisfied. Static priorities for LoadBalancer remain 22/26. The original
27-versus-22 **state** gap remains; the one saved transition is a redundant full
retry after an already exhaustive trial, not a removed state.

Independent complete normalized references contain 64 and 442 states. For each
AST and JSON result the semantic auditor validates all exported edges, all
selected outcomes and all selected C1 certificates; checks actual completed
barrier markers and closed targets; and independently tests the selected core's
strong cycle condition. LoadBalancer has 21 genuinely reduced trials, 5 accepted
exhaustive candidates, 1 full fallback and 3 rejected-proviso witnesses. Its core
has 6 full vertices. QuiescenceResend has 152 reduced trials, 49 full fallbacks,
66 rejected-proviso witnesses and 17 accepted closed-full-barrier outcomes. Its
core has 49 full vertices. No cycle avoids all full vertices in either core.

The future-pending model remains 19/20 baseline versus 18/19 ARIA with closed-full
barriers disabled. The terminating feedback variant still stops on deadlock
(38/61 baseline, 14/14 ARIA); the assertion variant still stops on assertion
failure (13/16 baseline, 6/6 ARIA). Error-prefix counts are not complete spaces.
A new Loop/Relay cycle with a concurrently pending Fault.Reveal assertion also
reports assertion failure in baseline, AST and JSON; ARIA explicitly rejects the
closed partial loop before exposing the error. No terminal bypass is present.

## Reproduce

```bash
bash tests/compare_cycle_barriers.sh
```

This builds ARIA/RMC, tests the graph prototype, actual C++ helpers and real AST
gates, generates AST/JSON/full controls for both positive models, compiles the
same source under the legacy proviso, checks selected-core semantics, and runs
the error/future-time regressions. Evidence is under `tmp/CycleBarriers/`, with
`summary.json`, state exports, logs and semantic reports. Current regression
expectations distinguish full candidates from genuine reductions.

The finite checks and sufficient argument support this scoped refinement; they
are not a proof that every pre-existing dependency analysis or all generator
behavior is correct. General feedback-action certificates and further graph-size
improvements remain separate work.
