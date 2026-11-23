#!/usr/bin/env bash
set -euo pipefail
rmc_root=$(cd "$(dirname "$0")/.." && pwd)
if [[ "$(uname -s)" == Darwin ]]; then
  export JAVA_HOME=$(/usr/libexec/java_home -v 17)
  export PATH="$JAVA_HOME/bin:$PATH"
fi
cd "$rmc_root"
mvn package -P executable -DskipTests
mkdir -p target/property-policy-tests
javac -cp target/rmc-2.14.jar -d target/property-policy-tests tests/PropertyMetadataPolicyTest.java
java -cp target/rmc-2.14.jar:target/property-policy-tests PropertyMetadataPolicyTest tests/fixtures/CellRegisterObserved.rebeca tests/fixtures/CellRegisterObserved.property
run_stamp=$(date +%Y%m%d_%H%M%S)
python3 tests/check_property_ast_metadata.py --output "tmp/ProductionPropertyAst_$run_stamp"
python3 tests/validate_property_filter_integration.py --output "tmp/PropertyFilterIntegration_$run_stamp"
python3 -m unittest discover -s tests -p test_property_representatives.py
