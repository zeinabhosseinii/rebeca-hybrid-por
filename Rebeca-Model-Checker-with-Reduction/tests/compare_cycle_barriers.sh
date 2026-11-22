#!/usr/bin/env bash
set -euo pipefail
rmc_root=$(cd "$(dirname "$0")/.." && pwd)
if [[ "$(uname -s)" == Darwin ]]; then
  export JAVA_HOME=$(/usr/libexec/java_home -v 17)
  export PATH="$JAVA_HOME/bin:$PATH"
fi
cd "$rmc_root/../ARIA"
mvn package -DskipTests
cd "$rmc_root"
mvn package -P executable -DskipTests
python3 tests/test_cycle_barrier_reference.py
python3 tests/validate_cycle_barrier.py
python3 tests/validate_action_trial.py
python3 tests/test_online_por_audit.py
classes=$(mktemp -d)
trap 'rm -rf "$classes"' EXIT
javac -cp target/rmc-2.14.jar -d "$classes" tests/QuiescenceCertificateTest.java tests/FullBarrierGateTest.java
java -cp "target/rmc-2.14.jar:$classes" FullBarrierGateTest
python3 tests/run_cycle_barriers.py
# Future-time, terminating-feedback and assertion cases retain their outcomes.
python3 tests/run_quiescence_models.py --models QuiescenceFuturePending QuiescenceTerminates QuiescenceAssertion
