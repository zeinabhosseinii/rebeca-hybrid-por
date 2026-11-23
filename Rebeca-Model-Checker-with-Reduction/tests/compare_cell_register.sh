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
run_stamp=$(date +%Y%m%d_%H%M%S)
python3 tests/compare_cell_register.py --output "tmp/CellRegister_$run_stamp" "$@"
