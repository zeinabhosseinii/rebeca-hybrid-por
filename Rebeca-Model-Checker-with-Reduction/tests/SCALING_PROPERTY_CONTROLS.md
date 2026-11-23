# Explicit assertion controls and the property-scope boundary

Historical diagnostic checkpoint: a restricted production integration now exists;
see [INVARIANT_GATE_INTEGRATION.md](INVARIANT_GATE_INTEGRATION.md). Statements
below about no runtime integration describe that earlier checkpoint.

These are native correctness regressions, not additional performance timings.
Production generator, dependency rules, proviso and error handling are unchanged.
The new four-mode macOS measurements are also archived in
`results/four_path_macos_20261123_{audit,benchmark}.json`; the readable complete
metrics are in [results/four_path_macos_20261123.md](results/four_path_macos_20261123.md).
All source hashes match the generator and all warmups/repetitions were satisfied.

The recorded macOS shared-six control has 117,648 states / median 0.91555 s with
online POR disabled, versus 22,527 / 0.28799 s with it enabled: about 80.85% fewer
states and 3.18 times smaller median native time. Against static (1.17903 s), the
ratio is about 4.09. Independent 4/6/8 controls have identical state/transition
counts with/without online POR and no demonstrated runtime benefit. These are
native benchmark comparisons with explicit denominators, not a global claim.

## Assertions and deliberate error

Starting from the exact shared two-worker epoch model, the healthy fixture adds
source assertions at the end of each affected handler:

* Workers: `0 <= cycle && cycle < 3`.
* Hub Step handlers: `0 <= count && count < 3`.
* Hub Finish handlers: `0 <= done && done < 2`.

The checks occur after the increment/wrap or epoch reset. The fault fixture
retains ALL healthy assertions and differs by exactly one added assertion in
Worker1.Tick, immediately after increment: `assertion(cycle != 2)`. A worker
reaching its second step violates that assertion. The fixture does not replace
an actual failure by a loop or change error handling. Checked sources are saved
as `fixtures/ScalePropertyHealthy.rebeca` and `fixtures/ScalePropertyFault.rebeca`.

All four modes use the same assertion bodies. The runner regenerates static
annotations and checks body preservation; dynamic_no_por uses the exact native
copy helper. Healthy runs must be satisfied. Fault runs must report assertion
failed, have a nonempty counterexample and identify the W1/TICK failing edge.
An unexpected outcome, deadlock, missing trace or different fault edge fails the
runner. Error runs are explicitly incomplete explored prefixes, not full graphs.

## Observed Linux results

| Fixture | Mode | Result | States / transitions | Trace states |
|---|---|---|---:|---:|
| Healthy bounds | full | satisfied | 157 / 277 | 0 |
| Healthy bounds | static | satisfied | 157 / 265 | 0 |
| Healthy bounds | dynamic | satisfied | 128 / 189 | 0 |
| Healthy bounds | dynamic_no_por | satisfied | 144 / 253 | 0 |
| Injected fault | full | assertion failed | 12 / 16 | 5 |
| Injected fault | static | assertion failed | 12 / 16 | 5 |
| Injected fault | dynamic | assertion failed | 8 / 8 | 4 |
| Injected fault | dynamic_no_por | assertion failed | 12 / 16 | 5 |

Every fault trace identifies W1.Tick. Trace counts include the solver's synthetic
error state. No native run continued after that first assertion failure.
`results/scaling_property_controls_linux_20261123.json` records the measurements.
These new assertion controls have not yet been executed on the user's macOS.

## Important scope finding

With these source assertions, the EXISTING conservative AST gate generates
`return false && _porResultState->porFullExpanded` in the dynamic helper. There
are zero full-barrier events in both fixtures. Assertion calls are outside the
current restricted zero-time certificate; this is the pre-existing fail-closed
behavior, not a new forced disablement or changed benchmark flag.

Therefore the assertion detection result cannot be cited as proof that the
completed-full-barrier optimization preserves arbitrary assertions. Its guarded
optimization is inactive in these property-bearing runs. The healthy dynamic
count differs from the no-assertion benchmark (128 versus 117), consistently with
a changed supported fragment. No unsupported gate is lifted to recover speed.

These checks establish concrete bounds/bug detection on the tested finite
instances. They are not a general theorem for all properties, worker counts,
scheduler fairness, deadlines or arbitrary temporal logic. Lifting the assertion
scope restriction requires a justified observation/visibility certificate and
relevant semantic/negative checks; a successful assertion regression alone is
insufficient. Runtime COND work remains paused.

## Reproduce without performance reruns

With already-built Java 17 JARs:

```bash
python3 tests/check_scaling_properties.py --output tmp/ScalingPropertyControlsFresh
```

Fresh directory required. Per-mode generated sources, logs, reports, counterexamples
and the summary are retained. The runner records unexpected failures and rethrows
them; only the deliberate assertion failure is an expected test outcome. Native
solver exceptions themselves are never bypassed by the driver.
