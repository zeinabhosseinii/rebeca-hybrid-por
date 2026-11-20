# org.rebecalang.rmc

Rebeca Model Checker (RMC) with Partial Order Reduction (POR), Aria's ERDG-based POR, and Symmetry Reduction for Timed Rebeca models.

## Build

Requires JDK 17 (JDK 25+ breaks Lombok).

```bash
mvn package -P executable -DskipTests
```

This produces `target/rmc-2.14.jar`.

## Flags

| Flag | Description |
|------|-------------|
| `-s <file>` | Rebeca model source file (required) |
| `-e TIMED_REBECA` | Extension — always use this for Timed Rebeca |
| `-v 2.3` | Compiler version |
| `-x` | Export state space to `statespace.xml` |
| `-o <dir>` | Output directory for generated C++ files |
| `--por` | Enable Partial Order Reduction (sole-sender safety analysis) |
| `--aria` | Enable Aria's ERDG-based POR (shared-destination interference analysis) |
| `--symm` | Enable Symmetry Reduction |
| `--nosafemode` | Disable array bounds / null checks |
| `--tts` | Use TTS semantics instead of FTTS |

`--por` and `--aria` are mutually exclusive reduction strategies. Either can be combined with `--symm`.

## Running a model

### Step 1 — Generate C++ from a Rebeca model

**No reduction (baseline):**
```bash
java -jar target/rmc-2.14.jar -s <model.rebeca> -e TIMED_REBECA -v 2.3 -x -o <output_dir>
```

**Partial Order Reduction (`--por`):**
```bash
java -jar target/rmc-2.14.jar -s <model.rebeca> -e TIMED_REBECA -v 2.3 -x -o <output_dir> --por
```

**Aria's ERDG-based POR (`--aria`):**
```bash
java -jar target/rmc-2.14.jar -s <model.rebeca> -e TIMED_REBECA -v 2.3 -x -o <output_dir> --aria
```

**Symmetry Reduction (`--symm`):**
```bash
java -jar target/rmc-2.14.jar -s <model.rebeca> -e TIMED_REBECA -v 2.3 -x -o <output_dir> --symm
```

**POR + Symmetry:**
```bash
java -jar target/rmc-2.14.jar -s <model.rebeca> -e TIMED_REBECA -v 2.3 -x -o <output_dir> --por --symm
```

**Aria's POR + Symmetry:**
```bash
java -jar target/rmc-2.14.jar -s <model.rebeca> -e TIMED_REBECA -v 2.3 -x -o <output_dir> --aria --symm
```

### Step 2 — Compile the generated C++

```bash
g++ -std=c++11 -O2 <output_dir>/*.cpp -o execute
```

### Step 3 — Run the model checker

```bash
./execute
```

## Test models

Test models are located in `src/main/java/org/rebecalang/rmc/testrebecamodels/`.

## Import ARIA action dependencies

Generate a fresh schema-v2 JSON with `ARIA_EXPORT=1` from the exact source model
passed to RMC. The export now includes `sourceSha256`. Older exports must be
regenerated. Use the original unannotated model in both commands.

```bash
cd "$HOME/Desktop/rebeca-hybrid-por/ARIA"
mvn clean package
ARIA_PRUNE=1 ARIA_EXPORT=1 ./run.sh file benchmarks/SlotGuard.rebeca
cd ../Rebeca-Model-Checker-with-Reduction
mvn package -P executable -DskipTests
java -jar target/rmc-2.14.jar \
  -s ../ARIA/benchmarks/SlotGuard.rebeca -e TIMED_REBECA -v 2.3 \
  --aria --aria-json ../ARIA/output/SlotGuard_pruned/SlotGuard_conditional.json \
  -o tmp/SlotGuard_json
cd tmp/SlotGuard_json
g++ -std=c++11 -pthread -O2 *.cpp -o execute
./execute
```

`--aria-json` requires `--aria` and FTTS timed model checking. RMC checks the
source hash, instance/class inventory, action names, unique pair IDs and complete
pair coverage before importing. Invalid input aborts generation. The
`ARIA-JSON: loaded ...` message confirms successful import.

The imported table replaces the pairwise SDI matrix embedded in generated C++.
INDEPENDENT pairs map to false. ALWAYS and COND map to true symmetrically.
Actions absent from the export remain dependent. Existing ample-set ordering
and the FTTS proviso still apply. Runtime conditional-guard resolution remains
a separate implementation step.


## FTTS validation and complete terminal exploration

Build with JDK 17 (`JAVA_HOME=$(/usr/libexec/java_home -v 17)` on macOS).
Safe array accesses now use an immediately invoked C++11 lambda with a private
index value. This avoids shared scratch-index writes in array assignments and
also evaluates nested indices exactly once.

ARIA singleton selection conservatively checks the candidate against every
message-server ID of other actors, including future actions. Unknown/omitted
IDs retain dependency. Same-time alternatives for the candidate force full
expansion. This can reduce less than the old queue-head-only check. The BFS
proviso requires every generated successor to be new or open; any closed
successor forces fallback. Earlier comments incorrectly described an existential
check. Successors already generated during failed attempts remain stored, so
transition counts may include repeat attempts. This is not a proof of timed POR:
the exported relation still needs validation for queue ordering, enabling,
timing and property visibility before dynamic guard pruning is trusted.

For finite FTTS models, compile BOTH baseline and ARIA output with:

```bash
g++ -std=c++11 -pthread -O2 -DEXPLORE_ALL_TERMINALS *.cpp -o execute
./execute > full-report.xml
```

This validation mode continues after empty-message terminal successors. It still
reports `deadlock` if terminal transitions were seen; there is no single error
trace in this mode. `<exploration complete="true" .../>` means the work queue
was exhausted. Assertions, overflow and missed deadlines still abort and report
`complete="false"`. Terminal-transition counts include repeated exploration
attempts and are NOT unique terminal-state counts. This mode does not make an
infinite model finite. The usual build without this macro still stops at the
first deadlock and prints its trace. Compare property outcomes after complete
runs; state counts need not match between baseline and POR.

Run `bash tests/compare_slotguard.sh` to build and regenerate both SlotGuard
variants and compare completed reports. A fresh ARIA JSON must already exist.
Reports are saved under `tmp/SlotGuard_full_{baseline,aria}/full-report.xml`.
Run `python3 tests/validate_ftts.py` for the standalone C++ snippet regressions.
