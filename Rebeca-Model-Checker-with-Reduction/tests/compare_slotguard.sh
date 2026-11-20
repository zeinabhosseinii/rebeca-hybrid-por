#!/usr/bin/env bash
set -euo pipefail
rmc_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$rmc_root"
if [[ "$(uname -s)" == Darwin ]]; then
  export JAVA_HOME=$(/usr/libexec/java_home -v 17)
  export PATH="$JAVA_HOME/bin:$PATH"
fi
mvn clean package -P executable -DskipTests
model_path="$rmc_root/../ARIA/benchmarks/SlotGuard.rebeca"
json_path="$rmc_root/../ARIA/output/SlotGuard_pruned/SlotGuard_conditional.json"
for run_mode in baseline aria; do
  run_dir="$rmc_root/tmp/SlotGuard_full_$run_mode"
  # Positional parameters also support zero extra arguments in macOS Bash 3.2.
  set -- -jar target/rmc-2.14.jar -s "$model_path" -e TIMED_REBECA -v 2.3 -o "$run_dir"
  if [[ "$run_mode" == aria ]]; then
    set -- "$@" --aria --aria-json "$json_path"
  fi
  java "$@"
  (
    cd "$run_dir"
    g++ -std=c++11 -pthread -O2 *.cpp -o execute
    ./execute > full-report.xml 2> full-errors.log
  )
done
python3 - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET
results = []
for mode in ('baseline', 'aria'):
    path = Path('tmp') / ('SlotGuard_full_' + mode) / 'full-report.xml'
    report = ET.parse(path).getroot()
    result = report.findtext('checked-property/result')
    states = report.findtext('system-info/reached-states')
    transitions = report.findtext('system-info/reached-transitions')
    print(f'{mode}: result={result}, states={states}, transitions={transitions} (stops on first error)')
    results.append(result)
if results[0] != results[1]:
    raise SystemExit('FAIL: property outcomes differ')
print('PASS: property outcomes agree. Counts before an error are not full-space sizes.')
PY
