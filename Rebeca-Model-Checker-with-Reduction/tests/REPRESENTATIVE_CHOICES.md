# LoadBalancer representative choice comparison

This is an offline audit of the exact reviewed LoadBalancer model. It changes no
online generator rule. Run `bash tests/compare_cycle_barriers.sh`, then
`bash tests/compare_representatives.sh`. The second command regenerates the static
control with the current RMC JAR and compares complete exported state contents,
including queues, variables and time. Run-local IDs are not used to match states.
Only unused sender fields are projected, for the source hash reviewed by the audit.

The first common-prefix divergence is after `Bootstrapper.Initialize` followed by
`PrimarySrc.Dispatch`. Both `PrimaryRelay.Forward` and `SecondarySrc.Dispatch` are
enabled. Dynamic selects the former; static selects the latter. Dynamic diagnostics
show `global_dependency_check` accepted the relay trial. The later source action
was not tried: this is first-acceptable representative selection, not a rejection
of the source action by the cycle proviso.

The static source action passes the full-graph persistent/relational-diamond check
across all three states reachable while avoiding it. Both entire exported graphs
also pass the finite action-outcome and strong cycle checks. Dynamic has 27 states,
static 22; nine states are shared, 18 dynamic-only and 13 static-only. Thus the
static graph is not simply the dynamic graph with five surplus states removed.

Safe online adoption requires more than reversing this one choice: each preferred
candidate must satisfy the runtime independence/persistence certificate, retain
all parameter and nondeterministic outcomes, meet observation restrictions and
pass the actual traversal's cycle proviso. Failed candidates must retain the
normal fallback and first-error handling. Offline full-graph evidence is not a
runtime certificate or a general proof. Choosing priorities alone does not supply
these conditions. No claim is made that a different order must produce 22 states.

The JSON report includes the shared prefix, both choices, full enabled set,
static action evidence, dynamic decision lines and complete finite graph audits.
