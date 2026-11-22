# Native quiescence boundary regressions

This suite adds four controlled variants of the supplied LoadBalancer model and
runs each plus the original through the real Java compiler/generator and native
C++ execution. Each case runs without reduction, with ARIA AST, and with exported
ARIA JSON. No production reduction rule is changed by this suite.

## Triggers

- `LoadBalancerSmall`: original positive case. Initialize is constructor-only;
  after consumption it can be excluded as a permanently disabled blocker.
- `QuiescenceResend`: Bootstrapper counts its starts and resends Initialize once
  from a handler, creating four circulating load tokens. The certificate must
  remain false for Initialize even after its second invocation, because this
  static analysis deliberately ignores branch truth when collecting senders.
- `QuiescenceFuturePending`: the constructor schedules Initialize after 2; the
  PrimarySource constructor also seeds a current-time load token. Hub becomes
  active while Initialize remains pending in the future. The static no-runtime-
  sender certificate is true, but the runtime queue test must keep the blocker.
  Its zero-time feedback cycle can prevent time from advancing to the pending
  message; satisfied reachability does not assert eventual delivery or progress.
- `QuiescenceTerminates`: both Hub feedback sends stop when their load reaches 3.
  All tokens are eventually consumed. Both baseline and reductions must stop at
  the first deadlock and provide a counterexample trace, even though the positive
  quiescence certificate was used before the error.
- `QuiescenceAssertion`: a handler executes `assertion(PrimaryLoad < 2)` after
  incrementing the load from 1. All three modes must report assertion failure when
  reached. The analyzer's unknown/non-message-call fallback disables all
  quiescence certificates in this model.

## Measured results

Each cell is report states / report transition counter. AST and JSON agree in
these runs, though matching counts is not the general criterion for correctness.

| Case | Baseline | ARIA AST | ARIA JSON | Outcome in all three modes |
|---|---:|---:|---:|---|
| Original | 101 / 202 | 27 / 32 | 27 / 32 | satisfied |
| Runtime resend | 1041 / 4062 | 338 / 720 | 338 / 720 | satisfied |
| Future pending | 19 / 20 | 18 / 19 | 18 / 19 | satisfied |
| Terminating feedback | 38 / 61 | 14 / 14 | 14 / 14 | deadlock |
| Assertion | 13 / 16 | 6 / 6 | 6 / 6 | assertion failed |

**The last two rows count work until the first error, not complete spaces.**
They must not be used to report complete-state-space reduction ratios. Trace
lengths/order may differ between baseline and POR. The assertion-failing state
can appear in a trace before being stored in the reached-state table.

The runner checks the actual emitted static certificate table for Bootstrapper,
not just final outcomes. It checks runtime skip/block events to exercise both
layers: the resend and future-pending cases have zero quiescence skips; the
original has 12; the deadlock case has 4; the assertion case has zero.
Smaller counts in the resend/pending rows come from existing reductions and
sender normalization, not from activating the new quiescence certificate. Deadlock
and assertion outcomes require nonempty first-error traces. No mode bypasses a
terminal or resumes after an error. No static priority model is used here.

## Reproduce

```bash
bash tests/compare_quiescence_models.sh
```

This builds ARIA and executable RMC with the available original compiler artifact,
then runs native generation/compilation/execution for 15 combinations. macOS uses
Java 17. The outputs and incremental `summary.json` are stored under
`tmp/QuiescenceModels/`. For existing built jars, run
`python3 tests/run_quiescence_models.py`; `--models QuiescenceResend` selects one
case. A partial selection's summary describes only those selected cases.

Every generated source is refreshed before native compilation; missing generated
C++ or unexpected outcomes fail the suite. Logs for each generator/build/run are
preserved. The JSON importer also verifies source hashes. Compiler errors do not
count as property failures. These are focused regression variants of one topology,
not broad validation across unrelated actor protocols, a general POR proof, or
an implementation of runtime COND guards.
