# Validation status and next measurement, 2026-11-23

Implementation/results reference before this audit:
`b4f9dc9b1b83f420852eeff276f35713b260018c` on
`aria-action-dependency-export`. No production source changed in this step.

## Completed evidence

| Claim | Evidence | Limit |
|---|---|---|
| First errors are not suppressed | Deadlock/assertion fixtures stop with traces in full/static/dynamic paths | Not exhaustive coverage of all exception paths |
| Restricted full-barrier proviso | Actual native helper/trial controls, AST scope gate and selected-core cycle audits | Requires stated zero-time/bundle and C1/observation assumptions |
| Scaling small-instance semantic behavior | Both static/dynamic graphs of independent/shared families with 2 AND 3 workers pass finite checks | Not an inductive proof for arbitrary N; sender/equal-time-queue projection is restricted and successor-consistency checked |
| Measured performance | macOS 10-repeat rotated runs, all satisfied | Native timing only; generated families, not all applications |
| Shared-Hub mechanism | Separate Linux native controls isolate completed-full-barrier effect | Diagnostic traces and outcome checks, not a six-worker full-graph certificate |

## New three-worker finite audit

Fresh Java generation and native C++11/O2 runs, with export enabled solely for
finite auditing, produced:

| Family | Full states / transitions | Static states / transitions | Dynamic states / transitions |
|---|---:|---:|---:|
| Independent / 3 | 185 / 457 | 107 / 247 | 124 / 301 |
| Shared / 3 | 469 / 1,225 | 469 / 1,141 | 207 / 289 |

All completed as satisfied. Source fingerprints, observations, initial states,
C0, retained outcomes, partial-expansion persistence/diamonds and the strong cycle
condition passed in the reviewed finite projection. The static independent graph
has 53 full vertices and 96 partial-action certificates; the dynamic independent
graph has 124 full vertices and no partial-action certificate. The static shared
graph has 391 full vertices and 138 partial-action certificates; the dynamic
shared graph has 72 full vertices and 135 partial-action certificates. Certificate
counts are action checks, not numbers of reduced states.

Raw evidence: `results/scaling_audit_three_workers_linux_20261123.json`.
Reproduce with already built JARs and Java 17:

```bash
python3 tests/benchmark_scaling.py --output tmp/ScalingAudit3Fresh \
  --sizes 3 --repeats 1 --audit-small
```

## Consequence for attribution

For independent 2- and 3-worker instances, EVERY dynamic state is semantically
full relative to the normalized reference. Its smaller raw state count therefore
cannot be cited as evidence of runtime representative pruning in those instances.
This finding concerns those audited sizes; larger independent sizes have not
received the same full semantic audit. It reinforces the need to distinguish
generated representation/normalization from POR rather than generalize from raw
counts. Static can still prune real choices under this audit.

For shared three workers, 135 of the 207 dynamic states are partial and have
certified retained action behavior; the cycle certificate also passes. The shared
six-worker diagnostic already measured 117,648 states in the dynamic-generated
PO-disabled control versus 22,527 current dynamic states. The original full
baseline has 188,641 states. These controls provide different comparisons and
must retain their labels.

## Next work, in order

1. Add dynamic-generated PO-disabled native code as a FOURTH, uniformly measured
   benchmark mode, in both families, with the same warmup/repetitions/order policy.
   This separates native POR effects from generated representation effects. The
   existing full/static/dynamic end-user comparisons remain valid as labeled,
   but do not isolate a pure POR speedup.
2. Obtain a general correctness argument for the actual retained-candidate
   conditions and their observation scope, or keep claims explicitly finite and
   fragment-scoped. An all-N queue-bound/epoch argument alone does not prove C1
   for all-N executions.
3. Extend evaluation to an independently selected application family and explicit
   properties before asserting broader performance/property-preservation results.

Runtime COND work remains paused. Reaching the static count is not a correctness
criterion. No general bug-free-generator claim, global priority-safety claim,
general memory advantage or induction over all model sizes has been established.
