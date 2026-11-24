Current extension: [fixed literal payloads may be consumed by handlers](FIXED_PARAMETER_COMMUNICATION.md), with parameterized scalar-function equality kept conservative.

# Nullary communicating models: optional property-aware POR

This extends `--aria --aria-property-filter -p MODEL.property`, not ordinary
`--aria`. No runtime conditional-dependency guard is enabled. The generated
code without the optional flag remains byte-identical to the previous artifact.

Current extension: literal primitive message payloads are also admitted when
all handler parameters are unread. See [the exact restrictions and tests](UNREAD_MESSAGE_PARAMETERS.md).
The nullary restrictions below describe the initial certificate.

## Admission certificate

The typed compiler AST must expose all relevant primitive state reads/writes,
static receiver bindings and a supported external state assertion. Runtime
handlers must be nullary. Timing, sender observation, priorities, nondeterminism,
message parameters, opaque expressions and conditional runtime sends are refused.
Reserved native clock/sender names cannot be shadowed. This is a sufficient,
restricted certificate, not support for the whole Rebeca language.

Count constructor messages with multiplicity. A runtime handler sending more
than one message is accepted only if no runtime handler can send to it. Its
execution count is then bounded by constructor seeds. The stable global bound is
`B = constructor messages + sum(seed(handler) * (outdegree(handler)-1))`
for such one-shot fanouts. The native handler enqueues before its message is
removed, so every queue must have capacity strictly greater than `B+1`.
LoadBalancer has B=2; the three-token variant has B=3. No overflow is ignored.
Unsupported models retain full candidate choices in this optional mode, apart
from independently certified actor-local or separately reviewed legacy cases.

For admitted zero-time nullary messages, queue effects are additions/removals
on multisets, with multiplicity preserved and sender unobserved. The capacity
bound prevents those operations from introducing queue errors. Primitive
read/write conflicts remain. Two different methods of the same actor may also
commute when their complete scalar programs are syntactically identical after
removing fixed sends. This relaxation excludes every source-assertion method;
it does not assume assertions or erase their checks. Different scalar programs
with overlapping read/write sets remain dependent.

## Native selection and proviso

A candidate retains **all current alternatives of one actor**, including mixed
Hub methods. It does not split dependent messages into arbitrary representatives.
The native C1 test starts from pending messages outside the chosen label set and
follows statically known sends, stopping at chosen labels. Any scalar conflict
reachable without executing that set rejects the candidate. Property visibility
is checked for every chosen alternative. Partial successor acceptance still
requires a fresh state in this optional path; full candidates are exempt. Normal
error handling and first-error stopping remain in force.

## Observed native results

Both sides use the same generated source: only the control's POR macro is removed.
These matched controls are not the separate 101-state baseline generator.
The external `Balanced` assertion here checks load ranges 1..3, not equality,
fairness or liveness. The trivial assertion observes no fields.

| Model/property | Control states/steps | Filtered states/steps | Result |
|---|---:|---:|---|
| LoadBalancer/range bounds |64/128|42/55|satisfied|
| LoadBalancer/true |64/128|27/31|satisfied|
| Renamed LoadBalancer/bounds |64/128|42/55|satisfied|
| Hub identical shared-field updates/true |64/128|27/31|satisfied|
| Hub different read/write updates/true |109/218|48/63|satisfied|
| Three-token mixed Hub alternatives |391/1172|242/454|satisfied|
| Global property violation |8/9|5/5|assertion failed|
| Source assertion |16/23|8/8|assertion failed|
| Terminating feedback |23/38|14/15|deadlock|
| Conditional-send refusal |30/50|30/46|deadlock|
| Insufficient-margin refusal |64/128|64/110|satisfied|
| Repeatable-fanout refusal |14/55|14/19|queue overflow|

Steps are solver counters, not unique graph edges. Rejected trials can contribute
exported edges and counters even when final choices are full. Count differences
in refused cases therefore do not imply permission for a partial candidate.
The 22-state static-priority run remains a separate scheduling experiment; it
is not a target enforced by this implementation.

Every completed healthy graph is independently checked against the full control:
initial-state correspondence, C0, retained outcomes, set-level persistence and
diamonds along avoidance paths, property observations and strong cycle coverage.
All exported trial edges are checked for validity separately. Cycle checks use
final accepted actor decisions, not rejected-trial edges. Nine mixed Hub union
choices are exercised by the three-token case. The different read/write case
exercises actual dependency rejection. These are finite-model checks, not a
language-wide soundness proof. Error cases must stop with a nonempty trace.

## Reproduction

Run `bash tests/check_communicating_properties.sh` with Java 17 and the project's
compiler dependency available. It builds RMC, runs 11 typed-AST admission/refusal
checks, and runs both native modes for all 12 models. A C++11 compiler is needed.
See `results/communicating_properties_linux_20261123.json` and
`results/nullary_queue_certificate_checks_linux_20261123.json` for saved evidence.
Final generation equivalence records which tested C++ programs match the final
JAR; per-run hashes are preserved. Diagnostic/export-enabled short runs are not
performance benchmarks and justify no speed or memory claim.
