# ARIA: Actor-based Reduction via Independence Analysis

Static priority assignment for Rebeca actor models via the Essential Rebeca Dependency Graph (ERDG). Produces `@priority`-annotated models that Afra consumes directly for priority-guided state-space exploration.

Based on: *Causal-Aware Partial-Order Reduction for Actor Models* — Hosseini, Ghassemi, Hojjat (2026).

---

## How it works

ARIA runs a five-step pipeline:

1. Parse the Rebeca model with an ANTLR4 grammar and extract per-instance state variable accesses and send statements.
2. Build the ERDG — four node sets (rebecs, message servers, activations, variables) and six edge types encoding causal and data-flow structure.
3. Detect **SDI** (Shared Destination Interference): two rebecs are dependent iff they send causally-independent messages to a shared destination whose handlers have **SVI** (Shared Variable Interference).
4. Partition rebecs into interference groups, build the Hierarchical Rebec Graph (HRG), and assign global actor priorities via topological sort.
5. Assign intra-rebec message server priorities from the SVI partition, then write `@priority` annotations into the output model.

State-space reductions of **33–64%** across nine benchmarks, with all property violations preserved (deadlock, queue overflow, assertion correctness).

---

## Requirements

- Java 17+, Maven 3.8+, Graphviz

```bash
brew install openjdk@17 maven graphviz
```

---

## Usage

```bash
mvn clean compile
./run.sh file benchmarks/BankTransfer.rebeca   # run a single model
./run.sh run BankTransfer                       # run a registered benchmark
./run.sh run-all                                # run all benchmarks
./run.sh list                                   # list registered benchmarks
```

Output goes to `output/<ModelName>/`:

| File | Description |
|------|-------------|
| `<ModelName>_annotated.rebeca` | priority-annotated model for Afra |
| `ERDG.png` | Essential Rebeca Dependency Graph |
| `RIG.png` | Rebec Interference Graph |
| `HRG.png` | Hierarchical Rebec Graph |

---

## Benchmarks

| Benchmark | Full | Ours | Reduction | Bug |
|-----------|:----:|:----:|:---------:|-----|
| TicketService (2 customers) | 34 | 18 | 33% | Deadlock |
| TicketService (3 customers) | 126 | 45 | 64% | Deadlock |
| BankTransfer | 5,026 | 2,381 | 52% | Deadlock |
| ResourceManager | 143,978 | 46,759 | 67% | — |
| LoadBalancer | 992 | 362 | 63% | — |
| SlotGuard | 3,521,765 | 919,634 | 74% | — |
| GradientSync | 1,313 | 584 | 55% | Queue Overflow |
| ImageProcessor | 1,144 | 660 | 42% | Queue Overflow |
| RequestPipeline | 2,214 | 1,091 | 50% | Assertion Violation |
| AsyncStreamBench | 7,588 | 4,820 | 36% | Assertion Violation |

---

## Adding a benchmark

Place a `.rebeca` file in `benchmarks/` and run it directly with `./run.sh file`. To register it for `./run.sh run <name>`:

```bash
python3 << 'PYEOF'
import json
with open('benchmarks/benchmarks.json', 'r') as f:
    data = json.load(f)
with open('benchmarks/MyModel.rebeca', 'r') as f:
    model = f.read()
data['benchmarks'].append({"name": "MyModel", "description": "...", "model": model})
with open('benchmarks/benchmarks.json', 'w') as f:
    json.dump(data, f, indent=2)
PYEOF
```

---

## Full verification workflow

```bash
# 1. generate priority assignment
./run.sh file benchmarks/MyModel.rebeca
# → output/MyModel/MyModel_annotated.rebeca

# 2. generate C++ state-space explorer via RMC
cd ~/Desktop/org.rebecalang.rmc
export JAVA_HOME=/opt/homebrew/Cellar/openjdk@17/.../Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
./run-rmc.sh -s /path/to/MyModel_annotated.rebeca -e TIMED_REBECA -v 2.3 -x -o ./tmp/MyModel

# 3. compile and explore
g++ -std=c++11 -pthread -O2 ./tmp/MyModel/*.cpp -o execute
./execute -x statespace.xml
```

---

## Supported syntax

Standard Core Rebeca plus: `abstract reactiveclass`/`extends`, `abstract msgsrv`, `?(a,b)` nondeterminism, `(Type)cast`, `sender`/`instanceof`, `int[5]` arrays, `for`/`while`/`break`/`continue`, `assertion(...)`, `env` declarations, `after`/`deadline` (Timed Rebeca), `//` and `/* */` comments.

---

## License

MIT

## Action dependency export

Run `ARIA_EXPORT=1 ./run.sh file benchmarks/SlotGuard.rebeca` to write
`output/SlotGuard/SlotGuard_conditional.json`. With `ARIA_PRUNE=1`, the
output directory is `SlotGuard_pruned`. Exported access lists always omit
accesses classified NEVER by GuardAnalysis.

Schema version 2 adds `actions` and `actionDependencies`. Action IDs are local
to the export and map to an instance and message server. Reachable runtime
message servers are included, constructors are excluded. Every unordered pair,
including the diagonal, has one row. Swap left and right when looking up a pair
in the other direction. Unknown action IDs must retain dependency.

Pair classes are ALWAYS, COND and INDEPENDENT. Same-instance pairs are ALWAYS.
Cross-instance pairs contain shared-destination SVI witnesses after NEVER
pruning. At least one ALWAYS witness makes the pair ALWAYS, otherwise any
witness makes it COND. No witnesses means INDEPENDENT under this SDI relation.
Causal exclusions are deliberately retained conservatively in this export.
This table describes SDI, and the generator must still enforce queue, timing,
property visibility and POR proviso requirements.

Each SVI witness identifies its target instance and conflicting variable, plus
leftSend, rightSend, leftAccess and rightAccess references. An access reference
uses instance, messageServer and a zero-based accessIndex into the exported
(filtered) accesses array. The referenced records contain the condition, class,
arguments and evaluable flag. Witnesses form a disjunction, the four access
conditions within each witness form a conjunction in their respective execution
contexts. Target-handler parameters come from the corresponding SEND arguments.
The target accesses describe later handler execution, so evaluating all four
conditions against the current state is insufficient. Until runtime resolution
accounts for intermediate writes and guard flippers, retain COND dependencies.
Unknown conditions also retain dependency. This export does not itself implement
runtime conditional resolution.

Exports generated through the CLI also contain `sourceSha256`, the SHA-256 of
the input model's UTF-8 source. The RMC `--aria-json` importer requires this hash
to match its source model. Regenerate JSON after any model edit.
