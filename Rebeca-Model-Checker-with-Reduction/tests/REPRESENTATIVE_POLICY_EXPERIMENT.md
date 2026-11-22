# Preference-only native experiment

Run `bash tests/compare_cycle_barriers.sh` first (builds the current generator,
exports both full references and error fixtures), then:

```bash
python3 tests/test_online_por_audit.py
python3 tests/experiment_representative_policy.py
```

The experiment copies generated AST-path C++ into `tmp/RepresentativePolicy`.
Its only native source mutation is the `_por_order` permutation. The production
generator, actor and method priorities, candidate certificates, trial loop,
parameter alternatives, cycle proviso and first-error handling are unchanged.
`static_actor_preference` is deliberately a benchmark-specific control, not an
inferred general ranking rule. It uses [3,4,1,2,0,5] instead of [0,1,2,3,4,5].
`reverse` uses [5,4,3,2,1,0]. Every candidate still passes the existing runtime
checks. All exported outcomes and the selected preserving core are independently
audited against the full reference, including the strong cycle condition.

Linux measurements (states / reported transitions; not portable count gates):

| Model | Original | Static actor preference | Reverse |
|---|---:|---:|---:|
| LoadBalancerSmall | 27 / 31 | 40 / 45 | 40 / 45 |
| QuiescenceResend | 201 / 328 | 216 / 337 | 232 / 373 |

All six graphs pass the finite semantic and selected-core cycle checks. The
macOS original Resend count previously measured 189 / 303; each local experiment
must pass its own graph audit regardless of its measured size.

The preferred ordering really does select `SecondarySrc.Dispatch` at the first
common-prefix divergence, and its runtime trial is accepted. Nevertheless later
choices give a larger graph. Static actor iteration preference does not reproduce
static scheduling's eligibility filtering or method-priority queue behavior.
Therefore this experiment supplies no basis to promote this preference as an
optimization, and does not close the 27-versus-22 gap. Keep the production order.

A newly reached exhaustive Hub actor union exposed a limitation of the offline
auditor. It now permits multiple handlers only when the declared selection is
exactly the entire enabled action set and every outcome of every handler is
present. This is a full expansion, not an independence assumption. Non-exhaustive
multi-handler selections remain unsupported and fail closed. An adversarial test
removes one handler's branch and verifies rejection.

Error controls reverse the preference and require the real deadlock/assertion
outcome with a nonempty counterexample trace. Reversing the pending-assertion
fixture can expose the error before its loop closes; loop-rejection coverage is
reported separately instead of requiring that traversal to first visit a cycle.
The original-order cycle helper and pending-loop controls remain in
`compare_cycle_barriers.sh`. No errors are caught and continued by the model
checker. Summary: `tmp/RepresentativePolicy/summary.json`.

Observed reverse-order error controls: pending assertion stopped at 2 states / 2
transitions with 3 trace states; terminating model stopped at deadlock after
20 / 21 with 14 trace states; assertion model stopped at 6 / 6 with 7 trace
states. These first-error exploration sizes are also traversal-dependent.
