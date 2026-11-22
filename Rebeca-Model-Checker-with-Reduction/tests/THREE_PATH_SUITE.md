# Three-path model comparison pilot

Run from RMC after pulling the current branch:

```bash
bash tests/compare_model_suite.sh
```

The wrapper builds ARIA and RMC with Java 17, then writes a fresh timestamped
`tmp/ThreePathSuite_*` directory. Existing output is never silently reused.
For already-built JARs use `python3 tests/compare_model_suite.py --output <fresh-dir>`.
Optional `--models <names...>`, `--repeats N` (default 3) and `--timeout seconds`
select a subset or measurement budget. Python 3, POSIX wait4 and C++11 are required;
Linux and macOS peak-RSS units are normalized to KiB. No external time utility is
required. A timeout, generation/compilation failure or malformed report is an
execution failure, not a satisfied outcome.

## Models and settings

This is a small regression pilot, not a representative benchmark collection.
It contains LoadBalancerSmall, its runtime-resend and future-pending variants,
its terminating/deadlock and assertion variants, and PassiveSendIndependent
(a different local/passive-sink fragment, which eventually deadlocks). Thus the
six entries do not constitute six independent application families.

Each model is regenerated in three modes: unannotated FTTS without POR (`full`),
a fresh ARIA priority-annotated model without online POR (`static`), and the
unannotated FTTS model with `--aria` (`dynamic`, AST path). The suite checks that
annotation changes only priority lines, verifies the native PO/TTS configuration,
and uses C++11, pthreads and O2 uniformly. No diagnostics, graph export, symmetry,
manual priority edits, source patches or custom hash sizes are enabled.
Constructors/message bodies, including assertions, are retained. These runs use
the default reachability/deadlock/deadline check and source assertions; model
comments describing balance or consistency are not added formal properties.
The JSON-input dynamic path is covered by the existing cycle-barrier regressions,
not timed as a fourth mode here.

## Metrics and evidence boundaries

For each mode the suite records source SHA256, property name/type/result, reached
states/transitions, counterexample trace length and whether exploration completed
without an error. Native search repeats use fresh processes; result and counts
must be stable within a mode. Errors stop normally on every repeat. Expected
results must match in all modes, and error runs require nonempty traces. No
exception is suppressed to produce a complete export. The suite does not add
property options or bypass the solver's first-error handling.

`native_wall_*` measures the native process launch through completion, excluding
Java generation, ARIA annotation and C++ compilation. All three individual samples,
median, minimum and maximum are retained. Startup/hash-table allocation can
outweigh search on these tiny models; three fixed-order samples support no general
speed ranking. Generation/compile and shared per-model ARIA export time are
reported separately. The export measurement is repeated as metadata in each mode
row, not three independent preprocessing operations to sum.

`peak_rss_*` comes from OS wait4 resource usage for each separately reaped native
child, not a cumulative maximum across compiler/Java processes. Linux KiB and
macOS bytes are normalized to KiB. It includes process overhead and allocated
hash tables. `solver_estimated_bytes` is the solver's internal sizeof-based
estimate and is NOT process RSS. The solver's `total-spent-time` uses whole wall
seconds; those raw values are retained but not used for subsecond rankings.
Machine/compiler/JAR hashes and flags accompany the report. Build time for the
JARs is not included in per-model timing.

An error row's state/transition counts describe the explored prefix up to the
first error, not a completed graph, and are not comparable as a full-space
reduction percentage. Transition counts are reported solver transitions, not
deduplicated exported edges. A satisfied result and agreeing outcomes do not
prove POR correctness, property preservation for arbitrary models, or equivalence
of these three graphs. This suite performs outcome/performance comparison only;
use the separate full-graph semantic audits where their reviewed scope applies.
No static-versus-dynamic superiority claim follows from this pilot.

`summary.json` retains samples/provenance, `summary.csv` gives all mode metrics,
and `summary.md` is the compact table. Each case saves original and annotated
sources, generated C++, build/generation logs and all per-repeat reports/error
logs. Partial-case mode JSONs remain available on failure. The final process exits
nonzero for any outcome mismatch/missing error trace; such rows remain visible.
Recorded Linux measurements are under `tests/results/three_path_linux_20261123.*`.
The user's macOS measurement of this new suite has not yet been run.
