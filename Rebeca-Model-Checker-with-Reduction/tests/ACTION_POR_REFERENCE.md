# Action-level selection: finite-graph reference implementation

This is a design/validation reference, NOT an online optimization of RMC. It
requires the complete reference graph first. The normal Java generator and C++
solver are unchanged: they still produce 38/46 on LoadBalancerSmall and stop
immediately on a deadlock or assertion. A 27-state reference output must NOT be
reported as the online generator's result, speedup, or proof for all Rebeca models.

## Selection rule

Actions are (owner instance, message-server name), including different message
servers of the SAME actor. A candidate singleton contains all transitions of
that action class, including different message occurrences/nondeterministic
outcomes. For each candidate at s, traverse EVERY state reachable in the full
graph along paths that avoid that candidate action. In every visited state v:

1. The candidate must still be enabled (persistence).
2. Every candidate successor must preserve the exported property observations.
3. For every other enabled action b, every outcome of either action must leave
   the other enabled. Unknown or missing edges reject the candidate.
4. The complete sets of destinations from a;b and b;a must be equal (a relational
   diamond). All nondeterministic outcomes are included; comparing one outcome
   is insufficient.

These checks inspect the actual finite-state behavior, including queue and data
updates. A local read/write check or a diamond in s alone is not accepted as a
certificate: future paths avoiding a are also checked. If certification fails,
try another candidate; if none passes, expand all enabled actions.

Before accepting any candidate, apply the conservative BFS proviso: ALL its
successors must be new or currently Open. A current/self or Closed successor
rejects it. The implementation does not relax this condition to hit a target
count. All alternatives of an accepted action class remain; it does not assign
static message priorities or declare all same-instance pairs independent.

This reference is restricted to finite, zero-execution-time, zero-shift FTTS
exports and reachability observations. It rejects a first-error/incomplete run,
POR/symmetry input, unequal actor/message priorities, missing generated metadata,
missing targets or state-count mismatches. It is not a generic timed/LTL proof
checker. Its JSON is tied to the exact full-graph SHA-256 and is not imported by
RMC; state IDs must not be transferred to a different run.

## Measured experiment

Using the uploaded generated code, the unreduced control with sender normalization
retained has 64 states. PO was disabled only in a copied generated configuration;
plain unnormalized baseline remains 101 states. The full reference graph was
exported with normal deadlock/assertion stopping.

The reference algorithm gives:

- 64 full states -> 27 visited reference states.
- 26 singleton expansions, one full expansion.
- Six candidate rejections by the cycle proviso.
- At reference state 12_0 it selects Hub.ReceiveSecondary while both distinct Hub
  message servers are enabled; the persistence/diamond checks certify the choice.
- 27 distinct selected graph edges. This is NOT the same counter as RMC's reported
  46 transitions (which includes attempts/fallback and an initial counter offset).

This experiment demonstrates a certified action-level choice on this finite
reference and provides an oracle for future online implementations. It does not
remove the up-front cost of the 64-state graph. Runtime conditional-guard
resolution is still not implemented. The 22-state static-priority schedule is
still a different policy and cannot be assumed equivalent solely from its count.

## Tests and reproduction

```bash
python3 tests/test_action_por_reference.py
bash tests/run_action_por_reference.sh
```

The shell script expects previously generated `tmp/LoadBalancerSmall_aria_json/`
from `compare_loadbalancer.sh`. It copies only sources/headers to a new reference
folder and disables PO there; it never edits the input output or the generator.
The ordinary native solver exports a full graph, still stopping at errors. The
Python reference refuses to process an unsatisfied native report. Results are
written to `tmp/LoadBalancerSmall_action_reference.json`.

Seven unit tests cover distinct same-actor messages, future interference that a
local diamond misses, enabling/disabling, all nondeterministic branches, property
visibility, cycle starvation of an error observation, and rejection of reduced
or incomplete inputs. Error-preservation cases here are synthetic transition
graph tests, not a completed native exploration past a model error.

## Remaining online work

The reference certificate depends on the full graph. Replacing that query with
sound static/runtime sufficient conditions is still needed before promoting the
rule into the online generator. That implementation must conservatively reject
what it cannot establish and must agree with reference decisions where it claims
certification. No full-graph lookahead or unvalidated priority schedule has been
silently inserted into the production solver.
