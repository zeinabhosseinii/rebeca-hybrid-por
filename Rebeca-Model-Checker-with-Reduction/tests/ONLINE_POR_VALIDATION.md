# Semantic audit of the online LoadBalancer reduction

The current AST and JSON solvers each have 25 accepted reductions, checked against the completed
64-state unprioritized, sender-normalized graph. This is a finite-model audit,
not an online optimization and not a general proof of the Java/C++ generator.
It requires the full graph as input; it is not a claim of faster model checking.

## What is checked

`audit_online_por.py` consumes the actual online export and ordered diagnostic
log. It maps states by their exported contents using the exact benchmark hash
and unused-sender projection from the Hub audit. Numeric state IDs are not
assumed to correspond across runs. Zero-time, single-bundle, satisfied inputs
are required. Unknown mappings or incomplete decisions cause failure.

For every exported online edge it checks that the full graph contains the same
action and destination state. For each accepted trial it requires a single
distinct action identity of the selected actor, then checks:

1. The action remains enabled on every path avoiding that action.
2. All selected outcomes preserve the exported property observations.
3. For every other action and every nondeterministic branch, both orders remain
   enabled and yield equal sets of destination states (relational diamonds).
4. Every full-graph outcome of the selected action appears in the online export.
5. Every selected successor is not already closed, including the current state,
   according to the actual order of online expansions.

The reference's `Graph.certify` checks the first three conditions over the full
action-avoiding closure, not just the immediate pair of currently enabled
handlers. Multiple distinct actions of a selected actor are explicitly rejected
as unsupported by this auditor rather than assumed independent.

For every full fallback, all enabled full-graph actions and all of their outcomes
must appear online. Rejected proviso trials must have a real closed-successor
witness reachable through the named actor. Accepted trials cannot then claim a
full fallback. All exported states must have exactly one completed expansion.
Existing attempted transitions from rejected trials may remain in the export;
they are checked as real full-graph edges too, not treated as missing choices.

## Measured result

| Check | Result |
|---|---:|
| Online states checked | 27 |
| Accepted reductions certified | 25 / 25 |
| Complete full expansions | 2 / 2 |
| Closed-successor rejections verified | 4 / 4 |
| Distinct exported action/target edges validated | 30 / 30 |

Both AST and JSON paths pass all rows above. The report's transition counter remains 32. That counter includes attempted work
and is not the deduplicated exported edge relation counted here. Baseline stays
101/202, static priorities 22/26, and the old global-check control 38/46.

`test_online_por_audit.py` has eight tests, including deliberately broken
commutation, a hidden nondeterministic successor, an accepted self-loop, a false
closed-successor witness, incomplete full fallback, a fabricated edge and a
truncated trace. These fail even when observations contain no property failure.

## Run

After `bash tests/diagnose_hub_alternatives.sh`, the additional audit runs
automatically. For existing fresh exported graphs:

```bash
python3 tests/test_online_por_audit.py
python3 tests/audit_online_por.py
```

Evidence for each accepted action and rejected proviso is stored in
`tmp/LoadBalancerSmall_online_certificate.json` and its `_json.json` counterpart, with SHA256 hashes of the model,
full graph, online graph and trace. No code in the state-space generator, safety
matrix, cycle proviso, error handling or deadlock stopping is changed.

The checked observations here are those of the default reachability run. The
model's comment about balance is not a formal balance assertion. This audit
does not establish preservation of arbitrary LTL, timing, symmetry, other models
or future COND-guard rules. Those require separate arguments and validation.
