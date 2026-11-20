# LoadBalancerSmall validation

The input preserves the user-provided model: source/relay counters wrap after 2,
hub load counters wrap after 3. The original larger LoadBalancer is retained.

The standalone ARIA run with JDK 17 completed successfully:

- 7 actions; 28 unordered action pairs including diagonal.
- 18 INDEPENDENT, 10 ALWAYS, 0 COND.
- Priority-annotated model and source-hashed JSON generated successfully.

These are static-analysis results, not measured state-space sizes. This model
cannot exercise runtime conditional-dependency pruning because no pair is COND.
The balance sentence in the source is a comment, not a checked assertion/LTL
property. The default dynamic check covers deadlock/deadline reachability.

RMC generation could not be run on the clean validation host: the dependency
`org.rebecalang:compiler:LATEST` is not in its Maven cache or bundled repository.
Use the same compiler artifact as the user's successful desktop build to avoid
silently changing compiler semantics. The user reports 101 baseline states;
that number is not yet reproduced on this host.

Run `bash tests/compare_loadbalancer.sh` on the desktop with that dependency.
It prints baseline, static priorities, ARIA AST, ARIA JSON results separately.
It runs no terminal-skipping mode: every deadlock still throws and stops.
Equal property outcomes are a regression check, not proof of POR correctness.
Transition totals may include attempted transitions during POR fallback.
