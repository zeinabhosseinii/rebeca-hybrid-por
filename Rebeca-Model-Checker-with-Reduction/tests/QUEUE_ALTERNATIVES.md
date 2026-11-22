# Conservative same-actor queue-alternative reduction

This step implements exact-equivalence pruning, not a general commutativity rule
for distinct message servers. In particular it does NOT adopt the experimental
21-state Hub priority schedule as a sound production reduction.

## Enabled rule

For alternative index k > 0, skip it only if entries k and k-1 are identical in:
message ID, raw sender ID, execution time, deadline, and every parameter byte.
They must be adjacent. Missing parameter buffers cause fallback. Unknown values
or different fields cause fallback. The first alternative always runs.

changeOrder(k) moves that queue entry to the head using adjacent swaps. With two
adjacent identical entries, changeOrder(k) and changeOrder(k-1) yield the exact
same entire queue, including the order of all intervening entries. No state
variable, other actor state, clock or payload is changed by choosing between
those two representations. The same handler with the same nondeterministic
branches then executes from the identical configuration. The earlier alternative
therefore covers the later one, including its assertion/deadline/deadlock result.
This argument does not assume handlers are read/write independent. Equal
nonadjacent entries do NOT suffice: moving them to the head can produce a
different remainder order, so these alternatives are retained.

This applies only to reduction builds (PO). Plain baseline generation retains
its ordinary enumeration. On failed actor-level reduction, full expansion also
avoids only these exact duplicate scheduler choices. The cycle proviso remains
unchanged and is applied to every actually executed singleton-trial successor.
No exception is caught and ignored by this feature.

## All-alternative safety

The former `numberOfAlternatives == 1` restriction is replaced by checking the
existing global safety relation for EVERY candidate message ID of that actor,
without reordering or mutating the queue during the check. A safe queue head
cannot mask an unsafe second alternative. All nonequivalent alternatives and all
handler nondeterministic branches still execute during an accepted actor trial.
The ordinary closed-successor proviso and full fallback remain.

This does not relax the conservative JSON same-instance dependency table. It does
not remove a different handler merely because two variable footprints are disjoint.
Sending, queue bounds, enabling, timing and property effects still need a sound
independence argument before that broader rule can be enabled.

## Validation completed

- The predicates are extracted from the actual template and compiled under
  C++11 at O0/O2. Exhaustive queues of length 1..5 over six message variants
  check that every pruned choice gives exactly the same reordered queue.
- Counterexamples cover different methods, sender, payload, arrival, deadline,
  missing parameter buffers, nonadjacent equal messages and a safe first/unsafe
  second message alternative.
- Existing future-dependency/array/terminal regressions pass, including with
  diagnostics enabled.
- Generated C++ replays: AST and corrected JSON each return satisfied with
  38 states and 46 reported transitions (previously 38/52). Each trace logs
  eight equivalent-alternative skips. Transition totals also include trial and
  fallback attempts, so eight skips do not mean eight fewer unique graph edges.
- Modified generated-model controls still immediately report deadlock (4 states,
  4 transitions, 4 trace states) and assertion failed (2 states, 2 transitions,
  3 trace states), matching the previous solver.

The state-count gap 38 versus static ARIA's 22 is still open. This step removes
redundant choices safely; it does not claim to solve same-actor commutativity or
runtime COND evaluation. No new general POR proof is claimed. Full Java/RMC
regeneration must also be checked on the desktop that has the compiler artifact.

Run:

```bash
python3 tests/validate_queue_alternatives.py
python3 tests/validate_ftts.py
bash tests/compare_loadbalancer.sh
```
