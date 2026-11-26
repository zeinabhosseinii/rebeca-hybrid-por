# Four-path scaling benchmark extension

The active scaling runner includes the shared family. Independent-family measurements below are historical.


The current scaling runner now measures these modes together:

| Mode | Native input | Purpose |
|---|---|---|
| full | Unannotated model generated without ARIA | Original complete-search baseline |
| static | Fresh ARIA priority-annotated model, no online POR | Static tool comparison |
| dynamic | Unannotated model generated with ARIA | Current online reduction |
| dynamic_no_por | Copy of dynamic sources, one PO definition disabled | Same-generated-representation full-search control |

All other copied cpp/h bytes must match the dynamic source. The helper fails if
it cannot remove exactly one PO macro; it records both configuration hashes and
the unchanged native-file count. It does not regenerate/alter actors or priorities.
Each mode is compiled with the same settings, gets one warmup and the same number
of measured rounds (default ten). The seeded base order rotates across FOUR
positions. Native runtime and peak RSS remain separate from generation, copying
and compilation. Ratios never mix new control measurements with old three-mode
timing samples.

`dynamic_no_por` controls the online POR package within its generated code. It
is not an assertion that every original-vs-dynamic code-generation difference
is individually identified or that toggling PO changes only C1: other PO-guarded
implementation behavior is disabled too. Original full versus dynamic comparisons
remain valid tool comparisons but do not isolate runtime reduction alone.

## Validation performed

Both two-worker families were freshly generated and run with one warmup plus two
measured runs in all FOUR modes. All results were satisfied; source-copy/config
checks and finite semantic audits passed. The new control must retain every
projected full action/outcome at every state and cover the complete projected
reachable reference. Persistent partial choices are not accepted as full search.
The restricted unused-sender/equal-time-queue projection retains its original
source/time guards and full successor-consistency checks.

The additional adversarial validation confirms exact recorded source-copy bytes,
rejects duplicate PO macros, and removes an exported control branch on a temporary
copy to verify that the full-control audit rejects it. This validator runs after
the small audit in the shell wrapper. Production Java/C++ generator source and
first-error exception handling are unchanged. Unexpected errors still fail the
healthy benchmark; timeouts remain explicit incomplete runs.

## New Linux repeated measurements

Fresh six-worker runs for BOTH families: one warmup and TEN measured runs per
mode, diagnostics/export disabled, same rotating four-mode design. All eight
mode/instance pairs completed as satisfied with stable state/transition counts.
These are Linux results; the new four-mode macOS study has not yet run.

| Family / 6 workers | Mode | States | Transitions | Native median s |
|---|---|---:|---:|---:|
| Independent | full | 27,153 | 131,569 | 0.4383 |
| Independent | static | 7,525 | 34,141 | 0.3618 |
| Independent | dynamic | 15,624 | 75,001 | 0.3916 |
| Independent | dynamic_no_por | 15,624 | 75,001 | 0.3956 |
| Shared | full | 188,641 | 976,825 | 1.2083 |
| Shared | static | 188,641 | 815,893 | 1.1147 |
| Shared | dynamic | 22,527 | 36,865 | 0.3765 |
| Shared | dynamic_no_por | 117,648 | 605,053 | 0.8938 |

Independent state/transition counts are identical with/without online POR. Their
~1% median time difference is within overlapping ranges and is not a demonstrated
speed benefit. The original full-to-dynamic raw state saving cannot here be
credited to runtime representative pruning. No full six-worker graph equivalence
certificate is claimed merely from matching counts.

Shared dynamic has about 80.85% fewer states than the same-generated PO-disabled
control and about 2.37 times smaller median native time. The original full-to-
dynamic comparison is about 3.21 times; this is a different denominator. Neither
ratio is a new macOS measurement or a general speedup guarantee. This extension
corrects attribution rather than changing the online reduction algorithm.

Raw files: `results/four_path_audit_linux_20261123.{json,csv}` and
`results/four_path_benchmark6_linux_20261123.{json,csv}`, with labeled ratios in
`results/four_path_benchmark6_linux_20261123_comparisons.csv`.

## Run on macOS

After pulling, use the same entry point:

```bash
bash tests/run_scaling_benchmark.sh
```

It runs the small four-mode audit/adversarial checks and then the fresh four-mode
performance suite. The new mode adds work, so expect a longer run than before.
Keep the system powered and otherwise idle for the measurements. Send the two
new audit/benchmark summary JSON files. `comparisons.csv` explicitly labels the
representation-control, online-POR-control and original tool comparisons. The
existing directory freshness, default timeout, partial-result and error rules
remain; see [SCALING_BENCHMARK.md](SCALING_BENCHMARK.md).
