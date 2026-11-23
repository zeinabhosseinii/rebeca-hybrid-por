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
python3 tests/experiment_ast_property_representatives.py --full "tmp/CellPropertyReference_$run_stamp" --build-full --output "tmp/CellPropertyAst_$run_stamp"
python3 tests/check_property_ast_metadata.py --output "tmp/CellPropertyAstChecks_$run_stamp"
python3 -m unittest discover -s tests -p test_property_representatives.py
