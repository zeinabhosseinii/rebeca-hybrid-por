# Consumed fixed parameters and communicating-model scaling

The optional production queue certificate now accepts handler parameters used
in primitive assignments, branches and source assertions. Previously it
required every runtime parameter to be unread. **This is not arbitrary
parameter-sensitive POR:** every send to a particular receiver/method must
still have the same literal argument vector throughout the whole source.
Computed/forwarded arguments and multiple vectors are refused. Existing
zero-time, static-binding, unconditional runtime sends and bounded-queue
requirements remain. Unsupported models retain full choices under this
certificate. Native error handling, property visibility, dependency closure,
actor unions and successor proviso are unchanged.

## Why this extension is different from ignoring a payload

For each receiver/method, all constructor and runtime sends are checked before
admission. Thus every reachable message of that method has the same payload.
One can reason about the handler as its original body with those parameter
constants substituted. Its primitive state reads/writes remain the ones
computed from the typed AST, including reads in guards and source assertions.
Payload bytes and source assertions remain in native execution and graph
signatures; the implementation does not rewrite them away.

Identical source text is **not** sufficient to equate two parameterized
methods: their fixed argument values may differ. The scalar-program equality
relaxation is disabled whenever either method has formal parameters. This
keeps their normal read/write conflicts. The deliberately shared-field test
with identical `+ increment` bodies and different constants triggers 12 native
dependency rejections and passes the independent graph audit. The nullary
scalar equality rule remains available unchanged.

## Actual workload and matched control

The family is derived from the supplied communicating LoadBalancer. Dispatch,
Forward and both Hub handlers now take a limit parameter and use it in their
wrap-around branches. Five periods are tested: 3, 6, 12, 48 and 192. The
external assertion checks the Hub load ranges; it is not fairness or liveness.
A separate shared-Hub model consumes a parameter in arithmetic. Error variants
include a violated external property, a source assertion reading the parameter,
and terminated feedback that genuinely deadlocks.

| Period | Same-generated POR-off states | Property-aware POR states | Reduction |
|---:|---:|---:|---:|
|3|64|42|34.4%|
|6|127|81|36.2%|
|12|253|159|37.2%|
|48|1009|627|37.9%|
|192|4033|2499|38.0%|

These are matched native controls obtained by removing only the PO macro.
They are not the separate 101-state generator baseline or static priority22.
The native code has no complete reference graph available during reduction.
Full graphs are generated separately for validation after execution.

| Deliberate error | Control states before error | Reduced states before error | Result |
|---|---:|---:|---|
| External property violation |8|5|assertion failed|
| Source assertion consuming parameter |16|8|assertion failed|
| Terminated feedback |23|14|deadlock|

Errors stop immediately with nonempty counterexample traces. Those counts are
prefixes, not complete state-space sizes. A mixed-payload mutation is refused
and both paths visit 166 states. Solver step differences in refused cases can
include rejected trials; they do not indicate final partial choices.

## Checks and reproduction

`bash tests/check_fixed_parameters.sh` builds the executable JAR, checks typed
payload admission/refusals, and runs ten models in both native modes (20 runs).
Add `--benchmark` to compile separate O2 binaries without graph export or POR
diagnostics and run five measured repeats plus a warmup per binary on all five
healthy scales, with deterministic randomized execution order.

Every completed healthy validation graph checks initial correspondence, C0,
retained outcomes, property observations, set-level persistence/diamonds and
strong cycle coverage using final selected edges. Exported rejected-trial
edges are validated separately. Error models test actual first-error stopping.
The prior 12 nullary communicating programs and default generation were also
regenerated and found byte-identical. Eleven previous AST refusal checks pass.
These finite results support the implementation in the admitted fragment;
they are not a general Rebeca soundness theorem.

Saved evidence:
- `results/fixed_parameter_validation_linux_20261124.json`
- `results/fixed_parameter_ast_linux_20261124.json`
- `results/fixed_parameter_performance_linux_20261124.json`
- `results/fixed_parameter_regression_linux_20261124.json`
- `results/fixed_parameter_prior_checks_linux_20261124.json`

Ready-to-open sources and properties are `fixtures/FixedParameterLoad3.*`,
`fixtures/FixedParameterLoad192.*` and `fixtures/FixedParameterViolation.*`.

## Timing and memory: measured limitation

Ten binaries (five sizes times two modes) were built without graph export or
POR diagnostics. All 50 measured runs plus 10 warmups reproduced the audited
outcomes and counts. On period192, median wall time was 0.311s control and
0.315s reduced; median peak RSS was 1,707,544 and 1,706,904 KiB. This does not
show a speed or meaningful process-memory improvement. Solver state-storage
estimates did decrease from 96,792 to 59,976 bytes, which must not be confused
with process RSS. The native default hash exponent24 allocates substantial
fixed tables (Main.cpp), explaining why these small graphs do not dominate
memory or startup. Its existing `-s` option only permits increasing the size.
No table-size or engine behavior was changed for these measurements.

The validated result is state-space reduction and retained error detection;
no performance win is claimed. Larger communicating families or a separately
validated hash-allocation change would be needed to study that bottleneck.
The saved validation summary abbreviates long partial-certificate lists to
counts, digests and examples; the validator regenerates the complete lists.
