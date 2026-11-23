# Offline property-aware representative selection

The initial experiment below used reviewed manual metadata. The current reproduction wrapper now uses compiler AST-derived metadata and property IR; see `PROPERTY_AST_METADATA.md`. The original manual experiment remains available as a historical comparison, not as the current default.

This is a separate exact-model experiment. It does not change production RMC, static priorities, the conservative ARIA `--property` export, runtime COND, or native error stopping. It requires a complete full graph and is not an online performance improvement.

## Reviewed model and observations

The source is exactly `fixtures/CellRegisterObserved.rebeca`, SHA256 `e8e0a20c1af6af94fb02c59ff7ad2f9b33a84dd6b55872ee3b5cb89135a325f6`. The property file is exactly `CellRegisterObserved.property`, SHA256 `0036336cc8d2dcff564aedc3651c4e4084ed6f8eab031aae41a3b2790995947a`.

NoEarlyStore reads Cell.value and worker2.sent. The healthy control StoredBounds checks 0 <= Cell.value <= 2 and reads only Cell.value. Their predicates are explicitly implemented for these exact fixtures; this experiment is not a general property parser. Unsupported property names are refused without claiming a verification result.

Write effects are hand reviewed and pinned to the source: STORE writes Cell.value; each WRITEVALUE writes its own Worker.sent; STARTWORKERS and KEEPALIVE write no state field. Sending messages is still checked by the full relational dependency test; absence of scalar writes is not treated as independence. These tables are not production AST-derived metadata.

## Selection rule

For each state, try singleton actor/handler candidates in a deterministic order. All exported nondeterministic outcomes for that actor/handler, including distinct store arguments, remain in its target set.

1. Reject unknown effects and any candidate writing a property-observed field, even when the current truth value would be unchanged.
2. Check persistence, invisibility of the entire observed-field tuple, and relational diamonds on every full-graph path avoiding that candidate, using the existing finite Graph.certify implementation.
3. Require every candidate target to be neither the current vertex nor a closed vertex: the conservative BFS proviso. No completed-full barrier exception is added here.
4. If every candidate fails, expand all actions. A vertex is recorded fully expanded only after all selected edges have been processed.

Both full and reduced reference searches stop immediately when the first property-violating successor is found. They also stop on a reachable deadlock. No later edge is processed after that error. For a satisfied run, removing semantically fully expanded vertices must leave an acyclic graph, the strong sufficient cycle condition. For a first-error prefix this complete-cycle result is recorded null, not claimed to pass.

## Complete graph construction versus property checking

The native unprioritized generator first exports the complete reference graph **without the external NoEarlyStore property**, while retaining the source's original bound assertion. This intentional offline input-generation step enumerates legal model states and does not run a NoEarlyStore checker past an error. It is not presented as a native verification of NoEarlyStore. The separate offline searches then evaluate NoEarlyStore and stop on the first violation. Production native property checking still receives `-p` and stops normally.

The reference loader requires a satisfied complete reachability export, no PO/symmetry, uniform actor/method priorities, and zero-time transitions. Source/executable hashes, graph hashes and provenance are recorded. All property experiments share the same full reference graph and traversal order.

## Linux observations

| Property | Search | Result | Discovered states | Traversed unique graph edges |
|---|---|---|---:|---:|
| NoEarlyStore | Full reference | assertion failed | 5 | 7 |
| NoEarlyStore | Property-aware reference | assertion failed | 5 | 6 |
| StoredBounds | Full reference | satisfied | 11 | 24 |
| StoredBounds | Property-aware reference | satisfied | 11 | 21 |

The healthy reference keeps every reachable state; it skips three transitions, not three states. Its three partial choices are STARTWORKERS initially, worker2.WRITEVALUE at state 5_0, and worker1.WRITEVALUE at state 7_0. Each has the full finite dependency/observation proof and passes the BFS proviso. The strong cycle audit passes. There are eleven proviso rejections, five visible-write rejections, and four diamond rejections.

For NoEarlyStore only the initial STARTWORKERS partial choice is accepted before the error. The search records three visible-write rejections, three proviso rejections and one diamond rejection. The violation remains reachable and the reference stops on it. This result neither restores static priority reduction nor certifies arbitrary external properties.

Four existing native controls were freshly rechecked: full, dynamic, same-generated PO-off and property-aware conservative static. Each reports assertion failed with message NoEarlyStore and a nonempty counterexample (5 states, 7 reported steps). Those are native controls, **not** native runs of the offline representative policy. Legacy static's previously recorded false negative remains documented in CELL_EXTERNAL_PROPERTY.md.

Seven unit tests check visible writes, unknown effects, dependency rejection, self-cycle proviso, immediate assertion stopping, actual deadlock stopping, and unsupported properties. All pass. No runtime speed or memory benefit is claimed; reference graph construction cost dominates this tiny model and is outside an online checker.

## Reproduce

From Rebeca-Model-Checker-with-Reduction:

```bash
bash tests/run_property_representative_experiment.sh
```

The wrapper now builds RMC, creates a fresh native full export, extracts typed-AST property/effect metadata, runs both properties and both search policies, runs the metadata mutation checks, and runs the seven search tests. A successful experiment requires the NoEarlyStore violation, matching full/reduced results, and the healthy cycle certificate. It does not rerun the separate native external-property controls; use `check_cell_external_property.sh` for those.

The result is archived in `results/cell_property_representatives_linux_20261123.json`, including every candidate rejection, selected set and error trace. Complete reference graph, report and provenance are archived in `results/cell_property_reference_linux_20261123/`. Reproduction should rebuild with `--build-full`: the strict graph loader also inspects generated C++ configuration and priority sources, which are retained in the working output rather than this compact archive.

Before any online integration, replace the manually reviewed property/effect tables with typed-AST analysis, define a supported external-property fragment with fail-closed behavior, and establish its interaction with runtime C1 and proviso. The conservative property-aware production export remains the baseline.
