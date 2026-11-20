#!/usr/bin/env bash
set -euo pipefail
rmc_root=$(cd "$(dirname "$0")/.." && pwd)
project_root=$(cd "$rmc_root/.." && pwd)
if [[ "$(uname -s)" == Darwin ]]; then
  export JAVA_HOME=$(/usr/libexec/java_home -v 17)
  export PATH="$JAVA_HOME/bin:$PATH"
fi
cd "$project_root/ARIA"
mvn package -DskipTests
ARIA_PRUNE=1 ARIA_EXPORT=1 java -jar target/erdg-tool-0.1.0.jar file benchmarks/LoadBalancerSmall.rebeca
cd "$rmc_root"
mvn package -P executable -DskipTests
model_path="$project_root/ARIA/benchmarks/LoadBalancerSmall.rebeca"
annotated_path="$project_root/ARIA/output/LoadBalancerSmall_pruned/LoadBalancerSmall_annotated.rebeca"
json_path="$project_root/ARIA/output/LoadBalancerSmall_pruned/LoadBalancerSmall_conditional.json"
for run_mode in baseline static aria_ast aria_json; do
  run_dir="$rmc_root/tmp/LoadBalancerSmall_$run_mode"
  source_path="$model_path"
  if [[ "$run_mode" == static ]]; then source_path="$annotated_path"; fi
  set -- -jar target/rmc-2.14.jar -s "$source_path" -e TIMED_REBECA -v 2.3 -o "$run_dir"
  if [[ "$run_mode" == aria_ast ]]; then set -- "$@" --aria; fi
  if [[ "$run_mode" == aria_json ]]; then set -- "$@" --aria --aria-json "$json_path"; fi
  java "$@"
  (
    cd "$run_dir"
    g++ -std=c++11 -pthread -O2 *.cpp -o execute 2> compile.log
    ./execute > report.xml 2> errors.log
  )
done
python3 - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET
results=[]
for mode in ('baseline','static','aria_ast','aria_json'):
    path=Path('tmp')/('LoadBalancerSmall_'+mode)/'report.xml'
    report=ET.parse(path).getroot()
    result=report.findtext('checked-property/result')
    states=report.findtext('system-info/reached-states')
    transitions=report.findtext('system-info/reached-transitions')
    print(f'{mode}: result={result}, states={states}, transitions={transitions}')
    results.append(result)
    if mode=='baseline' and states!='101':
        print('NOTE: baseline differs from the previously reported 101; check engine/settings before comparing older results.')
if len(set(results))!=1:
    raise SystemExit('FAIL: property outcomes differ')
print('Outcomes agree. Only satisfied runs can be used here as completed-space comparisons; this is not a proof of POR.')
PY
