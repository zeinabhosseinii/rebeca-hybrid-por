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

The unannotated full path has 11 states while the same-generated control has 12. These are distinct generated-code baselines. This experiment checks outcomes and fault traces, not semantic graph equivalence for this parameterized benchmark; the numerical difference alone neither proves a defect nor establishes harmless representation equivalence. A full normalized graph audit is a separate next step before claiming that equivalence. Passing these finite tests is not a general property-preservation theorem.

Raw observations, source and executable hashes, toolchain identity, per-run order, certificate reports, and build durations are in `results/cell_register_linux_20261123.json`; the CSV and Markdown provide compact tables. Diagnostics are in `results/cell_register_diagnostics_linux_20261123.json`. These measurements are from Linux, not macOS.

## Reproduce

From `Rebeca-Model-Checker-with-Reduction`, run:

```bash
bash tests/compare_cell_register.sh
```

The wrapper builds both Java tools, selects Java 17 on macOS, then runs the experiment in a fresh timestamped directory. It requires the project's compiler dependency and a C++11 compiler. Defaults are ten measured repetitions and a 30-second timeout per native run; optional `--repeats` and `--timeout` arguments are forwarded. Each output includes `summary.json`, `summary.csv`, the exact sources, static annotation, generated C++, certificate reports, native reports, and logs.
