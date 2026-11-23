# Static scheduling and an observable intermediate state

## Reproduced false negative

The two rejected sufficient certificates were investigated in ARIA's actual pipeline. `Step1RebecDependencyGraph` builds actor groups only from SDI. `SDIAnalyzer` compares common destinations and SVI at their handlers; it correctly groups worker1 and worker2 because both send Cell.store, which writes Cell.value. Parameterized stores are therefore not simply ignored. Cell.keepAlive neither reads nor writes value, so it gives no SVI edge between a Worker and Cell. `Step2HierarchicalRebecGraph` lifts send edges; `Step3RebecPriorities` orders the worker group before Cell. `Step4MessageServerPriorities` orders store before keepAlive. The resulting schedule runs both workers before a Cell store. These are static scheduling rules, not a runtime persistent-set certificate for WRITEVALUE versus STORE.

The legacy ARIA CLI has no external-property input and no visibility analysis for it. Thus an observer involving both a worker's progress and Cell's value is not protected by this priority assignment. The issue demonstrated here is lack of external-property preservation, not a proved omission of store parameter conflicts from SDI.

`fixtures/CellRegisterObserved.rebeca` is the reviewed healthy CellRegisterBounds plus a boolean `sent` in each Worker, initialized false and set true immediately after the existing send. It changes no messages, original field values, branch decisions or queues; the added flag is an observer of completion. No keepAlive or deadlock behavior is modified.

`fixtures/CellRegisterObserved.property` supplies an external state assertion:

```text
property {
    Assertion {
        NoEarlyStore: !(cell.value == 1 && !worker2.sent);
    }
}
```

This deliberately false invariant asks whether value 1 can be stored before worker2 sends. Full exploration finds the execution starter.STARTWORKERS, worker1.WRITEVALUE, cell.STORE, with worker2.sent still false. Legacy static forces worker2 to send before Cell runs and misses that violation. The original bound assertion still holds and is not removed.

| Native path | Result | States | Reported steps |
|---|---|---:|---:|
| Full, external property | assertion failed: NoEarlyStore | 5 | 7 |
| Legacy static export, external property | satisfied | 9 | 12 |
| Dynamic, external property | assertion failed: NoEarlyStore | 5 | 7 |
| Same-generated PO-off, external property | assertion failed: NoEarlyStore | 5 | 7 |
| Property-aware conservative static export | assertion failed: NoEarlyStore | 5 | 7 |

These Linux counts are first-error prefixes except the satisfied legacy static run. They are not timing/performance results. The metadata name in RMC's reachability report remains its generic deadlock/deadline name; the assertion message explicitly identifies NoEarlyStore. The driver verifies that message and a nonempty counterexample for all four detecting paths.

## Conservative correction and its boundary

The ARIA file command now accepts:

```bash
java -jar target/erdg-tool-0.1.0.jar file MODEL.rebeca --property MODEL.property
```

With an external property, `ExternalPropertyPriorityPolicy` assigns **all actor priorities and all method priorities 1** in the annotated export. This retains scheduling choices until there is an actual property-preservation proof. The property is not parsed or proved by ARIA; file existence is checked, and RMC must still receive and compile/check it with `-p MODEL.property`. Disabling static scheduling reduction is not disabling the property or ignoring errors. Output uses the existing model-name directory, so it replaces any previous annotation for that name; the regression copies each variant before the next export.

This is an explicit property-aware route. Old annotated files and legacy calls without `--property` remain unchanged and **must not be treated as safe for arbitrary external properties**. Supplying a property only to RMC does not retroactively make a legacy ARIA annotation property-aware. `run`/`run-all` remain legacy commands; use `file ... --property ...` for this route. The external dependency JSON is still structural analysis, not an external-property certificate. This change does not establish global correctness of every dynamic mode either.

The original no-property CellRegisterBounds annotation was compared byte-for-byte against its pre-change export and is unchanged. There is no attempt to force the static/dynamic counts to match, and no production RMC, proviso, cycle, assertion or deadlock code is changed. The separate LoadBalancer static22 experiment is not rerun or re-certified by this step.

## Checks and reproduction

From Rebeca-Model-Checker-with-Reduction:

```bash
bash tests/check_cell_external_property.sh
```

The wrapper builds both Java projects, runs a Java policy check, then regenerates and compiles all five native variants. The driver deliberately expects legacy static to reproduce its false negative, and requires NoEarlyStore to fail in the other four. It verifies bodies are preserved and generated actor/method priorities are all 1 for the conservative variant. Missing property files, unknown file options and truncated options must fail, rather than silently selecting legacy mode.

The Java check covers actor and method normalization, unchanged input maps and preserved keys/id. Locally all 35 ARIA Java sources including the existing generated grammar were compiled with Java 17 against the existing shaded dependencies, then the executable artifact was updated and all five native tests passed. A Maven build was attempted but the offline cache lacked antlr4-maven-plugin 4.13.1; this is not reported as a successful Maven build. The wrapper provides the normal complete Maven build for an environment with those dependencies.

Raw observations and executable/source hashes are in `results/cell_external_property_linux_20261123.json`; five native reports including counterexamples are in the sibling `cell_external_property_linux_20261123/` directory. Scope is this exact regression. No arbitrary-property preservation theorem is claimed.


A subsequent offline property-aware representative experiment is documented in `PROPERTY_REPRESENTATIVE_EXPERIMENT.md`. It retains the NoEarlyStore violation and reduces three healthy reference edges without reducing states. It does not change the conservative production policy described here.
