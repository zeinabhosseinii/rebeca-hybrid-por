#!/usr/bin/env bash
set -euo pipefail
rmc_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$rmc_root"
# Optional reuse is for already regenerated sources, not a substitute for a build.
if [[ "${1:-}" != --reuse-generated ]]; then
  POR_DIAGNOSTICS=1 bash tests/compare_loadbalancer.sh
fi
bash tests/run_action_por_reference.sh
python3 tests/compare_loadbalancer_scheduling.py --output tmp/LoadBalancerSmall_post_quiescence_scheduling
python3 tests/audit_hub_alternatives.py
python3 tests/test_online_por_audit.py
python3 tests/audit_online_por.py
(
  cd tmp/LoadBalancerSmall_aria_json
  g++ -std=c++11 -pthread -O2 -DPOR_DIAGNOSTICS -DEXPORT_STATE_SPACE *.cpp -o execute-audit 2>compile-audit.log
  ./execute-audit >report.xml 2>errors.log
)
python3 tests/audit_online_por.py --online tmp/LoadBalancerSmall_aria_json --output tmp/LoadBalancerSmall_online_certificate_json.json
python3 - <<'PY'
import json
from pathlib import Path
r=json.loads(Path('tmp/LoadBalancerSmall_hub_audit.json').read_text())
if any(len(set(q['messages']))>1 for q in r['online_multi_message_hub_queues']):
    raise SystemExit('FAIL: unexpected distinct pending Hub messages')
if r['hub_branches']:raise SystemExit('FAIL: unexpected distinct Hub choice in current 27-state run')
if len(r['full_hub_branches'])!=3:raise SystemExit('FAIL: unexpected full-graph Hub branch count')
if any(not c['certified'] for b in r['full_hub_branches'] for c in b['certificates'].values()):
    raise SystemExit('FAIL: full-graph persistence check failed')
if not any(e['event']=='POR_ALTERNATIVE' for e in r['online_execution_diagnostics']):
    raise SystemExit('FAIL: regenerate with current alternative logging before reusing sources')
controls={e['experiment']:e for e in r['policy_controls']}
if (controls['dynamic_original']['states'],controls['dynamic_original']['transitions'])!=(27,32):
    raise SystemExit('FAIL: dynamic control changed')
if (controls['dynamic_method_priorities']['states'],controls['dynamic_method_priorities']['transitions'])!=(27,32):
    raise SystemExit('FAIL: unexpected Hub-priority effect')
print('PASS: no online distinct Hub choice; full graph has 3 certified choices; Hub priorities retain 27/32')
print('These are diagnostics; no online action reduction or priority policy was installed.')
PY
