#!/usr/bin/env bash
set -euo pipefail
rmc_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$rmc_root"
if [[ "$(uname -s)" == Darwin ]]; then
  export JAVA_HOME=$(/usr/libexec/java_home -v 17)
  export PATH="$JAVA_HOME/bin:$PATH"
fi
POR_DIAGNOSTICS=1 bash tests/compare_loadbalancer.sh
python3 tests/audit_por_decisions.py tmp/LoadBalancerSmall_aria_ast tmp/LoadBalancerSmall_aria_json
python3 tests/validate_quiescence_runtime.py tmp/LoadBalancerSmall_aria_ast
classes=$(mktemp -d)
trap 'rm -rf "$classes"' EXIT
javac -cp target/rmc-2.14.jar -d "$classes" tests/QuiescenceCertificateTest.java
java -cp "target/rmc-2.14.jar:$classes" QuiescenceCertificateTest
(
  cd tmp/LoadBalancerSmall_aria_ast
  g++ -std=c++11 -pthread -O2 -DPOR_DIAGNOSTICS -DPOR_DISABLE_QUIESCENCE *.cpp -o execute-no-quiescence 2>compile-control.log
  ./execute-no-quiescence > report-control.xml 2>errors-control.log
)
python3 - <<'CHECK'
from pathlib import Path
import xml.etree.ElementTree as ET
root=Path('tmp')
def result(path):
    r=ET.parse(path).getroot()
    return (r.findtext('checked-property/result'), int(r.findtext('system-info/reached-states')),
            int(r.findtext('system-info/reached-transitions')))
for mode, expected in [('baseline', (101,202)), ('static',(22,26)), ('aria_ast',(27,32)), ('aria_json',(27,32))]:
    actual=result(root/('LoadBalancerSmall_'+mode)/'report.xml')
    if actual!=('satisfied',*expected):raise SystemExit(f'FAIL: {mode}: {actual}')
control=result(root/'LoadBalancerSmall_aria_ast/report-control.xml')
if control!=('satisfied',38,46):raise SystemExit(f'FAIL: disabled control {control}')
log=(root/'LoadBalancerSmall_aria_ast/errors.log').read_text()
if 'POR_QUIESCENT_SKIP' not in log:raise SystemExit('FAIL: certificate never used')
print('PASS: full=101/202; static=22/26; AST=JSON=27/32; disabled control=38/46')
CHECK
# These fixtures must continue to stop at the first deadlock with a trace.
bash tests/compare_isolated_local.sh
bash tests/compare_passive_send.sh
