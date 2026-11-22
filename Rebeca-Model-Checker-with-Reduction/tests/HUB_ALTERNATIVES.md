# Hub choices after the quiescence fix

This investigation uses the current online 27-state solver, not the historical
38-state solver. It adds per-executed-alternative diagnostics, a controlled replay
runner and a finite-graph audit. No scheduling, dependence, proviso or deadlock
rule is changed.

## Finding: the proposed same-Hub choice is absent from the current run

The current dynamic export contains **zero states with both distinct Hub handlers
available**. Its only multi-message Hub queue has two identical ReceivePrimary
messages (state 27_0 in this run). The existing exact-equivalence predicate skips
the duplicate queue alternative; it does not eliminate a different handler.
Consequently adding priorities to the two Hub handlers changes nothing: 27/32
remains 27/32. The previous suggestion that this choice might explain the
remaining 27-versus-22 gap does not apply to the current schedule.

| Controlled generated-C++ experiment | States | Report transitions | Outcome |
|---|---:|---:|---|
| Current dynamic AST | 27 | 32 | satisfied |
| Static actor and method priorities | 22 | 26 | satisfied |
| Dynamic with only static actor order as candidate preference | 42 | 50 | satisfied |
| Static actor priorities only | 37 | 47 | satisfied |
| Static message priorities only | 101 | 199 | satisfied |
| Current dynamic with Hub message priorities | 27 | 32 | satisfied |

Changing candidate preference is not equivalent to enforcing actor eligibility
by priority. In particular, dependencies and BFS proviso can cause later
candidates or full fallback. These controls measure interactions; the state-count
differences must not be interpreted as additive contributions.

## First concrete difference

The state contents agree after Bootstrapper.Initialize then PrimarySrc.Dispatch.
At that configuration the dynamic solver selects PrimaryRelay.Forward, whereas
static priorities select SecondarySrc.Dispatch (priority 2 beats relay priority 3).
Both exports happen to call this state 3_0, but the audit matches complete state
contents rather than assuming IDs from separate runs correspond.

The dynamic/static state sets share only 9 signatures: 18 dynamic-only and 13
static-only. Thus 27 minus 22 is not a set of five redundant states. Signatures
retain variables, times, ordered messages, parameters, arrival/deadline metadata
and atomic propositions. Sender alone is projected away because the exact
hash-checked benchmark contains no sender expression. This is not a comparison
procedure for sender-sensitive models.

## What the complete unprioritized graph says

The full sender-normalized control has 64 states. It has three distinct-Hub
choice states (12_0, 34_0, 54_0 locally), absent from the current dynamic export.
For each, both handlers pass the existing reference's relational diamond and
persistence checks on all four action-avoiding continuation states. This is a
finite-model result requiring the full graph, not an online certificate. It
cannot justify a new general feedback-send rule, nor does it optimize a choice
that the current online traversal never encounters.

The current online trace still rejects Hub trials at states 19, 25, 26 and 27
because successors are closed. Later candidates succeed at the first three;
state 27 expands fully. Initial state 1 also expands fully. We retain those
checks. Removing proviso or enforcing priorities solely to reach 22 is not
supported by this investigation.

## Reproduce

```bash
bash tests/diagnose_hub_alternatives.sh
```

The default command rebuilds and generates the normal four variants, regenerates
the full reference, executes the six isolated policy controls, and writes:

- `tmp/LoadBalancerSmall_hub_audit.json` (state matches, both-order evidence,
  action-avoiding paths, policy divergence and actual online trace events).
- `tmp/LoadBalancerSmall_hub_audit.md` (readable summary).
- `tmp/LoadBalancerSmall_post_quiescence_scheduling/` (source copies, graph exports,
  logs and reports for each control).

`--reuse-generated` skips Java generation only when current generated sources
already exist; the runner requires the new alternative trace events. None of the
copied experimental priority changes are installed into the generator.
`POR_ALTERNATIVE` records phase (trial/full), actor, selected message, alternative
index and handler name after changeOrder, before execution. Original exceptions
still stop execution immediately. Builds with and without diagnostics retain
27/32. The signature unit tests protect queue order, variables, time and
run-local-ID handling.

The useful next algorithmic question is how to choose a good persistent actor set
under the existing cycle condition, and validate it on more than one model.
The evidence here does not support installing a new same-Hub reduction rule.
