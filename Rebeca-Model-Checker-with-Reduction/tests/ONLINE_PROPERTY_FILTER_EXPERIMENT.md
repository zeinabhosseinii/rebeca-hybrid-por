# Experimental online property filter in generated native code

Update: the subsequent optional production generator path is documented in `PROPERTY_FILTER_INTEGRATION.md`. The results below describe their original experiment stage; defaults remain unchanged.

This is the first native online use of the typed-AST metadata, implemented as an opt-in generated-C++ experiment. Production Java and Velocity templates are unchanged. The conservative ARIA external-property export remains the production baseline. This is not generic property-aware POR integration.

## What is connected

`experiment_online_property_filter.py` compiles the diagnostic typed-AST extractor, generates ordinary unannotated `--aria` C++ with the actual external property supplied through `-p`, and copies that generated program into experimental variants. A strict single insertion point adds a candidate filter in TimedModelChecker.cpp. It changes no other generated file and verifies that fact byte-for-byte.

The gate uses actual native actor initialization order and each Actor.cpp messageNames table to map AST `[instance, handler]` effects to native actor/message IDs. All partial permissions default false. Metadata must be complete, match the exact source and property hashes, and describe the reviewed CellRegisterObserved source. Source drift, refused metadata or an unmapped action denies partial permission. Symmetry/annotated inputs are not exposed by this driver; generation uses the pinned unannotated source.

For each candidate, the existing native C1 machinery has already selected its alternatives. If the candidate is semantically exhaustive, it may proceed regardless of visibility: it omits no scheduler choice. Otherwise **every alternative** must be known and must write no property-observed field. Mixed actor unions therefore cannot hide a visible method. A refused candidate is skipped and the original candidate search/full fallback continues. No new candidate is created and no dependency check is bypassed.

The existing C1 check, successor execution, BFS proviso, full-expansion markers, state hashing, error exceptions and native assertions are unchanged. The external-property configuration continues to disable isolated/passive certificates and completed-full barriers. The experimental online run does not read a full graph. Complete graphs are used only afterwards by the separate semantic audit.

## Native results on Linux

| Property | Variant | Result | States | Reported solver transitions | Property-filter rejections |
|---|---|---|---:|---:|---:|
| NoEarlyStore | Same-generated PO-off control | assertion failed | 5 | 7 | 0 |
| NoEarlyStore | Current unmodified dynamic | assertion failed | 5 | 7 | 0 |
| NoEarlyStore | Experimental online filter | assertion failed | 5 | 7 | 1 |
| NoEarlyStore | Metadata deliberately refused | assertion failed | 5 | 7 | 4 |
| StoredBounds | Same-generated PO-off control | satisfied | 12 | 28 | 0 |
| StoredBounds | Current unmodified dynamic | satisfied | 12 | 34 | 0 |
| StoredBounds | Experimental online filter | satisfied | 12 | 30 | 2 |
| StoredBounds | Metadata deliberately refused | satisfied | 12 | 28 | 7 |

All four NoEarlyStore variants stop with the exact assertion message and a nonempty native counterexample. The healthy experiment still has 12 raw states, or 11 after the reviewed equal-time queue/sender projection. Reported transitions include rejected-trial/fallback execution; 34 versus 30 is not four fewer unique semantic graph edges and is not evidence of a speedup. Current and experimental healthy graphs have the same single partial representative (initial STARTWORKERS). The extra offline representatives are not newly authorized by the conservative native C1 machinery.

There is no state-count improvement in this example. The useful result is the tested native visibility connection and conservative refusal path, not a claimed new reduction or performance win.

## Finite graph audit

`audit_online_property_filter.py` compares each healthy native graph against its same-generated PO-off control. It retains parameter text, variable types/values and message multiplicity, projects only the reviewed unused sender and zero-time queue order, and verifies every control alias has the same projected successors. It checks initial state, C0, all retained action outcomes, the finite persistence/observed-value diamond certificate for partial choices, and the strong sufficient cycle condition. All pass.

Current and experimental variants each have 11 semantically full raw vertices and one certified partial vertex. With metadata refused, all 12 raw vertices are semantically full and the complete reachable projected state set matches control. This tests that refusal really retains behavior, rather than merely giving the expected property result. It is an exact finite example, not a theorem about arbitrary models or properties. A first-error prefix is not passed off as a complete cycle audit.

## Native deadlock control

A separate negative fixture is derived by removing the pre-existing keepAlive self-sends from CellRegisterObserved, solely to make it terminate. It is not used in the benchmark comparison and does not replace the original model. Its source hash is outside the experimental allowlist, so all partial permission is denied. With the healthy bound property still enabled, both the same-generated PO-off control and filtered native program stop with **deadlock**, 11 states / 13 reported transitions and nonempty counterexamples. No exception or deadlock reporting code is modified. This is a real native stopping test, in addition to the four native assertion failures above.

## Reproduce

From Rebeca-Model-Checker-with-Reduction:

```bash
bash tests/run_online_property_filter.sh
```

The wrapper builds RMC, runs the eight native property variants, performs the healthy graph audit, and runs the two terminating negative controls. It requires Java 17, the project compiler dependency and a C++11 compiler. Every invocation uses fresh output directories; diagnostic/export timings are not performance measurements.

Results are archived in `results/online_property_filter_linux_20261123.json`, `results/online_property_filter_graph_audit_linux_20261123.json`, and `results/online_property_filter_deadlock_linux_20261123.json`. Full generated programs, property metadata, patch permissions, native exports, logs and reports remain in the reproduction output. No change is installed into the production generator by this experiment.

Before promotion into production, broaden the native validation matrix, review metadata-to-native identity mapping and error visibility, and define the supported external-property contract. The exact-source allowlist must not simply be removed because this one finite audit passed.
