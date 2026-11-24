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
python3 tests/check_unused_parameter_refusals.py --output "tmp/FixedParameterAst_$run_stamp"
python3 tests/validate_fixed_parameters.py --output "tmp/FixedParameters_$run_stamp"
if [[ "${1:-}" == --benchmark ]]; then
  python3 tests/benchmark_fixed_parameters.py --validation "tmp/FixedParameters_$run_stamp" --output "tmp/FixedParameterBenchmark_$run_stamp" --repeats 5
fi
