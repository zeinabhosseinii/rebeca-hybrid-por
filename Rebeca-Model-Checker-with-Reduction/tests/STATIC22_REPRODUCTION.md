# Exact static-22 reproduction

`fixtures/LoadBalancerSmall_static22.rebeca` is the frozen ARIA-generated priority
model, byte-for-byte copied from the output used for the 22-state measurement.
The body matches `../ARIA/benchmarks/LoadBalancerSmall.rebeca`: after removing
priority-only lines and blank lines, every remaining line matches. Counters,
queue sizes, sends, constructors and main bindings are unchanged.

SHA256 of unannotated model:
`fbd2dbefff81ef86df52c961ba93784f8f5f3ff4bea7a2e9cf9c842ae579108b`

SHA256 of frozen annotated model:
`32f3cd5401a999dc24c002336aad3ab7decec8d2b9b39176dc3d037a8a662487`

| Actor | Priority |
|---|---:|
| PrimarySrc | 1 |
| SecondarySrc | 2 |
| PrimaryRelay | 3 |
| SecondaryRelay | 4 |
| Hub | 5 |
| Bootstrapper | 6 |

Hub.ReceiveSecondary has message priority 1, Hub.ReceivePrimary priority 2;
all other handlers have priority 1. Smaller numbers win in this backend.

Run from the RMC directory:

```bash
bash tests/reproduce_static22.sh
```

The command builds executable RMC and independently generates/compiles/runs both
models. Settings: Java 17, RMC 2.14 with the original compiler 2.27 artifact,
TIMED_REBECA v2.3, default FTTS and safe mode, g++ C++11/O2. Neither run uses
`--aria`, `--aria-json`, online PO or TTS. Reports and sources are stored under
`tmp/Static22Reproduction/{baseline,static22}/`. The reproduction checks the model
body match, hashes, no-PO/default-FTTS configuration and expected report values:
unannotated 101 states / 202 transitions; annotated 22 / 26; both satisfied.
A GUI run must use the same semantic settings to compare counts meaningfully.
The default checked property is deadlock/deadline reachability; the source's
balance sentence is a comment, not a formal checked balance property.

## What this does and does not establish

22 is an observed count for this exact annotated model and backend configuration,
not a claim that any tool/engine must always return 22. Matching property results
and a smaller graph do not prove the general priority reduction sound.

The dynamic ARIA path uses action keys `(instance, handler)` in its dependency
matrix, but its general ample candidate is still an actor, with all its queue
alternatives examined. Restricted local/passive-send rules can select a specific
alternative; they do not cover LoadBalancer feedback. Runtime COND pruning is
not connected. Therefore it would be inaccurate to call the current dynamic
implementation a complete, optimal action-level reducer.

Even a correct action-level algorithm has no automatic guarantee of a graph
smaller than every static scheduling policy. Candidate choice, eligibility and
cycle conditions matter. Here the static run enforces priorities while the
dynamic run tries its safety checks and conservative BFS proviso. After Initialize
then PrimarySrc.Dispatch, static selects SecondarySrc.Dispatch and dynamic
selects PrimaryRelay.Forward. See HUB_ALTERNATIVES.md for controlled measurements.
These measurements do not establish that the entire generator is bug-free.
