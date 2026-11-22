# Historical investigation: 38 dynamic states versus 22 static-priority states

For the current **27-state** solver, see [HUB_ALTERNATIVES.md](HUB_ALTERNATIVES.md).
The distinct-Hub choice described below is absent from the current dynamic run.

All measurements below replay the uploaded generated C++ with C++11/O2.
They do not depend on substituting a different Rebeca compiler. The original
model checker still throws at the first deadlock; no terminal-skipping mode is
used. All runs below report satisfied for the default reachability check.

## Controlled policy experiments

| Experiment | States | Transitions | Changed factor |
| --- | ---: | ---: | --- |
| Original dynamic AST (corrected JSON agrees) | 38 | 52 | None |
| Original ARIA static-priority model | 22 | 26 | None |
| Dynamic with static actor-priority order as candidate preference only | 42 | 59 | Candidate order, no eligibility restriction |
| Static actor priorities only | 37 | 47 | Hub message priorities made equal |
| Static message priorities only | 101 | 199 | All actor priorities made equal |
| Dynamic with Hub message priorities 1 and 2 | 21 | 25 | Message priorities only; dependency/proviso unchanged |

Additional controls: static with sender normalization still has 22/26. Allowing
same-method queue alternatives in the dynamic trial gives 38/54, so merely
removing the blanket single-alternative restriction for identical method IDs
does not solve the state-count gap. These controls are experiments, not changes
to the production generator.

The effects interact: these counts are not an additive decomposition. It would
be incorrect to conclude that actor priorities are worth exactly one state or
that 21 states proves a new sound general-purpose reduction.

## A concrete branch

Dynamic exported state 6_0 has both Hub.ReceiveSecondary and Hub.ReceivePrimary
available. Dynamic expansion emits successors through BOTH choices (to 7_0 and
8_0). Static expansion at its state 6_0 chooses ReceiveSecondary: priority 1
wins over ReceivePrimary's priority 2. The dynamic successor through the other
choice leads, for example, to state 8_0 with a pending ReceiveSecondary at Hub
and a Dispatch at SecondarySrc. This is a real additional representative path.
Actor-priority scheduling already differs earlier: at state 3_0 dynamic chooses
PrimaryRelay whereas static chooses SecondarySrc. State numbers are local to
each run and do not generally identify equivalent states.

The dynamic algorithm reduces among ACTORS but leaves competing same-time
messages of the chosen actor to getNumberOfAlternatives/changeOrder. ARIA's
static policy also imposes priorities WITHIN an actor. Treating (instance,
message server) as an action key does not, by itself, implement reduction among
these same-actor message alternatives. The same-instance dependency retained in
the JSON is a conservative choice; it must not just be flipped to independent.

getNumberOfAlternatives enumerates equal-arrival, equal-priority queue entries.
Therefore unequal Hub message priorities eliminate a scheduler choice, explaining
why the static policy can explore fewer representatives. Copying priorities into
the dynamic run is a useful control, not a proof that the choice is sound for
arbitrary models, properties, timing or queue semantics.

## Proviso and other conservative fallbacks

The dynamic trace contains 38 state expansions:

- 26 accept a singleton trial.
- 12 fully expand: the initial Bootstrapper state, 10 states with multiple queue
  alternatives, and one state after a closed-successor proviso failure.
- There are 28 total singleton trials: two proviso rejections. At state 37, a
  later candidate succeeds after an earlier trial fails, so that state is not
  one of the 12 full expansions.

At state 36, PrimaryRelay's successor is closed state 6; at state 37, its successor
is closed state 7. The proviso rejection condition remains intact in all candidate-order or
message-priority controls; the policy can encounter different states after a
schedule change, but the rejection condition itself is never disabled.

The global dependency check also conservatively blocks Hub against
Bootstrapper.Initialize even after Bootstrapper's queue has drained. Improving
that requires an enabling/future-reachability argument, not simply checking
whether the conflicting actor is empty now.

## State-set comparison

With state variables, time and ordered message queues compared, but sender names
ignored because no handler in this model reads sender, the exports have:
21 shared state signatures, 17 dynamic-only and one static-only signature.
Thus "16 extra states" is an arithmetic difference, not a literal subset of
sixteen extra states. This comparison does not establish trace equivalence.
Exported transition counts are also distinct from the report's transition
counter; the original exports contain 51 and 25 edges respectively, while the
reports count 52 and 26. Use report counters consistently for the tables above.

## Reproduce

After generating the four normal variants, run:

```bash
python3 tests/compare_loadbalancer_scheduling.py
```

Or pass `--base` pointing to the extracted diagnostics ZIP directory. The script
copies only generated C++/headers into new experiment directories, checks each
patch matches exactly, compiles with state export/decision diagnostics, and writes
reports, state-space exports, logs and summary.json under
`tmp/LoadBalancerSmall_scheduling/`. It never edits the input generated files.

No production scheduling rule changed in this investigation. The next algorithmic
step is to define and validate a safe rule for choosing among same-actor message
alternatives, including queue/enabling effects and the cycle proviso. It is not
to suppress alternatives merely to reproduce a smaller number.
