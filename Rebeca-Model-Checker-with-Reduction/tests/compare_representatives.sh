#!/usr/bin/env bash
set -euo pipefail
rmc_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$rmc_root"
if [[ "$(uname -s)" == Darwin ]]; then
  export JAVA_HOME=$(/usr/libexec/java_home -v 17)
  export PATH="$JAVA_HOME/bin:$PATH"
fi
# Generate the static control with the same installed generator used by the
# dynamic controls. Run compare_cycle_barriers.sh first for full/dynamic exports.
python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0,'tests')
from run_cycle_barriers import ROOT,generate,compile_run
from compare_representative_choices import run
static=ROOT/'tmp/RepresentativeChoices/static'
generate(ROOT/'tests/fixtures/LoadBalancerSmall_static22.rebeca','LoadBalancerSmall','baseline',static)
r=compile_run(static,['-DEXPORT_STATE_SPACE'])
if r['result']!='satisfied':raise ValueError(r)
print('Static control:',r,flush=True)
base=ROOT/'tmp/CycleBarriers/LoadBalancerSmall'
run(base/'full',base/'aria_ast',static,ROOT/'tmp/LoadBalancerSmall_representative_choices.json')
PY
