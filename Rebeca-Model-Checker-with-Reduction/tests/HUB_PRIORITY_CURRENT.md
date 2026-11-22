# Hub priorities after the current proviso changes

This experiment separates actor iteration preference from Hub message priorities.
It uses copied generated C++ only. No online generator certificate, candidate
split rule, proviso or error handling is installed or relaxed.

Reproduce after the existing cycle-barrier suite:

```bash
bash tests/compare_representatives.sh
python3 tests/experiment_hub_priority.py
```

`compare_representatives.sh` regenerates the static control with the current JAR.
The experiment regenerates native executables from copies of the existing current
AST sources. Output: `tmp/HubPriority/summary.json` plus per-control graphs/logs.
The only extra mutation beyond the checked preference permutation assigns Hub's
two method-priority entries to 1 and 2. This is a semantic scheduling control,
not an independently certified online partial-order reduction rule.

Linux measurements, states / reported transitions (not portable pass conditions):

| Control | States / transitions | States with both distinct Hub actions enabled in full reference |
|---|---:|---:|
| Current dynamic | 27 / 31 | 0 |
| Hub method priorities only | 27 / 31 | 0 |
| Static actor iteration preference only | 40 / 45 | 3 |
| Actor iteration preference plus Hub priorities | 29 / 31 | 3 |
| Actual static actor and method priorities | 22 / 26 | 3 |

The current 27-state execution never reaches a choice between the two distinct
Hub handlers. Thus adding a rule limited to that choice cannot change this run.
It is not the direct explanation of the current 27-versus-22 difference.

In the full 64-state sender-normalized reference there are three such Hub states.
At each state BOTH singleton choices pass persistence and relational diamonds
across all four states reachable while avoiding the selected action. This is
stronger than checking only the immediate diamond. The JSON retains every
avoiding continuation and the evidence for both choices.

At the three Hub choice states actually visited by the 40-state preference
control, replaying its processing prefix finds no successor blocked by the
closed-partial-state proviso for either hypothetical singleton. The JSON records
these blockers, not a claim that the whole hypothetical continuation is safe:
changing a choice changes future processing and the proviso must be checked anew.
The 40-state native run conservatively executes both handlers as an actor union.
The two priority controls with such states select ReceiveSecondary.

All four final dynamic-control graphs and the actual 22-state static graph pass
the finite action-outcome/persistence and strong cycle checks against the full
reference. These are benchmark-specific certificates, not a general compiler
proof and not a proof that every priority assignment is safe.

The actor-plus-Hub-priority control does NOT pass the original online-scope audit.
At its first mixed Hub state the priority scheduler omits one handler, while the
unmodified generated diagnostics claim an exhaustive actor expansion relative to
the priority-filtered alternative count. This is not exhaustive relative to the
unprioritized reference. The script keeps that audit failure explicitly separate
from the successful final-graph audit; it never treats the failed online claim as
a certificate. In particular, copied-source priority changes cannot authorize
full-expansion barriers in a production reduction.

Decision: finite evidence permits exploring a singleton Hub representative for
this instance; the production generator must still retain the unsplit union
until a general same-actor certificate is implemented. Such a certificate must
cover local reads/writes, outgoing queue effects, parameters/nondeterminism,
observations and all action-avoiding continuations (or a sufficient static proof),
then pass the actual run's cycle proviso. A priority number supplies none of that.
No production split is installed here. Optimizing this unused branch cannot by
itself shrink the present 27-state run to 22.
