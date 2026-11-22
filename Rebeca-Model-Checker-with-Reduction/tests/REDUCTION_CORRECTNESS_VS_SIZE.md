# Is 27 dynamic states versus 22 static states an implementation error?

Counts alone cannot answer that. The current dynamic reducer is less effective
on this benchmark, and the general generator is not proved bug-free. The checks
below address this exact finite benchmark under the existing default reachability
observations; the source's balance comment is not a checked balance property.

## Check both reductions, not only the dynamic one

`audit_both_reductions.py` compares actual static and dynamic exported relations
with the completed 64-state full sender-normalized graph. The original unnormalized
baseline remains 101 states. Sender projection is restricted by the exact source
hash of this benchmark, which does not read sender.

The check requires the same initial state and validates state contents, enabled
nonemptiness (C0), complete outcomes of each selected action, and the existing
reference's action-avoiding persistence/relational-diamond/observation tests.
It also checks a strong sufficient cycle condition: every reduced cycle must
pass a state whose **actual exported relation** contains every enabled action and
all its outcomes. To test it, remove such fully expanded vertices and require
the remaining graph to be acyclic. A diagnostic label saying reduced/full is
not used as a substitute for this semantic comparison.

| Actual graph | States | Checked action identities at states | Semantically full vertices | Cycle avoiding all full vertices |
|---|---:|---:|---:|---|
| Static priorities | 22 | 22 | 4 | none |
| Current dynamic | 27 | 30 | 9 | none |

Both pass this sufficient finite check. This supports the validity of BOTH
representative graphs for this instance. It does not establish arbitrary-property
preservation, a general exporter/generator proof, or optimality. The cycle test
is sufficient, not necessary: failure would require investigation and would not
by itself prove that a different valid cycle rule is wrong.

## Exhaustive fixed-order control

A separate copied-C++ experiment tried all 720 permutations of the six actor
preferences. The source model, dependency checks, selected-action branch handling,
closed-successor proviso, hash settings and error stopping were unchanged. Only
the order in which already eligible candidates are tried varied.

| Dynamic reached states | Number of orders |
|---:|---:|
| 27 | 288 |
| 29 | 144 |
| 30 | 36 |
| 31 | 12 |
| 32 | 96 |
| 38 | 96 |
| 42 | 48 |

All runs were satisfied. The best state count was 27, not 22. Some orders gave
27/31 instead of 27/32 report counters; this is not a smaller state graph and
is not justification for installing a benchmark-specific order. An auxiliary
small-hash run reproduced the histogram; the table above was also measured with
the original default hash setting. Runtime can be several minutes because each
run initializes the model checker's hash tables.

The previous static-priority preference control gives 42/50. Combining that
actor preference with experimental Hub method priorities gives 31/35; static
priorities alone give 22/26. Neither priority change is promoted to production.
These interacting results disprove the simplistic fix of copying a priority
list and claiming the dynamic engine must now match the static count.

## Diagnosis and repair scope

The current dynamic policy tries its available sufficient certificates and uses
a conservative per-successor BFS proviso. The static model enforces actor/method
priorities, producing a different representative traversal; its finite graph
still passes the semantic and strong-cycle tests above. There is no theorem in
this implementation that dynamic selection is minimum-size or always dominates
the static policy. The remaining gap is therefore an optimization limitation
supported by these finite results, not an established semantic bug to patch by
forcing the number 22.

A stronger persistent-set construction or a different justified cycle strategy
is algorithm work. It must preserve the required observations and detect errors
on adversarial models. Disabling proviso, suppressing deadlocks, hardcoding actor
names/order, or importing arbitrary priorities as forced eligibility are not
repairs. Current local/passive certificates still deliberately fall back for
unsupported general feedback programs. This limitation remains open.

## Reproduce from current exported controls

```bash
python3 tests/audit_both_reductions.py
# Optional expensive copied-source experiment:
python3 tests/sweep_loadbalancer_order.py
```

The first command expects full/reference and exported scheduling controls created
by the earlier diagnosis scripts. If necessary regenerate controls using:

```bash
bash tests/run_action_por_reference.sh
python3 tests/compare_loadbalancer_scheduling.py --output tmp/LoadBalancerSmall_action_candidate_scheduling
```

The report is `tmp/LoadBalancerSmall_both_reductions.json`. The order experiment
writes `tmp/ActionOrderSweep/results.json` and never edits production templates
or the input generated sources. No additional desktop run is needed to interpret
the measurements already obtained on the validation host.
