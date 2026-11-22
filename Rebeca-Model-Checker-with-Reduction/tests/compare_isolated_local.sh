#!/usr/bin/env bash
set -euo pipefail
rmc_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$rmc_root"
if [[ "$(uname -s)" == Darwin ]]; then
  export JAVA_HOME=$(/usr/libexec/java_home -v 17)
  export PATH="$JAVA_HOME/bin:$PATH"
fi
mvn package -P executable -DskipTests
for model in IsolatedLocalIndependent IsolatedLocalConflict; do
  for mode in baseline aria; do
    run_dir="$rmc_root/tmp/${model}_${mode}"
    set -- -jar target/rmc-2.14.jar -s "$rmc_root/tests/fixtures/$model.rebeca" -e TIMED_REBECA -v 2.3 -o "$run_dir"
    if [[ "$mode" == aria ]]; then set -- "$@" --aria; fi
    java "$@"
    (
      cd "$run_dir"
      g++ -std=c++11 -pthread -O2 -DPOR_DIAGNOSTICS *.cpp -o execute 2>compile.log
      ./execute >report.xml 2>errors.log
    )
  done
done
python3 - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET
for model in ('IsolatedLocalIndependent','IsolatedLocalConflict'):
    results={}
    for mode in ('baseline','aria'):
        directory=Path('tmp')/(model+'_'+mode)
        report=ET.parse(directory/'report.xml').getroot()
        result=report.findtext('checked-property/result')
        states=int(report.findtext('system-info/reached-states'))
        trace=report.findall('counter-example-trace/state')
        if result!='deadlock' or not trace:raise SystemExit(f'FAIL: {model}/{mode} must stop with a deadlock trace')
        results[mode]=states
        print(f'{model}/{mode}: {result}, states={states}, trace states={len(trace)}')
    log=(Path('tmp')/(model+'_aria')/'errors.log').read_text()
    accepted='POR_LOCAL_ACTION' in log
    if model=='IsolatedLocalIndependent':
        if not accepted or results['aria']>=results['baseline']:raise SystemExit('FAIL: positive local action was not selected')
    elif accepted:raise SystemExit('FAIL: conflicting actions received a certificate')
print('PASS: distinct local actions reduced online; conflicts fall back; deadlocks stop both runs')
PY
