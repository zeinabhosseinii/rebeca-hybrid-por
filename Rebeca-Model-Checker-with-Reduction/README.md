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
