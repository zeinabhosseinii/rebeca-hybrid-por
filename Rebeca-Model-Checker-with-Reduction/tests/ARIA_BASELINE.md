# ARIA online reduction: fixed implementation baseline

Recorded 2026-11-23 (Asia/Tehran). Implementation reference:
[`0a4687b4a18abf0f3e78879b6e7fe502a2b2c942`](https://github.com/zeinabhosseinii/rebeca-hybrid-por/commit/0a4687b4a18abf0f3e78879b6e7fe502a2b2c942),
branch `aria-action-dependency-export`. The commit, rather than the moving branch,
identifies this baseline. This document records the existing implementation; it
adds no reduction rule and does not declare the entire generator proven correct.
`ARIA_BASELINE.json` records source hashes and the baseline assumptions.

## Operational scope

Java 17, RMC 2.14, original Rebeca compiler 2.27, TIMED_REBECA version 2.3,
FTTS, generated C++11. Baseline dynamic runs use the unannotated model with
`--aria` (AST) or `--aria --aria-json <export>` (JSON), with no symmetry or external
property model. Diagnostics use `POR_DIAGNOSTICS` and `EXPORT_STATE_SPACE`.
Controls that change priorities or candidate order operate on copied native
sources; they are not production policies. Runtime COND pruning is paused:
conditional/unknown dependencies remain dependent. The standalone guard evaluator
does not authorize runtime independence.

## What each certificate does and does not establish

| Mechanism | Supported claim | Boundary / failure behavior |
|---|---|---|
| Global dependency check | Tests real active handler IDs against the dependency matrix; all active alternatives must pass | Not a new proof of the pre-existing matrix; does not prove two different handlers of one actor independent. Unknown/conditional entries remain dependent |
| Isolated local candidate | Restricted local-effect fragment admitted by the analyzer and runtime guards | No general arbitrary handler certificate; unsupported effects fall back to ordinary selection/full expansion |
| Passive-send candidate | Restricted constant local assignments and at most one nullary untimed direct send to an empty-effect handler, with runtime queue/readiness/priority/capacity and disjointness checks | No feedback-routing, arbitrary sends, general guards or timing proof; unknown effects fail closed. See PASSIVE_SEND_ONLINE.md |
| Post-constructor quiescence | A blocker is permanently disabled when no runtime handler can send its name AND every slot of its instance queue lacks it | Constructors may have queued work; future/non-head messages still block. Unknown AST disables certification. Does not rewrite or prove the dependency matrix |
| Queue equivalence | Adjacent queue entries may be skipped only when the exact implemented entry-equivalence test succeeds | No arbitrary merging of equal handler names, different parameters or nonadjacent entries |
| Full-expansion barrier | A normally completed full expansion may discharge the restricted BFS cycle condition | Only the conservative zero-time gate below; an unprocessed/default state is never a barrier |

Detailed mechanisms: [ACTION_CANDIDATES.md](ACTION_CANDIDATES.md),
[PASSIVE_SEND_ONLINE.md](PASSIVE_SEND_ONLINE.md),
[QUIESCENCE_CERTIFICATE.md](QUIESCENCE_CERTIFICATE.md),
[CYCLE_BARRIERS.md](CYCLE_BARRIERS.md). Historical counts in older documents do not
supersede this snapshot.

Candidates retain their exact queue-alternative indices and all parameter and
nondeterministic outcomes. First acceptable candidate wins in the existing actor
preference order. If a trial fails the proviso, later certified candidates may be
tried; if none passes, full fallback runs. Different handlers of an actor remain
an unsplit actor union unless a supported special certificate justifies a split.
No general same-actor send/feedback certificate has been installed.

## Exact proviso contract

An exhaustive candidate includes every currently eligible alternative of its
actor, in order, and no other eligible actor exists under the FTTS rules. It is
full expansion, not genuine reduction. Otherwise every outcome must lead to:

1. A newly stored state; or
2. A state with positive open-count; or
3. A previously completed, explicitly marked full expansion, only when the
   zero-time barrier gate is enabled.

One invalid closed-partial successor rejects the entire candidate even if its
other nondeterministic outcomes pass. `porFullExpanded` starts false, is not
inferred from `usedReducedSet`, and is set only after normal completion of a full
candidate or fallback. Exceptions leave before that completion marker.

The barrier gate requires ARIA, no symmetry/property model or property definitions,
and a conservative AST certificate covering constructors as well as handlers.
Timing suffixes (even explicit after(0)), time primitives, annotations, unknown
nodes/calls, inheritance, synchronous methods and unsupported declarations disable
it. Without this gate, the closed-barrier exception is unavailable. Exhaustive
candidates still retain all eligible behavior. `POR_LEGACY_PROVISO` is a regression
control restoring the old new/open-only predicate, not the baseline mode.

The sufficient cycle argument assumes valid dependency/persistence and observation
conditions plus one zero-time bundle per state. Remove fully expanded vertices
from the selected preserving core: remaining edges point forward in processing
order, hence cannot cycle. This is not a proof for arbitrary timed merging,
symmetry, arbitrary temporal properties or opaque code. Legal edges left by failed
trials are checked separately from the selected preserving core.

## First-error contract

Deadlock, assertion failure and missed deadlines are errors that stop exploration
and produce the normal report/counterexample mechanism. They are not caught and
continued to obtain a complete graph. Queue overflow is rethrown with actor
context. Tests expecting an error check the actual result and a nonempty trace;
`satisfied` alone is never a correctness certificate. First-error runs are
incomplete state spaces and are not audited as full reachability graphs.

Evidence: `compare_cycle_barriers.sh` detects a pending assertion beside a loop
and checks future work, deadlock and assertion fixtures in baseline/AST/JSON.
`experiment_representative_policy.py` additionally checks reverse preference.
On the user's macOS run, reverse controls stopped as follows:

| Fixture | Actual result | States / transitions before stop | Trace states |
|---|---|---:|---:|
| CyclePendingAssertion | assertion failed | 2 / 2 | 3 |
| QuiescenceTerminates | deadlock | 20 / 21 | 14 |
| QuiescenceAssertion | assertion failed | 6 / 6 | 7 |

These tests do not constitute exhaustive coverage of every exception pathway.
Deadline checks remain in both trial and fallback code; this evidence set does
not claim a newly executed deadline-specific end-to-end regression.

## Recorded state-space evidence

| Model / mode | Linux states / reported transitions | User macOS states / reported transitions |
|---|---:|---:|
| LoadBalancer unannotated baseline | 101 / 202 | 101 / 202 |
| LoadBalancer static priorities | 22 / 26 | 22 / 26 (also independently confirmed in AFRA) |
| LoadBalancer dynamic AST and JSON | 27 / 31 | 27 / 31 |
| QuiescenceResend dynamic AST and JSON | 201 / 328 | 189 / 303 |

All listed dynamic satisfied exports passed the finite full-reference audit for
these reviewed source hashes. The audit projects unused sender fields only for
those models, matches state contents rather than numeric IDs, checks legal edges,
persistence over all action-avoiding paths, relational diamonds, selected outcome
completeness, actual proviso decisions, full barriers and the selected-core cycle
condition. Exhaustive actor unions must retain every enabled handler/outcome;
non-exhaustive multi-handler auditing is unsupported and fails closed.

Reported transition counts and unique exported graph edges are distinct metrics
(e.g. LoadBalancer 31 reported versus 30 unique exported). Exact counts are
measurements, not pass conditions. Equal-time queue ordering has no explicit tie
break; traversal differences are a possible explanation of platform differences,
not a confirmed diagnosis of every count discrepancy.

The 27-versus-22 gap remains. Preference experiments gave 40 states, not an
improvement. Hub-priority-only retained 27; actor preference plus Hub priority
produced 29 in Linux diagnostics. That last final graph passes finite checks but
its priority-filtered claim of full expansion is not certified against the
unprioritized reference. No diagnostic priority policy is installed. The current
27-state run does not visit a distinct-Hub-handler choice; splitting that unused
choice alone cannot shrink it. See [HUB_PRIORITY_CURRENT.md](HUB_PRIORITY_CURRENT.md).

## Reproduction and acceptance of later changes

From the RMC directory, with Java 17, Maven, Python 3 and a C++11 compiler:

```bash
bash tests/compare_cycle_barriers.sh
bash tests/reproduce_static22.sh
bash tests/compare_representatives.sh
python3 tests/experiment_representative_policy.py
python3 tests/experiment_hub_priority.py
```

The first command builds both projects and runs the proviso, actual trial-loop,
AST gate, finite positive-graph and first-error checks. The remaining commands
are controls/diagnostics, not additional production options. Dependencies must
include compiler 2.27. Per-run logs, exports and summaries are under `tmp/`.
The macOS Hub-priority experiment is not recorded as completed in this snapshot;
its Linux results must not be presented as a macOS measurement.

Before accepting a later reduction change, state its new scope/proof obligation,
retain all selected outcomes and first-error stopping, run relevant negative
controls, and audit complete positive graphs where feasible. Report count/time/
memory changes separately from semantic evidence. A smaller graph, matching
`satisfied` results, or matching the static count cannot replace these checks.
The next evaluation is multiple models and properties, not a claim of general
superiority or a requirement to force the dynamic graph to 22 states.
