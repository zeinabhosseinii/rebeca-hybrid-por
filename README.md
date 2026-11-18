# Rebeca Hybrid POR

Static and Dynamic Partial-Order Reduction for Rebeca

This research project combines **ARIA**, the static analysis component, and **Rebeca-Model-Checker-with-Reduction**, the dynamic model-checking component, to study partial-order reduction (POR) for Rebeca actor models.

The journal work extends *Causal-Aware Partial-Order Reduction for Actor Models* by Zeinab Hosseini, Fatemeh Ghassemi, and Hossein Hojjat. The original paper develops static dependency analysis and priority assignment. The extension investigates more precise guarded dependencies and their use during state-space exploration.

## Components

| Directory | Role | Main output |
| --- | --- | --- |
| [`ARIA/`](ARIA/) | Static parsing, ERDG-based dependency analysis, priority assignment, and guard-aware analysis. | Priority-annotated Rebeca models, dependency graphs, and optional conditional-analysis JSON. |
| [`Rebeca-Model-Checker-with-Reduction/`](Rebeca-Model-Checker-with-Reduction/) | Dynamic exploration through generated C++ model checkers, with baseline, POR, ERDG-based reduction, and symmetry options. | Verification results and optional exported state spaces. |

`ARIA/Modere/` contains an additional model-checker implementation retained from the supplied project. The two top-level components above define the journal project's main organization.

## How the static and dynamic parts relate

**ARIA** analyzes a model before exploration. It combines causal relationships and Shared Variable Interference (SVI) to identify Shared Destination Interference (SDI). It constructs the Essential Rebeca Dependency Graph (ERDG), derives actor and message-server priorities, and emits `@priority` annotations.

**Rebeca-Model-Checker-with-Reduction** generates a C++ state-space explorer. With `--aria`, its Java generator builds an ERDG-based interference table, and the generated explorer consults that table against the messages currently at actor queue heads when choosing reduced exploration. Thus, dynamic selection currently uses dependency information computed statically.

**Current integration status:** both components belong to the combined journal project. The supplied source includes ARIA's conditional JSON exporter, but no corresponding importer or per-state conditional-guard resolver was found in the dynamic component. Automatic JSON-driven conditional reduction is a development objective, rather than an existing end-to-end pipeline.

## Requirements

- JDK 17 for both Maven builds; the dynamic component uses Lombok and recommends JDK 17.
- Maven; ARIA's existing instructions recommend Maven 3.8 or newer.
- A C++ compiler supporting C++11, such as `g++`, for generated model checkers.
- Graphviz for graph rendering.

The dynamic component depends on `org.rebecalang:compiler` with version `LATEST`. A clean build needs access to a repository or Maven cache providing that artifact. Its bundled `repo/` supplies additional dependencies and must be retained. Pinning the compiler version is recommended for reproducible releases.

## Run the static component

From the combined repository root:

```bash
cd ARIA
mvn clean package
java -jar target/erdg-tool-0.1.0.jar file benchmarks/case3.rebeca
```

The shaded JAR entry point is `erdg.Main`. Other supported commands include:

```bash
java -jar target/erdg-tool-0.1.0.jar list
java -jar target/erdg-tool-0.1.0.jar run BankTransfer
java -jar target/erdg-tool-0.1.0.jar run-all
```

The supplied `run.sh` hardcodes a local macOS Homebrew JDK 26 path. Use the JAR commands above for a portable invocation, or adapt that script to your installed JDK before using it. The supplied `compare.sh` also relies on the local launcher.

### Guard-aware extension

| Variable | Effect when set to `1` |
| --- | --- |
| `ARIA_DEBUG` | Print accesses and guard-analysis diagnostics. |
| `ARIA_PRUNE` | Exclude NEVER accesses and sends from effective dependency analysis. |
| `ARIA_EXPORT` | Export conditional-analysis JSON and print flipper information. |

```bash
ARIA_DEBUG=1 ARIA_PRUNE=1 ARIA_EXPORT=1 \
  java -jar target/erdg-tool-0.1.0.jar file benchmarks/case3.rebeca
```

| Classification | Meaning | Offline behavior |
| --- | --- | --- |
| `ALWAYS` | The analysis establishes that the access condition holds. | Retain the access. |
| `NEVER` | The analysis establishes that the access condition cannot hold. | Omit from effective analysis when pruning is enabled. |
| `COND` | The condition depends on state or cannot be resolved precisely. | Retain conservatively and export for future integration. |

`COND` includes uncertainty; it does not establish that both truth values occur in reachable executions. Unsupported expressions are represented conservatively.

Outputs are placed under `output/<model>/`, or `output/<model>_pruned/` when pruning is enabled:

- `<model>_annotated.rebeca`
- `ERDG.png`, `RIG.png`, and `HRG.png`
- `<model>_conditional.json` when export is enabled

The version-1 JSON includes instances, state variables, possible values, message-server accesses, resolved send targets, and **flippers**: message servers that can change variables used in conditional guards. NEVER accesses are omitted. Consumers must retain dependencies for conditions marked `evaluable: false`.

A false guard can become true later. Future conditional reduction must account for flippers reachable from pending messages and an appropriate cycle proviso before discarding dependencies.

## Run the dynamic component

From the combined repository root:

```bash
cd Rebeca-Model-Checker-with-Reduction
mvn package -P executable -DskipTests
```

The executable JAR is `target/rmc-2.14.jar`. The following example uses an unannotated bundled model and the default FTTS exploration semantics:

```bash
java -jar target/rmc-2.14.jar \
  -s src/main/java/org/rebecalang/rmc/testrebecamodels/Aria-benchmarks/BankTransfer.rebeca \
  -e TIMED_REBECA -v 2.3 -o out_aria --aria

g++ -std=c++11 -O2 out_aria/*.cpp -o out_aria/execute
./out_aria/execute
```

Choose a separate output directory for each configuration:

| Configuration | Generation flags |
| --- | --- |
| Baseline exploration | Neither `--por` nor `--aria` |
| Conventional POR | `--por` |
| ERDG-based dynamic selection | `--aria` |
| Symmetry reduction | `--symm`, optionally combined with one reduction strategy |

Select one of `--por` and `--aria` per run. The parser accepts both, but the ARIA branch takes precedence in the implementation. The POR templates inspected here implement FTTS reduction; equivalent reduction behavior under `--tts` has not been established.

To enable transition-system export during generation, add `-x statespace.xml` before `-o`. Execute the generated checker from the intended working directory for relative output paths.

Existing `@priority` annotations affect scheduling even in baseline runs. For dynamic comparisons, use identical model files and priority settings across configurations; unannotated models are the clearest starting point. The static annotation workflow and dynamic reduction workflow need separate, explicitly documented experiment configurations.

## Implementation map

| Location | Responsibility |
| --- | --- |
| `ARIA/src/main/java/erdg/Main.java` | Static analysis pipeline and environment flags. |
| `ARIA/src/main/java/erdg/ast/` | Expressions, model information, and guarded accesses. |
| `ARIA/src/main/java/erdg/erdg/` | Dependency analysis, `GuardAnalysis`, `FlipperAnalysis`, and `JsonExporter`. |
| `ARIA/benchmarks/` | Static benchmarks and journal case studies. |
| `Rebeca-Model-Checker-with-Reduction/src/main/java/org/rebecalang/rmc/ERDGSafetyAnalyzer.java` | ERDG-based safety/interference analysis for generated checkers. |
| `Rebeca-Model-Checker-with-Reduction/src/main/resources/vtl/timedrebeca/analyzer/` | Generated exploration and reduction templates. |
| `Rebeca-Model-Checker-with-Reduction/src/main/java/org/rebecalang/rmc/testrebecamodels/Aria-benchmarks/` | Dynamic-component benchmark models. |

## Evaluation and limitations

The original paper's Table 1 reports static-ARIA results on 11 benchmarks. These are historical paper results, not measurements of the completed journal extension. Static ARIA achieves **36% to 74%** state-space reduction across these benchmarks.

The development notes report NEVER pruning on selected journal case studies and a 16-model graph comparison. These observations should be reproduced with labeled baselines before presenting journal evaluation claims. Unchanged graphs alone do not prove preservation of verification outcomes.

For reproducible comparisons, record model version, priorities, exploration semantics, reduction flags, stopping criteria, states, transitions, time, and memory. Search order affects counts when verification stops at the first violation. Static parsing support also differs from the precision of guard analysis: modified variables, environment/local identifiers, arrays, sender-based expressions, and loops can remain conservative or incomplete.

## Validation of this snapshot

A smoke check using the supplied prebuilt RMC JAR generated and compiled BankTransfer with `--aria`, then reported a deadlock after reaching 3,388 states and 19,381 transitions. This checks that supplied binary workflow only; it does not establish that the JAR matches the current source or reproduce the paper evaluation. C++ compilation emitted warnings. Fresh Maven builds were not performed because Maven was unavailable in the inspection environment.

## Development priorities

- Connect conditional-analysis export to the dynamic generator.
- Resolve supported conditional accesses against exploration state.
- Account for future flippers and cycle conditions.
- Check preservation of deadlock, assertion, and queue-overflow results.
- Improve analysis precision and publish reproducible journal benchmarks.

## Related paper

Zeinab Hosseini, Fatemeh Ghassemi, and Hossein Hojjat. *Causal-Aware Partial-Order Reduction for Actor Models.*

The supplied paper identifies the original artifact as [aria-model-checker](https://github.com/zeinabhosseinii/aria-model-checker). Add the final proceedings metadata and citation identifier when confirmed.

## Licensing

Preserve the existing component and third-party license notices. `Rebeca-Model-Checker-with-Reduction/LICENSE` contains GNU GPL version 2, and `ARIA/Modere/LICENSE` also contains an upstream license. ARIA's supplied README states MIT, but a separate top-level ARIA license file was not present in the supplied archive. A single license for the entire combined project is not asserted here.
