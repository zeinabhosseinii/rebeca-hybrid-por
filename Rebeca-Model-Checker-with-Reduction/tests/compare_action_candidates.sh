#!/usr/bin/env bash
set -euo pipefail
rmc_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$rmc_root"
if [[ "$(uname -s)" == Darwin ]]; then
  export JAVA_HOME=$(/usr/libexec/java_home -v 17)
  export PATH="$JAVA_HOME/bin:$PATH"
fi
POR_DIAGNOSTICS=1 EXPORT_STATE_SPACE=1 bash tests/compare_loadbalancer.sh
python3 tests/validate_action_candidates.py
python3 tests/test_action_candidate_audit.py
python3 tests/validate_action_trial.py
python3 tests/validate_isolated_local.py
python3 tests/validate_passive_send.py
bash tests/run_action_por_reference.sh
for mode in aria_ast aria_json; do
  python3 tests/audit_online_por.py --online "tmp/LoadBalancerSmall_$mode" --output "tmp/action_semantics_$mode.json"
done
bash tests/compare_isolated_local.sh
bash tests/compare_passive_send.sh
for mode in baseline aria; do
  directory="$rmc_root/tmp/ActionParameterAlternatives_$mode"
  set -- -jar target/rmc-2.14.jar -s tests/fixtures/ActionParameterAlternatives.rebeca -e TIMED_REBECA -v 2.3 -o "$directory"
  if [[ "$mode" == aria ]]; then set -- "$@" --aria; fi
  java "$@"
  (
    cd "$directory"
    g++ -std=c++11 -pthread -O2 -DPOR_DIAGNOSTICS *.cpp -o execute 2>compile.log
    ./execute >report.xml 2>errors.log
  )
done
python3 tests/audit_action_candidates.py tmp/LoadBalancerSmall_aria_ast tmp/LoadBalancerSmall_aria_json \
  tmp/IsolatedLocalIndependent_aria tmp/IsolatedLocalConflict_aria \
  tmp/PassiveSendIndependent_aria tmp/PassiveSendSharedQueue_aria tmp/ActionParameterAlternatives_aria
python3 - <<'PY'
import json
from pathlib import Path
import xml.etree.ElementTree as E
r=json.loads(Path('tmp/action_candidate_decisions.json').read_text())
for mode in ('aria_ast','aria_json'):
    row=r['LoadBalancerSmall_'+mode]
    if row['accepted_scopes']!={'action':25}:raise SystemExit('FAIL: unexpected LoadBalancer action choices')
    report=E.parse('tmp/LoadBalancerSmall_'+mode+'/report.xml').getroot()
    if (report.findtext('system-info/reached-states'),report.findtext('system-info/reached-transitions'))!=('27','32'):
        raise SystemExit('FAIL: unexpected LoadBalancer graph counts')
for case in ('IsolatedLocalConflict','PassiveSendSharedQueue'):
    if not r[case+'_aria']['accepted_scopes'].get('actor_union'):raise SystemExit('FAIL: unsupported splitting was hidden')
for mode in ('baseline','aria'):
    report=E.parse('tmp/ActionParameterAlternatives_'+mode+'/report.xml').getroot()
    if report.findtext('checked-property/result')!='deadlock' or not report.findall('counter-example-trace/state'):
        raise SystemExit('FAIL: parameter fixture must stop on the first deadlock')
first=r['ActionParameterAlternatives_aria']['states']['1']['representatives'][0]
if first['scope']!='action' or int(first['alternatives'])!=2 or len(first['executed'])!=2:
    raise SystemExit('FAIL: distinct parameter frames were lost')
print('PASS: explicit action selection, retained parameter branches, visible actor fallback, finite semantic checks and first-deadlock stopping')
PY
