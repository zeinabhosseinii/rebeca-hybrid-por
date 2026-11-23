# Restricted inductive counter invariant checker

Historical diagnostic checkpoint: a restricted production integration now exists;
see [INVARIANT_GATE_INTEGRATION.md](INVARIANT_GATE_INTEGRATION.md). Statements
below about no runtime integration describe that earlier checkpoint.

This is a new OFFLINE proof prototype over the compiler's typed AST. It is not
wired to runtime selection or the full-barrier gate. Reports explicitly retain
`runtime_gate_changed=false` and
`runtime_observation_compatibility_certified=false`. It advances beyond predicate
footprints: within the stated fragment it checks initialization, inductiveness
and every assertion at its actual program point, without enumerating reachable
global states. It is not a formally verified implementation or a general POR
correctness theorem.

## Scope actually checked

* Closed, statically bound Timed Rebeca source compiled as Core 2.3; atomic FTTS
  handlers and signed 32-bit integer arithmetic are the semantic contract.
* No global/environment/feature variables, records/interfaces, inheritance,
  synchronous methods, class/method/main annotations or dynamic/null bindings.
* Scalar int state fields only, no field initializers: exactly one explicit,
  nullary constructor must initialize all fields on every analyzed path.
* Nullary handlers; plain local assignments, blocks, simple field-to-integer
  comparisons in if/else, and direct nullary untimed self/known-rebec sends.
* Assignment expressions use integer constants, local fields, addition,
  subtraction and negation. Every intermediate interval must fit int32, even
  if a later reset would return it to range. No C++ overflow wrap is assumed.
* Assertions are conjunctions of local scalar comparisons `< <= > >= ==` to
  int32 constants. Every state field needs an inferred lower/upper interval
  strictly inside the int32 extremes. Missing bounds or empty domains refuse.
* Loops, declarations inside handlers, parameters, arrays, casts, opaque calls,
  timing, nondeterministic expressions, compound assignments, increment,
  arbitrary boolean predicates and nonlocal field accesses are unsupported.
  Unsupported code is structurally refused even in a branch thought unreachable.

The verifier uses typed nodes/compiler labels rather than parsing source text or
matching counter names. Tests include renamed fields and equivalent branch order.
The constructor/handler/method checks are structural; bound values and class/
field names are taken from the source, not from a model-name whitelist.

## What constitutes a granted result

1. Collect bound assertions into a candidate interval I for each state field.
   Treat their conjunction as a proposed invariant, NOT an assumed fact about
   constructors or assertion program points.
2. Abstractly execute each constructor from uninitialized state. No implicit zero
   initialization is credited. Every read requires prior initialization and every
   normal exit must lie inside I.
3. For EVERY handler, including uncalled handlers, start from the product I and
   abstractly execute the complete body. Assignments transform intervals;
   comparisons split/refine true and false paths, and if/else outcomes are kept.
4. Each assertion must already follow from the current interval on every incoming
   path. Assertions do NOT narrow the analysis state or become assumptions.
   An assertion before a wrap can therefore fail even when the final field value
   would have been inside I.
5. Every normal handler exit must re-establish I. Path/node/depth budgets refuse
   rather than granting a partial analysis. Unsupported effects refuse.

For the healthy model, the candidate is cycle=[0,2] in each worker, Hub.count=[0,2]
and Hub.done=[0,1]. Increment produces [1,3] before the worker wrap; the branch
separates [1,2] from [3,3], resets the latter to zero and establishes the assertion
at its later program point. The same mechanism verifies the equality-triggered
epoch reset in Finish, without discarding a false-condition path.

The sufficient inductive argument is: constructors establish product I, and any
scheduled atomic handler from I preserves I and passes each assertion before
normal completion. Local scalar ownership, absence of opaque/shared external
writes, checked closed bindings and sends without local effects make this
compositional across actors. Induction over completed handler executions then
establishes the checked assertions along arbitrary executions of THIS model
under that contract. A send/other solver exception may stop an execution earlier;
it must not be caught and resumed as though the handler completed. The proof
does not establish deadlock freedom, fairness, queue-capacity bounds, termination
of a whole cyclic model or an all-N theorem for every generated source size.

For != guards, a disjoint complement may be overapproximated by its interval hull;
this can refuse a valid model. Nonconvex != assertions are not supported. More
generally a refused result is not a counterexample: the domain may be too weak,
an unreachable handler is still checked, or source lies outside the fragment.

## Tests and observed outcomes

Seventeen source-compiled cases were checked, seven granted and ten refused.
Granted: healthy two-worker model, three-worker and six-worker versions,
renamed fields, another valid constructor value, an extra in-range writer and
an equivalent reversal of the wrap guard. This is an inductive check for each
concrete source, not an enumeration of all message interleavings.

Refused: removed reset, invalid/missing initialization, extra out-of-range writer,
possible intermediate int32 overflow, an assertion moved before the wrap,
an unsupported loop, a tighter bound violated during a step, the earlier !=
fault fixture, and a missing lower bound. The extra-writer case illustrates
checking all handlers even when no current sender calls the new one.

Two genuinely faulty mutants were also generated and executed with the original
full solver, without online POR:

| Mutation | Native result | Explored states / transitions | Trace states |
|---|---|---:|---:|
| Remove Worker0 reset | assertion failed | 21 / 29 | 8 |
| Tighten Worker0 upper bound to <2 | assertion failed | 6 / 7 | 4 |

Both traces identify W0.Tick. These are first-error prefixes, not complete state
spaces. Other certificate refusals were NOT all claimed to be reachable native
bugs. The native solver and exception handling were unchanged.

Raw reports, candidate intervals, checked method lists, refusals and the two
native outcomes: `results/counter_invariant_linux_20261123.json`. Source and JAR/
verifier fingerprints are recorded. The tests were run on Linux; this new suite
has not been reported as run on macOS.

## Reproduction and runtime boundary

```bash
bash tests/check_counter_invariants.sh
```

The wrapper builds the Java 17 executable JAR and compiles the offline checker.
For existing JARs use:

```bash
python3 tests/check_counter_invariants.py --output tmp/CounterInvariantFresh
```

`--skip-native` runs only compiler/abstract-interpretation cases and is recorded
as such. Fresh directory required. Every source must compile; a compiler/process
failure cannot count as successful refusal. Individual source, compiler log and
certificate files are retained; the two native runs retain reports and traces.

A granted result discharges the assertion-truth obligation only under this
restricted semantics. Since such assertions are pure and always true, an erasure
argument may support a FUTURE narrowly gated extension. That still requires
production integration/review of the certificate, keeping time/bundle, C1,
observation, all-outcome and proviso conditions intact, plus positive/negative
runtime gate tests. No boolean is passed from this prototype to the generator.
The invariant check must not be treated as permission to ignore unproved or
failed assertions, enable arbitrary temporal properties, or resume after errors.
COND remains paused and no performance counts were forced.
