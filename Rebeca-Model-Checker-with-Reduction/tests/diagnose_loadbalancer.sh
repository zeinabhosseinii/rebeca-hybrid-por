#!/usr/bin/env bash
set -euo pipefail
rmc_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$rmc_root"
diag_dir="$rmc_root/tmp/LoadBalancerSmall_diagnostics"
mkdir -p "$diag_dir"
if [[ -f tmp/LoadBalancerSmall_aria_json/report.xml ]]; then
  python3 tests/audit_loadbalancer.py > "$diag_dir/before.txt"
fi
POR_DIAGNOSTICS=1 bash tests/compare_loadbalancer.sh > "$diag_dir/comparison.log" 2>&1 || {
  cat "$diag_dir/comparison.log"
  exit 1
}
python3 tests/audit_loadbalancer.py > "$diag_dir/after.txt"
cat "$diag_dir/after.txt"
python3 tests/audit_por_decisions.py tmp/LoadBalancerSmall_aria_ast tmp/LoadBalancerSmall_aria_json --output "$diag_dir/decisions.json"
python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
root=Path('tmp'); destination=root/'LoadBalancerSmall_diagnostics.zip'
with ZipFile(destination,'w',ZIP_DEFLATED) as z:
    for name in ('LoadBalancerSmall_diagnostics','LoadBalancerSmall_audit',
                 'LoadBalancerSmall_baseline','LoadBalancerSmall_static',
                 'LoadBalancerSmall_aria_ast','LoadBalancerSmall_aria_json'):
        for path in (root/name).rglob('*'):
            if path.is_file() and path.suffix in ('.txt','.log','.xml','.csv','.cpp','.h','.json','.md'):
                z.write(path,path.relative_to(root))
print(destination.resolve())
PY
