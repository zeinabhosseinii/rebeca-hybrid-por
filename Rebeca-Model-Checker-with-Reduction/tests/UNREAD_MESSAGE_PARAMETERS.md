# Literal payloads not observed by handlers

The optional `--aria --aria-property-filter` queue certificate now also accepts
primitive message parameters if **no handler reads any of its parameters** and
all send arguments are literal AST nodes, with one identical argument vector
for every send to a given receiver/method. Nullary messages remain accepted.
The existing zero-time, static-binding, bounded-queue and property visibility
requirements remain. Public class/diagnostic names containing `NullaryQueue`
are retained for compatibility; their admitted fragment is extended here.

This is deliberately not general parameter-sensitive POR. Reading a parameter
in an assignment, guard, source assertion or forwarded payload refuses this
certificate. Computed send arguments and multiple literal payload vectors for the same
receiver/method also refuse it. The check covers all
handlers, including currently unreachable ones. Metadata must first accept the
whole source, so opaque statements cannot evade the parameter-use traversal.

Since payloads cannot affect any scalar update, send, branch or assertion,
all invocations of a given handler have the same effects regardless of payload.
Queue messages still retain their payloads and multiplicity in the native
state and independent graph audit; no parameter values are overwritten or
merged. Literal sends add fixed queue vectors. The previous queue-capacity
bound and actor-union selection therefore remain applicable. The scalar
program equality relaxation only applies to parameter-independent programs
and still excludes source assertions. Runtime dependency checks, property
visibility and successor proviso are unchanged.

## Native differential tests

Run `bash tests/check_unread_parameters.sh` to build and run both suites.

`python3 tests/validate_unused_parameters.py --output tmp/UnreadPayloadRun`
compiles and executes both native modes for five variants of the supplied
LoadBalancer. It requires a built executable RMC JAR, Java 17 and g++.

`python3 tests/check_unused_parameter_refusals.py --output tmp/PayloadRefusals`
checks typed-AST admission and refusal for unread literals, guard use,
assertion use, forwarded parameters and computed payload expressions.

The same-generated POR-off control is used, not the separate 101-state
baseline. Positive completed graphs undergo outcome, avoidance-set diamond,
property observation and selected-edge strong-cycle audits. Error runs stop
at the first error with a counterexample. These finite checks do not establish
a theorem for arbitrary parameterized models. Source timing measurements are
diagnostic runs, not performance benchmarks.

Saved evidence is in `results/unread_message_parameters_linux_20261123.json`,
`results/unread_parameter_refusals_linux_20261123.json`, and
`results/unread_parameter_regression_equivalence_linux_20261123.json`.

A deliberately mixed 7/9 payload experiment failed the stronger label-level
diamond audit before this restriction. It is now a refusal regression: correct
property outcomes alone did not justify accepting that reduction.

| Variant | Control states | Filtered states | Outcome |
|---|---:|---:|---|
| Unread fixed payload, range property |64|42|satisfied|
| Unread fixed payload, violated property |8|5|assertion failed|
| Unread fixed payload, terminating feedback |23|14|deadlock|
| Parameter used in update, certificate refused |64|64|satisfied|
| Different literal payloads, certificate refused |82|82|satisfied|

Error-row counts describe exploration before the first error, not complete
state spaces. Separate solver step counters may include rejected trials.
