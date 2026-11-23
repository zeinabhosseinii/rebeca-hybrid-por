# Typed-AST property and action metadata for the offline experiment

This replaces the manually supplied metadata in the default property-representative experiment. It remains diagnostic/offline: no production RMC, native proviso, assertion/deadlock behavior or ARIA static export code is changed. The conservative production `--property` policy remains the baseline.

## Extraction

`PropertyEffectAstAudit.java` compiles the model using the real Rebeca compiler and compiles the property with its real PropertyCompiler in one Spring context. It walks typed AST nodes rather than searching source text or serializing compiler object graphs. Compiler objects have cyclic links; the exporter instead emits a small explicit JSON predicate IR.

A model index maps every main instance to its reactive class and resolves knownrebec bindings positionally against the typed main declaration. Reads/writes are qualified as `[instance, Class.field]`; messages as `[target-instance, HANDLER]`. The same Worker class therefore gives distinct worker1 and worker2 effects. Formal parameter reads are pure inputs, not state reads; sending `cell.store(id)` records the state read Worker.id and the resolved send to cell.STORE. It does not infer that sending is independent: the finite full-graph persistence/diamond check is still required.

Assignments record local scalar writes using compiler state-variable labels. Conditional guards and both branches are traversed, so conditional writes are overapproximated. Direct sends record their target handler and scan every argument; explicit after/deadline expressions are refused. Source assertions are traversed for reads and purity; their truth is not proved by this extractor. Constructors are checked within the same shape fragment but are not emitted as runtime actions. Main constructor actuals must be literal primitives. The complete reference export must still finish satisfied with source assertions enabled.

Property field references are resolved through the main-instance/class index. The exporter emits a read footprint and a typed tree of field references, decimal primitive literals, boolean negation, comparisons, conjunctions and disjunctions. It accepts exactly one external state assertion with no aliases/definitions or temporal formulas. The separate Python consumer evaluates this IR on full exported states; there is no hardcoded NoEarlyStore/StoredBounds predicate in that consumer.

## Supported fragment and refusal

The restricted diagnostic supports primitive scalar int/short/byte/boolean fields, simple assignments, scalar pure expressions, conditionals, static knownrebec/self sends, primitive formal parameters and untimed source assertions. No inheritance, interfaces, synchronous methods, model annotations, global/environment/feature/record data, field initializers, arrays, dynamic receivers, loops, increments, local declarations, timed sends, property arithmetic, aliases or temporal operators are accepted. Expression and statement traversal have explicit depth/node limits. It is deliberately narrower than the compiler language.

Any rejected class/model/constructor/property shape makes metadata unsupported. A rejected handler has no published complete footprint and makes the whole experiment's metadata unsupported. The consumer then sets reduction_enabled false and returns **unsupported_not_checked**, without treating the property as true. A normal full checker must verify such a property; this diagnostic does not pretend to have evaluated an unsupported predicate. Compilation errors, incomplete exports, missing action metadata, source/provenance mismatches or ambiguous action identities prevent a successful experiment.

Metadata completeness is only an effect/observation-shape result, not a proof of independence, assertion truth, bounded arithmetic or property preservation. Action candidates still undergo the existing exhaustive finite dependency/observation check and conservative BFS proviso. The graph loader rejects PO/symmetry, unequal priorities, nonzero transition times and incomplete native runs.

## Results

A fresh native full reference export was generated, then the experiment extracted metadata separately for the two property files:

| Property | Full reference | AST-driven representatives |
|---|---|---|
| NoEarlyStore | assertion failed, 5 states / 7 graph edges | assertion failed, 5 states / 6 graph edges |
| StoredBounds | satisfied, 11 states / 24 graph edges | satisfied, 11 states / 21 graph edges |

NoEarlyStore's footprint is cell.Cell.value and worker2.Worker.sent. StoredBounds observes only cell.Cell.value. The effects and observations reproduce the earlier reference choices and counts without using the manual writes table or manual predicate function. The driver passes AST-derived write sets explicitly to the shared search routine; the historical module's default table is not used.

The false property still stops at the first violation. The healthy reduced graph passes the strong sufficient cycle condition. First-error prefixes report that complete-cycle result as null. There is no state reduction here, no online integration and no runtime performance claim.

Thirteen real compiler-AST cases passed: baseline, renamed observed field, changed observed instance, extra conditional write, timed send, array field, loop, increment, local declaration, property arithmetic, property alias, multiple assertions and main-argument nondeterminism. The four positive cases verify actual changed footprints, resolved sends and per-instance ownership. The nine refusals verify both extractor rejection and consumer reduction disabling. An opaque predicate IR is also refused. The existing seven search/proviso/first-error/deadlock unit tests pass.

The new driver and mutation tools were compiled with Java 17 against the current executable RMC dependencies. No production Java rebuild is needed for test-only classes. Native control results from the preceding experiment remain separate; this step regenerates the healthy native full graph but does not claim new native executions of the offline reduction policy.

## Reproduce

From Rebeca-Model-Checker-with-Reduction:

```bash
bash tests/run_property_representative_experiment.sh
```

The wrapper now selects the AST-driven path by default. It builds RMC normally, exports a fresh native full graph, compiles the diagnostic Java classes, extracts both property metadata files, runs full/reduced reference searches, executes thirteen compiler-AST cases, and runs the seven search unit tests. The output contains summary.json and the exact extracted metadata, IR, compile logs and native reference artifacts.

Raw results: `results/cell_ast_property_representatives_linux_20261123.json` and `results/cell_ast_metadata_checks_linux_20261123.json`. The former includes complete metadata, source/property/extractor/graph hashes, all candidate decisions and counterexample paths. Scope remains the finite example; generic online authorization requires a separate supported-property contract and runtime integration review.


The subsequent opt-in native connection is documented in `ONLINE_PROPERTY_FILTER_EXPERIMENT.md`. It filters copies of generated C++ and preserves the production conservative baseline; it does not install the diagnostic extractor into production generation.
