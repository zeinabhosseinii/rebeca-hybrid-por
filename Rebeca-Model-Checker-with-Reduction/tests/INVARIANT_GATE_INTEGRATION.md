# Restricted invariant-certified assertion integration

The production gate now admits a narrowly proved class of source assertions.
This supersedes the earlier offline-only checkpoints; it does not grant general
assertion/LTL support. `CounterInvariantCertificate` is a per-analysis production checker using the
existing compiler AST and no new library dependency. It creates fresh analysis state for every call,
uses the previously tested interval algorithm, and returns false on unsupported
input/analysis refusal. No global mutable certificate state is shared.

## Exact gate and sufficient argument

The original assertion-free structural path is tried first. If it fails, the
new path requires BOTH:

1. Every source assertion has an inductive interval proof under the restricted
   contract in [COUNTER_INVARIANT_CERTIFICATE.md](COUNTER_INVARIANT_CERTIFICATE.md).
2. The independent existing structural zero-time scan passes, recognizing only
   those already-proved builtin assertions as permitted untimed calls.

The file generator STILL requires ARIA, no symmetry, no external property model
and no property assertion/definition objects. No C1 matrix, same-actor split,
parameter/nondeterminism treatment, queue-equivalence filter or proviso predicate
was relaxed. Quiescence retains its original scanner with assertion permission
false. Local/passive certificates are not broadened by this change. No new
command-line flag is required. Runtime COND remains paused.

Within the checked closed atomic int32 fragment, constructors establish product
interval I, every handler preserves it, and every assertion is established at its
actual program point. Its expression is pure and total. The generated assertion
implementation has no effect on true conditions and throws on false ones.
Consequently erasing these PROVED always-true checks is semantically inert under
that contract; the assertion-free zero-time/barrier argument and existing C1/
observation assumptions then apply. This is the extra obligation discharged, not
a new proof of the pre-existing dependency analyzer or all POR behavior.

Assertions are NOT erased from emitted C++. They continue to execute and throw
normally. No solver exception is caught and resumed. An invalid constructor,
unknown writer/effect, noninductive bound, overflow possibility or unsupported
predicate keeps the original conservative path. It does not turn a false
assertion into a true assertion. External properties are outside this proof.

## Checks performed on the integrated executable JAR

* Maven/Java 17 build succeeds (original compiler 2.27 dependency).
* The production certificate and final structural gate agree with all 17
  positive/negative source cases from the offline matrix. Seven are admitted;
  ten refuse. 136 concurrent calls on immutable compiled models give the same
  answers; analysis state is isolated per call.
* Existing real-AST full-barrier and quiescence tests pass, as do compiled native
  proviso helpers and actual candidate-trial-loop controls.
* For the original unannotated LoadBalancer, all 30 generated cpp/h files are
  byte-identical to the pre-integration sources. Its assertion-free path is kept.
* Fresh full/static/dynamic/PO-disabled runs on healthy and faulty assertion
  fixtures preserve the expected property outcomes. All source assertions are
  still present in generated actor C++.
* Healthy positive graphs pass the independent finite action-outcome/persistence/
  diamond and strong-cycle audit, including full behavior in the PO-disabled
  control. This audit remains restricted to the reviewed source hash/projection.
* Removing a reset or tightening the bound keeps the production gate false and
  the generated online checker stops at assertion failure with trace.
* Explicit after(0), symmetry and an external property definition each generate
  a disabled closed-barrier gate. They are not enabled by source invariant truth.

## Recorded Linux native results

| Model | Mode | Result | States / transitions | Gate literal | Full barrier events |
|---|---|---|---:|---|---:|
| Healthy assertion bounds | full | satisfied | 157 / 277 | absent | 0 |
| Healthy assertion bounds | static | satisfied | 157 / 265 | absent | 0 |
| Healthy assertion bounds | dynamic | satisfied | 117 / 145 | true | 63 |
| Healthy assertion bounds | dynamic_no_por | satisfied | 144 / 253 | true, PO off | 0 |
| Deliberate != fault | dynamic | assertion failed | 8 / 8 | false | 0 |
| Removed reset | dynamic | assertion failed | 12 / 12 | false | 0 |
| Tightened bound | dynamic | assertion failed | 5 / 5 | false | 0 |

The old healthy dynamic control had 128 / 189 with the gate false; the new
proved-source path reaches 117 / 145. These are correctness diagnostics, not
performance timings. PO-disabled source contains a true helper literal but cannot
use it because PO is off. Its zero barrier-event count is expected.

A further fixture has a proved bound but intentionally terminates:
`InvariantCertifiedDeadlock.rebeca`. Full and dynamic both report DEADLOCK at
2 states / 2 transitions with nonempty traces. The dynamic gate is true, yet
there are ZERO completed-full-barrier events: executeRebec throws at the deadlock
before any full-completion marker. Thus assertion truth does not bypass deadlock
or convert an erroring expansion into a barrier. A bound certificate is not a
deadlock-freedom certificate.

Raw integrated results: `results/invariant_gate_integration_linux_20261123.json`.
This new integrated suite has not yet been reported as executed on macOS. Older
performance datasets remain tied to their prior JARs and must not be silently
relabeled as timings of this extension.

## Reproduction

```bash
bash tests/check_invariant_integration.sh
```

The wrapper builds, generates the mutation matrix, compares production gates,
runs the concurrent and original AST controls, generates/native-runs both four-
mode assertion fixtures, audits the healthy graph, and runs dynamic fault,
certified-deadlock and excluded-gate controls. Reports are under a fresh
`tmp/InvariantIntegration_<stamp>` directory. Its `validation/summary.json` is
the main integrated result; logs and individual native traces are retained.
No performance suite needs to be rerun to check this correctness extension.

The checker remains a tested restricted implementation, not a formally verified
proof engine. No arbitrary source assertion, temporal property, timed merging or
new same-actor independence rule is authorized by this change.
