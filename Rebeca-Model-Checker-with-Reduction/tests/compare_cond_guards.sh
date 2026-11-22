#!/usr/bin/env bash
set -euo pipefail
rmc_root=$(cd "$(dirname "$0")/.." && pwd)
if [[ "$(uname -s)" == Darwin ]]; then
  export JAVA_HOME=$(/usr/libexec/java_home -v 17)
  export PATH="$JAVA_HOME/bin:$PATH"
fi
cd "$rmc_root/../ARIA"
mvn package -DskipTests
ARIA_PRUNE=1 ARIA_EXPORT=1 java -jar target/erdg-tool-0.1.0.jar file benchmarks/SlotGuard.rebeca
cd "$rmc_root"
mvn package -P executable -DskipTests
classes=$(mktemp -d)
trap 'rm -rf "$classes"' EXIT
javac -cp target/rmc-2.14.jar -d "$classes" tests/AriaGuardEvaluatorTest.java tests/AriaGuardAudit.java
java -cp "target/rmc-2.14.jar:$classes" AriaGuardEvaluatorTest
python3 tests/validate_guard_audit.py --classpath "$rmc_root/target/rmc-2.14.jar:$classes"
