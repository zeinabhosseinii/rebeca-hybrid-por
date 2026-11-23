# Existing shared-register benchmark with an explicit safety property

This experiment adapts the existing `ARIA/benchmarks/case1.rebeca`, a small abstract shared-register service, rather than the generated worker/counter scaling family. It is not an industrial application.

Original SHA256: `e2cdaa2e62324289071e398cf251a54c7f34d2065379f23b58c4033a12dc34f7`.

`CellRegisterBounds.rebeca` adds only `assertion(value >= 0 && value <= 2)` immediately after the Cell stores an incoming value. The Cell starts at zero and this handler is its only runtime writer. This checks stored-value safety; it makes no fairness or eventual-service claim. The original Cell already contains a `keepAlive` self-loop: the adaptation neither adds nor removes it.

`CellRegisterInvalidClient.rebeca` additionally changes the second client's constructor argument from 2 to 3. This remains a valid byte argument, but violates the service's value contract when stored. No assertion, error handling, or termination behavior is removed.

## Four paths and measurement

The paths are unannotated full exploration, freshly exported ARIA static priorities, dynamic ARIA, and an exact copy of the dynamic generated sources with only the PO macro disabled. Static export is checked to preserve the model body. The same-generated control separates online reduction from the different full generator path.

One warmup and ten measured native executions per mode and model, with a seeded rotating order, give 88 executions. Compilation and ARIA export are recorded separately. Timed runs disable graph export and diagnostics. Per-child peak RSS and native wall time are recorded; timeouts and outcome mismatches fail the experiment. Fault counts describe prefixes ending at the first error, not complete spaces.

| Model | Full states/steps | Static states/steps | Dynamic states/steps | Same-generated PO-off states/steps |
|---|---:|---:|---:|---:|
| Healthy | 11/25 | 9/12 | 12/34 | 12/28 |
| Invalid client | 6/9 | 6/7 | 6/11 | 6/9 |

All healthy runs report satisfied. All 44 faulty executions, including warmups, stop with assertion failed and have a nonempty counterexample ending at `cell.STORE`. This experiment exercises assertion stopping; the separate invariant integration suite covers deadlock stopping. No production generator or stopping rule is changed by this experiment.

## Certificate and representative decisions

Both production invariant proofs and the structural full-expansion barrier gate return false for both sources. The offline explanation is `only int state fields supported`: the existing Worker uses a byte field, and constructor/message parameters are also outside the certificate fragment. The gate is checked false in both generated dynamic variants. The certificate is deliberately not widened to accommodate the benchmark. Ordinary dependency checking and exhaustive full candidates remain available.

A separate healthy diagnostic run reproduces 12 states and 34 reported transitions. It records one reduced outcome, five full fallbacks, and six full candidates; accepted proof labels are three global dependency checks and four unsplit actor unions. Five proviso rejection records occur. Closed witnesses are seven exhaustive witnesses; no completed-full barrier witnesses occur. Counts of solver transitions include trial/fallback work and must not be presented as unique exported graph edges. This diagnostic run is excluded from timing results.

## What this establishes and what remains open

Dynamic exploration saves no states against its same-generated control here (12 versus 12), and static priorities produce fewer states (9). This is a negative reduction result with conservative certificate refusal, not a performance win. Healthy medians are about 0.16 seconds with substantial ranges; these short runs support no speed ranking or memory advantage.

The unannotated full path has 11 states while the same-generated control has 12. The subsequent finite graph audit below resolves this difference for this exact healthy model. Passing these finite tests is not a general property-preservation theorem.

Raw observations, source and executable hashes, toolchain identity, per-run order, certificate reports, and build durations are in `results/cell_register_linux_20261123.json`; the CSV and Markdown provide compact tables. Diagnostics are in `results/cell_register_diagnostics_linux_20261123.json`. These measurements are from Linux, not macOS.

## Reproduce

From `Rebeca-Model-Checker-with-Reduction`, run:

```bash
bash tests/compare_cell_register.sh
```

The wrapper builds both Java tools, selects Java 17 on macOS, then runs the experiment in a fresh timestamped directory. It requires the project's compiler dependency and a C++11 compiler. Defaults are ten measured repetitions and a 30-second timeout per native run; optional `--repeats` and `--timeout` arguments are forwarded. Each output includes `summary.json`, `summary.csv`, the exact sources, static annotation, generated C++, certificate reports, native reports, and logs.

## Follow-up: resolving 11 versus 12

`audit_cell_register_graphs.py` compiles fresh exports of all four native variants. It checks the exact healthy source hash and refuses nonzero times. It preserves variable names, types and values, actor identities, message text including arguments, message attributes other than unused sender, and queue multiplicities. The source never reads sender. Equal-time queues are compared as multisets, explicitly separate from the initial ordered comparison.

The extra control state is `8_0`: Cell value is zero, both workers have finished forwarding, and the Cell queue contains `store(2), store(1), keepAlive()`. Control state `6_0` has the same pending messages with the two stores reversed. Removing sender alone does not merge them: the ordered comparison still has 12 states. The queue multiset comparison gives 11.

Crucially, the audit checks **every raw alias individually**. Both have identical sets of projected successors for each actor/handler action, retaining every distinct target value caused by the different store arguments. It does not union differing alias behavior to make an equality pass. The full and same-generated PO-off initial states, complete projected state sets, and complete labeled successor relations are equal. This is a finite transition-system equivalence under the stated projection for this source, not just a count match. It does not license queue sorting in arbitrary models or certify all parameter handling.

| Path | Raw states | Ordered states ignoring sender | Multiset states ignoring sender | Unique actor/handler/source/target edges |
|---|---:|---:|---:|---:|
| Full | 11 | 11 | 11 | 24 |
| Static | 9 | 9 | 9 | 11 |
| Dynamic | 12 | 12 | 11 | 26 |
| Same-generated PO-off | 12 | 12 | 11 | 27 |

Unique exported edge counts differ from the solver's reported transition counts in the timing table. Static and dynamic raw/projection counts are recorded, but this new audit establishes full/control equivalence only; it is not a new static/dynamic POR correctness certificate.

No production generator, hashing rule, assertion, proviso or deadlock behavior is changed. The extra raw state is explained by queue representation in this finite comparison; there is still no dynamic state saving against its same-generated control. Static remains smaller at nine states.

Run after the four-path experiment, replacing CASE with its healthy case directory:

```bash
python3 tests/audit_cell_register_graphs.py --case CASE/CellRegisterBounds --output CASE/graph_audit.json --export-native
python3 -m unittest discover -s tests -p test_cell_register_graph_audit.py
```

The four focused tests require parameter values and multiplicities to remain distinct, require queue-order projection to be explicit, reject timed messages, and reject aliases with missing behavior. The Linux audit is archived in `results/cell_register_graph_audit_linux_20261123.json`. Full/control exported graphs and reports are archived alongside it in `results/cell_register_graphs_linux_20261123/`; they retain their exact hashes from the audit. No performance comparison is made from these export-enabled runs.

## Follow-up: reduction certificates and real assertion stopping

`audit_cell_register_reductions.py` builds on the pinned-source full/control equivalence. For each static/dynamic raw state it checks C0, equality of all retained actor/handler outcome sets, and a sufficient set-level persistence/relational-diamond condition along all full-graph paths avoiding the selected set. Actions inside the selected set need not commute with one another. It also removes semantically fully expanded raw vertices and checks that the remaining reduced graph is acyclic, a strong sufficient cycle proviso. This is an exported finite-graph certificate, not an audit of every runtime diagnostic decision.

The exact healthy source has only the stored-value assertion. Every reachable full-state Cell.value is within 0..2; full exploration completed satisfied, and no model step is an error. Assertions occur immediately after the single store assignment, so their truth is covered for this source. Empty atomic propositions alone would not justify invisibility for arbitrary properties. Do not reuse this observation argument for another property or model.

| Check | Dynamic | Static |
|---|---|---|
| Initial state/C0 | Pass | Pass |
| Retained action outcomes | Pass | Pass |
| Strong cycle condition | Pass | Pass |
| Sufficient persistent-set/diamond certificate | Pass | Refused |
| Semantically full raw states | 11 of 12 | 2 of 9 |

Dynamic has one partially expanded raw state: it chooses starter.STARTWORKERS, with a verified avoidance region. The remaining eleven are semantically full, explaining why this example gives practically no dynamic reduction.

Static's sufficient certificate is refused at two partial choices, when a remaining worker sends a value while Cell already has a pending store. For example, full state 3_0 has value zero, pending store(1), and worker2.WRITEVALUE enabled. Executing the new send before STORE permits storing either pending value; executing STORE first must store 1. The two orders therefore have different two-step outcome sets. The JSON records the exact full-state IDs and left/right destination sets. This fails a sufficient commutation test; it is **not** a proof that ARIA's static algorithm is incorrect, nor a counterexample to this bound assertion. A different, property-specific or algorithm-specific argument would be needed to certify those static choices. The healthy assertion remains satisfied in the complete reference graph and both reduced runs.

A fresh native execution of each faulty mode still stopped at assertion failed, with a nonempty trace whose failing edge is cell.STORE. These four observations are in `results/cell_register_fault_recheck_linux_20261123.json`; the preceding benchmark also verified all 44 faulty runs including warmups. This is actual first-error stopping; no error bypass or generator change was introduced. These fault runs do not exercise deadlock; the separate deadlock integration tests remain the evidence for that behavior.

Run after graph export:

```bash
python3 tests/audit_cell_register_reductions.py --case CASE/CellRegisterBounds --output CASE/reduction_audit.json
python3 -m unittest discover -s tests -p 'test_cell_register*.py'
```

The command fails if the dynamic sufficient certificate fails. Static refusal is explicitly recorded, not converted into a pass. Three new tests check set-level treatment, disabling and nondeterministic diamond failures; all seven Cell audit tests pass. Counts and witnesses are archived in `results/cell_register_reductions_linux_20261123.json`. This step changes tests and documentation only; certificate scope, runtime COND, proviso and stopping behavior are unchanged.
