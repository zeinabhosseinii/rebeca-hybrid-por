# Scaling results and shared-Hub mechanism, 2026-11-23

## Recorded macOS measurements

User-supplied audit and benchmark JSONs are stored unchanged in
`results/scaling_macos_20261123_audit.json` and
`results/scaling_macos_20261123_benchmark.json`. All generated source hashes were
recomputed from `scaling_models.py` and matched. All warmups and measured runs
were satisfied; no timeout occurred. The small two-worker finite audits passed
for both static/dynamic graphs in both families. Larger graphs were not given a
new full semantic certificate. The compact complete metrics table is
[results/scaling_macos_20261123.md](results/scaling_macos_20261123.md).

The benchmark contains 10 measured runs after one warmup per mode, with rotating
order, diagnostics/export disabled. On macOS arm64 / Apple clang 16:

| Family / size | Full states / median s | Static states / median s | Dynamic states / median s |
|---|---:|---:|---:|
| Independent / 8 | 715,713 / 6.4410 | 124,765 / 1.3193 | 390,624 / 3.6933 |
| Shared / 6 | 188,641 / 1.3252 | 188,641 / 1.1788 | 22,527 / 0.2762 |

In the independent case static is about 2.8 times faster than dynamic. In the
shared case dynamic is about 4.3 times faster than static and about 4.8 times
faster than full. Dynamic shared states are about 88% fewer than static.
These are measured native-search comparisons for these generated instances, not
end-to-end preprocessing comparisons or a general superiority claim. For shared
six-worker RSS, static is about 1041 MiB versus dynamic 1055 MiB: state reduction
is not a demonstrated process-memory win over static.

## Separate Linux diagnostic controls

The same six-worker shared model (source hash recorded in the diagnostic JSON)
was compiled separately with POR_DIAGNOSTICS. Diagnostic timings are not used in
any speed comparison. Current graph counts match macOS, but all ablation/log
counts below are Linux measurements, not observations of a macOS diagnostic run.
The production generator and dependency rules were not changed.

| Native control | States | Reported transitions | Result |
|---|---:|---:|---|
| Dynamic-generated C++ with PO disabled | 117,648 | 605,053 | satisfied |
| Old new/open-only proviso | 117,434 | 876,849 | satisfied |
| Exhaustive candidates allowed, completed closed barriers disabled | 117,434 | 858,477 | satisfied |
| Current proviso | 22,527 | 36,865 | satisfied |

The PO-disabled control retains the dynamic-generated representation. Thus the
188,641 unannotated-baseline versus 22,527 dynamic difference is not all credited
to runtime representative selection: the generated-code/representation control
already has 117,648 states without online POR. State-count differences across
these controls are not additive proof components, nor are their graphs assumed
to have interchangeable IDs.

The narrow closed-barrier ablation changes only the final enabled-barrier return
in copied generated C++; the existing exhaustive/new/open checks remain intact.
Its growth from 22,527 to 117,434 isolates the importance of accepting successors
of already completed full expansions in this traversal. The legacy macro also
changes exhaustive-candidate treatment, so it is reported as a separate control.
More conservative trials can leave extra legal generated edges before fallback;
therefore the legacy transition count can exceed the full-search control's.
No altered control is installed in production.

## Actual current decisions

There were 22,527 completed state decisions:

* 18,414 genuinely reduced decisions.
* 18 exhaustive candidates (full expansions).
* 4,095 full fallbacks.

All 18,432 accepted trials selected actor H, using `global_dependency_check`.
Every accepted representative had exactly ONE queue alternative. No isolated-local
or passive-send proof was accepted; there were no quiescence skips. Thus these
special certificates do not explain this particular run's reduction. No runtime
COND pruning or new same-actor splitting was involved.

The log contains 13,557 closed-successor acceptances justified by completed full
barriers and 14 by exhaustive expansion. Current candidates had zero proviso
rejections. Disabling completed barriers produced 197,553 rejected successor
checks and 107,560 full fallbacks (plus 4,093 exhaustive candidates). The old
proviso produced 209,437 rejected successor checks and 111,635 full fallbacks.
Witness counts are events, not numbers of distinct states.

Worker trials were blocked by dependencies on other workers (18,432 blocker
events in the current run), while Hub trials passed. In the observed traversal,
Hub is selected as soon as it can process the pending action, before exploring
all worker/Hub scheduling combinations; when it cannot supply a candidate, full
fallback retains the worker alternatives. This state-dependent choice works with
the completed-full-barrier proviso. It does not rely on prioritizing one of two
different simultaneously pending Hub handlers in the current reduced run.

The static generated initialization gives H and every worker actor priority 1.
The static Hub method priorities are Finish=1 and Step=2. Thus static actor
priorities do not distinguish those actors in this instance; method priorities
reduce some reported transitions but leave 188,641 reached states. These concrete
assignments and the dynamic trace explain the different behavior; they do not
establish that all models with shared destinations behave the same way.

## Reproduction and limits

After generating a scaling benchmark, point the separate diagnostic runner at
its `shared_6/dynamic` generated source directory:

```bash
python3 tests/diagnose_scaling.py \
  --source tmp/ScalingBenchmark_<stamp>/shared_6/dynamic \
  --output tmp/ScalingShared6DiagnosticsFresh
```

It copies native sources, compiles current/legacy/narrow-barrier/PO-disabled
controls and requires satisfied reports and complete decision traces when POR
is enabled. The PO-disabled control has no POR_STATE events; its zero logged
state count is not zero explored states. Outputs include native sources, logs,
reports and summary JSON. `--controls` can select individual controls. Source
paths must refer to the generated dynamic benchmark, not static sources.

This runner checks trace completeness/outcomes and measures a mechanism through
controlled changes. It is not an additional full-graph equivalence audit of the
six-worker instance. First-error stopping is unchanged; an unexpected error
fails the healthy-instance diagnostic rather than being continued or suppressed.
Raw Linux evidence: `results/scaling_shared6_diagnostics_linux_20261123.json`.
