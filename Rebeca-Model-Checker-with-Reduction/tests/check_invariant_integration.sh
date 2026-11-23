#!/usr/bin/env bash
set -euo pipefail
rmc_root=$(cd "$(dirname "$0")/.." && pwd)
if [[ "$(uname -s)" == Darwin ]]; then
  export JAVA_HOME=$(/usr/libexec/java_home -v 17)
  export PATH="$JAVA_HOME/bin:$PATH"
fi
cd "$rmc_root"
mvn package -P executable -DskipTests
run_stamp=$(date +%Y%m%d_%H%M%S)
base="tmp/InvariantIntegration_$run_stamp"
python3 tests/check_counter_invariants.py --output "$base/certificates" --skip-native
mkdir -p "$base/classes"
javac -cp target/rmc-2.14.jar -d "$base/classes" tests/CounterInvariantIntegrationTest.java tests/QuiescenceCertificateTest.java tests/FullBarrierGateTest.java
java -cp "target/rmc-2.14.jar:$base/classes" CounterInvariantIntegrationTest "$base/certificates"
java -cp "target/rmc-2.14.jar:$base/classes" FullBarrierGateTest
java -cp "target/rmc-2.14.jar:$base/classes" QuiescenceCertificateTest
python3 tests/check_scaling_properties.py --output "$base/properties" --export-healthy
python3 tests/validate_invariant_integration.py --cases "$base/certificates" --properties "$base/properties" --output "$base/validation"
