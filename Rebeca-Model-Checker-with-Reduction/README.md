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
