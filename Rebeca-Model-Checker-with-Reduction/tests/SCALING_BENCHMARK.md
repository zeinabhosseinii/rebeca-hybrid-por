# Bounded-epoch scaling benchmarks

From the RMC directory, after pulling the branch:

```bash
bash tests/run_scaling_benchmark.sh
```

The command builds ARIA/RMC with Java 17, runs a two-worker finite semantic audit
of both families, and then runs the performance suite. No production generator
rule is changed. Use mains power and avoid other heavy workloads on the machine.
The default performance sizes are independent 4/6/8 workers and shared 2/4/6
workers. Default repetitions: ONE unmeasured warmup per mode followed by TEN
measured runs per mode, with a seeded rotating mode order (balanced over groups
of four rounds). All native measurements run sequentially. Sizes can consume
substantial memory; this is not a hard memory-capped runner.

The default per-native-run timeout is 30 seconds. A timeout kills/reaps that
process group, records `status=timeout`, and skips further runs of that mode at
that size while other modes/sizes continue. The final exit is 2 if any mode timed
out; timeout is not `satisfied` or a performance win. Build/parse/process errors
and unhealthy outcomes fail explicitly. No search error is caught and continued.
Partial completed samples of a timed-out mode are retained, not a valid complete
performance estimate. No hard state-count target is imposed.

Options forwarded to the performance run include:

```bash
bash tests/run_scaling_benchmark.sh --repeats 10 --timeout 30
# One family / alternative sizes (the small audit still runs first):
bash tests/run_scaling_benchmark.sh --families shared --sizes 3 5 6
```

For already-built JARs:

```bash
python3 tests/benchmark_scaling.py --output tmp/MyScalingAudit --sizes 2 --repeats 2 --audit-small
python3 tests/benchmark_scaling.py --output tmp/MyScalingTiming --repeats 10
```

Fresh output directories are required. `--independent-sizes` and `--shared-sizes`
set family-specific sizes; `--sizes` overrides both. Model generation accepts
1..16 workers, but that syntax limit is NOT a recommended feasible upper size.
The finite graph audit is restricted to <=3 workers. Never mix graph-export audit
timings with the export-disabled performance run. If all completed baselines are
still subsecond on a particular machine, larger sizes need a separate bounded
calibration; the default sizes are starting points, not a duration guarantee.

## Model construction and boundedness argument

`scaling_models.py` deterministically generates source with three work steps per
worker per epoch. Models and fresh priority-annotated equivalents are saved in
the output. Annotation is checked to change only priority lines.

* Independent family: each worker advances through bounded local self-messages,
  then sends its unique Finish to the Hub and waits. The Hub releases all workers
  only after consuming N Finish messages.
* Shared family: intermediate worker steps go through a shared Hub counter, which
  wraps modulo three, and receive a reply before continuing. Completion uses the
  same mandatory epoch barrier. Hub Step handlers conflict through the shared
  counter, unlike the independent local work.

Each worker has at most one circulating work/completion message until it finishes;
a consumed Finish leaves it waiting at the barrier. Hub occupancy is at most N,
so its queue has N+1 slots (including the empty terminator); each worker queue
has two slots and at most one message. All worker counters and the Hub counters
are bounded. When the last Finish is consumed the Hub immediately releases N new
worker messages; no empty terminal state is intended. Within an epoch there are
only finitely many work steps/messages. Thus a continuously enabled high-priority
worker cannot run forever while other workers await completion of that epoch.

An earlier prototype with unbounded worker self-loops was rejected: static
priorities could starve other workers and its graph failed the strong cycle
check. That prototype is not part of this benchmark and its measurements are not
used. These models avoid that particular artifact by construction; this is not a
general theorem that static ARIA priorities preserve arbitrary properties.

These are healthy cyclic reachability/deadlock/deadline benchmarks with no formal
fairness/LTL property and no assertions added to disable a certificate. A
`satisfied` result does not independently establish fairness or all properties.
The benchmark requires actual `satisfied` in every completed warmup/measured run
and stable state/transition counts within repeated runs of a mode. Baseline
completion is a prerequisite to any full-space reduction ratio at that size.

## Small finite validation and its projection

The audit matches the exact generated program text. No sender is read, there are
no timed suffixes, and every exported time/arrival is checked to be zero with
infinite deadlines. It projects unused sender and represents these equal-time
queues as multisets (including complete message contents and multiplicity), so
static priority sorting can be compared to unprioritized FTTS alternatives. This
projection is limited to these generated models, not arbitrary actor queues.

On the completed baseline it checks that EVERY state merged by the projection
has exactly the same projected action/successor relation and observations. A
projection that changes this relation is rejected. It then checks reduced states,
initial state, C0, all outcomes of every retained action, persistence and relational
diamonds over the full action-avoiding closure for partial expansions, and that
every reduced-graph cycle crosses a full expansion. A full expansion does not
need individual action independence. The new PO-disabled control must retain EXACTLY the projected full action relation
at every state and cover every reachable projected reference state; a partial
persistent set is not accepted for that control. The wrapper additionally checks
exact native-copy bytes, rejection of duplicate PO definitions and rejection of
an intentionally removed control branch. This is a sufficient finite check, not a
runtime certificate and not a proof of all instances/sizes of a family.

## Measurements and interpretation

The four modes are `full` (unannotated FTTS without POR), `static` (fresh ARIA
priority annotations without online POR), `dynamic` (unannotated FTTS with
`--aria` AST), and `dynamic_no_por` (an exact copy of dynamic-generated C++ with
one PO macro removed from Config.h). The control preserves every other native
file byte-for-byte; copy metadata records configuration fingerprints. It is
compiled with the same flags, warmed up and measured in the same rotated rounds.
This is a control of the online POR implementation in its generated representation,
not a claim that every internal compiler optimization has been independently
isolated. Copy time and compilation are separate preparation costs; no second
Java generation is attributed to this copied mode. No experimental native
patches or changed hash sizes are used. Compilation is C++11/pthreads/O2 in all
modes. Performance runs disable diagnostics/export. Preparation (ARIA annotation,
Java generation and native compilation) is recorded separately from native time.
No JSON-input mode is timed here; existing regressions cover it separately.

Every native sample contains result, states/transitions, elapsed wall time,
per-child OS peak RSS (KiB), solver-estimated bytes and coarse solver time. Wall
time includes process startup. The median/min/max and sample counts are in CSV;
all samples, warmups, orders, tool versions and JAR hashes are in JSON. Low startup
cost is still important; ten samples do not eliminate noise or establish a
general ranking. RSS includes hash-table/process overhead, not just stored states.
A smaller state count need not imply a smaller process footprint.

Outputs: `tmp/ScalingAudit_<stamp>/summary.json` and
`tmp/ScalingBenchmark_<stamp>/{summary.json,summary.csv,comparisons.csv}`, plus per-case models,
sources, compilation/generation logs and individual XML/error reports. Only
small instances are graph-audited; larger completed instances have outcome checks
and the family argument, not a full semantic equivalence certificate.

## Recorded Linux checks before the fourth-mode extension (2026-11-23)

Both final two-worker families passed complete generation, one warmup plus two
measured runs in every mode, and the finite semantic/strong-cycle audit.
Calibration ran one warmup plus TWO measured runs for six workers, and one
warmup plus ONE measured run for eight independent workers. These calibrations
are not the ten-repeat performance study. All runs completed as satisfied.

| Family / workers | Full states | Static states | Dynamic states | Full native time |
|---|---:|---:|---:|---:|
| Independent / 6 | 27,153 | 7,525 | 15,624 | median 0.42 s (2 samples) |
| Shared / 6 | 188,641 | 188,641 | 22,527 | median 1.26 s (2 samples) |
| Independent / 8 | 715,713 | 124,765 | 390,624 | 5.11 s (1 sample) |

Eight independent workers reached a multi-second baseline on this host, but
macOS must be measured separately. Native timeout cleanup was exercised with a
1 ms limit on the existing eight-worker executable and raised TimeoutExpired.
No production solver exception handler was changed. Raw calibration and audit
records are in `tests/results/scaling_calibration_linux_20261123.json`.


## Four-mode comparisons

`comparisons.csv` labels each baseline/target explicitly. `representation_control`
compares original full to dynamic-generated PO-disabled; `online_por_control`
compares the latter to dynamic. The remaining three comparisons retain the
full/static/dynamic native end-user comparisons. A speed ratio above one means
the named target has a smaller median time than its named baseline. State
reduction can be negative. Ratios are emitted only for completed modes; partial
timeout samples never generate a valid speedup entry. Graph-export audit ratios
are diagnostics only and must not be used as performance results.

The mode list is recorded in JSON schema version 2. Old three-mode reports remain
historical data and are not rewritten or combined with freshly measured fourth
mode times. The final wrapper runs all four modes together. With ten rounds,
position counts differ by at most one; rotations balance positions exactly in
groups of four rounds. This is not a fully randomized experimental design.

See [FOUR_PATH_BENCHMARK.md](FOUR_PATH_BENCHMARK.md) for extension verification.
