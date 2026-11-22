# Online sufficient condition for distinct same-actor message alternatives

This feature requires no full state graph, saved state IDs or reference JSON.
It is deliberately narrower than the finite-graph oracle. It does NOT promote
the 27-state offline result or the 21-state priority experiment into RMC.

## Static certificate

From the compiler AST, ERDGSafetyAnalyzer builds separate local metadata. A
supported handler must have no parameters, no inheritance, and consist solely
of nested blocks and ordinary assignments of primitive int/boolean literals to
declared int/boolean state variables. Its write footprint is recorded. The
literal must fit int range or be true/false. Arrays, reads, guards, arithmetic,
loops, calls, sends, assertions, timing statements, local declarations, unknown
AST classes and unsupported types fail the whitelist. Two different supported
handlers are certified independent only if their write sets are disjoint.

This metadata does not change the JSON dependency matrix or its conservative
same-instance entries. It has its own stronger, explicitly delimited contract.

## Runtime certificate

The selector is enabled only for ARIA FTTS reduction with no property file, no user property
assertions/definitions and no symmetry. For candidate actor r:

- Every other actor queue must be empty, including future-dated messages.
- Every queued message of r must have a static local certificate.
- Parameters must have zero maximum frame length (conservative class-wide gate).
- ALL queued messages must be ready now, have infinite deadlines, and belong to
  the same equal-time/equal-priority alternative group. No postponed work hides.
- The chosen message-server ID must occur exactly once and commute with every
  other queued handler. Unknown IDs and all failed checks fall back.

The chosen alternative is executed as an action-level trial. The existing BFS
closed-successor proviso checks all its actual outcomes. If it fails, the solver
falls back to the ordinary actor/full expansion; it does not suppress the other
message alternatives in that fallback. Uncertified models retain the existing
solver path. Deadlock/assertion exceptions still propagate and stop execution.

## Why this is sufficient within the supported fragment

There can be no future activity outside the one finite queue: all other queues
are empty, and every pending handler performs only constant local assignments.
No message, clock update or nondeterministic branch can be generated. Any path
avoiding the chosen message therefore just removes some of the other queued
messages. The chosen message remains enabled. Its disjoint primitive writes
commute with every such handler, including sequences of those handlers. No
custom property observes a discarded intermediate valuation, and no queue
capacity can grow. All work is equally ready with infinite deadlines. This
establishes the restricted persistence/commutation/visibility conditions without
consulting a prebuilt graph. The normal proviso is retained as an extra safeguard.
The queue eventually drains in this fragment, and the original deadlock report
is preserved; this is not an instruction to continue past deadlock.

## Validation and limits

- Actual selector compiled at C++11 O0/O2; tests cover a positive distinct-handler
  case, shared-write rejection, unsupported handler, another queued actor,
  parameters, arrival/deadline/clock differences, priority-group differences,
  duplicate chosen method, disabled property gate and unknown message IDs.
- Actual Java whitelist/metadata code compiled and tested using typed AST fixture
  objects, including positive/disjoint and negative sends/reads/arrays/parameters/
  inheritance cases. This checks logic and syntax, not the external compiler JAR.
- Controlled generated-C++ replay with explicitly supplied certificate metadata:
  independent local writes give 4 states/4 transitions to deadlock, versus 5/5
  without the new selector. Conflicting writes retain 5/5 and deadlock. These
  controls include a Bootstrapper and are not the smaller fixture-model counts.
- LoadBalancer generated-code replay with all local certificates false retains
  38 states/46 transitions and satisfied. It contains sends and arithmetic, so
  it must not receive this certificate.

Full RMC regeneration with the external Rebeca compiler artifact remains to be
verified on the desktop. Tests never claim those counts are full explorations
for the intentionally deadlocking fixtures. Online support for sends, conditional
expressions, future enabling, nonempty other actors and general properties is
still absent and requires additional sufficient conditions. The original
38-versus-22 LoadBalancer state-count gap remains.

## Desktop checks

```bash
python3 tests/validate_isolated_local.py
python3 tests/validate_local_certificate.py
bash tests/compare_isolated_local.sh
bash tests/compare_loadbalancer.sh
```

The native fixture comparison generates two new models: disjoint writes and
shared writes. It requires both baseline and ARIA to stop with a deadlock trace,
requires a POR_LOCAL_ACTION trace and fewer discovered states in the positive
case, and rejects that trace in the conflicting case. The regular LoadBalancer
comparison must retain its previous counts. No full graph is read by either run.
