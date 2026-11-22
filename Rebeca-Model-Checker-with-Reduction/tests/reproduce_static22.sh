#!/usr/bin/env bash
set -euo pipefail
rmc_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$rmc_root"
if [[ "$(uname -s)" == Darwin ]]; then
  export JAVA_HOME=$(/usr/libexec/java_home -v 17)
  export PATH="$JAVA_HOME/bin:$PATH"
fi
mvn package -P executable -DskipTests
for mode in baseline static22; do
  model="$rmc_root/../ARIA/benchmarks/LoadBalancerSmall.rebeca"
  if [[ "$mode" == static22 ]]; then model="$rmc_root/tests/fixtures/LoadBalancerSmall_static22.rebeca"; fi
  directory="$rmc_root/tmp/Static22Reproduction/$mode"
  mkdir -p "$directory"
  # Default FTTS; intentionally no --aria or --aria-json in either run.
  java -jar target/rmc-2.14.jar -s "$model" -e TIMED_REBECA -v 2.3 -o "$directory" > "$directory/generation.log" 2>&1
  (
    cd "$directory"
    g++ -std=c++11 -pthread -O2 *.cpp -o execute 2>compile.log
    ./execute >report.xml 2>errors.log
  )
done
python3 - <<'PY'
from pathlib import Path
import hashlib,re,xml.etree.ElementTree as ET
original=Path('../ARIA/benchmarks/LoadBalancerSmall.rebeca')
static=Path('tests/fixtures/LoadBalancerSmall_static22.rebeca')
clean=re.sub(r'^\s*@priority\(\d+\)\s*$','',static.read_text(),flags=re.M)
def nonempty(text):return [line.rstrip() for line in text.splitlines() if line.strip()]
if nonempty(clean)!=nonempty(original.read_text()):raise SystemExit('FAIL: model bodies differ')
for mode,model,expected in [('baseline',original,(101,202)),('static22',static,(22,26))]:
    directory=Path('tmp/Static22Reproduction')/mode
    report=ET.parse(directory/'report.xml').getroot()
    result=report.findtext('checked-property/result')
    counts=tuple(int(report.findtext('system-info/'+tag)) for tag in ('reached-states','reached-transitions'))
    if re.search(r'^\s*#\s*define\s+(?:PO|TTS)\b',(directory/'Config.h').read_text(),re.M):
        raise SystemExit('FAIL: expected FTTS without online POR')
    print(f'{mode}: result={result}, states={counts[0]}, transitions={counts[1]}')
    print(f'  model={model.resolve()}')
    print(f'  SHA256={hashlib.sha256(model.read_bytes()).hexdigest()}')
    if result!='satisfied' or counts!=expected:raise SystemExit(f'FAIL: expected satisfied/{expected}')
print('PASS: same bodies; unannotated FTTS=101/202; frozen static-priority FTTS=22/26')
PY
