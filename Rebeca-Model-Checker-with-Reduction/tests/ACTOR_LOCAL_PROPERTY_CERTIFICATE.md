# Structural property-aware POR for actor-local runtime models

The optional `--aria-property-filter` path is no longer limited to one source digest. It now also admits a checked structural class: after initialization, every handler reads/writes only its own primitive state and sends only to its own resolved actor instance. Class, field and instance names, actor count and constant bounds are not hardcoded. The previously reviewed Cell fixture remains a separate legacy allowance; arbitrary communicating models are not newly admitted.

## Sufficient structural obligations

The shared typed-AST metadata must be complete. Its restricted fragment already excludes global/environment/feature/record data, reference/array state, inheritance/interfaces, synchronous calls, dynamic receivers, arbitrary builtins, timing, loops, opaque expressions and annotations. Handlers are finite blocks of scalar assignments, pure guards, untimed sends and local source assertions, with primitive parameters. Knownrebec bindings are statically resolved and cannot be reassigned by an accepted body. Runtime sends are then checked across **every handler**, including syntactically unreachable branches: each resolved destination must equal the handler owner's main instance.

Constructors are fully checked but may seed other actors before exploration starts. POR does not prune initialization. Static correlations in initial values/queues do not invalidate independence of subsequent actor-local transitions.

These obligations give disjoint actor-local state/queue effects between distinct actors. Another actor cannot change the selected actor's enabled message frames, branch inputs or source-assertion truth. Swapping their nonfailing transitions gives the same product state. All alternatives of a selected actor remain together: external-property mode still disables the separate isolated/passive split certificates. Existing native C1 checks remain mandatory as an additional conservative gate.

Property metadata must describe the supported external primitive state assertion. Partial candidates may not write any property-observed field. Hence they preserve the complete observed-field tuple, not merely the current assertion truth value. All alternative frames must pass this test. Unknown metadata, cross-actor runtime sends and other unreviewed structures retain full choices. Existing static annotations are explicitly refused; the feature does not pretend to reverse their scheduling effects.

Local source assertions are still executed. A pending local error is unaffected by other actors, and cycle protection prevents permanent deferral. This reasoning relies on the ordinary native/Rebeca execution contract; the metadata does not prove arithmetic bounds or repair unrelated compiler semantics.

## Explicit cycle rule and correct graph accounting

For this option, a partial candidate successor must satisfy NEW_STATE. Exhaustive candidates remain allowed. This replaces the optional path's previous open-successor allowance with a deliberately stricter rule; ordinary `--aria` without the property option retains its original proviso byte-for-byte. Each accepted partial edge increases discovery order in the zero-time supported fragment, so accepted partial edges alone cannot form a cycle. A failed trial falls back to another candidate or full expansion; it is not silently treated as accepted.

The expanded test suite exposed an **audit accounting issue**: native XML export includes valid transitions executed during trials of candidates that were subsequently rejected. A cycle in those trial-inclusive edges is not a cycle in final representative choices. The old rule's three-actor example also passes when checked on its actual final choices; the recorded export-only cycle is not evidence that the old proviso is unsound.

The new audit therefore uses complete diagnostic decisions to reconstruct each final selected actor set, while separately checking every exported trial edge belongs to the complete reference graph. It checks C0, initial observations, every retained action outcome, finite persistence/observed-tuple diamonds for partial choices and the strong sufficient cycle condition on final selections. It checks control aliases individually instead of unioning inconsistent outcomes. The stricter fresh-successor option makes the intended selected-cycle guarantee explicit; no general defect in the default proviso is claimed.

## Native results, Linux

All programs below use the real opt-in generator, compile native C++, and compare with a copy of that same generated code with PO disabled. The healthy graphs are complete and satisfied.

| Healthy model | States, both paths | Full unique edges | Filtered exported unique edges | Final selected unique edges |
|---|---:|---:|---:|---:|
| 2 actors, 3 values | 9 | 18 | 12 | 12 |
| 3 actors, 3 values | 27 | 81 | 39 | 33 |
| 4 actors, 3 values | 81 | 324 | 120 | 90 |
| Renamed class/fields/instances, 3 actors, 4 values | 64 | 192 | 84 | 72 |

Every healthy case passes the semantic and selected-cycle checks. The four-actor program exports 63.0% fewer unique edges (324 to 120), but **does not reduce its 81 states**. Selected edges omit valid rejected-trial work, so 90 must not be presented as the total exported work. Reported solver transitions are yet another counter (325 versus 130 here) and are recorded separately. No speed or memory claim is made.

A coupled two-actor model sends to its peer instead of itself. Its structural certificate is refused. Both paths finish satisfied with nine states, twelve unique edges, and all nine raw vertices semantically fully expanded. This tests actual conservative refusal on a communicating program.

Error cases compare first-error prefixes, not complete spaces:

| Case | Control | Filtered |
|---|---|---|
| External global violation | assertion failed, 2 states / 2 reported steps | assertion failed, 4 / 5 |
| Source assertion in all actors | assertion failed, 4 / 4 | assertion failed, 2 / 2 |
| Error only in deferred actor N2 | assertion failed, 12 / 15 | assertion failed, 6 / 8 |
| Terminating product | deadlock, 8 / 9 | deadlock, 4 / 4 |

Every error case has a nonempty native counterexample. The deferred-error test explicitly verifies that the failing transition belongs to N2, while the other actors continue self-sending and the external bound remains true. This protects against hiding an error in an unobserved actor. Deadlock is a real native stop; it is not skipped or replaced by a keepalive.

In total eighteen native case/control executions pass. Nine compiler-AST certificate checks cover local and renamed positive models; peer sends, unreachable peer sends, timed sends, arrays, increments, loops and annotations are refused. Full Maven executable assembly passed. Default native generated files without the option remain byte-identical to the pre-change external-property regression.

## Reproduce and scope

```bash
bash tests/check_actor_local_properties.sh
```

This builds RMC, checks the structural certificate, runs the nine native case/control pairs and audits every complete healthy graph. Sources, metadata, native programs, diagnostic decisions, XML and reports are retained in fresh output directories. Results are archived in `results/actor_local_properties_linux_20261123.json` and `results/actor_local_certificate_checks_linux_20261123.json`. The trial-inclusive cycle witness and its corrected interpretation are in `results/actor_local_open_successor_cycle_linux_20261123.json`.

This is a supported structural subclass, not a general admission of cross-actor messaging or arbitrary temporal properties. The LoadBalancer/Hub communicating pipeline is not covered by this new product certificate. The original static22/dynamic27 results are not relabeled as solved by it. The default path and error exceptions remain unchanged.
