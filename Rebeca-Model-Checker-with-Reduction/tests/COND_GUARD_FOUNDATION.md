# Typed COND guard evaluation foundation

`AriaGuardEvaluator` evaluates schema-v2 expression trees against an explicitly
provided **single-access-scope snapshot**. It returns TRUE, FALSE or UNKNOWN and
the state/parameter bindings read. It is not wired into C++ ample-set selection,
does not modify dependency matrices, and provides no persistence certificate.
All COND pairs continue to be imported as dependent.

## Supported subset

- Boolean and signed 32-bit integer literals; integer tokens only (not strings,
  decimal/exponent literals or floating-point values).
- Separately supplied typed state variables and handler parameters; the caller
  must provide the correct actor/handler scope. No global name lookup or implicit
  state-to-parameter fallback is used.
- Boolean `!`, `&&`, `||`; typed equality/inequality; integer comparisons and
  `+`, `-`, `*`, `/`, `%`, unary plus/minus.

Unsupported nodes/operators, exporter `unknown` nodes, missing/untyped bindings,
type mismatches, overflow, invalid division and malformed ASTs return UNKNOWN.
No source/expression string is executed. Depth and node budgets limit traversal.
UNKNOWN propagates strictly even where Boolean short-circuiting could determine
a result; unsupported conditions are not simplified into permission to prune.
An integer result alone is not a Boolean guard.

A snapshot FALSE can become TRUE after a writer. The unit tests explicitly show
this and verify that the existing importer still retains COND. The evaluator
does not prove absence of flippers, resolve future queued parameter values, model
intermediate writes, or supply sender/local-variable bindings. A future runtime
rule must justify these independently, along with queue/enabling effects and
the existing cycle proviso.

## Actual SlotGuard audit

The diagnostic reader checks schema/source hash and resolves all four access
references of each shared-destination reason. It checks index bounds, source
action association, SEND kind, receiver binding, destination handler and variable
association. These are cross-reference consistency checks, not a proof of the
exporter's semantic completeness.

The regenerated SlotGuard table has 6 COND pairs. After deduplicating references
within each pair there are 48 guard probes; all 48 return UNKNOWN with empty
bindings. More fundamentally, each pair contains exporter-unknown conditions:

- Approach sends use unresolved local `FlyTime`, and a `Window` parameter needs
  a concrete frame; send arguments also contain unresolved local `Missed`.
- Destination Report writes depend on unsupported `sender` comparisons and
  unresolved known-rebec identifiers Alpha/Beta/Gamma/Delta.
- Exported flipper metadata identifies Report and Tick as changers of the tower
  state flags. It is recorded for inspection, not assumed a complete certificate.

Supplying a value named `sender` in a map cannot override an AST `unknown` node.
No guard or dependency is cleared by this audit. `stabilityProven` is false in
all six diagnostic records, including any subexpression that happens to be
constant. The audit never labels a pair independent based on a snapshot.

## Validation and reproduction

```bash
bash tests/compare_cond_guards.sh
```

This rebuilds ARIA/RMC, regenerates SlotGuard JSON, compiles the tests against
the executable RMC JAR, and writes `tmp/SlotGuard_cond_guard_audit.json`.
The Java tests cover typed truth values, separated bindings, unknown sender,
Boolean/type errors, malformed expressions, arithmetic edges, depth limits,
a state-writer flip and preservation of imported COND dependencies.
The native Java diagnostic integration additionally rejects intentionally bad
indices, missing methods, source-hash mismatch, action mismatch and destination
handler mismatch. Missing inputs or inconsistent references fail the command.

Full Java compilation and both test layers passed on the validation host with
the original compiler 2.27 artifact. No C++ solver behavior changed, so the
previous LoadBalancer 27/32 and first-deadlock behavior are not new measurements
of a runtime guard optimization. Runtime COND pruning remains unimplemented.
