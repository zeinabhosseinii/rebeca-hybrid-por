#!/usr/bin/env bash
set -euo pipefail
rmc_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$rmc_root"
if [[ "$(uname -s)" == Darwin ]]; then
  export JAVA_HOME=$(/usr/libexec/java_home -v 17)
  export PATH="$JAVA_HOME/bin:$PATH"
fi
mvn package -P executable -DskipTests
for model in PassiveSendIndependent PassiveSendSharedQueue; do
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
for model in ('PassiveSendIndependent','PassiveSendSharedQueue'):
    for mode in ('baseline','aria'):
        directory=Path('tmp')/(model+'_'+mode)
        report=ET.parse(directory/'report.xml').getroot()
        outcome=report.findtext('checked-property/result')
        states=report.findtext('system-info/reached-states')
        if outcome!='deadlock' or not report.findall('counter-example-trace/state'):
            raise SystemExit(f'FAIL: {model}/{mode} must stop with a deadlock trace')
        print(f'{model}/{mode}: {outcome}, states={states}')
    log=(Path('tmp')/(model+'_aria')/'errors.log').read_text()
    accepted='POR_PASSIVE_SEND_ACTION' in log
    if accepted!=(model=='PassiveSendIndependent'):
        raise SystemExit(f'FAIL: unexpected passive-send certificate decision for {model}')
print('PASS: disjoint passive sends accepted; shared queues reject; deadlocks stop both modes')
PY
