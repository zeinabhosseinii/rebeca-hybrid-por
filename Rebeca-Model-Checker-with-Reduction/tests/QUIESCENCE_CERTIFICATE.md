# Post-constructor quiescence certificate

This is an online refinement of ARIA's global method dependency scan. A matrix
entry is unchanged; a blocker is skipped only in a state where it is certified
permanently disabled. No model names or handler names are hardcoded.

## Sufficient condition and argument

The Java analyzer gathers every message-server name sent by any runtime handler
of any reactive class, ignoring guards and receiver identity. A handler name
absent from that overapproximation has no runtime sender. Same-name handlers on
unrelated actors prevent certification too, intentionally conservative.

The analysis accepts exact blocks, conditionals, while loops, binary/unary
expressions, literals, dot access and term nodes. It traverses indices, send
arguments, and timed-send after/deadline expressions. Unknown nodes, for loops,
declarations, non-message calls, synchronous methods, interfaces on a class,
inheritance, subclasses of the supported actor/method AST nodes, and missing
handler bodies disable all certificates. Unsupported syntax is not silently
ignored. Constructors are excluded from runtime-sender collection because the
online search begins after construction has completed.

A true table entry alone does not remove a blocker. The generated C++ scans
**every slot of that instance's queue**, including delayed messages and non-head
entries. If the handler appears anywhere, it remains a blocker. Otherwise it is
absent now and no runtime action can enqueue it later, so it stays disabled on
all continuations. Existing constructor-scheduled messages are covered by this
queue test. No assumption that an empty queue alone implies permanent absence
is made. Self, sender and aliased receivers are covered by name-based collection.

The refinement is gated to ARIA with no symmetry and no property model,
assertions or property definitions, reusing the existing restricted-fragment
gate. Other modes retain their existing behavior. The original BFS proviso,
all-alternative checks, fallback and deadlock/error exceptions are unchanged.
`POR_DISABLE_QUIESCENCE` compiles a regression control retaining the old global
check. It does not change deadlock handling.

This argument certifies only this removal of permanently disabled blockers.
It is not a new proof of the pre-existing dependency matrix or all POR behavior.

## Complete generation and execution

With Java 17 and the original compiler 2.27 artifact supplied by the user:

| Mode | States | Transitions | Result |
|---|---:|---:|---|
| Baseline | 101 | 202 | satisfied |
| Static priorities | 22 | 26 | satisfied |
| ARIA AST, certificate disabled | 38 | 46 | satisfied |
| ARIA AST, certificate enabled | 27 | 32 | satisfied |
| ARIA JSON, certificate enabled | 27 | 32 | satisfied |

The online enabled traces have 25 reduced expansions and 2 full expansions
(initial dependency and one closed-successor proviso fallback). The imported
JSON dependencies remain unchanged. No static priorities were added to ARIA.
These transition counters include trial/fallback work; they are not necessarily
unique graph edges. The offline action reference's 27 states / 27 edges is a
separate algorithm; matching state counts do not imply equivalent graphs.
The source comment about balance is not a formal checked balance property.

Run:

```bash
bash tests/compare_quiescence.sh
```

The script rebuilds ARIA/RMC, generates all four modes, checks reports, compiles
the same generated AST source with the certificate disabled, runs the Java
certificate tests against the actual compiler AST API, and compiles the actual
generated safety function with queue mutations at O0/O2. The latter checks
pending head/tail slots, absent-but-resendable handlers, gate-off and disabled
controls. Existing isolated-local and passive-send fixtures must still stop at
the first deadlock with counterexample traces.

Decision reports are written by `tests/audit_por_decisions.py`. The new event
`POR_QUIESCENT_SKIP` names each blocker excluded by this certificate. This is
not a queue-head-only safety check. Full comparison with general feedback
sends, other properties and runtime COND evaluation remains separate work.
